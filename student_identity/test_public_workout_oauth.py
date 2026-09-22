"""
ARQUIVO: testes do login por Google do corredor de treinos.

POR QUE ELE EXISTE:
- fecha o "pronto quando" #1 da Onda B1 (docs/plans/public-workouts-produtizacao-corda.md)
  que faltava: "aluno entra com Google e continua logado". O e-mail
  (test_public_workout_login.py) ja cobria o resto.
- prova a isolacao: o callback do corredor nunca cria/altera StudentIdentity
  nem usa o cookie/callback do /aluno/ — so PublicWorkoutAccount e o cookie
  proprio do corredor.
"""

from unittest.mock import Mock, patch

from django.test import Client, RequestFactory, TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import PublicWorkoutAccount

from .models import StudentIdentity, StudentIdentityProvider, StudentIdentityStatus
from .oauth_providers import OAuthProviderError
from .public_workout_oauth import build_public_workout_oauth_state
from .public_workout_session import read_public_workout_session_value
from .public_workout_views import _build_public_workout_google_provider


def _mock_google_provider(*, email: str, photo_url: str = '') -> Mock:
    provider = Mock()
    provider.get_authorize_url.return_value = (
        'https://accounts.google.com/o/oauth2/v2/auth?redirect_uri=https%3A%2F%2Ftestserver%2Ftreinos%2Flogin%2Fgoogle%2Fcallback'
    )
    provider.exchange_code.return_value = Mock(
        provider='google', email=email, provider_subject='sub-1', photo_url=photo_url,
    )
    return provider


class PublicWorkoutGoogleStartViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_redirects_to_google_authorize_url(self, provider_factory_mock):
        provider_factory_mock.return_value = _mock_google_provider(email='aluno@example.com')

        response = self.client.get(reverse('public-workout-oauth-google-start'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response['Location'])
        provider_factory_mock.return_value.get_authorize_url.assert_called_once()

    @override_settings(STUDENT_GOOGLE_OAUTH_CLIENT_ID='google-client-id', STUDENT_GOOGLE_OAUTH_CLIENT_SECRET='secret')
    def test_real_provider_builds_treinos_callback_not_aluno(self):
        """Sem mock: prova que _build_public_workout_google_provider aponta
        pro callback do corredor, nao pro de /aluno/ (o ponto real de risco
        desta mudanca — ver BaseOAuthProvider.callback_url_name)."""
        request = RequestFactory().get('/treinos/login/google')

        authorize_url = _build_public_workout_google_provider().get_authorize_url(state='irrelevante', request=request)

        self.assertIn('%2Ftreinos%2Flogin%2Fgoogle%2Fcallback', authorize_url)
        self.assertNotIn('aluno', authorize_url)

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_error_from_provider_redirects_to_login_with_flag(self, provider_factory_mock):
        provider = Mock()
        provider.get_authorize_url.side_effect = OAuthProviderError('google-client-id-missing')
        provider_factory_mock.return_value = provider

        response = self.client.get(reverse('public-workout-oauth-google-start'))

        self.assertRedirects(response, f"{reverse('public-workout-login')}?error=google_indisponivel")

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_next_url_travels_inside_signed_state(self, provider_factory_mock):
        captured_state = {}

        def fake_authorize_url(*, state, request):
            captured_state['state'] = state
            return 'https://accounts.google.com/o/oauth2/v2/auth?x=1'

        provider = Mock()
        provider.get_authorize_url.side_effect = fake_authorize_url
        provider_factory_mock.return_value = provider

        self.client.get(reverse('public-workout-oauth-google-start'), {'next': '/renan/juliana'})

        from .public_workout_oauth import read_public_workout_oauth_state

        payload = read_public_workout_oauth_state(captured_state['state'])
        self.assertEqual(payload['next_url'], '/renan/juliana')

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_unsafe_next_is_dropped_from_state(self, provider_factory_mock):
        captured_state = {}

        def fake_authorize_url(*, state, request):
            captured_state['state'] = state
            return 'https://accounts.google.com/o/oauth2/v2/auth?x=1'

        provider = Mock()
        provider.get_authorize_url.side_effect = fake_authorize_url
        provider_factory_mock.return_value = provider

        self.client.get(reverse('public-workout-oauth-google-start'), {'next': 'https://evil.example.com/'})

        from .public_workout_oauth import read_public_workout_oauth_state

        payload = read_public_workout_oauth_state(captured_state['state'])
        self.assertEqual(payload['next_url'], '')


class PublicWorkoutGoogleCallbackViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_creates_account_and_sets_session_cookie_for_new_email(self, provider_factory_mock):
        provider_factory_mock.return_value = _mock_google_provider(email='novo@example.com')
        state = build_public_workout_oauth_state(next_url='')

        response = self.client.get(
            reverse('public-workout-oauth-google-callback'),
            {'code': 'oauth-code', 'state': state},
        )

        self.assertEqual(response.status_code, 200)
        account = PublicWorkoutAccount.objects.get(email='novo@example.com')
        self.assertIsNotNone(account.last_login_at)
        self.assertIn('octobox_treinos_session', response.cookies)
        session_payload = read_public_workout_session_value(response.cookies['octobox_treinos_session'].value)
        self.assertEqual(session_payload['account_id'], account.id)

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_stores_the_google_photo_on_the_account(self, provider_factory_mock):
        # Renan: "usar a foto do Google... no avatar" -- confere que o
        # callback repassa identity.photo_url pra resolve_or_create_
        # public_workout_account, nao so' o e-mail.
        provider_factory_mock.return_value = _mock_google_provider(
            email='com-foto@example.com', photo_url='https://lh3.googleusercontent.com/a/foto-real',
        )
        state = build_public_workout_oauth_state(next_url='')

        self.client.get(reverse('public-workout-oauth-google-callback'), {'code': 'oauth-code', 'state': state})

        account = PublicWorkoutAccount.objects.get(email='com-foto@example.com')
        self.assertEqual(account.photo_url, 'https://lh3.googleusercontent.com/a/foto-real')

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_reuses_existing_account_instead_of_duplicating(self, provider_factory_mock):
        existing = PublicWorkoutAccount.objects.create(email='ja-existe@example.com')
        provider_factory_mock.return_value = _mock_google_provider(email='ja-existe@example.com')
        state = build_public_workout_oauth_state(next_url='')

        self.client.get(reverse('public-workout-oauth-google-callback'), {'code': 'oauth-code', 'state': state})

        self.assertEqual(PublicWorkoutAccount.objects.filter(email='ja-existe@example.com').count(), 1)
        existing.refresh_from_db()
        self.assertIsNotNone(existing.last_login_at)

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_links_weakly_to_existing_student_identity_by_email(self, provider_factory_mock):
        identity = StudentIdentity.objects.create(
            email='dupla@example.com',
            provider=StudentIdentityProvider.GOOGLE,
            provider_subject='aluno-subject',
            status=StudentIdentityStatus.ACTIVE,
            box_root_slug='box-x',
            primary_box_root_slug='box-x',
        )
        provider_factory_mock.return_value = _mock_google_provider(email='dupla@example.com')
        state = build_public_workout_oauth_state(next_url='')

        self.client.get(reverse('public-workout-oauth-google-callback'), {'code': 'oauth-code', 'state': state})

        account = PublicWorkoutAccount.objects.get(email='dupla@example.com')
        self.assertEqual(account.student_identity_id, identity.id)
        # Informativo, nunca autoritativo (N5): nenhuma escrita do lado da StudentIdentity.
        identity.refresh_from_db()

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_redirects_to_next_url_when_present_in_state(self, provider_factory_mock):
        provider_factory_mock.return_value = _mock_google_provider(email='vai-pro-treino@example.com')
        state = build_public_workout_oauth_state(next_url='/renan/juliana')

        response = self.client.get(
            reverse('public-workout-oauth-google-callback'),
            {'code': 'oauth-code', 'state': state},
        )

        self.assertRedirects(response, '/renan/juliana', fetch_redirect_response=False)

    def test_missing_state_shows_invalid_link_error_and_creates_no_account(self):
        response = self.client.get(reverse('public-workout-oauth-google-callback'), {'code': 'oauth-code'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expirou ou já foi usado')
        self.assertEqual(PublicWorkoutAccount.objects.count(), 0)

    def test_missing_code_shows_invalid_link_error(self):
        state = build_public_workout_oauth_state(next_url='')

        response = self.client.get(reverse('public-workout-oauth-google-callback'), {'state': state})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expirou ou já foi usado')
        self.assertEqual(PublicWorkoutAccount.objects.count(), 0)

    def test_tampered_state_signature_shows_invalid_link_error(self):
        response = self.client.get(
            reverse('public-workout-oauth-google-callback'),
            {'code': 'oauth-code', 'state': 'lixo-nao-assinado'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expirou ou já foi usado')
        self.assertEqual(PublicWorkoutAccount.objects.count(), 0)

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_google_exchange_failure_shows_error_and_creates_no_account(self, provider_factory_mock):
        provider = Mock()
        provider.exchange_code.side_effect = OAuthProviderError('google-token-exchange-failed')
        provider_factory_mock.return_value = provider
        state = build_public_workout_oauth_state(next_url='')

        response = self.client.get(
            reverse('public-workout-oauth-google-callback'),
            {'code': 'oauth-code', 'state': state},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Não deu pra entrar com o Google')
        self.assertEqual(PublicWorkoutAccount.objects.count(), 0)

    @patch('student_identity.public_workout_views._build_public_workout_google_provider')
    def test_callback_never_creates_or_touches_student_identity(self, provider_factory_mock):
        provider_factory_mock.return_value = _mock_google_provider(email='so-corredor@example.com')
        state = build_public_workout_oauth_state(next_url='')

        before = StudentIdentity.objects.count()
        self.client.get(reverse('public-workout-oauth-google-callback'), {'code': 'oauth-code', 'state': state})

        self.assertEqual(StudentIdentity.objects.count(), before)
