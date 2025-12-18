from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.take_files, name='take_files'),
    path('download/', views.download_files, name='download_files'),
    path('upload-url/', views.file_upload, name='file_upload'),     # 이동됨
    path('save-meta/', views.save_file_meta, name='save_file_meta'), # 이동됨
    path('task-files/', views.get_task_files, name='get_task_files'),
]