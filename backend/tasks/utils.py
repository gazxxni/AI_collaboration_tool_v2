"""
업무(Task) 자동화 유틸리티
- 상태 자동 연동 (하위 완료 → 상위 자동 완료)
- 날짜 변경 → 하위 자동 조정
- 완료율 계산
"""
from django.db import transaction
from django.db.models import Q
from log.views import create_log


def get_all_subtasks(task):
    """
    재귀적으로 모든 하위 업무 조회
    
    Args:
        task: Task 객체
        
    Returns:
        QuerySet: 모든 하위 업무 (자식, 손자, 증손자...)
    """
    from db_model.models import Task
    
    subtasks = Task.objects.filter(parent_task=task)
    all_subtasks = list(subtasks)
    
    for subtask in subtasks:
        all_subtasks.extend(get_all_subtasks(subtask))
    
    return all_subtasks


def auto_adjust_subtask_dates(parent_task, days_shift, log_user):
    """
    상위 업무 날짜 변경 시 하위 업무 날짜 자동 조정
    
    Args:
        parent_task: 날짜가 변경된 상위 업무
        days_shift: 변경된 일수 (양수: 미래로, 음수: 과거로)
        log_user: 로그 기록할 사용자
        
    Returns:
        int: 업데이트된 하위 업무 수
    """
    from datetime import timedelta
    
    subtasks = get_all_subtasks(parent_task)
    
    if not subtasks:
        return 0
    
    updated_count = 0
    
    with transaction.atomic():
        # 벌크 업데이트로 성능 최적화
        for i in range(0, len(subtasks), 100):  # batch_size=100
            batch = subtasks[i:i+100]
            
            for subtask in batch:
                old_start = subtask.start_date
                old_end = subtask.end_date
                
                subtask.start_date = old_start + timedelta(days=days_shift)
                subtask.end_date = old_end + timedelta(days=days_shift)
                subtask.save(update_fields=['start_date', 'end_date'])
                
                # 로그 기록
                create_log(
                    action="일정 자동 조정",
                    content=f"상위 업무 일정 변경에 따라 자동 조정됨 ({days_shift:+d}일)",
                    user=log_user,
                    task=subtask
                )
                
                updated_count += 1
    
    return updated_count


def auto_update_parent_status(task, log_user):
    """
    하위 업무 상태 변경 시 상위 업무 상태 자동 업데이트 (양방향 전파)
    
    상태 결정 규칙 (우선순위):
    1. 하나라도 "피드백(2)" → 상위 "피드백(2)"
    2. 하나라도 "진행(1)" → 상위 "진행(1)"
    3. 모두 "완료(3)" → 상위 "완료(3)"
    4. 모두 "요청(0)" → 상위 "요청(0)"
    
    Args:
        task: 상태가 변경된 업무
        log_user: 로그 기록할 사용자
        
    Returns:
        list: 자동 업데이트된 상위 업무 task_id 리스트
    """
    STATUS_LABEL = {
        '0': "요청", '1': "진행", '2': "피드백", '3': "완료",
        0: "요청", 1: "진행", 2: "피드백", 3: "완료"
    }
    
    updated_parents = []
    current = task.parent_task
    
    while current:
        siblings = current.sub_tasks.all()
        
        if not siblings.exists():
            # 하위 업무가 없으면 더 이상 전파하지 않음
            break
        
        # 하위 업무들의 상태 분석
        statuses = [str(s.status) for s in siblings]
        
        # ✅ [개선] 상태 결정 로직 (우선순위 기반)
        if '2' in statuses:
            # 하나라도 피드백이면 → 피드백
            new_status = '2'
        elif '1' in statuses:
            # 하나라도 진행이면 → 진행
            new_status = '1'
        elif all(s == '3' for s in statuses):
            # 모두 완료면 → 완료
            new_status = '3'
        elif all(s == '0' for s in statuses):
            # 모두 요청이면 → 요청
            new_status = '0'
        else:
            # 혼재 상황 (요청 + 완료 혼합 등) → 진행으로 처리
            new_status = '1'
        
        # 상태 변경 필요 시 업데이트
        if str(current.status) != new_status:
            old_status = current.status
            current.status = new_status
            current.save(update_fields=['status'])
            
            # 로그 기록
            old_label = STATUS_LABEL.get(old_status, str(old_status))
            new_label = STATUS_LABEL.get(new_status, new_status)
            
            create_log(
                action="업무 상태 변경 (자동)",
                content=f"{old_label} → {new_label}",
                user=log_user,
                task=current
            )
            
            updated_parents.append(current.task_id)
            
            # ✅ [신규] 상위로 계속 전파
            current = current.parent_task
        else:
            # 상태 변경이 없으면 더 이상 전파 중단
            break
    
    return updated_parents


def calculate_subtask_completion_rate(task):
    """
    하위 업무 완료율 계산
    
    Args:
        task: Task 객체
        
    Returns:
        dict: {
            'total': 전체 하위 업무 수,
            'completed': 완료된 하위 업무 수,
            'rate': 완료율 (0-100)
        }
    """
    subtasks = get_all_subtasks(task)
    
    if not subtasks:
        return {'total': 0, 'completed': 0, 'rate': 0}
    
    total = len(subtasks)
    completed = sum(1 for s in subtasks if str(s.status) == '3')
    rate = round((completed / total) * 100) if total > 0 else 0
    
    return {
        'total': total,
        'completed': completed,
        'rate': rate
    }