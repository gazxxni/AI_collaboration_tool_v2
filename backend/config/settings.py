from pathlib import Path
import os
from dotenv import load_dotenv

# .env 파일 로드 (환경변수 관리)
load_dotenv()

# 기본 디렉토리 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent

# 보안 키 (배포 시에는 반드시 .env 등에서 관리 권장)
SECRET_KEY = 'django-insecure-w-ggn-ypwx8$n)3tfw&_1^7)lk!s9nf3a#-bj3rzxtl7&ja0ji'

# 디버그 모드 (개발 환경: True, 배포 환경: False)
DEBUG = True

# 호스트 허용 범위
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# 설치된 앱 정의
INSTALLED_APPS = [
    'daphne',          # ASGI 서버 (WebSocket 지원)
    'channels',        # Django Channels (실시간 통신)
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',  # REST API
    'corsheaders',     # CORS 제어
    
    # Infloop Custom Apps
    'chat',
    'gptapi',
    'schedule',
    'tasks',
    'db_model',
    'comments',
    'file',
]

# 미들웨어 정의
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',           # CORS 헤더 추가 (최상단 권장)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', # 세션 관리
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',       # CSRF 보안
    'django.contrib.auth.middleware.AuthenticationMiddleware', # 인증 처리
    'django.contrib.messages.middleware.MessageMiddleware',    # 메시지 처리
]

# URL 설정 경로
ROOT_URLCONF = 'config.urls'

# 템플릿 설정
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI 애플리케이션 (동기 서버)
WSGI_APPLICATION = 'config.wsgi.application'

# ASGI 애플리케이션 (비동기/채팅 서버)
ASGI_APPLICATION = 'config.asgi.application'

# 데이터베이스 설정 (로컬 MySQL 연결)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'infloop',                                  # import한 DB 이름
        'USER': os.getenv('DB_USER', 'root'),               # 로컬 MySQL 사용자명 (기본값 root)
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),   # 로컬 MySQL 비밀번호 (.env에서 로드 권장)
        'HOST': '127.0.0.1',                                # 로컬 호스트
        'PORT': '3306',                                     # MySQL 기본 포트
    }
}

# 비밀번호 검증 (기본 설정)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 언어 및 시간대 설정
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = False # 로컬 시간(KST) 사용을 위해 False 설정

# 정적 파일 경로
STATIC_URL = 'static/'

# 미디어 파일 경로 (로컬 저장소 사용)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 기본 오토 필드
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS 및 보안 설정 (React 연동)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']

# 세션 및 쿠키 설정
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True  # 개발 환경(http)에서도 None 설정 시 True 필요할 수 있음 (브라우저 정책)
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 86400  # 1일 유지

# Channels 레이어 (로컬 개발용 인메모리)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# REST Framework 설정
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,
}

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")