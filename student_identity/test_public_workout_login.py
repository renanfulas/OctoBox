"""
ARQUIVO: testes do login por e-mail do corredor de treinos (Onda B1 do CORDA).

POR QUE ELE EXISTE:
- e o "pronto quando" #2 da Onda B1: aluno entra por link de e-mail e cai
  no treino dele (a parte de sessao — o roteamento pro treino certo e
  Onda B3). Cobre tambem o rate limit (S1) e a regra de uso unico (D.5/S3).
"""

from unittest.mock import Mock, patch

from django.core import mail, signing
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutLocalStorageBackup,
    PublicWorkoutLoginToken,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)

from .delivery_gateways import StudentEmailDeliveryError
from .models import StudentIdentity
from .public_workout_login import (
    PUBLIC_WORKOUT_LOGIN_CODE_ATTEMPTS_MAX,
    PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX,
    PublicWorkoutLoginCodeAttemptsExceeded,
    PublicWorkoutLoginRateLimitExceeded,
    login_code_for_token,
    request_login_token,
    resolve_or_create_public_workout_account,
    verify_login_code,
    verify_login_token,
)
from .public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    PUBLIC_WORKOUT_SESSION_SALT,
    attach_public_workout_session_cookie,
    build_public_workout_session_value,
    clear_public_workout_session_cookie,
    get_public_workout_account_id_from_request,
    get_verified_public_workout_account_id_from_request,
    read_public_workout_session_value,
)


