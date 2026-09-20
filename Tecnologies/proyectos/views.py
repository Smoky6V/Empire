from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from accounts.authz import admin_required, user_in_group

from .forms import ActualizacionForm, AvanceRapidoForm, ProyectoAdminForm, VincularCodigoForm
from .metricas import panel_metricas
from .models import ActualizacionProyecto, Proyecto


def _es_admin(user):
    return user_in_group(user, 'Administradores') or user.is_staff


def _resolver_cliente(ref):
    """Resuelve username o email al usuario real. None si viene vacio o no existe."""
    ref = (ref or '').strip()
    if not ref:
        return None
    User = get_user_model()
    return User.objects.filter(Q(username__iexact=ref) | Q(email__iexact=ref)).first()


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
    if not (es_dueno or _es_admin(request.user)):
        messages.error(request, 'Ese proyecto no esta vinculado a tu cuenta.')
        return redirect('proyectos:mis')
    return render(request, 'proyectos/detalle.html', {
        'proyecto': proyecto, 'proyecto_json': _serialize(proyecto),
    })


@admin_required
@require_POST
@never_cache
def avance_rapido(request):
    """Actualiza estado/avance desde la tabla de inicio.html sin salir.

    Si el admin escribe titulo/detalle, tambien se publica en la bitacora
    que el cliente ve en tiempo real.
    """
    form = AvanceRapidoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'No se pudo actualizar: revisa estado y avance (0-100).')
        return redirect('index')
    proyecto = get_object_or_404(Proyecto, codigo=form.cleaned_data['codigo'])
    proyecto.estado = form.cleaned_data['estado']
    proyecto.avance = form.cleaned_data['avance']
    proyecto.save(update_fields=['estado', 'avance', 'actualizado'])
    titulo = form.cleaned_data.get('titulo', '').strip()
    detalle = form.cleaned_data.get('detalle', '').strip()
    if titulo or detalle:
        ActualizacionProyecto.objects.create(
            proyecto=proyecto,
            titulo=titulo or f'Avance al {proyecto.avance}%',
            detalle=detalle,
            avance=proyecto.avance,
            creado_por=request.user,
        )
    messages.success(request, f'{proyecto.codigo} actualizado. El cliente lo ve en tiempo real.')
    return redirect('index')


@admin_required
@require_GET
@never_cache
def panel_resumen_json(request):
    """JSON en vivo para KPIs y graficas del panel inicio.html.

    Solo staff/admin. Se consulta con polling cada 15s desde el JS del
    panel y devuelve panel_metricas() (todo derivado de la BD real).
    """
    resp = JsonResponse(panel_metricas())
    resp['Cache-Control'] = 'no-store'
    return resp


@admin_required
@never_cache
def admin_lista(request):
    proyectos = Proyecto.objects.select_related('cliente').all()
    return render(request, 'proyectos/admin_lista.html', {'proyectos': proyectos})


@admin_required
@never_cache
def admin_crear(request):
    form = ProyectoAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        proyecto = form.save(commit=False)
        cliente = _resolver_cliente(form.cleaned_data.get('cliente_ref'))
        ref = (form.cleaned_data.get('cliente_ref') or '').strip()
        if ref and cliente is None:
            form.add_error('cliente_ref', 'No existe ningun usuario con ese nombre o correo.')
        else:
            proyecto.cliente = cliente
            if cliente is not None and not proyecto.email_cliente:
                proyecto.email_cliente = cliente.email or ''
            proyecto.save()
            form.save_m2m() if hasattr(form, 'save_m2m') else None
            messages.success(request, 'Proyecto creado. Codigo para el cliente: ' + proyecto.codigo)
            # Si viene del panel inicio.html, vuelve al panel con el codigo visible.
            if request.POST.get('origen') == 'inicio':
                return redirect('index')
            return redirect('proyectos:admin_detalle', codigo=proyecto.codigo)
    return render(request, 'proyectos/admin_form.html', {'form': form, 'modo': 'crear'})


@admin_required
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


@admin_required
@never_cache
def admin_editar(request, codigo):
    proyecto = get_object_or_404(Proyecto, codigo=codigo.upper())
    inicial = {'cliente_ref': proyecto.cliente.username if proyecto.cliente else ''}
    form = ProyectoAdminForm(request.POST or None, instance=proyecto, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        proyecto = form.save(commit=False)
        cliente = _resolver_cliente(form.cleaned_data.get('cliente_ref'))
        ref = (form.cleaned_data.get('cliente_ref') or '').strip()
        if ref and cliente is None:
            form.add_error('cliente_ref', 'No existe ningun usuario con ese nombre o correo.')
        else:
            proyecto.cliente = cliente
            proyecto.save()
            messages.success(request, 'Proyecto actualizado. El cliente lo ve en tiempo real.')
            return redirect('proyectos:admin_detalle', codigo=proyecto.codigo)
    return render(request, 'proyectos/admin_form.html', {
        'form': form, 'modo': 'editar', 'proyecto': proyecto,
    })
