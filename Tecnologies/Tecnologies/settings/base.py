"""
Configuración base de Django para el proyecto Tecnologies (Empire).

Este módulo NO se usa directamente: `dev.py` y `prod.py` heredan de él.
Ningún secreto vive en este archivo ni en ningún otro `.py` del proyecto;
todo se lee desde variables de entorno (ver `.env.example`).
"""

from pathlib import Path
import environ

# BASE_DIR apunta a la carpeta que contiene manage.py (Tecnologies/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Si existe un archivo .env junto a manage.py, se carga automáticamente.
# En producción real las variables normalmente las inyecta el propio
# hosting/orquestador y no hace falta ningún archivo .env.
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))


# ---------------------------------------------------------------------------
# Secret key: obligatoria vía entorno. No hay valor por defecto a propósito:
# si falta, Django debe fallar de forma ruidosa en vez de arrancar inseguro.
# ---------------------------------------------------------------------------
SECRET_KEY = env.str("DJANGO_SECRET_KEY")


# ---------------------------------------------------------------------------
# Aplicaciones instaladas
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'accounts',
    'myapp',
    'api',
]

# Custom User Model mínimo (ver accounts/models.py). Se define desde el
# principio del proyecto para no tener que migrarlo más adelante.
AUTH_USER_MODEL = 'accounts.Usuario'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Tecnologies.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'Tecnologies.wsgi.application'


# ---------------------------------------------------------------------------
# Base de datos: MySQL vía variables de entorno. Sin valores por defecto
# para host/usuario/password/nombre: deben venir siempre del entorno.
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': env.str('DB_ENGINE', default='mysql.connector.django'),
        'NAME': env.str('DB_NAME'),
        'USER': env.str('DB_USER'),
        'PASSWORD': env.str('DB_PASSWORD'),
        'HOST': env.str('DB_HOST', default='localhost'),
        'PORT': env.str('DB_PORT', default='3306'),
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Django REST Framework: por ahora solo autenticación por sesión (coherente
# con que la web sigue siendo server-side rendered). Sin permisos abiertos
# por defecto: cada vista/endpoint debe declarar explícitamente su permiso.
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'auth': '10/min',
    },
}


# ---------------------------------------------------------------------------
# Logging: nunca se registran SECRET_KEY, contraseñas ni cadenas de conexión.
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