class PublicWorkoutLoginTokenModelTests(TestCase):
    def test_fresh_token_is_valid(self):
        account = PublicWorkoutAccount.objects.create(email='fresh@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        self.assertTrue(token.is_valid)
        self.assertFalse(token.is_expired)

    def test_expired_token_is_not_valid(self):
        account = PublicWorkoutAccount.objects.create(email='expired@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.assertTrue(token.is_expired)
        self.assertFalse(token.is_valid)

    def test_used_token_is_not_valid_even_if_not_expired(self):
        account = PublicWorkoutAccount.objects.create(email='used@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        token.mark_used()
        token.save()
        self.assertFalse(token.is_valid)


class ResolveOrCreatePublicWorkoutAccountPhotoTests(TestCase):
    """`photo_url` (Renan: "usar a foto do Google... no avatar da tela
    Treino"): so' o login por Google tem uma foto pra oferecer -- login
    por e-mail (chama sem esse argumento) nunca pode apagar uma foto que
    ja existia (mesma pegadinha real ja corrigida pro /aluno/, PR
    "corrige foto do Google perdida")."""

    def test_new_account_via_google_gets_the_photo(self):
        account = resolve_or_create_public_workout_account(
            email='nova@example.com', photo_url='https://lh3.googleusercontent.com/a/foto1',
        )

        self.assertEqual(account.photo_url, 'https://lh3.googleusercontent.com/a/foto1')

    def test_new_account_via_email_has_no_photo(self):
        account = resolve_or_create_public_workout_account(email='so-email@example.com')

        self.assertEqual(account.photo_url, '')

    def test_existing_email_only_account_gains_photo_on_first_google_login(self):
        resolve_or_create_public_workout_account(email='depois-google@example.com')

        account = resolve_or_create_public_workout_account(
            email='depois-google@example.com', photo_url='https://lh3.googleusercontent.com/a/foto2',
        )

        self.assertEqual(account.photo_url, 'https://lh3.googleusercontent.com/a/foto2')

    def test_email_login_never_clears_an_existing_photo(self):
        resolve_or_create_public_workout_account(
            email='com-foto@example.com', photo_url='https://lh3.googleusercontent.com/a/foto3',
        )

        account = resolve_or_create_public_workout_account(email='com-foto@example.com')

        self.assertEqual(account.photo_url, 'https://lh3.googleusercontent.com/a/foto3')

    def test_google_login_refreshes_a_changed_photo(self):
        resolve_or_create_public_workout_account(
            email='foto-muda@example.com', photo_url='https://lh3.googleusercontent.com/a/velha',
        )

        account = resolve_or_create_public_workout_account(
            email='foto-muda@example.com', photo_url='https://lh3.googleusercontent.com/a/nova',
        )

        self.assertEqual(account.photo_url, 'https://lh3.googleusercontent.com/a/nova')


class RequestLoginTokenTests(TestCase):
    def test_does_not_create_account_or_token_for_unpaid_email(self):
        token = request_login_token(email='NOVO@Example.com  ', base_url='https://octoboxfit.com.br')

        self.assertIsNone(token)
        self.assertFalse(PublicWorkoutAccount.objects.filter(email='novo@example.com').exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_pending_checkout_account_cannot_request_login_link(self):
        from public_workouts.billing import get_or_create_subscription
        account = PublicWorkoutAccount.objects.create(email='aguardando-pagamento@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.requires_login = True
        subscription.save(update_fields=['requires_login'])

        token = request_login_token(email=account.email, base_url='https://octoboxfit.com.br')

        self.assertIsNone(token)
        self.assertFalse(PublicWorkoutLoginToken.objects.filter(account=account).exists())

    def test_reuses_existing_account_for_same_email(self):
        PublicWorkoutAccount.objects.create(email='repeat@example.com')
        request_login_token(email='repeat@example.com', base_url='https://octoboxfit.com.br')
        request_login_token(email='repeat@example.com', base_url='https://octoboxfit.com.br')

        self.assertEqual(PublicWorkoutAccount.objects.filter(email='repeat@example.com').count(), 1)
        self.assertEqual(PublicWorkoutLoginToken.objects.count(), 2)

    def test_links_to_existing_student_identity_by_email_at_creation(self):
        StudentIdentity.objects.create(
            provider='google',
            provider_subject='sub-1',
            email='aluno-de-box@example.com',
        )
        resolve_or_create_public_workout_account(email='aluno-de-box@example.com')
        request_login_token(email='aluno-de-box@example.com', base_url='https://octoboxfit.com.br')

        account = PublicWorkoutAccount.objects.get(email='aluno-de-box@example.com')
        self.assertIsNotNone(account.student_identity_id)

    def test_changing_student_identity_email_later_does_not_resync_account(self):
        # N5 do CORDA: vinculo e informativo, resolvido so na criacao.
        identity = StudentIdentity.objects.create(
            provider='google',
            provider_subject='sub-2',
            email='original@example.com',
        )
        resolve_or_create_public_workout_account(email='original@example.com')
        request_login_token(email='original@example.com', base_url='https://octoboxfit.com.br')
        account = PublicWorkoutAccount.objects.get(email='original@example.com')
        original_link = account.student_identity_id

        identity.email = 'mudou@example.com'
        identity.save()

        account.refresh_from_db()
        self.assertEqual(account.student_identity_id, original_link)

    def test_rate_limit_exceeded_after_max_requests(self):
        email = 'ratelimited@example.com'
        PublicWorkoutAccount.objects.create(email=email)
        for _ in range(PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX):
            request_login_token(email=email, base_url='https://octoboxfit.com.br')

        with self.assertRaises(PublicWorkoutLoginRateLimitExceeded):
            request_login_token(email=email, base_url='https://octoboxfit.com.br')

    def test_email_has_html_alternative_with_the_login_link(self):
        PublicWorkoutAccount.objects.create(email='bonito@example.com')
        token = request_login_token(email='bonito@example.com', base_url='https://octoboxfit.com.br')

        sent = mail.outbox[0]
        self.assertEqual(len(sent.alternatives), 1)
        html_content, mimetype = sent.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn(str(token.token), html_content)
        self.assertIn('Entrar no treino', html_content)

    def test_email_subject_has_no_portuguese_accented_letters(self):
        # Mesma convencao de build_owner_onboarding_subject (que tambem usa
        # "·" livremente): o que se evita e acento de letra pt-BR (risco de
        # encoding quebrado em cliente legado), nao pontuacao unicode.
        PublicWorkoutAccount.objects.create(email='semacento@example.com')
        request_login_token(email='semacento@example.com', base_url='https://octoboxfit.com.br')

        subject = mail.outbox[0].subject
        accented_letters = set('áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ')
        self.assertFalse(accented_letters & set(subject), msg=f'subject com acento pt-BR: {subject!r}')


class VerifyLoginTokenTests(TestCase):
    def test_valid_token_returns_account_and_marks_used(self):
        account = PublicWorkoutAccount.objects.create(email='verify@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )

        result = verify_login_token(token=str(token.token))

        self.assertEqual(result.id, account.id)
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_token_cannot_be_used_twice(self):
        account = PublicWorkoutAccount.objects.create(email='onceonly@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )

        first = verify_login_token(token=str(token.token))
        second = verify_login_token(token=str(token.token))

        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_expired_token_returns_none(self):
        account = PublicWorkoutAccount.objects.create(email='expiredverify@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.assertIsNone(verify_login_token(token=str(token.token)))

    def test_unknown_token_returns_none(self):
        self.assertIsNone(verify_login_token(token='00000000-0000-0000-0000-000000000000'))

    def test_malformed_token_returns_none_not_500(self):
        self.assertIsNone(verify_login_token(token='nao-e-um-uuid'))


class VerifyLoginCodeTests(TestCase):
    """Código digitado no app instalado (o link do e-mail abre fora dele)."""

    def setUp(self):
        from shared_support.platform_cache import platform_cache

        platform_cache.clear()
        self.account = PublicWorkoutAccount.objects.create(email='codigo@example.com')
        self.token = PublicWorkoutLoginToken.objects.create(
            account=self.account, expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        self.code = login_code_for_token(self.token.token)

    def test_code_has_six_digits_and_is_stable_per_token(self):
        self.assertRegex(self.code, r'^\d{6}$')
        self.assertEqual(login_code_for_token(self.token.token), self.code)
        other = PublicWorkoutLoginToken.objects.create(
            account=self.account, expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        self.assertNotEqual(login_code_for_token(other.token), self.code)

    def test_matching_code_consumes_token_and_returns_account(self):
        result = verify_login_code(account_id=self.account.id, code=f' {self.code[:3]} {self.code[3:]} ')

        self.assertEqual(result.id, self.account.id)
        self.token.refresh_from_db()
        self.assertIsNotNone(self.token.used_at)

    def test_code_cannot_be_used_twice(self):
        self.assertIsNotNone(verify_login_code(account_id=self.account.id, code=self.code))
        self.assertIsNone(verify_login_code(account_id=self.account.id, code=self.code))

    def test_code_only_counts_for_tokens_of_the_logged_account(self):
        other = PublicWorkoutAccount.objects.create(email='outra-conta@example.com')
        other_token = PublicWorkoutLoginToken.objects.create(
            account=other, expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )

        self.assertIsNone(verify_login_code(account_id=self.account.id, code=login_code_for_token(other_token.token)))
        other_token.refresh_from_db()
        self.assertIsNone(other_token.used_at)

    def test_expired_token_code_is_rejected(self):
        self.token.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        self.token.save(update_fields=['expires_at'])

        self.assertIsNone(verify_login_code(account_id=self.account.id, code=self.code))

    def test_attempts_are_limited_per_account(self):
        wrong = str((int(self.code) + 1) % 1_000_000).zfill(6)
        for _ in range(PUBLIC_WORKOUT_LOGIN_CODE_ATTEMPTS_MAX):
            self.assertIsNone(verify_login_code(account_id=self.account.id, code=wrong))

        with self.assertRaises(PublicWorkoutLoginCodeAttemptsExceeded):
            verify_login_code(account_id=self.account.id, code=self.code)
        self.token.refresh_from_db()
        self.assertIsNone(self.token.used_at)

    def test_pending_payment_account_is_rejected(self):
        from public_workouts.billing import get_or_create_subscription

        subscription = get_or_create_subscription(account=self.account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.requires_login = True
        subscription.save(update_fields=['requires_login'])

        self.assertIsNone(verify_login_code(account_id=self.account.id, code=self.code))

    def test_login_email_carries_the_same_code_as_the_link(self):
        token = request_login_token(email=self.account.email, base_url='https://octoboxfit.com.br')

        sent = mail.outbox[-1]
        code = login_code_for_token(token.token)
        self.assertIn(code, sent.body)
        self.assertIn(code, sent.alternatives[0][0])
        self.assertIn(str(token.token), sent.body)


class PublicWorkoutLoginViewTests(TestCase):
    def test_google_errors_have_a_message_on_the_login_screen(self):
        for error, text in (
            ('conta_nao_encontrada', 'Não encontramos uma conta da Curva'),
            ('pagamento_pendente', 'ainda não foi confirmado'),
        ):
            from django.template.loader import render_to_string

            html = render_to_string('treinos/login.html', {'error': error})
            self.assertIn(text, html)

    def test_get_without_token_shows_form(self):
        response = self.client.get(reverse('public-workout-login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enviar link')

    def test_post_valid_email_sends_link_and_shows_confirmation(self):
        PublicWorkoutAccount.objects.create(email='chegou@example.com')
        response = self.client.post(reverse('public-workout-login'), {'email': 'chegou@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'chegou@example.com')
        self.assertEqual(len(mail.outbox), 1)

    def test_post_invalid_email_shows_error_without_sending(self):
        response = self.client.post(reverse('public-workout-login'), {'email': 'nao-e-email'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_rate_limited_shows_error(self):
        email = 'viewratelimit@example.com'
        PublicWorkoutAccount.objects.create(email=email)
        for _ in range(PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX):
            request_login_token(email=email, base_url='https://octoboxfit.com.br')

        response = self.client.post(reverse('public-workout-login'), {'email': email})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Muitos pedidos')

    def test_get_with_valid_token_sets_session_cookie(self):
        PublicWorkoutAccount.objects.create(email='cookie@example.com')
        token = request_login_token(email='cookie@example.com', base_url='https://octoboxfit.com.br')

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertRedirects(response, '/treinos/minha-conta', fetch_redirect_response=False)
        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        session_value = read_public_workout_session_value(response.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME].value)
        account = PublicWorkoutAccount.objects.get(email='cookie@example.com')
        self.assertEqual(session_value['account_id'], account.id)
        self.assertIs(session_value['identity_verified'], True)

    def test_get_with_invalid_token_shows_error_and_sets_no_cookie(self):
        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': 'lixo'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_get_without_token_carries_next_into_hidden_field(self):
        response = self.client.get(reverse('public-workout-login'), {'next': '/renan/giovanna'})
        self.assertContains(response, 'name="next" value="/renan/giovanna"')

    def test_post_carries_next_through_to_the_emailed_link(self):
        PublicWorkoutAccount.objects.create(email='comnext@example.com')
        self.client.post(
            reverse('public-workout-login'), {'email': 'comnext@example.com', 'next': '/renan/giovanna'}
        )
        self.assertIn('next=%2Frenan%2Fgiovanna', mail.outbox[0].body)

    def test_get_with_valid_token_and_next_redirects_there_and_sets_cookie(self):
        PublicWorkoutAccount.objects.create(email='volta@example.com')
        token = request_login_token(
            email='volta@example.com', base_url='https://octoboxfit.com.br', next_url='/renan/rafael'
        )

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token), 'next': '/renan/rafael'})

        self.assertRedirects(response, '/renan/rafael', fetch_redirect_response=False)
        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_get_with_valid_token_no_next_and_no_subscription_opens_account_hub(self):
        PublicWorkoutAccount.objects.create(email='seminext@example.com')
        token = request_login_token(email='seminext@example.com', base_url='https://octoboxfit.com.br')

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertRedirects(response, '/treinos/minha-conta', fetch_redirect_response=False)

    def test_get_with_valid_token_no_next_but_with_plan_slug_auto_redirects_to_own_treino(self):
        # Achado real (usuario): abrir o link do e-mail direto (sem ter
        # vindo de uma pagina /renan/<slug> especifica) deixava a pessoa
        # numa tela de "login feito" sem redirecionar pra lugar nenhum.
        account = PublicWorkoutAccount.objects.create(email='comslugautoredirect@example.com')
        PublicWorkoutSubscription.objects.create(
            account=account, plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        token = request_login_token(email='comslugautoredirect@example.com', base_url='https://octoboxfit.com.br')

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertRedirects(response, '/renan/bruno', fetch_redirect_response=False)
        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_explicit_next_wins_over_the_accounts_own_plan_slug(self):
        # ?next= explicito (ex.: aluno clicou no link a partir da tela de
        # anamnese) continua tendo prioridade sobre o auto-redirect.
        account = PublicWorkoutAccount.objects.create(email='nextganha@example.com')
        PublicWorkoutSubscription.objects.create(
            account=account, plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )
        token = PublicWorkoutLoginToken.objects.create(
            account=account, expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )

        client = Client()
        response = client.get(
            reverse('public-workout-login'), {'token': str(token.token), 'next': '/treinos/anamnese'}
        )

        self.assertRedirects(response, '/treinos/anamnese', fetch_redirect_response=False)

    def test_next_pointing_outside_renan_is_ignored_not_open_redirect(self):
        # _safe_public_workout_next: so aceita path exato de /renan/<slug>.
        # Qualquer outra coisa (outro host, outra rota do proprio site,
        # esquema javascript:) some silenciosamente em vez de virar destino.
        for unsafe_next in (
            'https://evil.example.com/phish',
            '//evil.example.com',
            '/painel-interno-privado',
            'javascript:alert(1)',
            '/renan/',
        ):
            email = f'unsafe-{hash(unsafe_next)}@example.com'
            PublicWorkoutAccount.objects.create(email=email)
            token = request_login_token(email=email, base_url='https://octoboxfit.com.br')

            client = Client()
            response = client.get(reverse('public-workout-login'), {'token': str(token.token), 'next': unsafe_next})

            self.assertRedirects(
                response, '/treinos/minha-conta', fetch_redirect_response=False,
                msg_prefix=f'next={unsafe_next!r} deveria cair no hub seguro',
            )
            self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_email_gateway_failure_does_not_raise_and_still_returns_token(self):
        # A falha de canal nunca vira 500 pro aluno — o token ja foi criado
        # e continua valido, ele so nao recebeu o e-mail ainda.
        with patch('signup.email_sender.send_html_email') as send_html_email:
            send_html_email.side_effect = StudentEmailDeliveryError('smtp-down')
            PublicWorkoutAccount.objects.create(email='canalcaiu@example.com')

            token = request_login_token(email='canalcaiu@example.com', base_url='https://octoboxfit.com.br')

        self.assertIsNotNone(token.token)
        self.assertEqual(len(mail.outbox), 0)


class PublicWorkoutSessionTests(TestCase):
    def test_build_and_read_round_trip(self):
        value = build_public_workout_session_value(account_id=42)
        self.assertEqual(read_public_workout_session_value(value)['account_id'], 42)
        self.assertIs(read_public_workout_session_value(value)['identity_verified'], False)

    def test_only_explicit_login_marks_identity_verified(self):
        from django.test import RequestFactory

        request = RequestFactory().get('/renan/bruno')
        request.COOKIES[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=42)
        self.assertIsNone(get_verified_public_workout_account_id_from_request(request))

        request.COOKIES[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=42, identity_verified=True,
        )
        self.assertEqual(get_verified_public_workout_account_id_from_request(request), 42)

    def test_old_signed_cookie_does_not_gain_verified_identity(self):
        from django.test import RequestFactory

        request = RequestFactory().get('/renan/bruno')
        request.COOKIES[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = signing.dumps(
            {'account_id': 42}, salt=PUBLIC_WORKOUT_SESSION_SALT, compress=True,
        )
        self.assertEqual(get_public_workout_account_id_from_request(request), 42)
        self.assertIsNone(get_verified_public_workout_account_id_from_request(request))

    def test_read_empty_value_returns_none(self):
        self.assertIsNone(read_public_workout_session_value(''))
        self.assertIsNone(read_public_workout_session_value(None))

    def test_read_tampered_value_returns_none(self):
        self.assertIsNone(read_public_workout_session_value('lixo-nao-assinado'))

    def test_attach_and_clear_cookie_on_response(self):
        from django.http import HttpResponse

        response = attach_public_workout_session_cookie(HttpResponse(), account_id=7)
        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

        cleared = clear_public_workout_session_cookie(HttpResponse())
        self.assertEqual(cleared.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME]['max-age'], 0)

    def test_cookie_path_is_broad_enough_for_the_renan_ownership_gate(self):
        # Onda B3, item 5: a view de /renan/<slug> precisa ler esta
        # sessao. path=/treinos/ nunca chegaria la (RFC 6265) — um
        # navegador de verdade so envia o cookie pra requisicoes dentro do
        # path declarado. Ver PONTOS CRITICOS em public_workout_session.py.
        from django.http import HttpResponse

        response = attach_public_workout_session_cookie(HttpResponse(), account_id=7)

        self.assertEqual(response.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME]['path'], '/')


class PublicWorkoutModelStrTests(TestCase):
    def test_account_str_is_email(self):
        account = PublicWorkoutAccount.objects.create(email='strtest@example.com')
        self.assertEqual(str(account), 'strtest@example.com')


class GetPublicWorkoutAccountIdFromRequestTests(TestCase):
    # Onda B2 Fatia B: PublicWorkoutSubscribeView usa isto pra saber quem
    # esta pedindo o checkout — sem cobertura ate este teste (achado ao
    # revisar o PR #216 apos o push da Fatia B).

    def _request_with_cookie(self, cookie_value):
        from django.test import RequestFactory

        request = RequestFactory().post('/treinos/subscribe')
        if cookie_value is not None:
            request.COOKIES[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = cookie_value
        return request

    def test_returns_account_id_from_valid_cookie(self):
        cookie_value = build_public_workout_session_value(account_id=99)
        request = self._request_with_cookie(cookie_value)

        self.assertEqual(get_public_workout_account_id_from_request(request), 99)

    def test_returns_none_without_cookie(self):
        request = self._request_with_cookie(None)

        self.assertIsNone(get_public_workout_account_id_from_request(request))

    def test_returns_none_for_tampered_cookie(self):
        request = self._request_with_cookie('lixo-nao-assinado')

        self.assertIsNone(get_public_workout_account_id_from_request(request))


class PublicWorkoutSubscribeViewTests(TestCase):
    # Onda B2 Fatia B (PR #216, commit 103c3ea8): a view em si (autenticacao,
    # plan_slug obrigatorio, idempotencia de get_or_create_subscription,
    # 503 quando a Stripe nao esta configurada) nao tinha teste proprio —
    # os 27 testes daquele commit cobrem stripe_checkout.py/stripe_handlers.py
    # e o ciclo de vida via billing.py, mas nao o endpoint HTTP que os liga.

    def _login(self, account):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.id
        )

    def test_without_session_cookie_returns_401(self):
        response = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'bruno'})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'nao_autenticado')

    def test_cookie_for_deleted_account_returns_401(self):
        # Conta apagada depois do cookie assinado ainda ser valido (ex.: GDPR/LGPD,
        # ou limpeza manual) — nao pode virar 500 nem autenticar como ninguem.
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=999999)

        response = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'bruno'})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'nao_autenticado')

    def test_missing_plan_slug_returns_400(self):
        account = PublicWorkoutAccount.objects.create(email='semplano@example.com')
        self._login(account)

        response = self.client.post(reverse('public-workout-subscribe'), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'plan_slug_obrigatorio')

    def test_stripe_not_configured_returns_503(self):
        account = PublicWorkoutAccount.objects.create(email='semstripe@example.com')
        self._login(account)

        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError

            start_checkout.side_effect = PublicWorkoutStripeNotConfiguredError('sem price id')
            response = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'bruno'})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'stripe_nao_configurado')

    def test_returns_checkout_url_on_success(self):
        # Achado real (Rafael, cliente legado): este e' o caminho feliz que
        # o botao "Pagamentos" de workout.html (data-workout-start-checkout,
        # account.js) depende -- faltava cobertura do proprio 200 antes
        # desta sessao, so' os 3 caminhos de erro acima tinham teste.
        account = PublicWorkoutAccount.objects.create(email='comstripe@example.com')
        self._login(account)

        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/pay/cs_test_rafael'
            response = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'rafael'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.stripe.com/pay/cs_test_rafael')

    def test_preserves_existing_legacy_subscription_tier_instead_of_forcing_essencial(self):
        # get_or_create_subscription(tier=ESSENCIAL) so' define o tier na
        # CRIACAO -- uma assinatura legada ja existente (ex.: Rafael em
        # Completo) nao pode ser rebaixada so' por passar por este endpoint.
        from public_workouts.models import PublicWorkoutSubscription, PublicWorkoutTier

        account = PublicWorkoutAccount.objects.create(email='completo@example.com')
        PublicWorkoutSubscription.objects.create(
            account=account, plan_slug='rafael', tier=PublicWorkoutTier.COMPLETO,
        )
        self._login(account)

        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/pay/cs_test_rafael'
            response = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'rafael'})

        self.assertEqual(response.status_code, 200)
        account.subscription.refresh_from_db()
        self.assertEqual(account.subscription.tier, PublicWorkoutTier.COMPLETO)


