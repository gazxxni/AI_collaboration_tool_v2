import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from db_model.models import Log, TaskManager, Project, FavoriteProject, ProjectMember

MAX_FAVORITES = 3

# ==========================================
# 프로젝트 세션 데이터 관리 (General에서 이동됨)
# ==========================================
@csrf_exempt
def receive_project_data(request):
    """최신 생성 프로젝트 ID 세션 저장"""
    if request.method == "POST":
        data = json.loads(request.body)
        project_id = data.get("project_id")
        request.session['latest_project_id'] = project_id
        request.session.modified = True
        return JsonResponse({"message": "Project ID saved", "project_id": project_id})
    return JsonResponse({"error": "POST only"}, status=405)

@csrf_exempt
def get_latest_project_id(request):
    """최신 생성 프로젝트 ID 조회"""
    project_id = request.session.get('latest_project_id')
    if project_id:
        return JsonResponse({"current_project_id": project_id})
    return JsonResponse({"error": "No project_id"}, status=404)

# ==========================================
# 기존 Project 뷰 클래스
# ==========================================
class ProjectLogsView(APIView):
    def get(self, request, project_id: int):
        session_uid = request.session.get("user_id")
        if not session_uid:
            return Response({"detail": "로그인이 필요합니다."}, status=401)

        is_member = ProjectMember.objects.filter(
            user_id=session_uid, project_id=project_id
        ).exists()
        if not is_member:
            return Response({"detail": "권한이 없습니다."}, status=403)

        task_ids = TaskManager.objects.filter(project_id=project_id).values_list('task_id', flat=True)
        logs_qs = (
            Log.objects
              .filter(Q(task_id__in=task_ids))
              .select_related('user', 'task')
              .order_by('-created_date')[:50]
        )

        data = [{
            "user_name":    (log.user.name if log.user else "알 수 없음"),
            "action":       log.action,
            "created_date": log.created_date,
            "task_name":    (log.task.task_name if log.task else None),
            "content":      (log.content or "")
        } for log in logs_qs]
        return Response(data)

class FavoriteToggleView(APIView):
    def post(self, request, user_id: int, project_id: int):
        session_uid = request.session.get("user_id")
        if not session_uid: return Response({"detail": "로그인이 필요합니다."}, status=401)
        # if int(session_uid) != int(user_id): return Response({"detail": "권한이 없습니다."}, status=403)

        if not ProjectMember.objects.filter(user_id=user_id, project_id=project_id).exists():
            return Response({"detail": "멤버가 아닌 프로젝트입니다."}, status=403)

        current_count = FavoriteProject.objects.filter(user_id=user_id).count()
        if current_count >= MAX_FAVORITES:
            return Response({"detail": f"즐겨찾기는 최대 {MAX_FAVORITES}개까지 가능합니다."}, status=400)

        FavoriteProject.objects.get_or_create(user_id=user_id, project_id=project_id)
        return Response({"message": "favorited", "favorited": True})

    def delete(self, request, user_id: int, project_id: int):
        session_uid = request.session.get("user_id")
        if not session_uid: return Response({"detail": "로그인이 필요합니다."}, status=401)
        
        FavoriteProject.objects.filter(user_id=user_id, project_id=project_id).delete()
        return Response({"message": "unfavorited", "favorited": False})

class CurrentProjectGetView(APIView):
    def get(self, request):
        if not request.session.get("user_id"):
            return Response({"detail": "로그인이 필요합니다."}, status=401)
        
        pid = request.session.get('current_project_id')
        user_id = request.session.get('user_id')
        
        data = {
            "project_id": pid,
            "project_name": None,
            "is_favorite": False,
            "user_id": user_id
        }

        if pid:
            try:
                project = Project.objects.get(pk=pid)
                data['project_name'] = project.project_name
                if user_id:
                    data['is_favorite'] = FavoriteProject.objects.filter(user_id=user_id, project=project).exists()
            except Project.DoesNotExist:
                pass
        
        return Response(data, status=status.HTTP_200_OK)

class CurrentProjectSetView(APIView):
    def post(self, request):
        if not request.session.get("user_id"):
            return Response({"detail": "로그인이 필요합니다."}, status=401)

        pid = request.data.get('project_id')
        try:
            pid = int(pid)
        except:
            return Response({"detail": "Invalid project_id"}, status=400)

        if not Project.objects.filter(project_id=pid).exists():
            return Response({"detail": "Project not found"}, status=404)

        request.session['current_project_id'] = pid
        request.session.modified = True
        return Response({"message": "current project set", "project_id": pid})