from datetime import date, timedelta
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response

from db_model.models import (
    User, Project, ProjectMember,
    Task, TaskManager,
    Comment, DirectMessage, DirectMessageRoom, Message
)

# 문자열/숫자 모두 대응
ACTIVE_STATUS_LIST = ['1', '2', 1, 2]
URGENT_DAYS = 3

class NotificationsView(APIView):
    def get(self, request):
        uid = request.session.get("user_id")
        if not uid:
            return Response({"detail": "로그인이 필요합니다."}, status=401)
        uid = int(uid)

        today = date.today()
        urgent_end = today + timedelta(days=URGENT_DAYS)
        recent_since_dt = timezone.now() - timedelta(days=7)

        # 1. 내가 맡은 task id
        my_task_ids = list(TaskManager.objects.filter(user_id=uid).values_list("task_id", flat=True))

        # 매핑 정보 미리 조회 (최적화)
        tm_rows = TaskManager.objects.filter(task_id__in=my_task_ids).values("task_id", "project_id", "project__project_name")
        task_info_map = {
            r["task_id"]: {"pid": r["project_id"], "pname": r["project__project_name"]} 
            for r in tm_rows
        }

        # (1) 긴급 업무
        urgent_qs = Task.objects.filter(
            task_id__in=my_task_ids,
            status__in=ACTIVE_STATUS_LIST,
            end_date__date__range=(today, urgent_end),
        ).values("task_id", "task_name", "end_date", "status")

        urgent_items = []
        for r in urgent_qs:
            tid = r["task_id"]
            info = task_info_map.get(tid, {})
            urgent_items.append({
                "type": "urgent_task",
                "id": tid,
                "title": r["task_name"],
                "due": r["end_date"],
                "status_code": r["status"],
                "created_at": r["end_date"],
                "project_id": info.get("pid"),
                "project_name": info.get("pname"),
            })

        # (2) 내 업무의 최근 댓글
        comment_qs = (Comment.objects
            .filter(task_id__in=my_task_ids, created_date__gte=recent_since_dt)
            .exclude(user_id=uid)
            .select_related("user", "task")
            .order_by("-created_date")[:30])

        comment_items = []
        for c in comment_qs:
            tid = c.task.task_id if c.task else None
            info = task_info_map.get(tid, {})
            comment_items.append({
                "type": "comment",
                "id": c.comment_id,
                "task_id": tid,
                "task_name": c.task.task_name if c.task else None,
                "author_name": c.user.name if c.user else "알 수 없음",
                "content": c.content,
                "created_at": c.created_date,
                "project_id": info.get("pid"),
                "project_name": info.get("pname"),
            })

        # (3) DM (최근 7일)
        room_ids = DirectMessageRoom.objects.filter(Q(user1_id=uid) | Q(user2_id=uid)).values_list("room_id", flat=True)
        dm_qs = (DirectMessage.objects
                .filter(room_id__in=room_ids, created_date__gte=recent_since_dt)
                .exclude(user_id=uid)
                .select_related("user", "room")
                .order_by("-created_date")[:30])

        dm_items = [{
            "type": "dm",
            "id": dm.message_id,
            "room_id": dm.room.room_id,
            "from_name": dm.user.name if dm.user else "알 수 없음",
            "content": dm.content,
            "created_at": dm.created_date,
        } for dm in dm_qs]

        # (4) 그룹 메시지
        my_project_ids = list(ProjectMember.objects.filter(user_id=uid).values_list("project_id", flat=True))
        
        msg_filter = Q(project_id__in=my_project_ids, created_date__gte=recent_since_dt) & ~Q(user_id=uid)
        
        # 멘션 모드 확인
        mode = request.query_params.get("mode")
        if mode == "mentions":
            me_name = User.objects.filter(pk=uid).values_list('name', flat=True).first() or ""
            msg_filter &= (Q(content__icontains=f"@{me_name}") | Q(content__icontains=f"@{uid}"))

        group_msg_qs = (Message.objects
            .filter(msg_filter)
            .select_related("user", "project")
            .order_by("-created_date")[:50])

        group_msg_items = [{
            "type": "group_message",
            "id": m.message_id,
            "project_id": m.project.project_id if m.project else None,
            "project_name": m.project.project_name if m.project else None,
            "from_name": m.user.name if m.user else "알 수 없음",
            "content": m.content,
            "created_at": m.created_date,
        } for m in group_msg_qs]

        # 통합 + 정렬
        items = urgent_items + comment_items + dm_items + group_msg_items
        items.sort(key=lambda x: x["created_at"] or timezone.now(), reverse=True)
        items = items[:30]

        # full=1 요청 처리 (헤더용)
        if request.query_params.get("full") == "1":
            me = User.objects.filter(user_id=uid).values("user_id", "name", "profile_image").first()
            
            current_project = None
            cur_pid = request.session.get("current_project_id")
            if cur_pid:
                current_project = Project.objects.filter(project_id=cur_pid).values("project_id", "project_name").first()
            
            my_projects = list(Project.objects.filter(project_id__in=my_project_ids).values("project_id", "project_name"))
            
            return Response({
                "user": me,
                "current_project": current_project,
                "my_projects": my_projects,
                "notifications": items,
            })

        return Response({"items": items})