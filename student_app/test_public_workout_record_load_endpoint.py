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

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutLoadLogSetRole, PublicWorkoutSubscription
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
        self.assertEqual(log.set_role, PublicWorkoutLoadLogSetRole.LEGACY_UNKNOWN)
        self.assertEqual(body['set_role'], PublicWorkoutLoadLogSetRole.LEGACY_UNKNOWN)

    def test_explicit_warmup_role_is_persisted(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 50,
                'performed_on': '2026-09-01', 'idempotency_key': 'warmup-role',
                'set_role': 'warmup',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['set_role'], 'warmup')
        self.assertEqual(PublicWorkoutLoadLog.objects.get(idempotency_key='warmup-role').set_role, 'warmup')

    def test_invalid_set_role_returns_400_without_writing(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 50,
                'performed_on': '2026-09-01', 'idempotency_key': 'invalid-role',
                'set_role': 'not-a-role',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)
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

    def test_boolean_reps_returns_400(self):
        # bool e subclasse de int em Python -- sem o cheque explicito em
        # _reps_or_none, reps=true viraria reps=1 no banco silenciosamente.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'reps': True, 'performed_on': '2026-01-05', 'idempotency_key': 'k-reps-bool'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_fractional_reps_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'reps': 8.5, 'performed_on': '2026-01-05', 'idempotency_key': 'k-reps-fracao'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_whole_number_float_reps_is_accepted(self):
        # 8.0 chega como float no JSON (sem ponto decimal na origem seria
        # int, mas alguns clientes serializam numero inteiro como float) --
        # nao e uma fracao de verdade, deve ser aceito como 8.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'reps': 8.0, 'performed_on': '2026-01-05', 'idempotency_key': 'k-reps-float-inteiro'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reps'], 8)

    def test_reps_above_ceiling_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'reps': 1000, 'performed_on': '2026-01-05', 'idempotency_key': 'k-reps-teto'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_non_finite_weight_kg_returns_400(self):
        # json.loads aceita o literal NaN (extensao nao-padrao) -- sem o
        # cheque .is_finite() em _decimal_or_none, isso viraria 500 mais
        # na frente (Decimal('NaN') < 0 levanta InvalidOperation).
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': float('nan'), 'performed_on': '2026-01-05', 'idempotency_key': 'k-peso-nan'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 0)

    def test_rir_half_point_is_accepted(self):
        # rir_spec do schema do programa ja usa meio-ponto (ex. "RIR 1.5")
        # -- confirma que a validacao nova nao regride essa precisao.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 100, 'rir': 1.5, 'performed_on': '2026-01-05', 'idempotency_key': 'k-rir-meio-ponto'}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['rir'], 1.5)

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

    def test_supersedes_key_corrects_the_target_record(self):
        # Fase 3 do plano curva-carga-completa-reps-rir-recorde (§4.1) --
        # MESMO endpoint, so' um campo opcional novo.
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 900, 'performed_on': '2026-01-05', 'idempotency_key': 'k-original'}
            ),
            content_type='application/json',
        )

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {
                    'movement_slug': 'agachamento-livre',
                    'weight_kg': 90,
                    'performed_on': '2026-01-05',
                    'idempotency_key': 'k-correcao',
                    'supersedes_idempotency_key': 'k-original',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['weight_kg'], 90.0)
        original = PublicWorkoutLoadLog.objects.get(idempotency_key='k-original')
        self.assertFalse(original.is_active)

    def test_correcting_someone_elses_record_returns_400(self):
        account_a = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        account_b = _make_account_with_subscription(email='b@example.com', plan_slug='bruno')
        _login(self.client, account_a.pk)
        self.client.post(
            self._url('juliana'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 900, 'performed_on': '2026-01-05', 'idempotency_key': 'k-de-a'}
            ),
            content_type='application/json',
        )

        _login(self.client, account_b.pk)
        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {
                    'movement_slug': 'agachamento-livre',
                    'weight_kg': 90,
                    'performed_on': '2026-01-05',
                    'idempotency_key': 'k-tentativa-b',
                    'supersedes_idempotency_key': 'k-de-a',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 1)

    def test_correcting_an_already_corrected_record_returns_409(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'movement_slug': 'agachamento-livre', 'weight_kg': 900, 'performed_on': '2026-01-05', 'idempotency_key': 'k-original'}
            ),
            content_type='application/json',
        )
        self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {
                    'movement_slug': 'agachamento-livre', 'weight_kg': 90, 'performed_on': '2026-01-05',
                    'idempotency_key': 'k-correcao-1', 'supersedes_idempotency_key': 'k-original',
                }
            ),
            content_type='application/json',
        )

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {
                    'movement_slug': 'agachamento-livre', 'weight_kg': 91, 'performed_on': '2026-01-05',
                    'idempotency_key': 'k-correcao-2', 'supersedes_idempotency_key': 'k-original',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 409)


class PublicWorkoutRecordLoadAchievementEndpointTests(TestCase):
    # Fase 4 do plano curva-carga-completa-reps-rir-recorde (§6.2) --
    # `achievement` chega pro cliente dentro do MESMO envelope JSON que
    # os outros campos, nunca um envelope separado.

    def _url(self, slug='bruno'):
        return reverse('public-workout-record-load', kwargs={'plan_slug': slug})

    def test_first_log_has_no_achievement_in_the_response(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 90, 'performed_on': '2026-01-05',
                'idempotency_key': 'k1', 'set_role': 'top_set',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['achievement'])

    def test_higher_weight_returns_an_achievement_envelope(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 90, 'performed_on': '2026-01-05',
                'idempotency_key': 'k1', 'set_role': 'top_set',
            }),
            content_type='application/json',
        )

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 92.5, 'performed_on': '2026-01-12',
                'idempotency_key': 'k2', 'set_role': 'top_set',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['achievement'],
            {'kind': 'load_record', 'previous_weight_kg': 90.0, 'delta_kg': 2.5},
        )

    def test_warmup_set_role_never_gets_an_achievement(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)
        self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 90, 'performed_on': '2026-01-05',
                'idempotency_key': 'k1', 'set_role': 'top_set',
            }),
            content_type='application/json',
        )

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'movement_slug': 'agachamento-livre', 'weight_kg': 120, 'performed_on': '2026-01-12',
                'idempotency_key': 'k2', 'set_role': 'warmup',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['achievement'])
        self.assertEqual(PublicWorkoutLoadLog.objects.count(), 2)
