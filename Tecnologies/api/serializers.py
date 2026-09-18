from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializer para /api/users/me/.

    Expone unicamente datos no sensibles del propio usuario autenticado.
    NUNCA incluye password/hash, is_staff ni is_superuser. `groups` es de
    solo lectura: un usuario no puede auto-asignarse un rol vía la API
    (eso corresponde al admin de Django o a un endpoint administrativo
    futuro con permiso explicito de Administrador).
    """

    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'groups']
        read_only_fields = ['id', 'username', 'date_joined', 'groups']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, style={'input_type': 'password'})


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False, style={'input_type': 'password'})
    new_password = serializers.CharField(trim_whitespace=False, style={'input_type': 'password'})

    def validate_new_password(self, value):
        # Reutiliza los mismos validadores de AUTH_PASSWORD_VALIDATORS que
        # ya se usan en el registro web (myapp.views.register).
        validate_password(value)
        return value
