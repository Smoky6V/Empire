import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class ApiAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='api_user', email='api@x.com', password='ClaveSegura2024!')

    def test_login_endpoint_publico_con_credenciales_correctas(self):
        response = self.client.post(reverse('api:login'),
                                     {'username': 'api_user', 'password': 'ClaveSegura2024!'},
                                     content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.json())

    def test_login_endpoint_credenciales_invalidas(self):
        response = self.client.post(reverse('api:login'),
                                     {'username': 'api_user', 'password': 'mala'},
                                     content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_login_endpoint_datos_invalidos(self):
        response = self.client.post(reverse('api:login'), {}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_login_endpoint_rate_limited(self):
        for _ in range(10):
            self.client.post(reverse('api:login'), {'username': 'x', 'password': 'y'},
                              content_type='application/json', REMOTE_ADDR='10.0.0.2')
        response = self.client.post(reverse('api:login'), {'username': 'x', 'password': 'y'},
                                     content_type='application/json', REMOTE_ADDR='10.0.0.2')
        self.assertEqual(response.status_code, 429)

    def test_me_endpoint_requiere_autenticacion(self):
        response = self.client.get(reverse('api:me'))
        self.assertEqual(response.status_code, 403)

    def test_me_endpoint_autenticado_devuelve_datos_propios_sin_password(self):
        self.client.login(username='api_user', password='ClaveSegura2024!')
        response = self.client.get(reverse('api:me'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['username'], 'api_user')
        self.assertNotIn('password', data)
        self.assertNotIn('is_staff', data)

    def test_me_patch_no_permite_escalar_privilegios(self):
        self.client.login(username='api_user', password='ClaveSegura2024!')
        self.client.patch(reverse('api:me'),
                           json.dumps({'is_staff': True, 'is_superuser': True, 'first_name': 'X'}),
                           content_type='application/json')
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.first_name, 'X')

    def test_password_change_requiere_old_password_correcto(self):
        self.client.login(username='api_user', password='ClaveSegura2024!')
        response = self.client.post(reverse('api:password-change'),
                                     json.dumps({'old_password': 'mala', 'new_password': 'OtraClaveSegura2024!'}),
                                     content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ClaveSegura2024!'))

    def test_password_change_rechaza_password_debil(self):
        self.client.login(username='api_user', password='ClaveSegura2024!')
        response = self.client.post(reverse('api:password-change'),
                                     json.dumps({'old_password': 'ClaveSegura2024!', 'new_password': '123'}),
                                     content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_password_change_exitoso_mantiene_sesion(self):
        self.client.login(username='api_user', password='ClaveSegura2024!')
        response = self.client.post(reverse('api:password-change'),
                                     json.dumps({'old_password': 'ClaveSegura2024!', 'new_password': 'OtraClaveSegura2024!'}),
                                     content_type='application/json')
        self.assertEqual(response.status_code, 204)
        # La sesion debe seguir activa (update_session_auth_hash aplicado).
        me = self.client.get(reverse('api:me'))
        self.assertEqual(me.status_code, 200)

    def test_logout_requiere_autenticacion(self):
        response = self.client.post(reverse('api:logout'))
        self.assertEqual(response.status_code, 403)

    def test_logout_cierra_sesion(self):
        self.client.login(username='api_user', password='ClaveSegura2024!')
        response = self.client.post(reverse('api:logout'))
        self.assertEqual(response.status_code, 204)
        me = self.client.get(reverse('api:me'))
        self.assertEqual(me.status_code, 403)
