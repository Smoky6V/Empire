"""Modelos del módulo de seguimiento de proyectos por código de compra.

Flujo pedido:
  1. El cliente compra un sistema -> el admin/staff crea un Proyecto y el
     sistema genera un código único (ej: EMP-XXXXXX) que se entrega al cliente.
  2. El usuario normal ingresa ese código en "Mi proyecto" y vincula el
     proyecto a su cuenta (o lo consulta públicamente solo con el código).
  3. El admin actualiza el avance/etapas del proyecto desde el panel admin y
     el usuario lo ve reflejado en tiempo real (polling cada 10s al endpoint
     JSON, sin necesidad de recargar la página).
"""

import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone


def generar_codigo_proyecto():
    """Genera un código único tipo EMP-A1B2C3 (6 caracteres alfanuméricos)."""
    alfabeto = string.ascii_uppercase + string.digits
    # Se excluyen caracteres confusos 0/O y 1/I para dictado telefónico.
    alfabeto = alfabeto.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    while True:
        codigo = 'EMP-' + ''.join(secrets.choice(alfabeto) for _ in range(6))
        # La verificación de unicidad real se hace en save(); aquí solo se
        # genera el candidato para no importar el modelo a nivel de módulo.
        return codigo


class Proyecto(models.Model):
    """Un sistema vendido a un cliente, rastreable por código de compra."""

    class Estado(models.TextChoices):
        PLANIFICACION = 'planificacion', 'En planificación'
        DISENO = 'diseno', 'En diseño'
        DESARROLLO = 'desarrollo', 'En desarrollo'
        REVISION = 'revision', 'En revisión'
        PRUEBAS = 'pruebas', 'En pruebas'
        PRODUCCION = 'produccion', 'En producción'
        ENTREGADO = 'entregado', 'Entregado'
        PAUSADO = 'pausado', 'Pausado'

    nombre = models.CharField(max_length=200, help_text='Nombre del sistema vendido.')
    descripcion = models.TextField(blank=True, default='')
    codigo = models.CharField(
        max_length=12, unique=True, editable=False,
        help_text='Código de seguimiento que se entrega al cliente al comprar.',
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PLANIFICACION)
    avance = models.PositiveSmallIntegerField(
        default=0, help_text='Porcentaje de avance 0-100 que actualiza el admin.',
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='proyectos',
        help_text='Usuario dueño del proyecto (se vincula con el código).',
    )
    email_cliente = models.EmailField(
        blank=True, default='',
        help_text='Correo del comprador al momento de la venta (respaldo).',
    )
    fecha_entrega_estimada = models.DateField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-actualizado']
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Reintenta hasta encontrar un código libre (colisión improbable).
            for _ in range(20):
                candidato = generar_codigo_proyecto()
                if not Proyecto.objects.filter(codigo=candidato).exists():
                    self.codigo = candidato
                    break
            if not self.codigo:
                raise ValueError('No se pudo generar un código único de proyecto.')
        # Sanea el avance al rango válido.
        self.avance = max(0, min(100, int(self.avance or 0)))
        super().save(*args, **kwargs)

    @property
    def estado_display(self):
        return self.get_estado_display()


class ActualizacionProyecto(models.Model):
    """Entradas de bitácora que el admin agrega a medida que avanza el proyecto.

    Cada actualización queda con fecha y el usuario la ve en su línea de
    tiempo en tiempo real (vía polling al endpoint JSON).
    """

    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name='actualizaciones',
    )
    titulo = models.CharField(max_length=200)
    detalle = models.TextField(blank=True, default='')
    avance = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Si se indica, actualiza también el avance del proyecto.',
    )
    creado = models.DateTimeField(default=timezone.now)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='actualizaciones_proyecto',
    )

    class Meta:
        ordering = ['-creado']
        verbose_name = 'Actualización de proyecto'
        verbose_name_plural = 'Actualizaciones de proyecto'

    def __str__(self):
        return f'{self.proyecto.codigo}: {self.titulo}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Si la actualización trae avance, se refleja en el proyecto padre.
        if self.avance is not None:
            self.proyecto.avance = max(0, min(100, int(self.avance)))
            self.proyecto.save(update_fields=['avance', 'actualizado'])
