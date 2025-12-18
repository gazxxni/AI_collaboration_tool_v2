from django.urls import path
from . import views

urlpatterns = [
    path('', views.comment_list_or_create, name='comment_list_or_create'),
    # 파일 관련 URL은 file 앱으로 이동했으므로 삭제
]