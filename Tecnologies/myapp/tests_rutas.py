from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class ProteccionDeRutasTests(TestCase):
    """Ningun rol sin permiso puede entrar a una ruta protegida escribiendo
    el link en el navegador: el admin de Django queda oculto (404) y las
    vistas con @login_required mandan al login propio con ?next=."""

    ADMIN_URL = '/admin/'
    PROTEGIDA = '/proyectos/mis-proyectos/'

    def setUp(self):
        cache.clear()
        self.usuarios_group, _ = Group.objects.get_or_create(name='Usuarios')
        self.normal = User.objects.create_user(
            username='normal', email='n@n.com', password='ClaveSegura2024!')
        self.normal.groups.add(self.usuarios_group)
        self.staff = User.objects.create_user(
            username='jefe', email='j@j.com', password='ClaveSegura2024!')
        self.staff.is_staff = True
        self.staff.save()

    # --- Admin de Django oculto para quien no es staff -------------------

    def test_admin_anonimo_devuelve_404(self):
        r = self.client.get(self.ADMIN_URL)
        self.assertEqual(r.status_code, 404)

    def test_admin_login_anonimo_devuelve_404(self):
        # Ni siquiera el formulario de acceso del admin queda expuesto.
        r = self.client.get(self.ADMIN_URL + 'login/')
        self.assertEqual(r.status_code, 404)

    def test_admin_usuario_normal_devuelve_404(self):
        self.client.login(username='normal', password='ClaveSegura2024!')
        r = self.client.get(self.ADMIN_URL)
        self.assertEqual(r.status_code, 404)

    def test_admin_no_redirige_al_login_del_admin(self):
        # Antes, un anonimo veia el formulario del admin; ahora ni se nombra.
        r = self.client.get(self.ADMIN_URL)
        self.assertNotIn('admin/login', r.content.decode('utf-8'))

    def test_admin_staff_si_entra(self):
        self.client.login(username='jefe', password='ClaveSegura2024!')
        r = self.client.get(self.ADMIN_URL)
        self.assertIn(r.status_code, (200, 302))

    def test_url_del_admin_se_reversa_igual(self):
        # Los {% url 'admin:...' %} siguen funcionando con el prefijo de settings.
        self.assertEqual(reverse('admin:index'), self.ADMIN_URL)

    # --- Vistas con login_required --------------------------------------

    def test_ruta_protegida_anonimo_redirige_al_login_propio(self):
        r = self.client.get(self.PROTEGIDA)
        self.assertEqual(r.status_code, 302)
        # Antes apuntaba a /accounts/login/ (inexistente): ahora es el login real
        # y conserva el destino para volver despues de iniciar sesion.
        self.assertEqual(r.url, f"{reverse('login')}?next={self.PROTEGIDA}")

    def test_login_con_next_valido_vuelve_a_la_ruta_pedida(self):
        r = self.client.post(reverse('login'), {
            'username': 'normal', 'password': 'ClaveSegura2024!',
            'next': self.PROTEGIDA,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, self.PROTEGIDA)

    def test_login_ignora_next_externo(self):
        # Open redirect: un destino de otro dominio se descarta.
        for malo in ('https://sitio-falso.com', '//sitio-falso.com', 'http://sitio-falso.com/x'):
            r = self.client.post(reverse('login'), {
                'username': 'normal', 'password': 'ClaveSegura2024!',
                'next': malo,
            })
            self.assertEqual(r.status_code, 302)
            self.assertEqual(r.url, reverse('index'))

    def test_login_sin_next_va_al_index(self):
        r = self.client.post(reverse('login'), {
            'username': 'normal', 'password': 'ClaveSegura2024!',
        })
        self.assertEqual(r.url, reverse('index'))

    def test_gestion_de_proyectos_denegada_a_usuario_normal(self):
        self.client.login(username='normal', password='ClaveSegura2024!')
        for ruta in ('/proyectos/gestion/', '/proyectos/gestion/nuevo/'):
            self.assertEqual(self.client.get(ruta).status_code, 403)

    def test_gestion_de_proyectos_necesita_sesion(self):
        r = self.client.get('/proyectos/gestion/')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse('login')))

    # --- Paginas de error con la identidad del sitio ---------------------

    def test_403_usa_plantilla_del_sitio(self):
        self.client.login(username='normal', password='ClaveSegura2024!')
        r = self.client.get('/proyectos/gestion/')
        self.assertEqual(r.status_code, 403)
        self.assertTemplateUsed(r, '403.html')

    def test_404_usa_plantilla_del_sitio(self):
        r = self.client.get('/admin/')
        self.assertEqual(r.status_code, 404)
        self.assertTemplateUsed(r, '404.html')
