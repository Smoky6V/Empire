from django import forms

from .models import ActualizacionProyecto, Proyecto


class VincularCodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=12, label='Código de tu proyecto',
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej: EMP-A1B2C3',
            'autocomplete': 'off',
            'class': 'emp-track__input',
        }),
    )

    def clean_codigo(self):
        return self.cleaned_data['codigo'].strip().upper()


class ProyectoAdminForm(forms.ModelForm):
    """Formulario del admin para crear/editar el proyecto vendido.

    Se usa tanto en /proyectos/gestion/* como en el panel de inicio.html.
    El campo `cliente` es opcional: acepta username o email y lo resuelve
    al usuario real en la vista (asi el admin no necesita saber el id).
    """

    cliente_ref = forms.CharField(
        required=False, label='Cliente (usuario o correo)',
        help_text='Escribe el username o correo del cliente. Opcional.',
        widget=forms.TextInput(attrs={'placeholder': 'ej: juanito o juan@correo.com'}),
    )

    class Meta:
        model = Proyecto
        fields = (
            'nombre', 'descripcion', 'estado', 'avance',
            'email_cliente', 'fecha_entrega_estimada',
        )
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }


class ActualizacionForm(forms.ModelForm):
    class Meta:
        model = ActualizacionProyecto
        fields = ('titulo', 'detalle', 'avance')
        widgets = {
            'detalle': forms.Textarea(attrs={'rows': 3}),
        }


class AvanceRapidoForm(forms.Form):
    """Actualizacion rapida desde la tabla de inicio.html (sin salir)."""
    codigo = forms.CharField(max_length=12, widget=forms.HiddenInput())
    estado = forms.ChoiceField(choices=Proyecto.Estado.choices)
    avance = forms.IntegerField(min_value=0, max_value=100)
    titulo = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Avance de la semana (opcional)'}),
    )
    detalle = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Detalle para el cliente (opcional)'}),
    )

    def clean_codigo(self):
        return self.cleaned_data['codigo'].strip().upper()

