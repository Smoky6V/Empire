from django.db.models import Avg, Count
from django.utils import timezone

from .models import ActualizacionProyecto, Proyecto


def panel_metricas():
    """Agrega todo lo que el panel inicio.html necesita como datos reales.

    Devuelve un dict 100% derivado de Proyecto/ActualizacionProyecto:
    KPIs, distribucion por estado, avance por proyecto, actividad por mes
    y actividad reciente. Sin numeros quemados.
    """
    hoy = timezone.localdate()
    hace_30 = hoy - timezone.timedelta(days=30)

    proyectos = list(Proyecto.objects.all().order_by('-actualizado')[:200])
    total = Proyecto.objects.count()

    por_estado_qs = (Proyecto.objects.values('estado')
                     .annotate(n=Count('id')))
    por_estado = {r['estado']: r['n'] for r in por_estado_qs}

    estados = list(Proyecto.Estado.choices)
    estados_labels = [etiqueta for _, etiqueta in estados]
    estados_data = [por_estado.get(valor, 0) for valor, _ in estados]
    estados_valores = [valor for valor, _ in estados]

    avance_prom = Proyecto.objects.aggregate(p=Avg('avance'))['p'] or 0
    entregados = por_estado.get(Proyecto.Estado.ENTREGADO, 0)
    activos = total - entregados
    actualizados_hoy = Proyecto.objects.filter(actualizado__date=hoy).count()
    nuevos_30 = Proyecto.objects.filter(creado__date__gte=hace_30).count()

    # Avance por proyecto (top 10 por actualizacion reciente).
    top = proyectos[:10]
    top_labels = [p.codigo for p in top]
    top_nombres = [p.nombre for p in top]
    top_avances = [p.avance for p in top]

    # Actividad: actualizaciones publicadas por mes, ultimos 6 meses.
    meses_labels, meses_data = [], []
    primero = hoy.replace(day=1)
    for i in range(5, -1, -1):
        y = primero.year
        m = primero.month - i
        while m <= 0:
            m += 12
            y -= 1
        meses_labels.append(f'{m:02d}/{y}')
        if m == 12:
            siguiente = timezone.datetime(y + 1, 1, 1).date()
        else:
            siguiente = timezone.datetime(y, m + 1, 1).date()
        inicio = timezone.datetime(y, m, 1).date()
        meses_data.append(
            ActualizacionProyecto.objects.filter(
                creado__date__gte=inicio, creado__date__lt=siguiente).count())

    # Proyectos creados por mes, ultimos 6 meses (linea "ventas/entregas").
    creados_data = []
    for i in range(5, -1, -1):
        y = primero.year
        m = primero.month - i
        while m <= 0:
            m += 12
            y -= 1
        if m == 12:
            siguiente = timezone.datetime(y + 1, 1, 1).date()
        else:
            siguiente = timezone.datetime(y, m + 1, 1).date()
        inicio = timezone.datetime(y, m, 1).date()
        creados_data.append(
            Proyecto.objects.filter(
                creado__date__gte=inicio, creado__date__lt=siguiente).count())

    # Avance promedio por mes segun fecha de creacion del proyecto.
    avance_mes = []
    for i in range(5, -1, -1):
        y = primero.year
        m = primero.month - i
        while m <= 0:
            m += 12
            y -= 1
        if m == 12:
            siguiente = timezone.datetime(y + 1, 1, 1).date()
        else:
            siguiente = timezone.datetime(y, m + 1, 1).date()
        inicio = timezone.datetime(y, m, 1).date()
        p = (Proyecto.objects.filter(
            creado__date__gte=inicio, creado__date__lt=siguiente)
            .aggregate(v=Avg('avance'))['v'] or 0)
        avance_mes.append(round(p, 1))

    recientes = (ActualizacionProyecto.objects
                 .select_related('proyecto').order_by('-creado')[:8])
    actividad = [{
        'codigo': a.proyecto.codigo,
        'proyecto': a.proyecto.nombre,
        'titulo': a.titulo,
        'avance': a.avance,
        'cuando': a.creado.strftime('%d/%m %H:%M'),
    } for a in recientes]

    # Datos extra que el JS del panel usa para refrescar sin recargar:
    # barras de avance por proyecto, lista de "por atender" y total bitacora.
    avance_por_proyecto = [
        {'codigo': p.codigo, 'nombre': p.nombre, 'avance': p.avance}
        for p in top
    ]
    por_atender = [{
        'codigo': p.codigo,
        'nombre': p.nombre,
        'estado': p.estado,
        'estado_display': p.get_estado_display(),
        'avance': p.avance,
    } for p in proyectos[:5]]
    total_actividad = ActualizacionProyecto.objects.count()

    return {
        'total': total,
        'activos': activos,
        'entregados': entregados,
        'avance_prom': round(avance_prom, 1),
        'actualizados_hoy': actualizados_hoy,
        'nuevos_30': nuevos_30,
        'por_estado': por_estado,
        'estados_labels': estados_labels,
        'estados_data': estados_data,
        'estados_valores': estados_valores,
        'top_labels': top_labels,
        'top_nombres': top_nombres,
        'top_avances': top_avances,
        'meses_labels': meses_labels,
        'meses_updates': meses_data,
        'meses_creados': creados_data,
        'meses_avance': avance_mes,
        'actividad': actividad,
        'avance_por_proyecto': avance_por_proyecto,
        'por_atender': por_atender,
        'total_actividad': total_actividad,
    }
