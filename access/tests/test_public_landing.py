from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings


@override_settings(
    ALLOWED_HOSTS=['testserver', 'www.octoboxfit.com.br', 'app.octoboxfit.com.br', 'octoboxfit.com.br'],
    STUDENT_OAUTH_PUBLIC_BASE_URL='https://app.octoboxfit.com.br',
)
class PublicLandingViewTests(TestCase):
    def test_home_renders_marketing_landing_for_anonymous_user(self):
        response = self.client.get(reverse('home'), HTTP_HOST='www.octoboxfit.com.br')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seu box com presença premium. Sua operação no controle.')
        self.assertContains(response, 'https://app.octoboxfit.com.br/login/')

    def test_home_redirects_anonymous_user_to_login_on_app_host(self):
        response = self.client.get(reverse('home'), HTTP_HOST='app.octoboxfit.com.br')

        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)

    def test_home_redirects_authenticated_user_to_app_host_role_operations(self):
        user = get_user_model().objects.create_user(
            username='landing-user',
            email='landing@example.com',
            password='SenhaForte@123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'), HTTP_HOST='www.octoboxfit.com.br')

        self.assertRedirects(
            response,
            'https://app.octoboxfit.com.br/operacao/',
            fetch_redirect_response=False,
        )

    def test_login_route_redirects_to_app_host_when_requested_from_marketing_host(self):
        response = self.client.get(reverse('login'), HTTP_HOST='www.octoboxfit.com.br')

        self.assertRedirects(
            response,
            'https://app.octoboxfit.com.br/login/',
            fetch_redirect_response=False,
        )
