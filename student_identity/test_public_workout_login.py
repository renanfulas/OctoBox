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

    def test_email_gateway_failure_does_not_raise_and_still_returns_token(self):
        # A falha de canal nunca vira 500 pro aluno — o token ja foi criado
        # e continua valido, ele so nao recebeu o e-mail ainda.
        with patch('student_identity.public_workout_login.get_student_email_gateway') as get_gateway:
            gateway = Mock()
            gateway.send.side_effect = StudentEmailDeliveryError('smtp-down')
            get_gateway.return_value = gateway

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


class PublicWorkoutModelStrTests(TestCase):
    def test_account_str_is_email(self):
        account = PublicWorkoutAccount.objects.create(email='strtest@example.com')
        self.assertEqual(str(account), 'strtest@example.com')

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
