from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class RegistroTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_registro_exitoso_crea_usuario_hasheado_y_grupo_usuarios(self):
        response = self.client.post(reverse('register'), {
            'username': 'nuevo',
            'email': 'nuevo@example.com',
            'password': 'ClaveSegura2024!',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username='nuevo')
        self.assertTrue(user.password.startswith('pbkdf2_'))
        self.assertTrue(user.groups.filter(name='Usuarios').exists())
        # El registro deja al usuario con sesion iniciada.
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_registro_rechaza_contrasena_debil(self):
        response = self.client.post(reverse('register'), {
            'username': 'debil',
            'email': 'debil@example.com',
            'password': '123',
        }, follow=True)
        self.assertFalse(User.objects.filter(username='debil').exists())

    def test_registro_rechaza_username_duplicado(self):
        User.objects.create_user(username='existente', email='a@a.com', password='ClaveSegura2024!')
        response = self.client.post(reverse('register'), {
            'username': 'existente',
            'email': 'otro@example.com',
            'password': 'ClaveSegura2024!',
        }, follow=True)
        self.assertEqual(User.objects.filter(username='existente').count(), 1)

    def test_registro_rechaza_email_duplicado(self):
        User.objects.create_user(username='uno', email='dup@example.com', password='ClaveSegura2024!')
        self.client.post(reverse('register'), {
            'username': 'dos',
            'email': 'dup@example.com',
            'password': 'ClaveSegura2024!',
        }, follow=True)
        self.assertFalse(User.objects.filter(username='dos').exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='carlos', email='c@c.com', password='ClaveSegura2024!')

    def test_login_correcto(self):
        response = self.client.post(reverse('login'), {
            'username': 'carlos', 'password': 'ClaveSegura2024!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_password_incorrecta(self):
        response = self.client.post(reverse('login'), {
            'username': 'carlos', 'password': 'incorrecta',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_logout(self):
        self.client.login(username='carlos', password='ClaveSegura2024!')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_login_rate_limited_tras_varios_intentos(self):
        for _ in range(10):
            self.client.post(reverse('login'), {'username': 'carlos', 'password': 'mala'},
                              REMOTE_ADDR='10.0.0.1')
        response = self.client.post(reverse('login'), {'username': 'carlos', 'password': 'mala'},
                                     REMOTE_ADDR='10.0.0.1')
        self.assertEqual(response.status_code, 429)


class AutorizacionPorRolTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name='Administradores')
        self.usuarios_group, _ = Group.objects.get_or_create(name='Usuarios')

    def test_anonimo_ve_inicio_publico(self):
        response = self.client.get(reverse('index'))
        self.assertTemplateUsed(response, 'inicio.html')

    def test_usuario_normal_ve_area_privada(self):
        user = User.objects.create_user(username='u1', email='u1@u.com', password='ClaveSegura2024!')
        user.groups.add(self.usuarios_group)
        self.client.login(username='u1', password='ClaveSegura2024!')
        response = self.client.get(reverse('index'))
        self.assertTemplateUsed(response, 'inicioPriv.html')

    def test_administrador_ve_panel_admin(self):
        admin = User.objects.create_user(username='admin1', email='a1@a.com', password='ClaveSegura2024!')
        admin.groups.add(self.admin_group)
        self.client.login(username='admin1', password='ClaveSegura2024!')
        response = self.client.get(reverse('index'))
        self.assertTemplateUsed(response, 'admindash.html')

    def test_usuario_de_otro_grupo_no_ve_panel_admin(self):
        """Un usuario sin el grupo Administradores nunca debe ver admindash.html."""
        user = User.objects.create_user(username='u2', email='u2@u.com', password='ClaveSegura2024!')
        user.groups.add(self.usuarios_group)
        self.client.login(username='u2', password='ClaveSegura2024!')
        response = self.client.get(reverse('index'))
        self.assertTemplateNotUsed(response, 'admindash.html')

class SesionRedireccionesTests(TestCase):
    """Un usuario con sesion no debe volver a ver /login ni /register.

    Con sesion iniciada esas vistas redirigen a 'index' (cada rol ve su
    plantilla), y las tres vistas se marcan como no cacheables para que el
    boton "atras" del navegador no muestre copias guardadas tras el logout.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='ana', email='ana@a.com', password='ClaveSegura2024!')

    def _entrar(self):
        self.client.login(username='ana', password='ClaveSegura2024!')

    def test_login_con_sesion_redirige_a_index(self):
        self._entrar()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

    def test_login_con_sesion_ignora_post_al_formulario(self):
        # Con sesion ni siquiera se procesa el POST: se redirige igual,
        # asi no se puede cambiar de cuenta sin cerrar sesion antes.
        self._entrar()
        response = self.client.post(
            reverse('login'), {'username': 'otro', 'password': 'x'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

    def test_register_con_sesion_redirige_a_index(self):
        self._entrar()
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

    def test_register_con_sesion_no_crea_otra_cuenta(self):
        self._entrar()
        response = self.client.post(reverse('register'), {
            'username': 'nuevo2', 'email': 'n2@n.com',
            'password': 'ClaveSegura2024!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))
        self.assertFalse(User.objects.filter(username='nuevo2').exists())

    def test_tras_logout_login_vuelve_a_mostrar_el_formulario(self):
        # Flujo completo pedido: cerrar sesion y volver a /login muestra el
        # formulario porque la sesion ya no existe.
        self._entrar()
        self.client.get(reverse('logout'))
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_no_cacheable(self):
        response = self.client.get(reverse('login'))
        self.assertIn('no-store', response['Cache-Control'])

    def test_register_no_cacheable(self):
        response = self.client.get(reverse('register'))
        self.assertIn('no-store', response['Cache-Control'])

    def test_index_no_cacheable_para_el_boton_atras(self):
        self._entrar()
        response = self.client.get(reverse('index'))
        self.assertIn('no-store', response['Cache-Control'])

