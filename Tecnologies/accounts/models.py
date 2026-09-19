from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    """
    Custom User Model minimo.

    Hereda todo de AbstractUser (username, email, password ya hasheada,
    first_name, last_name, is_active, is_staff, is_superuser, date_joined,
    last_login, groups, user_permissions) sin anadir campos nuevos.

    Se define como modelo propio desde el inicio para no depender de
    django.contrib.auth.models.User directamente: asi, si en el futuro
    se necesitan campos adicionales (telefono, avatar, etc.), se agregan
    aqui sin tener que migrar el modelo de usuario mas adelante (una de
    las migraciones mas costosas y arriesgadas en Django si se hace tarde).
    """
    pass
