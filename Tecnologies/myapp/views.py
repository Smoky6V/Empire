from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django_ratelimit.decorators import ratelimit

from accounts.authz import resolve_template_for_user

User = get_user_model()


# Limites de fuerza bruta: por IP para no bloquear a un usuario legitimo
# cuyo nombre sea adivinado/reutilizado por un atacante, y sin bloquear
# (block=False) para no crear una denegacion de servicio facil contra un
# usuario legitimo; en su lugar la vista comprueba `request.limited` y
# responde con el mismo mensaje de error generico que ya usaba.
LOGIN_RATE = '10/5m'
REGISTER_RATE = '5/15m'




@never_cache
@ratelimit(key='ip', rate=LOGIN_RATE, method='POST', block=False)
def login_view(request):
    # Un usuario con sesion ya iniciada no tiene nada que hacer en /login:
    # se le devuelve a su pagina principal para que el boton "atras" del
    # navegador nunca le muestre el formulario de acceso.
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':  # Si el método es POST
        if getattr(request, 'limited', False):
            return render(
                request, 'login.html',
                {'error': 'Demasiados intentos. Intenta de nuevo en unos minutos.'},
                status=429,
            )
        # Si el formulario es válido
        username = request.POST['username']
        password = request.POST['password']
            # Intentamos autenticar al usuario
        user = authenticate(request, username=username, password=password)

        if user is not None:
                login(request, user)  # Si el usuario es autenticado, hacemos login
                return redirect('index')  # Redirige a la página principal (asegúrate de que 'index' esté bien configurado)
        else:
                # Si el usuario no es autenticado, agregar un error
                 return render(request, 'login.html', {'error': 'Usuario o contraseña incorrectos'})
    
    

    return render(request, 'login.html')


@never_cache
def index(request):
    contexto = {}
    if request.user.is_authenticated:
        try:
            from proyectos.forms import ProyectoAdminForm
            from proyectos.metricas import panel_metricas
            from proyectos.models import Proyecto
            from accounts.authz import user_in_group
            es_admin = (
                user_in_group(request.user, 'Administradores')
                or request.user.is_staff
            )
            if es_admin:
                contexto['panel_proyectos'] = Proyecto.objects.select_related(
                    'cliente').prefetch_related('actualizaciones').all()
                contexto['panel_nuevo_form'] = ProyectoAdminForm()
                contexto['panel_estados'] = Proyecto.Estado.choices
                # Metricas reales del panel (KPIs + datos iniciales de graficas).
                contexto['panel_metricas'] = panel_metricas()
                # Altas recientes reales (usuarios + grupos + ultimo acceso).
                from django.contrib.auth import get_user_model
                contexto['panel_usuarios'] = (
                    get_user_model().objects.prefetch_related('groups')
                    .order_by('-date_joined')[:5])
            else:
                contexto['mis_proyectos_tabla'] = Proyecto.objects.filter(
                    cliente=request.user).prefetch_related('actualizaciones')
        except Exception:
            pass
    return render(request, resolve_template_for_user(request.user), contexto)


def logout_view(request):
    logout(request)
    return redirect('login')


@never_cache
@ratelimit(key='ip', rate=REGISTER_RATE, method='POST', block=False)
def register(request):
    # Igual que en /login: con sesion iniciada no tiene sentido crear otra
    # cuenta, se redirige a la pagina principal correspondiente al rol.
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, "Demasiados intentos de registro. Intenta de nuevo en unos minutos.")
            return redirect('register')

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not username or not email or not password:
            messages.error(request, "Todos los campos son obligatorios")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Nombre en uso")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Correo en uso")
            return redirect('register')

        try:
            validate_password(password)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

     #Agrega al usuario registrado automaticamente al grupo usuarios
        try:
            group = Group.objects.get(name='Usuarios')  
        except Group.DoesNotExist:
            group = Group.objects.create(name='Usuarios')  
        user.groups.add(group)

       
        login(request, user)
        return redirect('index')

    return render(request, 'register.html')
           