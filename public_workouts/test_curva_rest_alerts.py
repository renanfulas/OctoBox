"""Aviso push do fim do descanso: endpoint, agendamento, cancelamento e worker.

O envio real ao gateway fica de fora (`push.send` simulado); o que se prova é
quem pode agendar, para qual aparelho, quando o worker envia e o que impede
o envio (cancelamento, treino encerrado, aparelho revogado, atraso).
"""

import io
import json
import threading
import time
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from public_workouts import rest_alerts
from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutPushSubscription, PublicWorkoutRestAlert,
    PublicWorkoutRestAlertStatus, PublicWorkoutSubscription, PublicWorkoutTrainingSession,
)
from public_workouts.push import subscribe
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.training_sessions import finish_session, start_session


PUSH_SETTINGS = {
    'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY': 'test-public',
    'STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY': 'test-private',
    'STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT': 'mailto:test@example.com',
    'PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS': 'fcm.googleapis.com',
}
DEVICE = {
    'endpoint': 'https://fcm.googleapis.com/fcm/send/rest-device-1',
    'keys': {'p256dh': 'public-device-key', 'auth': 'auth-device-key'},
}
OTHER_DEVICE = {
    'endpoint': 'https://fcm.googleapis.com/fcm/send/rest-device-2',
    'keys': {'p256dh': 'public-device-key-2', 'auth': 'auth-device-key-2'},
}
# Folga do worker medida contra o horário marcado: a meta do produto é 1–2 s.
TOLERANCE = timedelta(milliseconds=500)


def _student(email='rest-curva@example.test', *, device=DEVICE):
    account = PublicWorkoutAccount.objects.create(email=email, onboarding_completed_at=timezone.now())
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    subscription = subscribe(account_id=account.pk, data=device) if device else None
    return account, subscription


def _session(account):
    return start_session(account_id=account.pk, plan_slug='bruno', day_id='seg')


def _schedule(account, session, *, remaining_ms=60_000, endpoint=DEVICE['endpoint'], **extra):
    return rest_alerts.schedule(
        account_id=account.pk, plan_slug='bruno', session_id=session.pk, endpoint=endpoint,
        remaining_ms=remaining_ms, exercise=extra.get('exercise', 'Supino reto'),
        set_number=extra.get('set_number', 2), now=extra.get('now'),
    )


def _run_in_own_connection(fn):
    """Roda fn numa thread com conexão própria e autocommit de verdade.

    O NOTIFY só sai no COMMIT, que a transação do TestCase nunca faz. Mesma
    técnica de student_identity/test_public_workout_login.py: TransactionTestCase
    não serve porque o flush não conhece os schemas de tenant.
    """
    outcome = {}

    def target():
        try:
            outcome['value'] = fn()
        except BaseException as exc:
            outcome['error'] = exc
        finally:
            connection.close()

    thread = threading.Thread(target=target)
    thread.start()
    return thread, outcome


def _joined(thread, outcome, *, timeout=10.0):
    thread.join(timeout=timeout)
    if 'error' in outcome:
        raise outcome['error']
    return outcome.get('value')


def _release_worker_lock():
    # Lock e LISTEN são da sessão do Postgres, não da transação do teste.
    with connection.cursor() as cursor:
        cursor.execute('UNLISTEN *')
        cursor.execute('SELECT pg_advisory_unlock_all()')


