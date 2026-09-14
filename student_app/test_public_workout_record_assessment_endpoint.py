"""
ARQUIVO: testes de POST /renan/<slug>/avaliacoes (Onda A3/B4 —
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- e o endpoint de escrita da autoavaliacao ONLINE (US Navy) que faltava:
  PublicWorkoutAssessmentsView (avaliacoes.json) so leitura, e a
  avaliacao PRESENCIAL (Jackson-Pollock) continua exclusiva do
  management command do treinador. Mesma regra de auth do record_load:
  exige sessao de LOGIN + gate de posse do slug.
"""

import json

from django.test import TestCase
from django.urls import reverse

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


class PublicWorkoutRecordAssessmentEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-record-assessment', kwargs={'plan_slug': slug})

    def test_without_session_returns_401(self):
        response = self.client.post(
            self._url(),
            data=json.dumps({'measured_at': '2026-01-05', 'weight_kg': 80}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)

    def test_session_of_another_slugs_owner_returns_404(self):
        account = _make_account_with_subscription(email='a@example.com', plan_slug='juliana')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05', 'weight_kg': 80}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_record_assessment_with_weight_and_measurements(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({
                'measured_at': '2026-01-05',
                'weight_kg': 80.5,
                'measurements': {'cintura': 82, 'pescoco': 38},
                'notes': 'medi em casa',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['measured_at'], '2026-01-05')
        self.assertEqual(body['weight_kg'], 80.5)
        self.assertEqual(body['measurements'], {'cintura': 82, 'pescoco': 38})
        self.assertIsNone(body['body_fat_percent'])

    def test_owner_can_record_with_only_measurements_no_weight(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05', 'measurements': {'cintura': 82}}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['weight_kg'])

    def test_body_fat_percent_in_payload_is_rejected(self):
        # Autoavaliacao online nunca declara BF% — isso e' exclusivo do
        # fluxo presencial do treinador (skinfold/dispositivo).
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05', 'weight_kg': 80, 'body_fat_percent': 15.0}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_body_fat_source_in_payload_is_rejected(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05', 'weight_kg': 80, 'body_fat_source': 'device'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_measured_at_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'weight_kg': 80}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_weight_and_measurements_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_measurements_not_a_dict_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05', 'measurements': 'cintura 82'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_negative_weight_kg_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-01-05', 'weight_kg': -10}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_malformed_json_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(self._url('bruno'), data=b'{nao-e-json', content_type='application/json')

        self.assertEqual(response.status_code, 400)

    def test_valid_json_that_is_not_an_object_returns_400(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'), data=json.dumps(['nao', 'e', 'um', 'objeto']), content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    def test_unknown_slug_returns_404(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('nao-existe'),
            data=json.dumps({'measured_at': '2026-01-05', 'weight_kg': 80}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)


_SEVEN_FOLDS = {
    'peitoral': 8, 'axilar': 15, 'triceps': 20,
    'subescapular': 13, 'abdomen': 26, 'iliaca': 13, 'coxa': 27,
}


class PublicWorkoutRecordAssessmentSkinfoldTests(TestCase):
    """Onda A3/B4 (segunda entrega): dobras cutaneas online, so depois
    que o treinador ja tiver lancado 1 avaliacao por dobra presencial
    deste plano — decisao do Renan de nao deixar liberado por padrao."""

    def _url(self, slug='bruno'):
        return reverse('public-workout-record-assessment', kwargs={'plan_slug': slug})

    def _unlock(self, plan_slug):
        from public_workouts.services import record_assessment

        record_assessment(
            plan_slug=plan_slug,
            measured_at='2026-01-01',
            body_fat_percent=18.0,
            body_fat_source='skinfold_jp7',
        )

    def test_skinfolds_rejected_without_presencial_history(self):
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'age': 30, 'skinfolds': _SEVEN_FOLDS}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_skinfolds_accepted_after_presencial_history_and_computes_body_fat(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'age': 30, 'skinfolds': _SEVEN_FOLDS}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNotNone(body['body_fat_percent'])
        self.assertIn('Dobras (mm)', body['notes'])

    def test_skinfolds_without_age_returns_400(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'skinfolds': _SEVEN_FOLDS}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_skinfolds_missing_one_fold_returns_400(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        incomplete = dict(_SEVEN_FOLDS)
        del incomplete['coxa']
        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'age': 30, 'skinfolds': incomplete}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_skinfolds_not_a_dict_returns_400(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'age': 30, 'skinfolds': 'nao-e-dict'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_skinfolds_non_numeric_value_returns_400(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        broken = dict(_SEVEN_FOLDS)
        broken['coxa'] = 'nao-e-numero'
        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'age': 30, 'skinfolds': broken}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_skinfolds_negative_value_returns_400(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        negative = dict(_SEVEN_FOLDS)
        negative['coxa'] = -5
        response = self.client.post(
            self._url('bruno'),
            data=json.dumps({'measured_at': '2026-02-01', 'age': 30, 'skinfolds': negative}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_body_fat_percent_still_rejected_even_with_skinfolds_unlocked(self):
        self._unlock('bruno')
        account = _make_account_with_subscription(email='bruno@example.com', plan_slug='bruno')
        _login(self.client, account.pk)

        response = self.client.post(
            self._url('bruno'),
            data=json.dumps(
                {'measured_at': '2026-02-01', 'age': 30, 'skinfolds': _SEVEN_FOLDS, 'body_fat_percent': 9.0}
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