class PublicWorkoutColdSignupViewTests(TestCase):
    # Entrega 5, Fase 2 (docs/plans/public-workouts-escala-e-nutricao-corda.md,
    # D.1/D.2/D.2b): ao contrario de PublicWorkoutSubscribeView, esta view
    # tem que funcionar pra um DESCONHECIDO — sem cookie, sem plan_slug.

    def _post(self, **data):
        data.setdefault('accept_contract', '1')
        with patch('student_identity.public_workout_views.start_checkout_lead_session') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/pay/cs_test_cold'
            return self.client.post(reverse('public-workout-cold-signup'), data)

    def test_works_without_any_session_cookie(self):
        response = self._post(email='estranho@example.com', tier=PublicWorkoutTier.COMPLETO)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.stripe.com/pay/cs_test_cold')

    def test_missing_email_returns_400(self):
        response = self._post(email='', tier=PublicWorkoutTier.ESSENCIAL)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'email_ou_tier_invalido')

    def test_invalid_tier_returns_400(self):
        response = self._post(email='estranho@example.com', tier='vip-supremo')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'email_ou_tier_invalido')

    def test_missing_tier_returns_400(self):
        response = self._post(email='estranho@example.com')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'email_ou_tier_invalido')

    def test_captures_lead_without_creating_account_or_subscription(self):
        self._post(email='novo@example.com', tier=PublicWorkoutTier.PREMIUM)

        from public_workouts.models import PublicWorkoutCheckoutLead
        lead = PublicWorkoutCheckoutLead.objects.get(email='novo@example.com')
        self.assertEqual(lead.tier, PublicWorkoutTier.PREMIUM)
        self.assertFalse(PublicWorkoutAccount.objects.filter(email='novo@example.com').exists())
        self.assertFalse(PublicWorkoutSubscription.objects.exists())

    def test_marketing_opt_in_is_separate_and_optional(self):
        self._post(email='optin@example.com', tier=PublicWorkoutTier.COMPLETO, marketing_consent='1')
        self._post(email='semoptin@example.com', tier=PublicWorkoutTier.COMPLETO)
        from public_workouts.models import PublicWorkoutCheckoutLead
        opted_in = PublicWorkoutCheckoutLead.objects.get(email='optin@example.com')
        not_opted_in = PublicWorkoutCheckoutLead.objects.get(email='semoptin@example.com')
        self.assertTrue(opted_in.marketing_consent)
        self.assertIsNotNone(opted_in.marketing_consent_at)
        self.assertFalse(not_opted_in.marketing_consent)
        self.assertIsNone(not_opted_in.marketing_consent_at)

    def test_does_not_authenticate_visitor_before_payment(self):
        response = self._post(email='novo2@example.com', tier=PublicWorkoutTier.ESSENCIAL)

        self.assertNotIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        self.assertFalse(PublicWorkoutAccount.objects.filter(email='novo2@example.com').exists())

    def test_second_signup_with_same_email_does_not_create_a_second_subscription(self):
        # RT1 (Entrega 5): duplo clique no CTA da landing nao pode duplicar.
        self._post(email='duplocheck@example.com', tier=PublicWorkoutTier.ESSENCIAL)
        self._post(email='duplocheck@example.com', tier=PublicWorkoutTier.PREMIUM)

        from public_workouts.models import PublicWorkoutCheckoutLead
        self.assertEqual(PublicWorkoutCheckoutLead.objects.filter(email='duplocheck@example.com').count(), 1)
        self.assertEqual(PublicWorkoutCheckoutLead.objects.get(email='duplocheck@example.com').tier, PublicWorkoutTier.PREMIUM)

    def test_stripe_not_configured_returns_503(self):
        with patch('student_identity.public_workout_views.start_checkout_lead_session') as start_checkout:
            from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError

            start_checkout.side_effect = PublicWorkoutStripeNotConfiguredError('sem price id')
            response = self.client.post(
                reverse('public-workout-cold-signup'), {'email': 'semstripe@example.com', 'tier': PublicWorkoutTier.ESSENCIAL, 'accept_contract': '1'}
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'stripe_nao_configurado')

    def test_success_url_uses_payment_verification_return_endpoint(self):
        with patch('student_identity.public_workout_views.start_checkout_lead_session') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/pay/cs_test_anamnese'
            self.client.post(
                reverse('public-workout-cold-signup'), {'email': 'vaipraanamnese@example.com', 'tier': PublicWorkoutTier.COMPLETO, 'accept_contract': '1'}
            )

        _, kwargs = start_checkout.call_args
        self.assertIn(reverse('public-workout-checkout-return'), kwargs['success_url'])
        self.assertIn('session_id={CHECKOUT_SESSION_ID}', kwargs['success_url'])
        self.assertIn('#curva-precos', kwargs['cancel_url'])

    @override_settings(STRIPE_SECRET_KEY='sk_test_x')
    def test_paid_return_creates_account_but_requires_email_login(self):
        from public_workouts.models import PublicWorkoutCheckoutLead
        lead = PublicWorkoutCheckoutLead.objects.create(
            email='retorno-pago@example.com', tier=PublicWorkoutTier.COMPLETO,
            stripe_checkout_session_id='cs_paid',
        )
        paid_session = {
            'status': 'complete', 'payment_status': 'paid', 'customer': 'cus_paid',
            'subscription': 'sub_paid',
            'metadata': {'product': 'coaching', 'public_workout_checkout_lead_id': str(lead.pk),
                         'tier': PublicWorkoutTier.COMPLETO},
        }
        with patch('stripe.checkout.Session.retrieve', return_value=paid_session):
            response = self.client.get(reverse('public-workout-checkout-return'), {'session_id': 'cs_paid'})

        self.assertRedirects(response, '/treinos/login?checkout=retorno', fetch_redirect_response=False)
        self.assertNotIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        self.assertTrue(PublicWorkoutAccount.objects.filter(email=lead.email).exists())

    @override_settings(STRIPE_SECRET_KEY='sk_test_x')
    def test_completed_checkout_is_resumed_before_new_tier_can_mutate_lead(self):
        from types import SimpleNamespace
        from public_workouts.models import PublicWorkoutCheckoutLead
        lead = PublicWorkoutCheckoutLead.objects.create(
            email='checkout-concluido@example.com', tier=PublicWorkoutTier.ESSENCIAL,
            stripe_checkout_session_id='cs_already_paid',
        )
        with patch('stripe.checkout.Session.retrieve', return_value=SimpleNamespace(
            id='cs_already_paid', status='complete', payment_status='paid',
        )), patch('stripe.checkout.Session.create') as create_session:
            response = self.client.post(reverse('public-workout-cold-signup'), {
                'email': lead.email, 'tier': PublicWorkoutTier.PREMIUM, 'accept_contract': '1',
            })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['payment_complete'])
        self.assertIn('session_id=cs_already_paid', response.json()['checkout_url'])
        lead.refresh_from_db()
        self.assertEqual(lead.tier, PublicWorkoutTier.ESSENCIAL)
        create_session.assert_not_called()

    def test_requires_explicit_contract_acceptance(self):
        response = self.client.post(
            reverse('public-workout-cold-signup'),
            {'email': 'sem-aceite@example.com', 'tier': PublicWorkoutTier.ESSENCIAL},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'aceite_contrato_obrigatorio')
        self.assertFalse(PublicWorkoutAccount.objects.filter(email='sem-aceite@example.com').exists())

    def test_persists_the_accepted_contract_versions(self):
        self._post(email='contrato@example.com', tier=PublicWorkoutTier.COMPLETO)

        from public_workouts.models import PublicWorkoutCheckoutLead
        lead = PublicWorkoutCheckoutLead.objects.get(email='contrato@example.com')
        self.assertEqual(lead.offer_version, 'curva-2026-09-v1')
        self.assertEqual(lead.service_policy_version, 'curva-service-2026-09-v1')
        self.assertEqual(lead.terms_version, '2026-09-20')
        self.assertEqual(lead.privacy_version, '2026-09-20')
        self.assertEqual(lead.guarantee_model, 'refund_guarantee')
        self.assertIsNotNone(lead.contract_accepted_at)


