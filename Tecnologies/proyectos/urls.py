from django.urls import path

from . import views

app_name = 'proyectos'

urlpatterns = [
    path('rastrear/', views.buscar_por_codigo, name='buscar'),
    path('api/estado/<str:codigo>/', views.proyecto_estado_json, name='estado_json'),
    path('mis-proyectos/', views.mis_proyectos, name='mis'),
    path('mis-proyectos/<str:codigo>/', views.detalle_proyecto, name='detalle'),
    path('gestion/', views.admin_lista, name='admin_lista'),
    path('gestion/nuevo/', views.admin_crear, name='admin_crear'),
    path('gestion/<str:codigo>/', views.admin_detalle, name='admin_detalle'),
    path('gestion/<str:codigo>/editar/', views.admin_editar, name='admin_editar'),
]
