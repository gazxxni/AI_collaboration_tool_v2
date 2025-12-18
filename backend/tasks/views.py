import logging
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.authentication import SessionAuthentication

from db_model.models import Task, User, Project, FavoriteProject, TaskManager, File
from log.views import create_log
from .serializers import TaskSerializer, TaskNameSerializer, TaskManagerSerializer
from comments.serializers import FileSerializer

from .utils import (
    auto_adjust_subtask_dates,
    auto_update_parent_status,
    calculate_subtask_completion_rate
)

logger = logging.getLogger(__name__)

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """CSRF 검증을 건너뛰는 세션 인증 클래스"""
    def enforce_csrf(self, request):
        return

def get_log_user(request):
    """현재 요청을 보낸 사용자 객체 반환"""
    if request.user.is_authenticated:
        return request.user
    
    uid = request.data.get("user") or request.query_params.get("user") or request.session.get("user_id")
    if uid:
        return User.objects.filter(pk=uid).first()
    return None

def cascade_complete(task, log_user, status_label_map):
    """하위 업무가 모두 완료되면 상위 업무도 자동으로 완료 처리"""
    parent = task.parent_task
    while parent:
        if parent.sub_tasks.exclude(status='3').exists():
            break
        
        if parent.status != '3':
            old_status = parent.status
            parent.status = '3'
            parent.save(update_fields=["status"])

            create_log(
                action="업무 상태 변경 (자동)",
                content=f"{status_label_map.get(old_status, old_status)} → 완료",
                user=log_user,
                task=parent
            )
            parent = parent.parent_task
        else:
            break

