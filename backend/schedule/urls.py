from django.urls import path
from . import views

urlpatterns = [
    path('<int:schedule_id>/', views.get_schedule_detail, name='get_schedule_detail'),
    path('delete/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),
    path('list/', views.get_user_schedules, name='get_user_schedules'),  # user_id 없이 세션으로 조회
    path('create/', views.create_user_schedule, name='create_user_schedule'),  # user_id 없이 세션으로 추가
    path('update/<int:schedule_id>/', views.update_schedule, name='update_schedule'),
    path('task/list/', views.task_list, name='task_list'),
    path('api/tasks/', views.tasks_for_user, name='tasks_for_user'),
]