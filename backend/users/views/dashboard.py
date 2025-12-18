from datetime import date, timedelta
from calendar import monthrange
from django.db.models import Count, Exists, OuterRef, Max, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from db_model.models import (
    User, Project, ProjectMember, FavoriteProject,
    Task, TaskManager, Schedule, Log
)

# ✅ 상태 코드 안전 처리
DONE_STATUS_LIST = ['3', 3]
ACTIVE_STATUS_LIST = ['0', '1', '2', 0, 1, 2]
INCOMPLETE_STATUS_LIST = ['0', '1', 0, 1]
FEEDBACK_STATUS_LIST = ['2', 2]
URGENT_DAYS = 3

def month_bounds(yyyy_mm: str | None):
    """월 시작/종료 날짜 계산"""
    if yyyy_mm:
        try:
            y, m = map(int, yyyy_mm.split('-'))
            first = date(y, m, 1)
        except ValueError:
            t = date.today()
            first = date(t.year, t.month, 1)
    else:
        t = date.today()
        first = date(t.year, t.month, 1)
    last = monthrange(first.year, first.month)[1]
    return first, date(first.year, first.month, last)

class DashboardView(APIView):
    """
    사용자 대시보드 데이터 제공
    - 프로젝트 목록 및 진행률
    - 업무 통계
    - 최근 로그
    - 캘린더 데이터
    """
    def get(self, request, user_id: int):
        session_uid = request.session.get("user_id")
        if not session_uid:
            return Response({"detail": "로그인이 필요합니다."}, status=401)

        month = request.query_params.get('month')
        start_d, end_d = month_bounds(month)
        today = date.today()

        # User 확인
        user_info = User.objects.filter(pk=user_id).values('user_id', 'name').first()
        if not user_info:
            return Response({"detail": "User not found"}, status=404)

        # 1. 프로젝트 데이터 조회
        project_ids = list(
            ProjectMember.objects
            .filter(user_id=user_id)
            .values_list('project_id', flat=True)
        )
        
        if not project_ids:
            # 프로젝트가 없는 경우 빈 데이터 반환
            return Response({
                "user": user_info,
                "projects": [],
                "task_stats": {
                    "my_tasks": 0,
                    "completed_tasks": 0,
                    "incomplete_tasks": 0,
                    "feedback_tasks": 0,
                    "urgent_tasks": 0,
                },
                "recent_logs": [],
                "calendar": {"my": [], "team": []}
            })

        # 즐겨찾기 서브쿼리
        fav_exists = FavoriteProject.objects.filter(
            user_id=user_id, 
            project_id=OuterRef('project_id')
        )
        
        # 프로젝트 기본 정보
        projects_qs = (
            Project.objects
            .filter(project_id__in=project_ids)
            .annotate(is_fav=Exists(fav_exists))
            .values('project_id', 'project_name', 'is_fav')
        )

        # ✅ [개선됨] 프로젝트별 통계를 한 번에 조회
        total_by_project = dict(
            TaskManager.objects
            .filter(project_id__in=project_ids)
            .values('project_id')
            .annotate(cnt=Count('task', distinct=True))
            .values_list('project_id', 'cnt')
        )
        
        done_by_project = dict(
            TaskManager.objects
            .filter(project_id__in=project_ids, task__status__in=DONE_STATUS_LIST)
            .values('project_id')
            .annotate(cnt=Count('task', distinct=True))
            .values_list('project_id', 'cnt')
        )

        active_by_project = dict(
            TaskManager.objects
            .filter(project_id__in=project_ids, task__status__in=ACTIVE_STATUS_LIST)
            .values('project_id')
            .annotate(cnt=Count('task', distinct=True))
            .values_list('project_id', 'cnt')
        )

        deadline_by_project = dict(
            TaskManager.objects
            .filter(project_id__in=project_ids)
            .values('project_id')
            .annotate(deadline=Max('task__end_date'))
            .values_list('project_id', 'deadline')
        )

        # 프로젝트 데이터 조립
        projects_payload = []
        for p in projects_qs:
            pid = p['project_id']
            total = total_by_project.get(pid, 0)
            done = done_by_project.get(pid, 0)
            progress = int((done * 100) / total) if total else 0
            ongoing = active_by_project.get(pid, 0)

            dl = deadline_by_project.get(pid)
            if dl:
                dldate = dl.date() if hasattr(dl, "date") else dl
                remaining_days = (dldate - today).days
            else:
                remaining_days = None

            projects_payload.append({
                "project_id": pid,
                "project_name": p['project_name'],
                "is_favorite": bool(p['is_fav']),
                "progress": progress,
                "ongoing_tasks": ongoing,
                "remaining_days": remaining_days,
            })

        # 2. 내 업무 통계
        my_task_ids = list(
            TaskManager.objects
            .filter(user_id=user_id)
            .values_list('task_id', flat=True)
        )

        if my_task_ids:
            my_tasks_count = Task.objects.filter(task_id__in=my_task_ids).count()
            completed_count = Task.objects.filter(
                task_id__in=my_task_ids, 
                status__in=DONE_STATUS_LIST
            ).count()
            incomplete_count = Task.objects.filter(
                task_id__in=my_task_ids, 
                status__in=INCOMPLETE_STATUS_LIST
            ).count()
        else:
            my_tasks_count = completed_count = incomplete_count = 0

        # 피드백: 프로젝트 내 모든 업무 중 피드백 상태이면서 내가 담당자가 아닌 것
        all_project_task_ids = list(
            TaskManager.objects
            .filter(project_id__in=project_ids)
            .values_list('task_id', flat=True)
        )
        
        feedback_count = Task.objects.filter(
            task_id__in=all_project_task_ids,
            status__in=FEEDBACK_STATUS_LIST
        ).exclude(task_id__in=my_task_ids).count()

        # 긴급 업무: 마감 D-3 이내
        urgent_end = today + timedelta(days=URGENT_DAYS)
        urgent_count = Task.objects.filter(
            task_id__in=my_task_ids,
            status__in=ACTIVE_STATUS_LIST,
            end_date__date__range=(today, urgent_end)
        ).count()

        task_stats = {
            "my_tasks": my_tasks_count,
            "completed_tasks": completed_count,
            "incomplete_tasks": incomplete_count,
            "feedback_tasks": feedback_count,
            "urgent_tasks": urgent_count,
        }

        # 3. 최근 로그 (프로젝트별로 필터링)
        recent_logs_qs = (
            Log.objects
            .filter(task_id__in=all_project_task_ids)
            .select_related('user', 'task')
            .order_by('-created_date')[:20]
        )
        
        recent_logs = [{
            "user_name": (log.user.name if log.user else "알 수 없음"),
            "action": log.action,
            "created_date": log.created_date,
            "task_name": (log.task.task_name if log.task else None),
            "content": (log.content or "")
        } for log in recent_logs_qs]

        # 4. 캘린더 데이터
        my_calendar_qs = Schedule.objects.filter(
            user_id=user_id, 
            start_time__range=(start_d, end_d)
        ).values('schedule_id', 'start_time', 'title')
        
        my_calendar = [
            {
                "date": r['start_time'], 
                "schedule_id": r['schedule_id'], 
                "title": r['title']
            } 
            for r in my_calendar_qs
        ]

        team_calendar_qs = Task.objects.filter(
            task_id__in=all_project_task_ids, 
            end_date__date__range=(start_d, end_d)
        ).values('task_id', 'task_name', 'end_date')
        
        team_calendar = [
            {
                "date": r['end_date'], 
                "task_id": r['task_id'], 
                "task_name": r['task_name']
            } 
            for r in team_calendar_qs
        ]

        return Response({
            "user": user_info,
            "projects": projects_payload,
            "task_stats": task_stats,
            "recent_logs": recent_logs,
            "calendar": {"my": my_calendar, "team": team_calendar}
        })


