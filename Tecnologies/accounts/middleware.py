"""
Middleware de proteccion de rutas.

`ProteccionRutasMiddleware` hace dos cosas, y las dos van en la misma
direccion: **que un visitante no descubra como esta construido el sitio**.

1. Oculta el admin de Django (por defecto en /admin/).

   Sin esto, cualquiera que escribiera el link en el navegador veia el
   formulario de acceso del admin. Eso ya revela que el panel existe y ademas
   abre una superficie extra de fuerza bruta en otra URL distinta de /login.

   Quien no sea una cuenta staff ya autenticada recibe un 404 (la misma
   respuesta que una ruta que no existe), asi que:
     - un anonimo no descubre el panel,
     - un usuario normal con sesion tampoco puede entrar aunque pegue el link,
     - el unico punto de entrada al sistema es /login, y de ahi cada usuario
       cae en la plantilla que le corresponde por rol (accounts/authz.py).

2. Oculta las paginas tecnicas de DEBUG (404 y 500).

   Con DEBUG=True, cuando se escribe una ruta que no existe Django responde
   con su pagina tecnica que **lista TODAS las rutas del proyecto** (admin/,
   api/, proyectos/, login, ...). Es util para el desarrollador, pero fuera
   de él es un mapa de como atacar el sitio. Pasa lo mismo con la pagina de
   error 500, que imprime el traceback y parte del estado interno.

   A quien no sea staff se le entrega la plantilla de marca (404.html /
   500.html). Un miembro del equipo (staff) SI ve el detalle tecnico, para no
   perder la capacidad de depurar en desarrollo.

Es defensa en profundidad: no sustituye a los decoradores de las vistas
(`admin_required`, `group_required`, `login_required`), que siguen siendo
los que autorizan cada accion dentro de las rutas.

En produccion (DJANGO_ENV=production, DEBUG=False) Django ya no genera paginas
tecnicas; este middleware queda como un seguro extra sin cambiar nada.
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

import logging

logger = logging.getLogger('django.security')

# Plantillas con la identidad del sitio para los errores del sitio.
TEMPLATE_404 = '404.html'
TEMPLATE_500 = '500.html'


class ProteccionRutasMiddleware:
    """Oculta el admin y las paginas tecnicas de DEBUG a quien no es staff."""

    def __init__(self, get_response):
        self.get_response = get_response
        # Prefijo configurable (DJANGO_ADMIN_URL_PREFIX en el entorno): en
        # produccion se puede mover el admin a una ruta no adivinable.
        admin_prefijo = str(
            getattr(settings, 'ADMIN_URL_PREFIX', 'admin') or ''
        ).strip('/')
        self.admin_prefix = f'/{admin_prefijo}/' if admin_prefijo else ''
        # Prefijo de la API: /api/ (usado para controlar /api/auth/login/).
        api_prefijo = str(
            getattr(settings, 'API_URL_PREFIX', 'api') or ''
        ).strip('/')
        self.api_prefix = f'/{api_prefijo}/' if api_prefijo else ''
        self.api_auth_login_pattern = (
            self.api_prefix + 'auth/login/'
        )  # '/api/auth/login/'

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _es_staff(user):
        """Staff autenticado = puede ver el detalle tecnico de los errores."""
        return bool(
            user is not None
            and user.is_authenticated
            and user.is_staff
        )

    def _pagina_error(self, request, plantilla, codigo):
        """Renderiza la pagina de error del sitio; si falla, sin romper nada.

        Este middleware se ejecuta incluso durante un error, asi que el
        fallback vuelve a la respuesta original de Django (peor estetica,
        pero el sitio sigue funcionando).
        """
        try:
            return render(request, plantilla, status=codigo)
        except Exception:
            logger.exception('No se pudo renderizar %s', plantilla)
            return None

    @staticmethod
    def _es_html(response):
        """Solo se reemplazan respuestas HTML (las JSON de /api/ quedan igual)."""
        tipo = (response.get('Content-Type') or '').lower()
        return 'text/html' in tipo

    # --- ciclo de la peticion ---------------------------------------------

    def __call__(self, request):
        path = request.path
        is_admin = path.startswith(self.admin_prefix)
        is_api = path.startswith(self.api_prefix)

        # 1) Eliminado login API seguro: cualquier metodo da 404 cerradamente.
        if path == self.api_auth_login_pattern or path == self.api_auth_login_pattern.rstrip('/'):
            pagina = self._pagina_error(request, TEMPLATE_404, 404)
            if pagina is not None:
                logger.warning(
                    'Login API solicitado y bloqueado por seguridad (ruta: %s)',
                    path,
                )
                return pagina

        # 2) Admin de Django: ni siquiera mostrar su formulario de login.
        if is_admin:
            if not self._es_staff(getattr(request, 'user', None)):
                logger.warning(
                    'Acceso al admin bloqueado para usuario no staff (ruta: %s)',
                    path,
                )
                pagina = self._pagina_error(request, TEMPLATE_404, 404)
                if pagina is not None:
                    return pagina

        response = self.get_response(request)

        # 3) Paginas tecnicas de DEBUG: solo para staff.
        if settings.DEBUG and self._es_html(response):
            user = getattr(request, 'user', None)
            if not self._es_staff(user):
                if response.status_code == 404:
                    pagina = self._pagina_error(request, TEMPLATE_404, 404)
                    if pagina is not None:
                        return pagina
                elif response.status_code == 500:
                    logger.exception(
                        'Error interno (ruta: %s). El detalle tecnico solo se '
                        'muestra a cuentas staff.',
                        path,
                    )
                    pagina = self._pagina_error(request, TEMPLATE_500, 500)
                    if pagina is not None:
                        return pagina

        return response

