"""
ARQUIVO: testes do login por e-mail do corredor de treinos (Onda B1 do CORDA).

POR QUE ELE EXISTE:
- e o "pronto quando" #2 da Onda B1: aluno entra por link de e-mail e cai
  no treino dele (a parte de sessao — o roteamento pro treino certo e
  Onda B3). Cobre tambem o rate limit (S1) e a regra de uso unico (D.5/S3).
"""

from unittest.mock import Mock, patch

from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutLocalStorageBackup,
    PublicWorkoutLoginToken,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutTrainingExperience,
    PublicWorkoutTrainingGoal,
    PublicWorkoutTrainingLocation,
)

from .delivery_gateways import StudentEmailDeliveryError
from .models import StudentIdentity
from .public_workout_login import (
    PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX,
    PublicWorkoutLoginRateLimitExceeded,
    request_login_token,
    verify_login_token,
)
from .public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    attach_public_workout_session_cookie,
    build_public_workout_session_value,
    clear_public_workout_session_cookie,
    get_public_workout_account_id_from_request,
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


class RequestLoginTokenTests(TestCase):
    def test_creates_account_and_token_and_sends_email(self):
        token = request_login_token(email='NOVO@Example.com  ', base_url='https://octoboxfit.com.br')

        self.assertEqual(PublicWorkoutAccount.objects.filter(email='novo@example.com').count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(str(token.token), mail.outbox[0].body)
        self.assertIn('novo@example.com', mail.outbox[0].to)

    def test_reuses_existing_account_for_same_email(self):
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
        request_login_token(email='original@example.com', base_url='https://octoboxfit.com.br')
        account = PublicWorkoutAccount.objects.get(email='original@example.com')
        original_link = account.student_identity_id

        identity.email = 'mudou@example.com'
        identity.save()

        account.refresh_from_db()
        self.assertEqual(account.student_identity_id, original_link)

    def test_rate_limit_exceeded_after_max_requests(self):
        email = 'ratelimited@example.com'
        for _ in range(PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX):
            request_login_token(email=email, base_url='https://octoboxfit.com.br')

        with self.assertRaises(PublicWorkoutLoginRateLimitExceeded):
            request_login_token(email=email, base_url='https://octoboxfit.com.br')

    def test_email_has_html_alternative_with_the_login_link(self):
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


class PublicWorkoutLoginViewTests(TestCase):
    def test_get_without_token_shows_form(self):
        response = self.client.get(reverse('public-workout-login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enviar link')

    def test_post_valid_email_sends_link_and_shows_confirmation(self):
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
        for _ in range(PUBLIC_WORKOUT_LOGIN_RATE_LIMIT_MAX):
            request_login_token(email=email, base_url='https://octoboxfit.com.br')

        response = self.client.post(reverse('public-workout-login'), {'email': email})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Muitos pedidos')

    def test_get_with_valid_token_sets_session_cookie(self):
        token = request_login_token(email='cookie@example.com', base_url='https://octoboxfit.com.br')

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertEqual(response.status_code, 200)
        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        session_value = read_public_workout_session_value(response.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME].value)
        account = PublicWorkoutAccount.objects.get(email='cookie@example.com')
        self.assertEqual(session_value['account_id'], account.id)

    def test_get_with_invalid_token_shows_error_and_sets_no_cookie(self):
        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': 'lixo'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_get_without_token_carries_next_into_hidden_field(self):
        response = self.client.get(reverse('public-workout-login'), {'next': '/renan/giovanna'})
        self.assertContains(response, 'name="next" value="/renan/giovanna"')

    def test_post_carries_next_through_to_the_emailed_link(self):
        self.client.post(
            reverse('public-workout-login'), {'email': 'comnext@example.com', 'next': '/renan/giovanna'}
        )
        self.assertIn('next=%2Frenan%2Fgiovanna', mail.outbox[0].body)

    def test_get_with_valid_token_and_next_redirects_there_and_sets_cookie(self):
        token = request_login_token(
            email='volta@example.com', base_url='https://octoboxfit.com.br', next_url='/renan/rafael'
        )

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token), 'next': '/renan/rafael'})

        self.assertRedirects(response, '/renan/rafael', fetch_redirect_response=False)
        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_get_with_valid_token_no_next_and_no_subscription_keeps_confirmation_page(self):
        # Conta sem NENHUMA PublicWorkoutSubscription (nunca passou pelo
        # cadastro, so' digitou um e-mail qualquer em /treinos/login, que
        # request_login_token aceita de qualquer jeito) -- nao ha o que
        # resolver, a tela de confirmacao segue sendo o destino certo
        # (nunca empurra quem nem comecou a assinar pra anamnese).
        token = request_login_token(email='seminext@example.com', base_url='https://octoboxfit.com.br')

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'seminext@example.com')

    def test_get_with_valid_token_no_next_and_no_subscription_never_shows_awaiting_message(self):
        # Achado real (usuario), numa rodada de QA seguinte ao anterior:
        # "logged_in_as" tinha UMA so' mensagem pros dois casos de string
        # vazia -- quem nunca assinou nada via a MESMA frase de "seu treino
        # esta sendo preparado" de quem realmente ja pagou e preencheu a
        # anamnese. Regressao especifica: sem assinatura nenhuma, a frase
        # de "preparado" nunca aparece (seria enganoso -- essa pessoa nao
        # pagou nada ainda).
        token = request_login_token(email='semassinaturanenhuma@example.com', base_url='https://octoboxfit.com.br')

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'sendo preparado')

    def test_get_with_valid_token_no_next_subscription_without_slug_or_anamnese_redirects_to_anamnese(self):
        # Achado real (usuario): quem ja tem PublicWorkoutSubscription (via
        # cadastro/checkout) mas ainda nao preencheu a anamnese ficava
        # preso numa tela dizendo "volte pro link do seu treino" -- sem
        # treino nenhum montado ainda. Agora manda direto pra anamnese.
        token = request_login_token(email='semanamnese@example.com', base_url='https://octoboxfit.com.br')
        account = PublicWorkoutAccount.objects.get(email='semanamnese@example.com')
        PublicWorkoutSubscription.objects.create(account=account)

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertRedirects(response, '/treinos/anamnese', fetch_redirect_response=False)

    def test_get_with_valid_token_no_next_subscription_with_anamnese_but_no_slug_shows_awaiting_message(self):
        # Anamnese ja preenchida, mas Renan ainda nao montou/atribuiu o
        # treino (sem plan_slug) -- nao ha pra onde redirecionar, a tela
        # de confirmacao precisa deixar claro que o treino esta em
        # preparo, nunca um link morto pro treino que ainda nao existe.
        from public_workouts.services import save_training_profile

        token = request_login_token(email='aguardandotreino@example.com', base_url='https://octoboxfit.com.br')
        account = PublicWorkoutAccount.objects.get(email='aguardandotreino@example.com')
        PublicWorkoutSubscription.objects.create(account=account)
        save_training_profile(
            account_id=account.id,
            goal=PublicWorkoutTrainingGoal.HYPERTROPHY,
            physical_restrictions=[],
            physical_restrictions_detail='',
            training_experience=PublicWorkoutTrainingExperience.NEVER_TRAINED,
            days_per_week=3,
            training_location=PublicWorkoutTrainingLocation.FULL_GYM,
            motivation='',
            biggest_difficulty='',
            consent_given=True,
        )

        client = Client()
        response = client.get(reverse('public-workout-login'), {'token': str(token.token)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sendo preparado')

    def test_get_with_valid_token_no_next_but_with_plan_slug_auto_redirects_to_own_treino(self):
        # Achado real (usuario): abrir o link do e-mail direto (sem ter
        # vindo de uma pagina /renan/<slug> especifica) deixava a pessoa
        # numa tela de "login feito" sem redirecionar pra lugar nenhum.
        token = request_login_token(email='comslugautoredirect@example.com', base_url='https://octoboxfit.com.br')
        account = PublicWorkoutAccount.objects.get(email='comslugautoredirect@example.com')
        PublicWorkoutSubscription.objects.create(
            account=account, plan_slug='bruno', status=PublicWorkoutSubscriptionStatus.ACTIVE,
        )

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
            token = request_login_token(email=f'unsafe-{hash(unsafe_next)}@example.com', base_url='https://octoboxfit.com.br')

            client = Client()
            response = client.get(reverse('public-workout-login'), {'token': str(token.token), 'next': unsafe_next})

            self.assertEqual(response.status_code, 200, msg=f'next={unsafe_next!r} deveria cair na pagina normal')
            self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)

    def test_email_gateway_failure_does_not_raise_and_still_returns_token(self):
        # A falha de canal nunca vira 500 pro aluno — o token ja foi criado
        # e continua valido, ele so nao recebeu o e-mail ainda.
        with patch('signup.email_sender.send_html_email') as send_html_email:
            send_html_email.side_effect = StudentEmailDeliveryError('smtp-down')

            token = request_login_token(email='canalcaiu@example.com', base_url='https://octoboxfit.com.br')

        self.assertIsNotNone(token.token)
        self.assertEqual(len(mail.outbox), 0)


class PublicWorkoutSessionTests(TestCase):
    def test_build_and_read_round_trip(self):
        value = build_public_workout_session_value(account_id=42)
        self.assertEqual(read_public_workout_session_value(value)['account_id'], 42)

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


class PublicWorkoutColdSignupViewTests(TestCase):
    # Entrega 5, Fase 2 (docs/plans/public-workouts-escala-e-nutricao-corda.md,
    # D.1/D.2/D.2b): ao contrario de PublicWorkoutSubscribeView, esta view
    # tem que funcionar pra um DESCONHECIDO — sem cookie, sem plan_slug.

    def _post(self, **data):
        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
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

    def test_creates_account_and_pending_payment_subscription_without_plan_slug(self):
        self._post(email='novo@example.com', tier=PublicWorkoutTier.PREMIUM)

        account = PublicWorkoutAccount.objects.get(email='novo@example.com')
        subscription = account.subscription
        self.assertEqual(subscription.tier, PublicWorkoutTier.PREMIUM)
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        self.assertIsNone(subscription.plan_slug)

    def test_attaches_session_cookie_so_visitor_is_already_logged_in(self):
        response = self._post(email='novo2@example.com', tier=PublicWorkoutTier.ESSENCIAL)

        self.assertIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        account = PublicWorkoutAccount.objects.get(email='novo2@example.com')
        request = Mock(COOKIES={PUBLIC_WORKOUT_SESSION_COOKIE_NAME: response.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME].value})
        self.assertEqual(get_public_workout_account_id_from_request(request), account.pk)

    def test_second_signup_with_same_email_does_not_create_a_second_subscription(self):
        # RT1 (Entrega 5): duplo clique no CTA da landing nao pode duplicar.
        self._post(email='duplocheck@example.com', tier=PublicWorkoutTier.ESSENCIAL)
        self._post(email='duplocheck@example.com', tier=PublicWorkoutTier.PREMIUM)

        account = PublicWorkoutAccount.objects.get(email='duplocheck@example.com')
        self.assertEqual(PublicWorkoutSubscription.objects.filter(account=account).count(), 1)
        # Comportamento preexistente de get_or_create_subscription: os
        # defaults da SEGUNDA chamada sao ignorados.
        self.assertEqual(account.subscription.tier, PublicWorkoutTier.ESSENCIAL)

    def test_stripe_not_configured_returns_503(self):
        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            from public_workouts.stripe_checkout import PublicWorkoutStripeNotConfiguredError

            start_checkout.side_effect = PublicWorkoutStripeNotConfiguredError('sem price id')
            response = self.client.post(
                reverse('public-workout-cold-signup'), {'email': 'semstripe@example.com', 'tier': PublicWorkoutTier.ESSENCIAL}
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'stripe_nao_configurado')

    def test_success_url_points_straight_to_anamnese_not_back_to_login(self):
        # Achado real: a landing promete a anamnese "antes do primeiro
        # plano" (FAQ) mas o retorno do Stripe mandava pra /treinos/login,
        # pagina que nem olha pro ?assinatura=sucesso — beco sem saida.
        with patch('student_identity.public_workout_views.start_subscription_checkout') as start_checkout:
            start_checkout.return_value = 'https://checkout.stripe.com/pay/cs_test_anamnese'
            self.client.post(
                reverse('public-workout-cold-signup'), {'email': 'vaipraanamnese@example.com', 'tier': PublicWorkoutTier.COMPLETO}
            )

        _, kwargs = start_checkout.call_args
        self.assertIn(reverse('public-workout-training-intake'), kwargs['success_url'])
        self.assertIn('assinatura=cancelada', kwargs['cancel_url'])


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
