from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse


@override_settings(
    ALLOWED_HOSTS=['testserver', 'app.octoboxfit.com.br'],
    STUDENT_OAUTH_PUBLIC_BASE_URL='https://app.octoboxfit.com.br',
)
class LoginSecurityTests(TestCase):
    def test_staff_login_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            reverse('login-staff'),
            {'username': 'unknown-user', 'password': 'wrong-password'},
            HTTP_HOST='app.octoboxfit.com.br',
            HTTP_REFERER='https://app.octoboxfit.com.br/login/funcionario/',
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_login_ignores_external_next_url_in_form_context(self):
        response = self.client.get(
            reverse('login-staff'),
            {'next': '//evil.example/path'},
            HTTP_HOST='app.octoboxfit.com.br',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="next" value=""')
        self.assertNotContains(response, 'evil.example')

    def test_protected_operation_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse('role-operations'), HTTP_HOST='app.octoboxfit.com.br')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f"{reverse('login')}?next={reverse('role-operations')}")
