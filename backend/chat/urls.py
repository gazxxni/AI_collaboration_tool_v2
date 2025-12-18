from django.urls import path
from . import views

urlpatterns = [
    # 프로젝트 채팅 관련
    path('api/projects/<int:user_id>/', views.get_user_projects, name='get_user_projects'),
    path('api/messages/<int:project_id>/', views.get_project_messages, name='get_project_messages'),
    path('api/project_name/<int:project_id>/', views.get_project_name, name='get_project_name'),

    # DM (Direct Message) 관련
    path('api/dm_rooms/<int:user_id>/', views.get_dm_rooms, name='get_dm_rooms'),
    path('api/dm_rooms/create/', views.create_dm_room, name='create_dm_room'),
    path('api/dm_rooms/<int:room_id>/messages/', views.get_dm_messages, name='get_dm_messages'),
]