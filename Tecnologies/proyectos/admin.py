from django.contrib import admin

from .models import ActualizacionProyecto, Proyecto


class ActualizacionInline(admin.TabularInline):
    model = ActualizacionProyecto
    extra = 1
    fields = ('titulo', 'detalle', 'avance', 'creado')
    ordering = ('-creado',)


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'cliente', 'estado', 'avance', 'actualizado')
    list_filter = ('estado',)
    search_fields = ('codigo', 'nombre', 'email_cliente', 'cliente__username')
    readonly_fields = ('codigo', 'creado', 'actualizado')
    inlines = [ActualizacionInline]
    list_editable = ('estado', 'avance')


@admin.register(ActualizacionProyecto)
class ActualizacionProyectoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'titulo', 'avance', 'creado', 'creado_por')
    search_fields = ('proyecto__codigo', 'titulo')

    def save_model(self, request, obj, form, change):
        if not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

