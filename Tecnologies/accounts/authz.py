"""
Helpers de autorizacion reutilizables.

Antes, la logica de "que puede ver cada rol" vivia como un if/elif suelto
dentro de myapp.views.index. Se centraliza aqui para que:

  - la propia vista `index` la use para decidir que plantilla mostrar.
  - endpoints/vistas futuras que necesiten restringir acceso por grupo
    (por ejemplo un panel de administracion con URL propia) puedan
    reutilizar `group_required` en vez de repetir `if/elif` en cada vista.
  - las clases de permiso de la API (accounts/api_permissions.py) reutilicen
    la misma funcion `user_in_group`, evitando que la definicion de "quien
    es administrador" viva en dos sitios distintos.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def user_in_group(user, group_name):
    """True si el usuario esta autenticado y pertenece al grupo indicado."""
    return bool(user) and user.is_authenticated and user.groups.filter(name=group_name).exists()


def group_required(*group_names):
    """
    Decorador para vistas basadas en funcion: exige sesion iniciada Y
    pertenencia a alguno de los grupos indicados. Pensado para vistas
    dedicadas con URL propia (no para `index`, que es una unica vista
    publica cuyo contenido varia segun el rol).
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not any(user_in_group(request.user, g) for g in group_names):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def admin_required(view_func):
    """Permite a 'Administradores' O a cuentas staff (is_staff).

    Se usa en el modulo de proyectos para que el admin pueda vender y
    actualizar tanto desde el panel de inicio.html (staff) como desde
    las vistas de gestion, sin tener que entrar al /admin/ de Django.
    """
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not (user_in_group(request.user, 'Administradores') or request.user.is_staff):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


# Mapeo explicito y unico de rol -> plantilla. Se recorre en orden, por lo
# que si un usuario perteneciera a varios grupos, gana el primero de la
# lista (Administradores > Clientes > Vendedores > Usuarios).
ROLE_TEMPLATES = [
    ("Administradores", "admindash.html"),
    ("Clientes", "cliente_dashboard.html"),
    ("Vendedores", "vendedor_dashboard.html"),
    ("Usuarios", "inicioPriv.html"),
]


def resolve_template_for_user(user):
    """Devuelve la plantilla que corresponde mostrar en `/` para este usuario."""
    if user.is_authenticated:
        for group_name, template in ROLE_TEMPLATES:
            if user_in_group(user, group_name):
                return template
        # Cuentas staff (is_staff) sin grupo: ven el panel claro de inicio.html
        # en modo admin (bloque {% if request.user.is_staff %}). Sin esto,
        # un staff sin grupo caeria al inicio publico pero sin contexto admin.
        if getattr(user, 'is_staff', False):
            return "inicio.html"
    return "inicio.html"