class TaskViewSet(viewsets.ModelViewSet):
    """업무(Task) CRUD 및 상태 관리 ViewSet"""
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = []
    pagination_class = None
    lookup_field = 'task_id'
    
    STATUS_LABEL = {
        '0': "요청", '1': "진행", '2': "피드백", '3': "완료",
        0: "요청", 1: "진행", 2: "피드백", 3: "완료"
    }

    # backend/tasks/views.py - get_queryset() 개선

    def get_queryset(self):
        queryset = Task.objects.all()
        
        # 상세 조회/수정/삭제 시 필터링 건너뛰기
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return queryset

        # 안전장치: URL 파라미터에 task_id 또는 pk가 있어도 필터링 건너뜀
        if 'task_id' in self.kwargs or 'pk' in self.kwargs:
            return queryset

        # ──────────────────────────────────────────
        # ✅ [개선] 쿼리 파라미터 추출
        # ──────────────────────────────────────────
        project_id = (
            self.kwargs.get('project_id') or 
            self.request.query_params.get('project_id') or 
            self.request.session.get('project_id')
        )
        
        # 검색어 (업무명 + 설명)
        search = self.request.query_params.get('search', '').strip()
        
        # 담당자 필터 (쉼표로 구분된 다중 선택)
        assignees = self.request.query_params.get('assignees', '').strip()
        
        # 상태 필터 (쉼표로 구분된 다중 선택)
        statuses = self.request.query_params.get('statuses', '').strip()
        
        # 날짜 범위 필터
        start_after = self.request.query_params.get('start_after', '').strip()
        end_before = self.request.query_params.get('end_before', '').strip()
        
        # 정렬 기준
        ordering = self.request.query_params.get('ordering', '-created_date')
        
        # ──────────────────────────────────────────
        # ✅ [필터 적용]
        # ──────────────────────────────────────────
        if project_id:
            queryset = queryset.filter(taskmanager__project_id=project_id).distinct()
        
        # 검색어 필터 (업무명 OR 설명)
        if search:
            queryset = queryset.filter(
                Q(task_name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # 담당자 필터 (다중 선택)
        if assignees:
            assignee_list = [a.strip() for a in assignees.split(',') if a.strip()]
            if assignee_list:
                queryset = queryset.filter(
                    taskmanager__user__name__in=assignee_list
                ).distinct()
        
        # 상태 필터 (다중 선택)
        if statuses:
            status_list = [s.strip() for s in statuses.split(',') if s.strip()]
            if status_list:
                queryset = queryset.filter(status__in=status_list)
        
        # 날짜 범위 필터
        if start_after:
            queryset = queryset.filter(start_date__gte=start_after)
        
        if end_before:
            queryset = queryset.filter(end_date__lte=end_before)
        
        # ──────────────────────────────────────────
        # ✅ [정렬 적용]
        # ──────────────────────────────────────────
        # 허용된 정렬 기준만 적용 (보안)
        allowed_orderings = [
            'created_date', '-created_date',
            'end_date', '-end_date',
            'start_date', '-start_date',
            'status', '-status',
            'task_name', '-task_name'
        ]
        
        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_date')  # 기본값
        
        return queryset

    def perform_create(self, serializer):
        log_user = get_log_user(self.request)
        if not log_user:
            raise PermissionDenied("로그인이 필요합니다.")

        with transaction.atomic():
            task = serializer.save()
            project_id = self.request.data.get("project_id")
            
            if project_id:
                TaskManager.objects.create(
                    project_id=project_id, 
                    task=task, 
                    user=log_user
                )
                if hasattr(task, 'project_id'):
                    task.project_id = project_id
                    task.save()

            action = "하위 업무 생성" if task.parent_task else "상위 업무 생성"
            create_log(
                action=action,
                content=f"[task_id={task.task_id}] {task.task_name} 생성",
                user=log_user,
                task=task
            )

    def perform_update(self, serializer):
        log_user = get_log_user(self.request)
        if not log_user:
            raise PermissionDenied("로그인이 필요합니다.")

        old_instance = self.get_object()
        old_status = old_instance.status
        old_start = old_instance.start_date
        old_end = old_instance.end_date
        
        task = serializer.save()

        # ──────────────────────────────────────────
        # ✅ [신규] 날짜 변경 감지 → 하위 업무 자동 조정
        # ──────────────────────────────────────────
        if old_start != task.start_date or old_end != task.end_date:
            # 시작일 기준 변경 일수 계산
            days_shift = (task.start_date.date() - old_start.date()).days
            
            if days_shift != 0:
                updated_count = auto_adjust_subtask_dates(task, days_shift, log_user)
                
                if updated_count > 0:
                    logger.info(f"✅ 하위 업무 {updated_count}개 일정 자동 조정 완료 (task_id={task.task_id}, shift={days_shift:+d}일)")

       # ──────────────────────────────────────────
        # ✅ [신규] 상태 변경 감지 → 상위 업무 자동 업데이트
        # ──────────────────────────────────────────
        if str(old_status) != str(task.status):
            old_lbl = self.STATUS_LABEL.get(old_status, str(old_status))
            new_lbl = self.STATUS_LABEL.get(task.status, str(task.status))
            
            create_log(
                action="업무 상태 변경",
                content=f"{old_lbl} → {new_lbl}",
                user=log_user,
                task=task
            )
            
            # 상위 업무 자동 업데이트 (양방향 전파)
            updated_parents = auto_update_parent_status(task, log_user)
            
            if updated_parents:
                logger.info(
                    f"✅ 상위 업무 {len(updated_parents)}개 상태 자동 업데이트 완료\n"
                    f"   - 변경된 업무: task_id={task.task_id} ({old_lbl} → {new_lbl})\n"
                    f"   - 자동 업데이트된 상위: {updated_parents}"
                )

        # 담당자 변경 (기존 로직 유지)
        new_assignee_name = self.request.data.get("assignee")
        if new_assignee_name:
            new_user = User.objects.filter(name=new_assignee_name).first()
            if new_user:
                tm = TaskManager.objects.filter(task=task).first()
                if tm and tm.user != new_user:
                    old_user_name = tm.user.name if tm.user else "없음"
                    tm.user = new_user
                    tm.save()
                    
                    create_log(
                        action="담당자 변경",
                        content=f"{old_user_name} → {new_user.name}",
                        user=log_user,
                        task=task
                    )

    def perform_destroy(self, instance):
        log_user = get_log_user(self.request)
        if not log_user:
            raise PermissionDenied("로그인이 필요합니다.")

        create_log(
            action="업무 삭제",
            content=f"[task_id={instance.task_id}] {instance.task_name} 삭제됨",
            user=log_user,
            task=None
        )
        instance.delete()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_parent_statuses = {}
        
        parent = instance.parent_task
        while parent:
            old_parent_statuses[parent.task_id] = str(parent.status)
            parent = parent.parent_task
        
        # 실제 업데이트 수행 (여기서 perform_update가 호출됨)
        response = super().update(request, *args, **kwargs)
        
        # ✅ [신규] 업데이트 후 상태가 변경된 상위만 추출
        instance.refresh_from_db()
        auto_updated_parents = []
        
        parent = instance.parent_task
        while parent:
            parent.refresh_from_db()
            old_status = old_parent_statuses.get(parent.task_id)
            
            if old_status and str(parent.status) != old_status:
                # 상태가 변경된 상위 업무만 추가
                auto_updated_parents.append(parent.task_id)
            
            parent = parent.parent_task
        
        # ✅ 응답에 자동 업데이트 정보 추가
        if isinstance(response.data, dict):
            response.data['auto_updated'] = {
                'parents': auto_updated_parents
            }
        
        return response


@api_view(['POST', 'DELETE'])
def toggle_favorite_project(request, user_id, project_id):
    user = get_object_or_404(User, pk=user_id)
    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'POST':
        if FavoriteProject.objects.filter(user=user).count() >= 3:
            return Response({"message": "최대 3개까지만 즐겨찾기 가능합니다."}, status=400)
        
        _, created = FavoriteProject.objects.get_or_create(user=user, project=project)
        return Response(
            {"message": "즐겨찾기 추가됨" if created else "이미 등록됨"},
            status=201 if created else 400
        )

    elif request.method == 'DELETE':
        deleted, _ = FavoriteProject.objects.filter(user=user, project=project).delete()
        if deleted:
            return Response({"message": "즐겨찾기 해제됨"}, status=200)
        return Response({"message": "즐겨찾기 목록에 없습니다."}, status=400)


@api_view(['GET'])
def get_user_projects_with_favorite(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    
    is_fav_subquery = FavoriteProject.objects.filter(
        user=user, project=OuterRef('pk')
    )
    
    projects = Project.objects.filter(
        projectmember__user=user
    ).annotate(
        is_favorite=Exists(is_fav_subquery)
    ).values('project_id', 'project_name', 'is_favorite')

    data = []
    for p in projects:
        data.append({
            "project_id": p['project_id'],
            "project_name": p['project_name'],
            "is_favorite": p['is_favorite'],
            "latest_message_time": None
        })

    if not data:
        return Response({"error": "참여 중인 프로젝트가 없습니다."}, status=404)
        
    return Response({"projects": data})


@api_view(['GET'])
def project_progress(request, user_id, project_id):
    if not ProjectMember.objects.filter(user_id=user_id, project_id=project_id).exists():
        return Response({"error": "팀원이 아닙니다."}, status=404)

    tasks = Task.objects.filter(taskmanager__project_id=project_id).distinct()
    total = tasks.count()
    completed = tasks.filter(status='3').count()
    
    progress = round((completed / total) * 100) if total > 0 else 0

    return Response({
        "project_id": project_id,
        "progress": progress,
        "total_tasks": total,
        "completed_tasks": completed
    })


@api_view(['PATCH'])
def update_task_direct(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    serializer = TaskSerializer(task, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        assignee_name = request.data.get('assignee')
        if assignee_name:
            new_user = User.objects.filter(name=assignee_name).first()
            if new_user:
                TaskManager.objects.update_or_create(
                    task=task,
                    defaults={'user': new_user}
                )
                
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
def get_team_members(request):
    project_id = request.query_params.get('project_id')
    if not project_id:
        return Response({"error": "project_id required"}, status=400)

    members = User.objects.filter(
        projectmember__project_id=project_id
    ).values('user_id', 'name')
    
    return Response(list(members))


@api_view(['PATCH'])
def change_task_name(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    new_name = request.data.get('task_name')
    
    if not new_name:
        return Response({"error": "task_name required"}, status=400)

    old_name = task.task_name
    task.task_name = new_name
    task.save()

    create_log(
        action="업무명 변경",
        content=f"{old_name} → {new_name}",
        user=request.user if request.user.is_authenticated else None,
        task=task
    )
    
    return Response({"task_id": task.task_id, "task_name": new_name})


@api_view(['POST'])
def create_task_manager(request):
    serializer = TaskManagerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
def task_files(request):
    task_id = request.query_params.get('task_id')
    include_children = request.query_params.get('include_children', 'false').lower() == 'true'
    
    if not task_id:
        return Response({"error": "task_id required"}, status=400)

    if include_children:
        target_ids = {int(task_id)}
        current_ids = [int(task_id)]
        
        while current_ids:
            children = list(Task.objects.filter(parent_task_id__in=current_ids).values_list('task_id', flat=True))
            if not children:
                break
            target_ids.update(children)
            current_ids = children
            
        files = File.objects.filter(task_id__in=target_ids).select_related('user').order_by('-created_date')
    else:
        files = File.objects.filter(task_id=task_id).select_related('user').order_by('-created_date')

    return Response(FileSerializer(files, many=True).data)