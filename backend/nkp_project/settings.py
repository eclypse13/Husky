from pathlib import Path
from decouple import config
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    # For tokens
    'rest_framework.authtoken',

    # Local
    'core',

    # Archive, pedigree, dog page
    'dogs_module',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nkp_project.urls'

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

WSGI_APPLICATION = 'nkp_project.wsgi.application'

# MongoDB через MongoEngine - с обработкой ошибок
MONGODB_HOST = config('MONGODB_HOST', default='localhost')
MONGODB_PORT = config('MONGODB_PORT', default=27017, cast=int)
MONGODB_NAME = config('MONGODB_NAME', default='nkp_husky')

# Подключение к MongoDB с retry логикой
import mongoengine
import time


import logging

logger = logging.getLogger(__name__)

def connect_to_mongodb(retries=5, delay=2):
    """Подключение к MongoDB с повторными попытками"""
    for attempt in range(retries):
        try:
            mongoengine.connect(
                db=MONGODB_NAME,
                host=MONGODB_HOST,
                port=MONGODB_PORT,
                alias='default',
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            logger.info(f"✓ Successfully connected to MongoDB at {MONGODB_HOST}:{MONGODB_PORT}")
            return True
        except Exception as e:
            logger.warning(f"MongoDB connection attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error("ERROR: Could not connect to MongoDB after all retries")
                # В режиме разработки продолжаем без MongoDB
                if DEBUG:
                    logger.warning("WARNING: Running without MongoDB in DEBUG mode")
                    return False
                else:
                    sys.exit(1)


# Подключаемся к MongoDB при загрузке settings
connect_to_mongodb()

# Django использует SQLite только для auth/sessions/admin
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },

    'dogs_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DOGS_DB_NAME'),
        'USER': config('DOGS_DB_USER'),
        'PASSWORD': config('DOGS_DB_PASSWORD'),
        'HOST': config('DOGS_DB_HOST', default='postgres'),
        'PORT': config('DOGS_DB_PORT', default='5432'),
    }
}

# Роутер — направляет запросы в нужную БД
DATABASE_ROUTERS = ['nkp_project.db_routers.DogsRouter']

# Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{config('REDIS_HOST', default='redis')}:{config('REDIS_PORT', default=6379)}/0",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'nkp',
        'TIMEOUT': 3600,
    },
    # Отдельный кэш для парсеров (большой TTL, не мешается с основным)
    'parsers': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{config('REDIS_HOST', default='redis')}:{config('REDIS_PORT', default=6379)}/2",  # БД 2
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,  # Если Redis упадёт — парсеры продолжат работать (просто без кэша)
        },
        'KEY_PREFIX': 'parsers',
        'TIMEOUT': 7200,  # 2 часа
    }
}

# Sessions в Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 7200,  # 12 часов
}
CELERY_TASK_ACKS_LATE = True

CELERY_TASK_ROUTES = {

    # playwright: задачи которые физически открывают браузер
    # Только эти задачи идут в worker с concurrency=1
    'dogs_module.import_zooportal_dog': {'queue': 'playwright'},
    'dogs_module.import_zooportal_page': {'queue': 'playwright'},
    'dogs_module.import_hybrid_full_dog': {'queue': 'playwright'},
    'dogs_module.import_hybrid_full_page': {'queue': 'playwright'},
    'dogs_module.import_show_list': {'queue': 'playwright'},
    'dogs_module.import_show_results': {'queue': 'playwright'},
    'dogs_module.photo_fetch_zoo_via_playwright': {'queue': 'playwright'},
    'dogs_module.refresh_cookies': {'queue': 'playwright'},

    # celery: диспетчеры (только раздают задачи, Playwright не открывают)
    'dogs_module.import_zooportal_range': {'queue': 'celery'},
    'dogs_module.import_hybrid_full_range': {'queue': 'celery'},
    'dogs_module.import_shows_full': {'queue': 'celery'},
    'dogs_module.import_show_date_range': {'queue': 'celery'},
    'dogs_module.import_results_for_date_range': {'queue': 'celery'},
    'dogs_module.photo_fetch_zoo_bulk': {'queue': 'celery'},
    'dogs_module.photo_upload_bulk': {'queue': 'celery'},
    'dogs_module.process_pending_results': {'queue': 'celery'},
    'dogs_module.process_all_pending_results': {'queue': 'celery'},
    'dogs_module.recalculate_show_ratings': {'queue': 'celery'},
    'dogs_module.finalize_shows': {'queue': 'celery'},

    # ofa: HTTP к ofa.org
    'dogs_module.fetch_ofa_dog_task': {'queue': 'ofa'},
    'dogs_module.fetch_ofa_bulk_by_reg_task': {'queue': 'ofa'},
    'dogs_module.fetch_ofa_bulk_by_name_task': {'queue': 'ofa'},
    'dogs_module.refresh_ofa_sh_breed_stats': {'queue': 'ofa'},

    # ba: HTTP к breedarchive.com
    'dogs_module.fetch_breedarchive_dog': {'queue': 'ba'},
    'dogs_module.fetch_full_pedigree': {'queue': 'ba'},
    'dogs_module.sync_breedarchive_recent': {'queue': 'ba'},
    # browse через Playwright но без проблем (антибота) работает
    'dogs_module.sync_breedarchive_browse': {'queue': 'ba'},

    # coi: CPU-интенсивный расчёт
    'dogs_module.recalculate_all_coi': {'queue': 'coi'},

    # photos: HTTP к Яндекс.Диску + DB
    'dogs_module.photo_upload_one': {'queue': 'photos'},
    'dogs_module.photo_sync_yadisk_to_db': {'queue': 'photos'},
    'dogs_module.photo_stats': {'queue': 'photos'},
    'dogs_module.photo_delete_one': {'queue': 'photos'},
    'dogs_module.photo_backfill_hashes': {'queue': 'photos'},
    'dogs_module.photo_cleanup_placeholders': {'queue': 'photos'},

    # ml: HTTP к ML-сервису
    'dogs_module.train_ml_model_task': {'queue': 'celery'},
    'dogs_module.predict_breeding_task': {'queue': 'celery'},
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # For tokens
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '2000/hour',
        'user': '2000/hour'
    }
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'НКП Сибирский Хаски API',
    'DESCRIPTION': 'API для Национального клуба породы Сибирский хаски',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ['https://husky-nkp.ru']

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
