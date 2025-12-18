from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from users.views import ProjectLogsView

# 라우터 설정
router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet, basename='task')

urlpatterns = [
    # 1. Router URL (가장 먼저 매치되도록 배치)
    # /api/tasks/, /api/tasks/<id>/ 등이 여기서 처리됨
    path('', include(router.urls)),

    # 2. 팀원 및 파일 관련
    path('team-members/', views.get_team_members, name='get_team_members'),
    path('task-files/', views.task_files, name='task_files'),
    path('tasks/manager/', views.create_task_manager, name='create_task_manager'),
    
    # 3. tasks 하위 경로 중 pk를 포함하는 커스텀 경로는 router보다 뒤에 두거나, 
    # router가 처리하지 못하는 패턴이어야 함.
    # change-name은 /tasks/<id>/change-name/ 이므로 router와 충돌하지 않음.
    path('tasks/<int:task_id>/change-name/', views.change_task_name, name='change_task_name'),
    
    # 4. 프로젝트 관련
    path('projects/<int:project_id>/progress/', views.project_progress, name='project_progress'),

    # 5. 유저별 프로젝트
    path('users/<int:user_id>/projects/', views.get_user_projects_with_favorite, name='get_user_projects'),
    path('users/<int:user_id>/favorites/<int:project_id>/', views.toggle_favorite_project, name='toggle_favorite_project'),

    # 6. 프론트엔드 호환용
    path('user/tasks/<int:project_id>/', views.TaskViewSet.as_view({'get': 'list'}), name='user_project_tasks'),
    path('user/<int:user_id>/projects/', views.get_user_projects_with_favorite, name='get_user_projects_legacy'),
    path('user/<int:user_id>/favorites/<int:project_id>/', views.toggle_favorite_project, name='toggle_favorite_project_legacy'),
]