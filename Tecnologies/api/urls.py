from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    # Login API ELIMINADO POR SEGURIDAD: /api/auth/login/ se bloquea via
    # middleware (ruta = 404). El login se realiza solo con /login (web).
    #
    # path('auth/login/', views.LoginView.as_view(), name='login'),  # eliminado
    #
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/password/change/', views.PasswordChangeView.as_view(), name='password-change'),
    path('users/me/', views.MeView.as_view(), name='me'),
]