class TaskDetailsView(APIView):
    """
    업무 상세 조회 (모달용)
    - my: 내 모든 업무
    - incomplete: 미완료 업무
    - feedback: 피드백 필요
    - completed: 완료된 업무
    - urgent: 긴급 업무 (D-3 이내)
    """
    def get(self, request):
        session_uid = request.session.get("user_id")
        if not session_uid:
            return Response({"detail": "로그인이 필요합니다."}, status=401)

        t = request.query_params.get('type')
        
        # 내가 담당한 업무 ID
        my_task_ids = list(
            TaskManager.objects
            .filter(user_id=session_uid)
            .values_list('task_id', flat=True)
        )
        
        if not my_task_ids:
            return Response({"total": 0, "tasks": []})

        qs = Task.objects.filter(task_id__in=my_task_ids)

        # 타입별 필터링
        if t == 'my':
            pass  # 모든 업무
        elif t == 'incomplete':
            qs = qs.filter(status__in=INCOMPLETE_STATUS_LIST)
        elif t == 'feedback':
            qs = qs.filter(status__in=FEEDBACK_STATUS_LIST)
        elif t == 'completed':
            qs = qs.filter(status__in=DONE_STATUS_LIST)
        elif t == 'urgent':
            today = date.today()
            urgent_end = today + timedelta(days=URGENT_DAYS)
            qs = qs.filter(
                status__in=ACTIVE_STATUS_LIST, 
                end_date__date__range=(today, urgent_end)
            )
        
        # 데이터 조회
        task_list = list(
            qs.order_by('end_date')
            .values('task_id', 'task_name', 'status', 'end_date')
        )
        
        if not task_list:
            return Response({"total": 0, "tasks": []})

        # 프로젝트명 매핑 (한 번에 조회)
        tm_rows = TaskManager.objects.filter(
            task_id__in=[x['task_id'] for x in task_list]
        ).select_related('project').values('task_id', 'project__project_name')
        
        project_map = {
            r['task_id']: r['project__project_name'] 
            for r in tm_rows
        }

        # 결과 조립
        results = []
        for item in task_list:
            results.append({
                "task_id": item['task_id'],
                "task_name": item['task_name'] or "제목 없음",
                "status": item['status'],
                "status_code": item['status'],
                "end_date": item['end_date'],
                "project_name": project_map.get(item['task_id'], "-"),
            })

        return Response({"total": len(results), "tasks": results})