from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

def index(request):
    return HttpResponse("<h1>Infloop Server is Running! 🚀</h1>")

urlpatterns = [
    path('', index),
    path('admin/', admin.site.urls),

    path('api/users/', include('users.urls')),
    path('api/user/', include('users.urls')),

    path('api/', include('tasks.urls')),
    path('api/schedule/', include('schedule.urls')),
    path('', include('chat.urls')), 

    path('gptapi/', include('gptapi.urls')),
    path('api/gpt/', include('gptapi.urls')),
    
    path('api/files/', include('file.urls')),
    path('api/comments/', include('comments.urls')),
    
    path("api/", include("log.urls")), 
    

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)