@override_settings(**PUSH_SETTINGS)
class RestAlertEndpointTest(TestCase):
    def setUp(self):
        from shared_support.platform_cache import platform_cache

        platform_cache.clear()
        publish_program(slug='bruno', payload=build_example_payload())
        self.account, self.device = _student()
        self.session = _session(self.account)
        self.url = reverse('public-workout-push-rest', kwargs={'plan_slug': 'bruno'})

    def _login(self, account=None):
        token = PublicWorkoutLoginToken.objects.create(
            account=account or self.account, expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = self.client.get(reverse('public-workout-login'), {'token': str(token.token), 'next': '/renan/bruno'})
        self.assertEqual(response.status_code, 302)

    def _post(self, **overrides):
        body = {
            'session_id': str(self.session.pk), 'endpoint': DEVICE['endpoint'],
            'remaining_ms': 90_000, 'exercise': 'Supino reto', 'set_number': 3,
        }
        body.update(overrides)
        return self.client.post(self.url, data=json.dumps(body), content_type='application/json')

    def _delete(self, session_id=None):
        return self.client.delete(
            self.url, data=json.dumps({'session_id': str(session_id or self.session.pk)}),
            content_type='application/json',
        )

    def test_guided_launcher_exposes_rest_alert_url_only_to_verified_login(self):
        page = self.client.get('/renan/bruno')
        self.assertNotContains(page, 'data-rest-alert-url')
        self._login()
        page = self.client.get('/renan/bruno')
        self.assertContains(page, f'data-rest-alert-url="{self.url}"')
        self.assertContains(page, 'guided-rest-alert.js')

    def test_link_possession_without_verified_identity_cannot_schedule(self):
        self.client.get('/renan/bruno')  # cookie de posse, sem identity_verified
        self.assertEqual(self._post().status_code, 401)
        self.assertEqual(self._delete().status_code, 401)
        self.assertFalse(PublicWorkoutRestAlert.objects.exists())

    def test_schedule_uses_server_clock_and_targets_the_requesting_device(self):
        self._login()
        before = timezone.now()
        response = self._post(remaining_ms=90_000)
        after = timezone.now()
        self.assertEqual(response.status_code, 200)
        alert = PublicWorkoutRestAlert.objects.get(session=self.session)
        self.assertEqual(alert.status, PublicWorkoutRestAlertStatus.PENDING)
        self.assertEqual(alert.subscription_id, self.device.pk)
        self.assertGreaterEqual(alert.due_at, before + timedelta(seconds=90))
        self.assertLessEqual(alert.due_at, after + timedelta(seconds=90))
        self.assertEqual((alert.exercise_label, alert.set_number), ('Supino reto', 3))

    def test_plus_thirty_reschedules_the_same_alert(self):
        self._login()
        self._post(remaining_ms=60_000)
        first = PublicWorkoutRestAlert.objects.get(session=self.session)
        self._post(remaining_ms=88_000)
        alert = PublicWorkoutRestAlert.objects.get(session=self.session)
        self.assertEqual(PublicWorkoutRestAlert.objects.count(), 1)
        self.assertEqual(alert.pk, first.pk)
        self.assertEqual(alert.revision, first.revision + 1)
        self.assertGreater(alert.due_at, first.due_at + timedelta(seconds=27))

    def test_skip_cancels_pending_alert_once(self):
        self._login()
        self._post()
        response = self._delete()
        self.assertEqual(response.json(), {'ok': True, 'cancelled': 1})
        self.assertEqual(PublicWorkoutRestAlert.objects.get().status, PublicWorkoutRestAlertStatus.CANCELLED)
        self.assertEqual(self._delete().json()['cancelled'], 0)
        # O próximo descanso da mesma sessão reativa o mesmo registro.
        self._post()
        self.assertEqual(PublicWorkoutRestAlert.objects.get().status, PublicWorkoutRestAlertStatus.PENDING)

    def test_device_without_push_subscription_is_refused(self):
        self._login()
        response = self._post(endpoint=OTHER_DEVICE['endpoint'])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error'], 'push-not-subscribed')
        self.device.revoked_at = timezone.now()
        self.device.save()
        self.assertEqual(self._post().json()['error'], 'push-not-subscribed')
        self.assertFalse(PublicWorkoutRestAlert.objects.exists())

    def test_other_accounts_device_and_session_are_refused(self):
        other, other_device = _student('rest-other@example.test', device=OTHER_DEVICE)
        self._login()
        self.assertEqual(self._post(endpoint=OTHER_DEVICE['endpoint']).json()['error'], 'push-not-subscribed')
        foreign = _session(other)
        response = self._post(session_id=str(foreign.pk))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error'], 'session-not-active')
        # Nem cancelar o aviso de outra conta.
        _schedule(other, foreign, endpoint=other_device.endpoint)
        self.assertEqual(self._delete(foreign.pk).json()['cancelled'], 0)
        self.assertEqual(PublicWorkoutRestAlert.objects.get(session=foreign).status, PublicWorkoutRestAlertStatus.PENDING)

    def test_ended_or_unknown_session_is_refused(self):
        self._login()
        self.assertEqual(self._post(session_id='not-a-uuid').json()['error'], 'invalid-session')
        finish_session(account_id=self.account.pk, plan_slug='bruno', session_id=self.session.pk, partial=True)
        self.assertEqual(self._post().json()['error'], 'session-not-active')

    def test_invalid_remaining_and_set_number_are_refused(self):
        self._login()
        for value in (0, 999, 30 * 60 * 1000 + 1, '90000', True, None):
            response = self._post(remaining_ms=value)
            self.assertEqual(response.status_code, 400, value)
            self.assertEqual(response.json()['error'], 'invalid-remaining')
        self.assertEqual(self._post(set_number=0).json()['error'], 'invalid-set-number')
        self.assertFalse(PublicWorkoutRestAlert.objects.exists())

    def test_label_is_sanitized_and_trimmed(self):
        self._login()
        self._post(exercise='  Supino\n\x00reto  ' + 'x' * 200)
        label = PublicWorkoutRestAlert.objects.get().exercise_label
        self.assertTrue(label.startswith('Supino reto x'))
        self.assertEqual(len(label), 80)

    @override_settings(STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='')
    def test_schedule_needs_push_configured(self):
        self._login()
        self.assertEqual(self._post().status_code, 503)


@override_settings(**PUSH_SETTINGS)
class RestAlertDispatchTest(TestCase):
    def setUp(self):
        publish_program(slug='bruno', payload=build_example_payload())
        self.account, self.device = _student()
        self.session = _session(self.account)

    @patch('public_workouts.push.send', return_value=True)
    def test_due_alert_is_sent_once_with_rest_payload(self, send):
        now = timezone.now()
        alert = _schedule(self.account, self.session, remaining_ms=5_000, now=now - timedelta(seconds=6))
        self.assertEqual(rest_alerts.dispatch_due(now=now), {'sent': 1, 'failed': 0, 'cancelled': 0})
        self.assertEqual(rest_alerts.dispatch_due(now=now), {'sent': 0, 'failed': 0, 'cancelled': 0})
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['subscription'].pk, self.device.pk)
        self.assertEqual(kwargs['title'], 'Descanso acabou')
        self.assertEqual(kwargs['body'], 'Supino reto, série 2')
        self.assertEqual(kwargs['tag'], f'curva-rest-{self.session.pk}')
        self.assertEqual(kwargs['url'], '/renan/bruno#treino-guiado')
        self.assertEqual(kwargs['urgency'], 'high')
        self.assertEqual(kwargs['ttl'], rest_alerts.PUSH_TTL_SECONDS)
        self.assertEqual(kwargs['extra'], {'kind': 'rest', 'renotify': True, 'vibrate': [180, 90, 180]})
        alert.refresh_from_db()
        self.assertEqual(alert.status, PublicWorkoutRestAlertStatus.SENT)
        self.assertIsNotNone(alert.sent_at)

    @patch('public_workouts.push.send', return_value=True)
    def test_future_and_cancelled_alerts_are_not_sent(self, send):
        _schedule(self.account, self.session, remaining_ms=60_000)
        self.assertEqual(rest_alerts.dispatch_due()['sent'], 0)
        rest_alerts.cancel(account_id=self.account.pk, plan_slug='bruno', session_id=self.session.pk)
        self.assertEqual(rest_alerts.dispatch_due(now=timezone.now() + timedelta(minutes=2))['sent'], 0)
        send.assert_not_called()

    @patch('public_workouts.push.send', return_value=True)
    def test_ending_the_workout_stops_the_alert_even_without_client_cancel(self, send):
        now = timezone.now()
        alert = _schedule(self.account, self.session, remaining_ms=5_000, now=now - timedelta(seconds=6))
        finish_session(account_id=self.account.pk, plan_slug='bruno', session_id=self.session.pk, partial=True)
        self.assertEqual(rest_alerts.dispatch_due(now=now)['cancelled'], 1)
        send.assert_not_called()
        alert.refresh_from_db()
        self.assertEqual((alert.status, alert.last_error), (PublicWorkoutRestAlertStatus.CANCELLED, 'session-ended'))

    @patch('public_workouts.push.send', return_value=True)
    def test_revoked_device_is_not_sent(self, send):
        now = timezone.now()
        alert = _schedule(self.account, self.session, remaining_ms=5_000, now=now - timedelta(seconds=6))
        self.device.revoked_at = now
        self.device.save()
        self.assertEqual(rest_alerts.dispatch_due(now=now)['failed'], 1)
        send.assert_not_called()
        alert.refresh_from_db()
        self.assertEqual(alert.last_error, 'subscription-revoked')

    @patch('public_workouts.push.send', return_value=True)
    def test_alert_late_beyond_tolerance_expires_instead_of_buzzing_late(self, send):
        now = timezone.now()
        alert = _schedule(self.account, self.session, remaining_ms=5_000, now=now - timedelta(minutes=2))
        self.assertEqual(rest_alerts.expire_overdue(now), 1)
        self.assertEqual(rest_alerts.dispatch_due(now=now)['sent'], 0)
        send.assert_not_called()
        alert.refresh_from_db()
        self.assertEqual(alert.status, PublicWorkoutRestAlertStatus.EXPIRED)

    def test_gateway_failure_is_recorded(self):
        now = timezone.now()
        alert = _schedule(self.account, self.session, remaining_ms=5_000, now=now - timedelta(seconds=6))

        def refuse(**kwargs):
            kwargs['subscription'].last_error = 'webpush-failed:500'
            kwargs['subscription'].save()
            return False

        with patch('public_workouts.push.send', side_effect=refuse):
            self.assertEqual(rest_alerts.dispatch_due(now=now)['failed'], 1)
        alert.refresh_from_db()
        self.assertEqual((alert.status, alert.last_error), (PublicWorkoutRestAlertStatus.FAILED, 'webpush-failed:500'))

    def test_plus_thirty_during_send_keeps_the_new_alert_pending(self):
        now = timezone.now()
        _schedule(self.account, self.session, remaining_ms=5_000, now=now - timedelta(seconds=6))

        def reschedule_while_sending(**kwargs):
            _schedule(self.account, self.session, remaining_ms=30_000)
            return True

        with patch('public_workouts.push.send', side_effect=reschedule_while_sending):
            rest_alerts.dispatch_due(now=now)
        alert = PublicWorkoutRestAlert.objects.get(session=self.session)
        self.assertEqual(alert.status, PublicWorkoutRestAlertStatus.PENDING)
        self.assertGreater(alert.due_at, timezone.now() + timedelta(seconds=25))

    def test_stuck_send_is_failed_after_lease(self):
        alert = _schedule(self.account, self.session, remaining_ms=5_000)
        stale = timezone.now() - rest_alerts.SENDING_LEASE - timedelta(seconds=1)
        PublicWorkoutRestAlert.objects.filter(pk=alert.pk).update(
            status=PublicWorkoutRestAlertStatus.SENDING, claimed_at=stale,
        )
        rest_alerts.expire_overdue()
        alert.refresh_from_db()
        self.assertEqual(alert.status, PublicWorkoutRestAlertStatus.FAILED)

    def test_prune_keeps_live_alerts(self):
        alert = _schedule(self.account, self.session)
        old = timezone.now() - rest_alerts.RETENTION - timedelta(hours=1)
        PublicWorkoutRestAlert.objects.filter(pk=alert.pk).update(updated_at=old)
        self.assertEqual(rest_alerts.prune(), 0)
        PublicWorkoutRestAlert.objects.filter(pk=alert.pk).update(status=PublicWorkoutRestAlertStatus.SENT)
        self.assertEqual(rest_alerts.prune(), 1)

    @patch('public_workouts.push.send', return_value=True)
    def test_once_command_sends_what_is_due(self, send):
        _schedule(self.account, self.session, remaining_ms=1_000, now=timezone.now() - timedelta(seconds=2))
        call_command('run_public_workout_rest_alerts', '--once', stdout=io.StringIO())
        send.assert_called_once()


