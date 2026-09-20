from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import ActualizacionProyecto, Proyecto

User = get_user_model()


class ProyectoCodigoTests(TestCase):
    def test_crear_proyecto_genera_codigo_unico(self):
        p1 = Proyecto.objects.create(nombre='Sistema A')
        p2 = Proyecto.objects.create(nombre='Sistema B')
        self.assertTrue(p1.codigo.startswith('EMP-'))
        self.assertNotEqual(p1.codigo, p2.codigo)

    def test_avance_se_sanea_a_0_100(self):
        p = Proyecto.objects.create(nombre='X', avance=150)
        self.assertEqual(p.avance, 100)
        p.avance = -5
        p.save()
        self.assertEqual(p.avance, 0)

    def test_actualizacion_refleja_avance_en_proyecto(self):
        p = Proyecto.objects.create(nombre='Y', avance=10)
        ActualizacionProyecto.objects.create(proyecto=p, titulo='Fase 1', avance=55)
        p.refresh_from_db()
        self.assertEqual(p.avance, 55)


class ProyectoVistasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cli', email='c@c.com', password='ClaveSegura2024!')
        g, _ = Group.objects.get_or_create(name='Usuarios')
        self.user.groups.add(g)
        self.admin = User.objects.create_user(username='adm', email='a@a.com', password='ClaveSegura2024!')
        g2, _ = Group.objects.get_or_create(name='Administradores')
        self.admin.groups.add(g2)
        self.proyecto = Proyecto.objects.create(nombre='Tienda', estado='desarrollo', avance=30)

    def test_buscar_publico_por_codigo(self):
        r = self.client.get('/proyectos/rastrear/', {'codigo': self.proyecto.codigo})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.proyecto.codigo)

    def test_estado_json_publico_sin_datos_sensibles(self):
        r = self.client.get(f'/proyectos/api/estado/{self.proyecto.codigo}/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['codigo'], self.proyecto.codigo)
        self.assertNotIn('cliente', data.keys())
        self.assertNotIn('email', data.keys())

    def test_vincular_codigo_a_mi_cuenta(self):
        self.client.login(username='cli', password='ClaveSegura2024!')
        r = self.client.post('/proyectos/mis-proyectos/', {'codigo': self.proyecto.codigo}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.cliente, self.user)

    def test_no_se_puede_robar_codigo_ajeno(self):
        otro = User.objects.create_user(username='otro', email='o@o.com', password='ClaveSegura2024!')
        self.proyecto.cliente = otro
        self.proyecto.save()
        self.client.login(username='cli', password='ClaveSegura2024!')
        self.client.post('/proyectos/mis-proyectos/', {'codigo': self.proyecto.codigo})
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.cliente, otro)

    def test_admin_crea_proyecto_y_publica_avance(self):
        self.client.login(username='adm', password='ClaveSegura2024!')
        r = self.client.post('/proyectos/gestion/nuevo/', {
            'nombre': 'ERP', 'descripcion': 'Sistema', 'estado': 'desarrollo',
            'avance': 5, 'email_cliente': 'c@c.com',
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        nuevo = Proyecto.objects.get(nombre='ERP')
        self.assertTrue(nuevo.codigo.startswith('EMP-'))
        r2 = self.client.post(f'/proyectos/gestion/{nuevo.codigo}/', {
            'titulo': 'Avance 1', 'detalle': 'Listo modulo X', 'avance': 25,
        }, follow=True)
        self.assertEqual(r2.status_code, 200)
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.avance, 25)

    def test_usuario_normal_no_entra_a_gestion(self):
        self.client.login(username='cli', password='ClaveSegura2024!')
        r = self.client.get('/proyectos/gestion/')
        self.assertEqual(r.status_code, 403)
