from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages



def login_view(request):
    if request.method == 'POST':  # Si el método es POST
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
    
    
    if request.user.is_authenticated:
        return render(request, 'inicio.html')
    
    else:
         return redirect('login')


def logout_view(request):
    logout(request)
    return redirect('login')


def register(request):
    if request.method == 'POST':
         
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
         

         user= User.objects.create_user(
              username=username,
              email=email,
              password=password
         )

         login(request, user)
         return redirect('index')

    return render(request, 'register.html')
           