class PublicWorkoutBillingPortalViewTests(TestCase):
    # Onda B2, item 6 (Customer Portal) — ultimo item pendente da onda.
    # Mesmo mecanismo de sessao/erros de PublicWorkoutSubscribeViewTests.

    def _login(self, account):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.id
        )

    def test_without_session_cookie_returns_401(self):
        response = self.client.post(reverse('public-workout-billing-portal'))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'nao_autenticado')

    def test_cookie_for_deleted_account_returns_401(self):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=999999)

        response = self.client.post(reverse('public-workout-billing-portal'))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'nao_autenticado')

    def test_account_without_subscription_returns_404(self):
        account = PublicWorkoutAccount.objects.create(email='semassinatura@example.com')
        self._login(account)

        response = self.client.post(reverse('public-workout-billing-portal'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'sem_assinatura_com_checkout_concluido')

    def test_subscription_without_stripe_customer_id_returns_404(self):
        # Assinatura existe (get_or_create_subscription ja rodou) mas o
        # checkout nunca completou — link_stripe_ids nunca gravou o
        # customer_id. Nao ha o que gerenciar no portal ainda.
        from public_workouts.billing import get_or_create_subscription

        account = PublicWorkoutAccount.objects.create(email='checkoutincompleto@example.com')
        get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        self._login(account)

        response = self.client.post(reverse('public-workout-billing-portal'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'sem_assinatura_com_checkout_concluido')

    def test_stripe_not_configured_returns_503(self):
        from public_workouts.billing import get_or_create_subscription, link_stripe_ids

        account = PublicWorkoutAccount.objects.create(email='semstripeportal@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        link_stripe_ids(subscription, customer_id='cus_123', stripe_subscription_id='sub_123')
        self._login(account)

        with patch('student_identity.public_workout_views.start_customer_portal_session') as start_portal:
            from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError

            start_portal.side_effect = PublicWorkoutStripeNotConfiguredError('sem secret key')
            response = self.client.post(reverse('public-workout-billing-portal'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'stripe_nao_configurado')

    def test_returns_portal_url_when_customer_id_is_set(self):
        from public_workouts.billing import get_or_create_subscription, link_stripe_ids

        account = PublicWorkoutAccount.objects.create(email='comportal@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        link_stripe_ids(subscription, customer_id='cus_456', stripe_subscription_id='sub_456')
        self._login(account)

        with patch('student_identity.public_workout_views.start_customer_portal_session') as start_portal:
            start_portal.return_value = 'https://billing.stripe.com/session/bps_test_456'
            response = self.client.post(reverse('public-workout-billing-portal'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['portal_url'], 'https://billing.stripe.com/session/bps_test_456')
        _, kwargs = start_portal.call_args
        self.assertEqual(kwargs['customer_id'], 'cus_456')

    def test_successful_checkout_returns_url_and_reuses_existing_subscription(self):
        from public_workouts.models import PublicWorkoutSubscription

        account = PublicWorkoutAccount.objects.create(email='assina@example.com')
        self._login(account)

        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/session/abc123'

            first = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'bruno'})
            second = self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'bruno'})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['checkout_url'], 'https://checkout.stripe.com/session/abc123')
        self.assertEqual(second.status_code, 200)
        # P6 do CORDA: duplo POST em "assinar" nao duplica PublicWorkoutSubscription.
        self.assertEqual(PublicWorkoutSubscription.objects.filter(account=account).count(), 1)

    def test_start_subscription_checkout_receives_correct_success_and_cancel_urls(self):
        account = PublicWorkoutAccount.objects.create(email='urls@example.com')
        self._login(account)

        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/session/xyz'
            self.client.post(reverse('public-workout-subscribe'), {'plan_slug': 'bruno'})

        _, kwargs = start_checkout.call_args
        login_path = reverse('public-workout-login')
        self.assertIn(login_path, kwargs['success_url'])
        self.assertIn('assinatura=sucesso', kwargs['success_url'])
        self.assertIn('assinatura=cancelada', kwargs['cancel_url'])

    def test_login_token_str_reflects_state(self):
        account = PublicWorkoutAccount.objects.create(email='tokenstr@example.com')
        token = PublicWorkoutLoginToken.objects.create(
            account=account,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        self.assertIn('pendente', str(token))

        token.mark_used()
        token.save()
        self.assertIn('usado', str(token))

    def test_backup_str_includes_slug(self):
        backup = PublicWorkoutLocalStorageBackup.objects.create(plan_slug='giovanna', raw_blob={})
        self.assertIn('giovanna', str(backup))


class PublicWorkoutCustomCheckoutViewTests(TestCase):
    # Achado real (Rafael, cliente legado — seed_legacy_workout_accounts):
    # assinatura ja' nasce ACTIVE mas sem stripe_customer_id. Antes desta
    # view, o UNICO jeito de cobrar valor negociado era a acao de admin
    # "Gerar link..." (copiar/colar no WhatsApp) -- esta view fecha o loop
    # dentro do app. Mesmo padrao de sessao/erros de
    # PublicWorkoutBillingPortalViewTests.

    def _login(self, account):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.id
        )

    def test_without_session_cookie_returns_401(self):
        response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'nao_autenticado')

    def test_cookie_for_deleted_account_returns_401(self):
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=999999)

        response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'nao_autenticado')

    def test_account_without_subscription_returns_404(self):
        account = PublicWorkoutAccount.objects.create(email='semassinatura-custom@example.com')
        self._login(account)

        response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'nao_aplicavel')

    def test_subscription_with_stripe_customer_id_returns_404(self):
        # Ja tem stripe_customer_id -- usa o Customer Portal normal
        # (data-billing-portal), este caminho nao se aplica.
        from public_workouts.billing import get_or_create_subscription, link_stripe_ids

        account = PublicWorkoutAccount.objects.create(email='jatemstripe-custom@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        link_stripe_ids(subscription, customer_id='cus_789', stripe_subscription_id='sub_789')
        self._login(account)

        response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'nao_aplicavel')

    def test_subscription_without_custom_price_returns_404(self):
        # Assinatura legada existe, mas o Renan ainda nao preencheu
        # custom_monthly_price no admin.
        from public_workouts.billing import get_or_create_subscription

        account = PublicWorkoutAccount.objects.create(email='semvalor-custom@example.com')
        get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        self._login(account)

        response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'valor_nao_definido')

    def test_stripe_not_configured_returns_503(self):
        from public_workouts.billing import get_or_create_subscription

        account = PublicWorkoutAccount.objects.create(email='semstripe-custom@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        subscription.custom_monthly_price = 150
        subscription.save(update_fields=['custom_monthly_price'])
        self._login(account)

        with patch('student_identity.public_workout_views.start_custom_price_subscription_checkout') as start_checkout:
            from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError

            start_checkout.side_effect = PublicWorkoutStripeNotConfiguredError('sem secret key')
            response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'stripe_nao_configurado')

    def test_returns_checkout_url_when_custom_price_is_set(self):
        from public_workouts.billing import get_or_create_subscription

        account = PublicWorkoutAccount.objects.create(email='comvalor-custom@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno')
        subscription.custom_monthly_price = 150
        subscription.save(update_fields=['custom_monthly_price'])
        self._login(account)

        with patch('student_identity.public_workout_views.start_custom_price_subscription_checkout') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/pay/cs_test_custom'
            response = self.client.post(reverse('public-workout-custom-checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.stripe.com/pay/cs_test_custom')
        _, kwargs = start_checkout.call_args
        self.assertEqual(kwargs['subscription'], subscription)
