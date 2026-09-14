"""
ARQUIVO: testes de POST /renan/<slug>/carga (Onda B3, item 8 —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- e o endpoint HTTP que o outbox de IndexedDB da Onda B3 vai consumir
  pra sincronizar carga registrada offline. Ao contrario do
  backup-carga (B0/B1), exige sessao de LOGIN — carga precisa saber
  QUEM registrou (account_id), nao so "quem viu o link".
"""

import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutSubscription
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


class PublicWorkoutRecordLoadEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-record-load', kwargs={'plan_slug': slug})

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(),
            data=json.dumps({'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'performed_on': '2026-01-05', 'idempotency_key': 'k1'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_session_of_another_slugs_owner_returns_404(self):
        account = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'performed_on': '2026-01-05', 'idempotency_key': 'k2'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_owner_can_record_load(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {
                    'movement_slug': 'agachamento-livre',
                    'weight_kg': 100.5,
                    'reps': 8,
                    'rir': 2,
                    'performed_on': '2026-01-05',
                    'program_id': 'bruno-2026-q1',
                    'week_in_program': 1,
                    'idempotency_key': 'k3',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['movement_slug'], 'agachamento-livre')
        self.assertEqual(body['weight_kg'], 100.5)
        self.assertEqual(body['idempotency_key'], 'k3')

        log = PublicWorkoutLoadLog.objects.get(idempotency_key='k3')
        self.assertEqual(log.account_id, account.pk)
        self.assertEqual(log.weight_kg, Decimal('100.5'))

    def test_resending_the_same_idempotency_key_does_not_duplicate(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        payload = {
            'movement_slug': 'agachamento-livre',
            'weight_kg': 100,
            'performed_on': '2026-01-05',
            'idempotency_key': 'k-outbox-retry',
        }

        first = self.client.post(self._url('bruno'), data=json.dumps(payload), content_type='application/json')
        second = self.client.post(self._url('bruno'), data=json.dumps(payload), content_type='application/json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)

    def test_negative_weight_kg_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': -10, 'performed_on': '2026-01-05', 'idempotency_key': 'k4'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_missing_required_field_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'weight_kg': 100}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_malformed_json_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'), data=b'{nao-e-json', content_type='application/json')

        self.assertEqual(response.status_code, 400)

    def test_valid_json_that_is_not_an_object_returns_400(self):
        # JSON valido (nao levanta JSONDecodeError) mas nao e um dict --
        # branch separada de test_malformed_json_returns_400.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'), data=json.dumps(['nao', 'e', 'um', 'objeto']), content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_unknown_slug_returns_404(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('nao-existe'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'performed_on': '2026-01-05', 'idempotency_key': 'k5'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)

    def test_bodyweight_movement_accepts_null_weight(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {
                    'movement_slug': 'flexao-de-braco',
                    'weight_kg': None,
                    'reps': 20,
                    'performed_on': '2026-01-05',
                    'idempotency_key': 'k6',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['weight_kg'])