@override_settings(**PUSH_SETTINGS)
class RestAlertWorkerTimingTest(TestCase):
    """O worker dorme até o horário e envia dentro da folga, sem fila de minuto."""

    def setUp(self):
        publish_program(slug='bruno', payload=build_example_payload())
        self.account, self.device = _student()
        self.session = _session(self.account)
        self.addCleanup(_release_worker_lock)

    def test_worker_sleeps_until_due_and_sends_within_tolerance(self):
        sent = []

        def record(**kwargs):
            sent.append(timezone.now())
            return True

        alert = _schedule(self.account, self.session, remaining_ms=1_200)
        worker = rest_alerts.RestAlertWorker(max_idle=5.0)
        deadline = time.monotonic() + 6
        with patch('public_workouts.push.send', side_effect=record):
            worker.run(should_stop=lambda: bool(sent) or time.monotonic() > deadline)
        self.assertEqual(len(sent), 1)
        lateness = sent[0] - alert.due_at
        self.assertGreaterEqual(lateness, timedelta(0))
        self.assertLess(lateness, TOLERANCE)

    def test_second_worker_stands_by_while_the_first_holds_the_lock(self):
        first = rest_alerts.RestAlertWorker(max_idle=0.01)
        self.assertTrue(first._attach())
        outcome = []

        def other_process():
            try:
                outcome.append(rest_alerts.RestAlertWorker(standby_poll=0).tick())
            finally:
                connection.close()

        thread = threading.Thread(target=other_process)
        thread.start()
        thread.join(10)
        self.assertEqual(outcome, ['standby'])


