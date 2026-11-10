"""Telemetria de atraso da sincronização offline (F3,
docs/plans/curva-offline-first-estrategia.md): o envio drenado da fila do
aparelho traz X-Curva-Queued-Ms e vira uma linha de log sem dado pessoal."""

import json

from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from student_app.views.public_workout_offline_telemetry import (
    lag_bucket,
    log_offline_sync_lag,
    offline_sync_lag_ms,
)
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)

HOUR_MS = 3_600_000


class OfflineSyncLagParsingTests(SimpleTestCase):
    def _request(self, value=None):
        headers = {} if value is None else {'HTTP_X_CURVA_QUEUED_MS': value}
        return RequestFactory().post('/renan/bruno/carga', **headers)

    def test_ignores_missing_garbage_and_normal_online_sends(self):
        for value in (None, '', 'abc', '-5', '1.5', '59999'):
            self.assertIsNone(offline_sync_lag_ms(self._request(value)), value)

    def test_ignores_absurd_values(self):
        self.assertIsNone(offline_sync_lag_ms(self._request(str(91 * 24 * HOUR_MS))))

    def test_reads_a_real_delay(self):
        self.assertEqual(offline_sync_lag_ms(self._request(str(2 * HOUR_MS))), 2 * HOUR_MS)

    def test_buckets(self):
        self.assertEqual(lag_bucket(2 * 60_000), 'lt_5m')
        self.assertEqual(lag_bucket(30 * 60_000), 'lt_1h')
        self.assertEqual(lag_bucket(5 * HOUR_MS), 'lt_1d')
        self.assertEqual(lag_bucket(3 * 24 * HOUR_MS), 'lt_7d')
        self.assertEqual(lag_bucket(10 * 24 * HOUR_MS), 'gte_7d')

    def test_log_line_has_no_account_or_value(self):
        with self.assertLogs('octobox.curva.offline', level='INFO') as captured:
            log_offline_sync_lag(self._request(str(5 * HOUR_MS)), 'load')
        self.assertEqual(captured.output, [
            'INFO:octobox.curva.offline:curva_offline_sync_lag kind=load bucket=lt_1d lag_s=18000',
        ])


class OfflineSyncLagEndpointTests(TestCase):
    def setUp(self):
        account = PublicWorkoutAccount.objects.create(email='bruno-offline@example.com')
        PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.pk, identity_verified=True
        )

    def test_assessment_drained_from_the_queue_is_logged(self):
        with self.assertLogs('octobox.curva.offline', level='INFO') as captured:
            response = self.client.post(
                reverse('public-workout-record-assessment', kwargs={'plan_slug': 'bruno'}),
                data=json.dumps({'measured_at': '2026-11-08', 'weight_kg': 80, 'idempotency_key': 'k-lag'}),
                content_type='application/json',
                HTTP_X_CURVA_QUEUED_MS=str(26 * HOUR_MS),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured.output, [
            'INFO:octobox.curva.offline:curva_offline_sync_lag kind=assessment bucket=lt_7d lag_s=93600',
        ])

    def test_onboarding_and_guided_session_log_their_kind(self):
        with self.assertLogs('octobox.curva.offline', level='INFO') as captured:
            self.client.post(
                reverse('public-workout-onboarding-complete', kwargs={'plan_slug': 'bruno'}),
                HTTP_X_CURVA_QUEUED_MS=str(HOUR_MS),
            )
            self.client.post(
                '/renan/bruno/sessao', data=json.dumps({'action': 'nada'}), content_type='application/json',
                HTTP_X_CURVA_QUEUED_MS=str(HOUR_MS),
            )
        kinds = [line.split('kind=')[1].split(' ')[0] for line in captured.output]
        self.assertEqual(kinds, ['onboarding', 'guided'])
