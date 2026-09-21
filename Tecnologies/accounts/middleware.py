"""
Middleware de proteccion de rutas.

`AdminGateMiddleware` cierra la unica ruta que hasta ahora quedaba expuesta:
el admin de Django (por defecto en /admin/).

Sin esto, cualquiera que escribiera el link en el navegador veia el
formulario de acceso del admin. Eso ya revela que el panel existe y ademas
abre una superficie extra de fuerza bruta en otra URL distinta de /login.

Con este middleware, quien no sea una cuenta staff ya autenticada recibe un
404 (la misma respuesta que una ruta que no existe), asi que:
  - un anonimo no descubre el panel,
  - un usuario normal con sesion tampoco puede entrar aunque pegue el link,
  - el unico punto de entrada al sistema es /login, y de ahi cada usuario
    cae en la plantilla que le corresponde por rol (accounts/authz.py).

Es defensa en profundidad: no sustituye a los decoradores de las vistas
(`admin_required`, `group_required`, `login_required`), que siguen siendo
los que autorizan cada accion dentro de las rutas.
"""

from django.conf import settings
from django.shortcuts import render

import logging

logger = logging.getLogger('django.security')

# Nombre de la plantilla que se muestra en el 404 (misma que usa Django para
# el resto de rutas inexistentes, para no distinguir una de otra).
TEMPLATE_404 = '404.html'


class AdminGateMiddleware:
    """Devuelve 404 para el admin si el usuario no es staff autenticado."""

    def __init__(self, get_response):
        self.get_response = get_response
        # Prefijo configurable (DJANGO_ADMIN_URL_PREFIX en el entorno): en
        # produccion se puede mover el admin a una ruta no adivinable.
        prefijo = str(getattr(settings, 'ADMIN_URL_PREFIX', 'admin') or '').strip('/')
        # Normalizado a '/prefijo/' para poder comparar con request.path.
        self.prefijo = f'/{prefijo}/' if prefijo else ''

    def __call__(self, request):
        if self.prefijo and request.path.startswith(self.prefijo):
            user = getattr(request, 'user', None)
            es_staff = bool(
                user is not None
                and user.is_authenticated
                and user.is_staff
            )
            if not es_staff:
                # Se registra el intento sin exponer datos sensibles: es util
                # para detectar escaneos de /admin/ en los logs del servidor.
                logger.warning(
                    'Acceso al admin bloqueado para usuario no staff (ruta: %s)',
                    request.path,
                )
                return render(request, TEMPLATE_404, status=404)
        return self.get_response(request)
