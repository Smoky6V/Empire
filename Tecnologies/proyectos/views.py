from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from accounts.authz import group_required, user_in_group

from .forms import ActualizacionForm, ProyectoAdminForm, VincularCodigoForm
from .models import Proyecto


def _serialize(proyecto):
    acts = [
        {'titulo': a.titulo, 'detalle': a.detalle, 'avance': a.avance,
         'creado': a.creado.strftime('%d/%m/%Y %H:%M')}
        for a in proyecto.actualizaciones.all()[:30]
    ]
    return {
        'codigo': proyecto.codigo, 'nombre': proyecto.nombre,
        'descripcion': proyecto.descripcion, 'estado': proyecto.estado,
        'estado_display': proyecto.get_estado_display(),
        'avance': proyecto.avance,
        'entrega': (proyecto.fecha_entrega_estimada.strftime('%d/%m/%Y')
                    if proyecto.fecha_entrega_estimada else None),
        'actualizado': proyecto.actualizado.strftime('%d/%m/%Y %H:%M'),
        'actualizaciones': acts,
    }


def buscar_por_codigo(request):
    proyecto = None
    cod = request.GET.get('codigo', '').strip().upper()
    if cod:
        proyecto = Proyecto.objects.filter(codigo=cod).first()
        if proyecto is None:
            messages.error(request, 'No encontramos ningun proyecto con ese codigo.')
    return render(request, 'proyectos/buscar.html', {
        'proyecto': proyecto,
        'proyecto_json': _serialize(proyecto) if proyecto else None,
        'codigo_buscado': cod,
    })


@require_GET
def proyecto_estado_json(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo.upper())
    resp = JsonResponse(_serialize(proyecto))
    resp['Cache-Control'] = 'no-store'
    return resp


@login_required
@never_cache
def mis_proyectos(request):
    form = VincularCodigoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cod = form.cleaned_data['codigo']
        try:
            proyecto = Proyecto.objects.get(codigo=cod)
        except Proyecto.DoesNotExist:
            messages.error(request, 'Ese codigo no existe. Verifica e intenta de nuevo.')
        else:
            if proyecto.cliente_id and proyecto.cliente_id != request.user.id:
                messages.error(request, 'Ese codigo ya esta vinculado a otra cuenta.')
            else:
                proyecto.cliente = request.user
                proyecto.save(update_fields=['cliente', 'actualizado'])
                messages.success(request, 'Proyecto vinculado a tu cuenta: ' + proyecto.nombre)
                return redirect('proyectos:detalle', codigo=proyecto.codigo)
    proyectos = Proyecto.objects.filter(cliente=request.user).prefetch_related('actualizaciones')
    return render(request, 'proyectos/mis_proyectos.html', {'form': form, 'proyectos': proyectos})


@login_required
@never_cache
def detalle_proyecto(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo.upper())
    es_dueno = proyecto.cliente_id == request.user.id
    es_admin = user_in_group(request.user, 'Administradores') or request.user.is_staff
    if not (es_dueno or es_admin):
        messages.error(request, 'Ese proyecto no esta vinculado a tu cuenta.')
        return redirect('proyectos:mis')
    return render(request, 'proyectos/detalle.html', {
        'proyecto': proyecto, 'proyecto_json': _serialize(proyecto),
    })


@group_required('Administradores')
@never_cache
def admin_lista(request):
    proyectos = Proyecto.objects.select_related('cliente').all()
    return render(request, 'proyectos/admin_lista.html', {'proyectos': proyectos})


@group_required('Administradores')
@never_cache
def admin_crear(request):
    form = ProyectoAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        proyecto = form.save()
        messages.success(request, 'Proyecto creado. Codigo para el cliente: ' + proyecto.codigo)
        return redirect('proyectos:admin_detalle', codigo=proyecto.codigo)
    return render(request, 'proyectos/admin_form.html', {'form': form, 'modo': 'crear'})


@group_required('Administradores')
@never_cache
def admin_detalle(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo.upper())
    form = ActualizacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        act = form.save(commit=False)
        act.proyecto = proyecto
        act.creado_por = request.user
        act.save()
        messages.success(request, 'Avance publicado. El cliente lo ve en tiempo real.')
        return redirect('proyectos:admin_detalle', codigo=proyecto.codigo)
    return render(request, 'proyectos/admin_detalle.html', {
        'proyecto': proyecto, 'form': form,
        'actualizaciones': proyecto.actualizaciones.all(),
    })


@group_required('Administradores')
@never_cache
def admin_editar(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo.upper())
    form = ProyectoAdminForm(request.POST or None, instance=proyecto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Proyecto actualizado. El cliente lo ve en tiempo real.')
        return redirect('proyectos:admin_detalle', codigo=proyecto.codigo)
    return render(request, 'proyectos/admin_form.html', {
        'form': form, 'modo': 'editar', 'proyecto': proyecto,
    })
