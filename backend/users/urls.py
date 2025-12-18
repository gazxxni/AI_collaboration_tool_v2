from django.urls import path
from . import views

# ✅ [핵심] tasks 앱의 뷰를 가져옵니다. (프로젝트 목록 조회 기능)
from tasks.views import get_user_projects_with_favorite, toggle_favorite_project

urlpatterns = [
    # ==========================================================
    # 1. 인증 및 사용자 프로필
    # ==========================================================
    path('login/', views.LoginView.as_view(), name='login'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('name/', views.get_user_name, name='get_user_name'),
    path('userslist/', views.get_users_list, name='get_users_list'),
    path('profile/', views.get_user_profile, name='get_user_profile'),
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
    path('update-skill/', views.update_skill, name='update_skill'),
    path('<int:user_id>/subjects/', views.UserSubjectsAPIView.as_view(), name='user-subjects'),

    # ==========================================================
    # 2. 프로젝트 목록 및 즐겨찾기 (Tasks 앱 뷰 연결)
    # ==========================================================
    # ✅ 이 경로들이 있어야 Topbarst에서 500/404 에러가 안 납니다.
    path('<int:user_id>/projects/', get_user_projects_with_favorite, name='get_user_projects'),
    path('<int:user_id>/favorites/<int:project_id>/', toggle_favorite_project, name='toggle_favorite_project'),

    # ==========================================================
    # 3. 대시보드 및 통계
    # ==========================================================
    path('<int:user_id>/dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('task-details/', views.TaskDetailsView.as_view(), name='task_details'),

    # ==========================================================
    # 4. 알림
    # ==========================================================
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),

    # ==========================================================
    # 5. 프로젝트 관리 (세션 등)
    # ==========================================================
    path('project/data/', views.receive_project_data, name='receive_project_data'),
    path('project/latest/', views.get_latest_project_id, name='get_latest_project_id'),
    path('projects/set/', views.CurrentProjectSetView.as_view(), name='current-project-set'),
    path('projects/get/', views.CurrentProjectGetView.as_view(), name='current-project-get'),
    path('projects/<int:project_id>/logs/', views.ProjectLogsView.as_view(), name='project-logs'),
    
    # ==========================================================
    # 6. 게시판
    # ==========================================================
    path('posts/', views.get_posts, name='posts-list'),
    path('posts/save/', views.save_post, name='posts-save'),
    path('posts/update/<int:post_id>/', views.update_post, name='posts-update'),
    path('posts/delete/<int:post_id>/', views.delete_post, name='posts-delete'),

    # ==========================================================
    # 7. 회의록
    # ==========================================================
    path('minutes/save/', views.save_minutes, name='save_minutes'),
    path('minutes/update/<int:minutes_id>/', views.update_minutes, name='update_minutes'),
    path('minutes/delete/<int:minutes_id>/', views.delete_minutes, name='delete_minutes'),
    path('minutes/<int:project_id>/', views.get_minutes_by_project, name='get_minutes_by_project'),
    path('minutes/html2docx/<int:minutes_id>/', views.export_minutes_docx, name='export_minutes_docx'),

    # ==========================================================
    # 8. 보고서
    # ==========================================================
    path('report/save/', views.save_report, name='save_report'),
    path('report/update/<int:report_id>/', views.update_report, name='update_report'),
    path('report/delete/<int:report_id>/', views.delete_report, name='delete_report'),
    path('report/<int:project_id>/', views.get_reports_by_project, name='get_reports_by_project'),
    path('report/html2docx/<int:report_id>/', views.export_report_docx, name='export_report_docx'),
]