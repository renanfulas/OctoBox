from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PublicLandingViewTests(TestCase):
    def test_home_renders_marketing_landing_for_anonymous_user(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu box, sem ruido. Sua operacao, em controle.')
        self.assertContains(response, reverse('login'))

    def test_home_redirects_authenticated_user_to_role_operations(self):
        user = get_user_model().objects.create_user(
            username='landing-user',
            email='landing@example.com',
            password='SenhaForte@123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('role-operations'), fetch_redirect_response=False)
