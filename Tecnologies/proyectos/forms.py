from django import forms

from .models import ActualizacionProyecto, Proyecto


class VincularCodigoForm(forms.Form):
    """El usuario normal pega aquí el código que recibió al comprar."""
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
    """Formulario del admin para crear/editar el proyecto vendido."""

    class Meta:
        model = Proyecto
        fields = (
            'nombre', 'descripcion', 'estado', 'avance',
            'cliente', 'email_cliente', 'fecha_entrega_estimada',
        )
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }


class ActualizacionForm(forms.ModelForm):
    """Formulario del admin para publicar un avance en la línea de tiempo."""

    class Meta:
        model = ActualizacionProyecto
        fields = ('titulo', 'detalle', 'avance')
        widgets = {
            'detalle': forms.Textarea(attrs={'rows': 3}),
        }
