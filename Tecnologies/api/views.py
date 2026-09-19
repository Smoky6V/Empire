from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, PasswordChangeSerializer, UsuarioSerializer


class LoginView(APIView):
    """
    POST /api/auth/login/

    Autentica y crea una sesion de Django (misma sesion que usa la web).
    No hay endpoint publico de "quien soy" antes de esto: si las
    credenciales son invalidas, se responde 401 sin filtrar si fue el
    usuario o la contraseña lo que fallo.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': 'Credenciales invalidas.'}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response(UsuarioSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/auth/logout/ — cierra la sesion actual."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """
    GET/PATCH /api/users/me/

    Siempre opera sobre `request.user`: nunca recibe un id de otro usuario
    por URL/body, así que no hay superficie para IDOR/BOLA en este endpoint.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        serializer = UsuarioSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordChangeView(APIView):
    """POST /api/auth/password/change/ — cambia la contraseña del propio usuario."""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Contraseña actual incorrecta.'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        # Mantiene la sesion activa tras cambiar la contraseña (si no, Django
        # invalida la sesion actual por el cambio de password hash).
        update_session_auth_hash(request, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
