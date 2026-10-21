"""
ARQUIVO: testes de POST /renan/<slug>/onboarding (PublicWorkoutOnboardingCompleteView).

POR QUE ELE EXISTE:
- mesmo gate de sessao de PublicWorkoutRecordLoadView (401 sem login, 404
  se a sessao e' de outra conta) -- onboarding_completed_at e' um dado da
  CONTA, nunca aceita sem saber com certeza qual conta esta do outro lado.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _make_account_with_subscription(*, email, plan_slug) -> PublicWorkoutAccount:
    account = PublicWorkoutAccount.objects.create(email=email)
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)
    return account


def _login(client, account_id):
    client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=account_id)


class PublicWorkoutOnboardingCompleteEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-onboarding-complete', kwargs={'plan_slug': slug})

    def test_without_session_returns_401(self):
        response = self.client.post(self._url())

        self.assertEqual(response.status_code, 401)

    def test_session_of_another_slugs_owner_returns_404(self):
        account = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_marks_the_account_as_onboarded(self):
        account = _make_account_with_subscription(email='b@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        self.assertIsNone(account.onboarding_completed_at)

        response = self.client.post(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertIsNotNone(account.onboarding_completed_at)

    def test_is_idempotent_and_does_not_move_the_timestamp(self):
        account = _make_account_with_subscription(email='c@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        self.client.post(self._url('bruno'))
        account.refresh_from_db()
        first_timestamp = account.onboarding_completed_at

        self.client.post(self._url('bruno'))
        account.refresh_from_db()

        self.assertEqual(account.onboarding_completed_at, first_timestamp)

    def test_already_onboarded_account_stays_onboarded(self):
        account = _make_account_with_subscription(email='d@example.com', plan_slug='bruno')
        already_completed = timezone.now()
        account.onboarding_completed_at = already_completed
        account.save(update_fields=['onboarding_completed_at'])
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertEqual(account.onboarding_completed_at, already_completed)
