from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _crear_grupos(sender, **kwargs):
    from django.contrib.auth.models import Group
    for nombre in ('Administradores', 'Clientes', 'Vendedores', 'Usuarios'):
        Group.objects.get_or_create(name=nombre)


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        post_migrate.connect(_crear_grupos, sender=self)
