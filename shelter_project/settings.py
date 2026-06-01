"""
Django settings for shelter_project project.
"""

from pathlib import Path
import os
import re

BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузка .env файла
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-p6jtvur592d(jy^_lol&a-cs=zl1=@%5h)v_lt5vtp5^p8g)2r')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ALLOWED_HOSTS
ALLOWED_HOSTS_ENV = os.environ.get('ALLOWED_HOSTS', '')
if ALLOWED_HOSTS_ENV:
    ALLOWED_HOSTS = ALLOWED_HOSTS_ENV.split(',')
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']

# Application definition
INSTALLED_APPS = [
    'cloudinary_storage',  # ДОБАВЛЕНО: должен быть выше staticfiles
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',  # ДОБАВЛЕНО
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'accounts',
    'animals',
    'applications',
    'news',
    'donations',
    'meetings',
    'messages.apps.MessagesConfig',
    'care',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'shelter_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context.auth_user',
                'messages.context.unread_messages',
                'animals.context.active_shelters',
            ],
        },
    },
]

WSGI_APPLICATION = 'shelter_project.wsgi.application'

# ========== НАСТРОЙКА БАЗЫ ДАННЫХ (РАБОТАЕТ БЕЗ ДОП. БИБЛИОТЕК) ==========
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Парсим DATABASE_URL вручную через regex
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):?(\d+)?/([^?]+)'
    match = re.match(pattern, DATABASE_URL)
    
    if match:
        db_user, db_password, db_host, db_port, db_name = match.groups()
        db_port = db_port or '5432'
        
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': db_name,
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': db_host,
                'PORT': db_port,
                'OPTIONS': {'sslmode': 'require'},
                'CONN_MAX_AGE': 600,
            }
        }
    else:
        raise ValueError(f"Invalid DATABASE_URL format")
else:
    # Локальная разработка
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'AnimalShelterDB'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', '1'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files - Cloudinary (ДОБАВЛЕНО)
MEDIA_URL = '/media/'  # оставлен для обратной совместимости
# MEDIA_ROOT больше не используется, файлы хранятся в Cloudinary

# DRF & Spectacular
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'user_id',
    'USER_ID_CLAIM': 'user_id',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Анималити API',
    'DESCRIPTION': 'API для приюта животных',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings (Mail.ru SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mail.ru'
EMAIL_PORT = int(os.environ.get('MAILRU_EMAIL_PORT', '465'))
EMAIL_HOST_USER = os.environ.get('MAILRU_EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('MAILRU_EMAIL_PASSWORD', '')
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'no-reply@example.com'

# Security
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =========================================================
# CLOUDINARY CONFIGURATION (ДОБАВЛЕНО)
# =========================================================
import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    CLOUD_NAME = 'dpgmufhxd',
    API_KEY = '132519868974749',
    API_SECRET = 'RNsVjtbdTfKfhYe_rJ5axQeDJJQ',
    SECURE = True
)

# Media files will be stored in Cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
