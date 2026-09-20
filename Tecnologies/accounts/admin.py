from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


class UsuarioAdmin(UserAdmin):
    """Admin del usuario: muestra grupos y permite asignar el rol rapido."""
    list_display = ('username', 'email', 'is_staff', 'is_active', 'get_grupos')
    list_filter = ('groups', 'is_staff', 'is_active')

    @admin.display(description='Grupos')
    def get_grupos(self, obj):
        return ', '.join(g.name for g in obj.groups.all())


admin.site.register(Usuario, UsuarioAdmin)
