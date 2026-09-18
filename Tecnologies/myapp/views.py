from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
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




@ratelimit(key='ip', rate=LOGIN_RATE, method='POST', block=False)
def login_view(request):
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


def index(request):
    return render(request, resolve_template_for_user(request.user))


def logout_view(request):
    logout(request)
    return redirect('login')


@ratelimit(key='ip', rate=REGISTER_RATE, method='POST', block=False)
def register(request):
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
           