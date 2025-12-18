from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q, F
from django.contrib.auth.models import AnonymousUser
from db_model.models import Log, TaskManager

# ──────────────────────────────────────────
# ① 프로젝트별 로그 조회 (개선됨)
# ──────────────────────────────────────────
@api_view(["GET"])
def get_project_logs(request, project_id):
    """
    프로젝트와 관련된 모든 로그 조회
    1. Task가 존재하고 해당 프로젝트에 속한 경우
    2. Task가 삭제되었지만 해당 프로젝트의 Task였던 경우
    
    ✅ 개선사항:
    - content__icontains 제거 (성능 문제)
    - TaskManager 기반으로 프로젝트 소속 Task ID 먼저 수집
    - 삭제된 Task도 정확하게 추적
    """
    try:
        # 1. 해당 프로젝트에 속한 모든 Task ID 수집 (현재 + 과거)
        project_task_ids = set(
            TaskManager.objects
            .filter(project_id=project_id)
            .values_list('task_id', flat=True)
        )
        
        # 2. 로그 조회: 해당 Task ID들과 연결된 로그만 가져오기
        logs = (
            Log.objects
            .filter(
                Q(task_id__in=project_task_ids) |  # Task가 있는 경우
                Q(task_id__isnull=True)             # Task가 삭제된 경우도 포함
            )
            .select_related("user", "task")
            .order_by("-created_date")[:100]  # 최신 100개
        )

        data = []
        for log in logs:
            # Task가 삭제되었는지 확인
            task_name = log.task.task_name if log.task else None
            
            # Task가 None이고 content에 스냅샷이 있으면 파싱
            if not task_name and log.content:
                task_name = _parse_task_name_from_snapshot(log.content)
            
            data.append({
                "log_id": log.log_id,
                "created_date": log.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                "action": log.action,
                "content": log.content,
                "user_name": log.user.name if log.user else "알 수 없음",
                "task_name": task_name or "삭제된 업무",
            })
            
        return Response(data, status=200)
        
    except Exception as e:
        print(f"❌ Log Error: {e}")
        return Response({"error": str(e)}, status=500)


def _parse_task_name_from_snapshot(content):
    """
    로그 content에서 업무명 추출
    예: "[task_id=123] 백엔드 API 개발 업무가 삭제됨" → "백엔드 API 개발"
    """
    import re
    match = re.match(r'^\[task_id=\d+\]\s*(.+?)\s*(업무가\s*삭제됨|업무\s*생성)?$', content)
    if match:
        return match.group(1).strip()
    return None


# ──────────────────────────────────────────
# ② 공통 로그 기록 함수 (Service Layer)
# ──────────────────────────────────────────
def create_log(action, content, user=None, task=None, comment=None):
    """
    로그 생성 헬퍼 함수
    
    Args:
        action: 로그 액션 (예: "업무 생성", "상태 변경")
        content: 로그 내용
        user: User 객체 (None 가능)
        task: Task 객체 (None 가능)
        comment: Comment 객체 (None 가능)
    
    Returns:
        Log 객체 또는 None (실패 시)
    
    ✅ 개선사항:
    - AnonymousUser 처리
    - PK 없는 객체 방어 로직
    - 에러 로깅 개선
    """
    # 인증되지 않은 유저(AnonymousUser)는 None으로 처리
    if isinstance(user, AnonymousUser):
        user = None
        
    # user 객체는 있지만 아직 DB에 저장되지 않은 경우 (pk 없음)
    if user and not user.pk:
        user = None

    try:
        return Log.objects.create(
            action=action,
            content=content,
            user=user,
            task=task,
            comment=comment,
        )
    except Exception as e:
        print(f"❌ Failed to create log: {e}")
        print(f"   - action: {action}")
        print(f"   - content: {content}")
        return None