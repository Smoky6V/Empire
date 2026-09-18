"""
Configuración de PRODUCCIÓN.

Se activa con DJANGO_ENV=production. Falla de forma explícita si faltan
variables críticas en vez de arrancar con valores inseguros por defecto.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Obligatorio en prod: sin default. Si no está configurado, Django no arranca.
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS')

# --- HTTPS / HSTS ---
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = env.int('DJANGO_HSTS_SECONDS', default=31536000)  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- Cookies ---
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# --- Headers adicionales ---
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# --- CORS ---
# No se instala django-cors-headers todavía: hoy el único cliente de /api/
# es el propio sitio (mismo origen), así que no hace falta. El día que un
# frontend/app externo consuma la API desde otro origen, se añade
# django-cors-headers aquí con una whitelist explícita (nunca '*').
