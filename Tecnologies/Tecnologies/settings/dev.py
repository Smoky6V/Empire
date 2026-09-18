"""
Configuración de DESARROLLO.

Se activa por defecto (ver __init__.py) salvo que DJANGO_ENV=production.
Sigue exigiendo SECRET_KEY y credenciales de BD por entorno (nunca
hardcodeadas), pero relaja lo que solo importa en producción real.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# En desarrollo no es necesario forzar HTTPS ni cookies "secure" (normalmente
# no hay TLS en localhost).
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
