from pathlib import Path
from decouple import config
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='unsafe-secret-key')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'app',
    'drf_spectacular',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='postgres'),
        'USER': config('POSTGRES_USER', default='postgres'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='postgres'),
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default=5432, cast=int),
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Дозволяємо передачу кукі через CORS
CORS_ALLOW_CREDENTIALS = True

# Переконайся, що твій фронтенд у списку дозволених (не використовуй '*')
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# Дозволяємо всі стандартні та кастомні заголовки
from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-suppress-toast',
]

# Також важливо для CSRF захисту (Django потребує цього для POST запитів)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        # 'rest_framework.permissions.IsAuthenticated',
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Обмеження частоти для чутливих ендпоінтів (вхід, реєстрація, відновлення пароля) - захист від перебору
    'DEFAULT_THROTTLE_RATES': {
        'auth': config('AUTH_THROTTLE_RATE', default='20/min'),
    },
}

# Політика паролів (застосовується при реєстрації та відновленні пароля)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

NOVA_POSHTA_API_KEY = config('NOVA_POSHTA_API_KEY', default='')
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')
ARCGIS_FRONT_LINE_URL = config('ARCGIS_FRONT_LINE_URL', default='https://services.arcgis.com/...')

SPECTACULAR_SETTINGS = {
    'TITLE': 'Inventory Management System API',
    'DESCRIPTION': 'API для автоматизованого розподілу дефіцитних ресурсів',
    'VERSION': '1.0.0',
}

# --- EMAIL (відновлення пароля) ---
# Якщо EMAIL_HOST не задано - листи друкуються в консоль/логи сервера (зручно для розробки).
EMAIL_HOST = config('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
def _clean_from_email(value, fallback):
    """Повертає коректний рядок "Ім'я <email>", інакше - запасний адрес (логін SMTP)."""
    from email.utils import parseaddr
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    name, addr = parseaddr(value or '')
    try:
        validate_email(addr)
        return value
    except ValidationError:
        return fallback or 'ResQ System <no-reply@resq.ua>'


# Пароль додатка Google часто копіюють з пробілами ("abcd efgh ...") - прибираємо їх
if EMAIL_HOST:
    EMAIL_HOST_PASSWORD = EMAIL_HOST_PASSWORD.replace(' ', '')

DEFAULT_FROM_EMAIL = _clean_from_email(
    config('DEFAULT_FROM_EMAIL', default='') or None,
    EMAIL_HOST_USER if EMAIL_HOST else None,
)


# --- ЛІМІТИ ЗАЯВОК ---
# Максимум одиниць ресурсу в заявках одного (не адміністратора) заявника, якщо у ресурсу не задано власний ліміт.
DEFAULT_MAX_PER_REQUEST = config('DEFAULT_MAX_PER_REQUEST', default=1000, cast=int)


# Запуск тестів зі зведеним звітом (CSV та Markdown у backend/test_reports/)
TEST_RUNNER = 'app.tests.report_runner.ReportRunner'
