from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse


@override_settings(
    ALLOWED_HOSTS=['testserver', 'www.octoboxfit.com.br', 'app.octoboxfit.com.br', 'octoboxfit.com.br'],
    STUDENT_OAUTH_PUBLIC_BASE_URL='https://app.octoboxfit.com.br',
)
class RequestTimingHeadersTests(TestCase):
    def test_public_responses_keep_server_timing_but_hide_internal_debug_headers_by_default(self):
        response = self.client.get(reverse('home'), HTTP_HOST='www.octoboxfit.com.br')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Server-Timing', response)
        self.assertNotIn('X-OctoBox-Session-Engine', response)
        self.assertNotIn('X-OctoBox-Session-Key-Present', response)
        self.assertNotIn('X-OctoBox-User-Authenticated', response)
        self.assertNotIn('X-OctoBox-Shell-Cache-Hit', response)

    @override_settings(REQUEST_TIMING_EXPOSE_DEBUG_HEADERS=True)
    def test_debug_headers_can_be_explicitly_enabled_for_internal_diagnostics(self):
        response = self.client.get(reverse('home'), HTTP_HOST='www.octoboxfit.com.br')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Server-Timing', response)
        self.assertIn('X-OctoBox-Session-Engine', response)
        self.assertIn('X-OctoBox-Session-Key-Present', response)
        self.assertIn('X-OctoBox-User-Authenticated', response)
