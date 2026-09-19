from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class CustomUserModelTests(TestCase):
    def test_create_user_hashes_password(self):
        user = User.objects.create_user(username='ana', email='ana@example.com', password='ClaveSegura2024!')
        self.assertNotEqual(user.password, 'ClaveSegura2024!')
        self.assertTrue(user.password.startswith('pbkdf2_'))
        self.assertTrue(user.check_password('ClaveSegura2024!'))

    def test_user_model_is_custom(self):
        self.assertEqual(User._meta.app_label, 'accounts')
        self.assertEqual(User._meta.model_name, 'usuario')