class RestAlertWorkerNotifyTest(TestCase):
    """Agendado depois que o worker dormiu: o NOTIFY do commit acorda o worker.

    Sem o NOTIFY ele só reavaliaria depois de `max_idle` (10 s) e perderia o horário.
    Tudo em conexões próprias (com commit), apagado no fim.
    """

    def setUp(self):
        email = 'rest-notify@example.test'

        def create():
            account = PublicWorkoutAccount.objects.create(email=email)
            PublicWorkoutPushSubscription.objects.create(
                account=account, endpoint=DEVICE['endpoint'], subscription=DEVICE,
            )
            session = PublicWorkoutTrainingSession.objects.create(account=account, plan_slug='bruno', day_id='seg')
            return account.pk, session.pk

        self.account_id, self.session_id = _joined(*_run_in_own_connection(create))
        self.addCleanup(lambda: _joined(*_run_in_own_connection(
            lambda: PublicWorkoutAccount.objects.filter(pk=self.account_id).delete()
        )))

    def test_idle_worker_wakes_on_notify_and_sends_on_time(self):
        sent, stop = [], threading.Event()

        def record(**kwargs):
            sent.append(timezone.now())
            stop.set()
            return True

        with patch('public_workouts.push.send', side_effect=record):
            worker, worker_outcome = _run_in_own_connection(
                lambda: rest_alerts.RestAlertWorker(max_idle=10.0).run(should_stop=stop.is_set),
            )
            time.sleep(0.5)  # o worker já está dormindo, sem nada pendente
            alert = _joined(*_run_in_own_connection(lambda: rest_alerts.schedule(
                account_id=self.account_id, plan_slug='bruno', session_id=self.session_id,
                endpoint=DEVICE['endpoint'], remaining_ms=1_000,
            )))
            stop.wait(5)
            if not stop.is_set():
                stop.set()
                _joined(*_run_in_own_connection(lambda: rest_alerts._wake_worker()))
            _joined(worker, worker_outcome, timeout=15)
        self.assertEqual(len(sent), 1)
        lateness = sent[0] - alert.due_at
        self.assertGreaterEqual(lateness, timedelta(0))
        self.assertLess(lateness, TOLERANCE)
