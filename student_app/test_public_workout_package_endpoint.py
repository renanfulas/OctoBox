"""
ARQUIVO: testes de GET /renan/<slug>/pacote.json (Onda B3, item 8 — base,
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- contrapartida de LEITURA do S3 (PublicWorkoutRecordLoadView): expoe S2
  (build_student_package) — ultima carga por movimento, com 1RM estimado
  de verdade desde a Onda A3 — pra conta logada dona do slug. Mesma regra
  de auth do endpoint de escrita, testada aqui pelo lado GET.
"""

import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from public_workouts.services import record_load
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


class PublicWorkoutPackageEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-package', kwargs={'plan_slug': slug})

    def test_without_session_returns_401(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 401)

    def test_session_of_another_slugs_owner_returns_404(self):
        account = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_unknown_slug_returns_404(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.get(self._url('nao-existe'))

        self.assertEqual(response.status_code, 404)

    def test_owner_with_no_load_yet_gets_the_s2_shape(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body),
            {'last_load_by_movement', 'last_top_set_by_movement', 'one_rep_max_by_movement', 'substitutions', 'access_until'},
        )
        self.assertEqual(body['last_load_by_movement'], {})
        self.assertEqual(body['last_top_set_by_movement'], {})
        self.assertEqual(body['one_rep_max_by_movement'], {})
        self.assertEqual(body['substitutions'], {})
        self.assertIsNone(body['access_until'])

    def test_owner_gets_last_load_and_real_one_rep_max_estimate(self):
        # Onda A3: build_student_package agora estima 1RM de verdade —
        # confirma que o endpoint devolve isso, nao os {} vazios de antes.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        record_load(
            account_id=account.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            reps=5,
            performed_on='2026-01-05',
            idempotency_key='key-1',
        )
        _login(self.client, account.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['last_load_by_movement']['agachamento-livre']['weight_kg'], 100.0)
        self.assertEqual(body['last_top_set_by_movement']['agachamento-livre']['weight_kg'], 100.0)
        estimate = body['one_rep_max_by_movement']['agachamento-livre']
        self.assertEqual(estimate['formula'], 'brzycki')

    def test_does_not_leak_load_between_accounts(self):
        owner = _make_account_with_subscription(email='dono@example.com', plan_slug='bruno')
        other = _make_account_with_subscription(email='outro@example.com', plan_slug='juliana')
        record_load(
            account_id=owner.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on='2026-01-05',
            idempotency_key='key-dono',
        )
        _login(self.client, other.pk)

        response = self.client.get(self._url('juliana'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['last_load_by_movement'], {})

    def test_is_read_only_post_not_allowed(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'), data=json.dumps({}), content_type='application/json')

        self.assertEqual(response.status_code, 405)
