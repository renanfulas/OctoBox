"""L4: o fim do descanso do modo foco vira push agendado no servidor.

O iOS congela o PWA fora da tela, então o aviso do fim do descanso com o app
fechado ou a tela bloqueada sai do servidor. Aqui o aluno real usa o guia e o
servidor confere: agenda ao registrar a série, reagenda no "+30 s", cancela ao
pular e ao encerrar; com a tela à vista perto do fim o app cancela sozinho, e
se a tela bloquear depois disso o aviso volta e é enviado.

Service worker e PushManager simulados (o mesmo stub do e2e de verificação de
push), com o aparelho já inscrito: o Chromium de teste não fala com o serviço
de push real.
"""

import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import Page, expect

from tests.e2e.curva_login import enter_with_magic_link


_EMAIL = 'curva-rest-e2e@example.test'
_MOVEMENT_SLUG = 'curva-rest-e2e-squat'
_ENDPOINT = 'https://fcm.googleapis.com/fcm/send/e2e-rest-device'
PUSH_STUB = """(() => {
  const device = {
    endpoint: '%s',
    toJSON() { return { endpoint: this.endpoint, keys: { p256dh: 'test', auth: 'test' } }; },
    async unsubscribe() { return true; },
  };
  const registration = { pushManager: {
    async getSubscription() { return device; },
    async subscribe() { return device; },
  } };
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: {
    async register() { return registration; },
    async getRegistration() { return registration; },
  } });
  window.PushManager = function () {};
  window.Notification = { permission: 'granted', requestPermission: async () => 'granted' };
})();""" % _ENDPOINT
# Bloquear a tela: o navegador avisa a página com visibilitychange.
_LOCK_SCREEN = """() => {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
  document.dispatchEvent(new Event('visibilitychange'));
}"""
PUSH_SETTINGS = {
    'STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY': 'test-public',
    'STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY': 'test-private',
    'STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT': 'mailto:test@example.com',
    'PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS': 'fcm.googleapis.com',
}


@pytest.fixture(autouse=True)
def _cleanup_rest_alert_e2e(django_db_blocker):
    def cleanup():
        with django_db_blocker.unblock():
            from public_workouts.models import (
                PublicWorkoutAccount, PublicWorkoutMovement, PublicWorkoutOutboxMessage, PublicWorkoutProgram,
                PublicWorkoutPushSubscription,
            )

            program_ids = PublicWorkoutProgram.objects.filter(slug='bruno', program_id='rest-e2e-2026').values_list('pk', flat=True)
            PublicWorkoutOutboxMessage.objects.filter(
                aggregate_type='program', aggregate_id__in=[str(pk) for pk in program_ids],
            ).delete()
            subscription_ids = PublicWorkoutPushSubscription.objects.filter(endpoint=_ENDPOINT).values_list('pk', flat=True)
            PublicWorkoutOutboxMessage.objects.filter(
                aggregate_type='push_subscription', aggregate_id__in=[str(pk) for pk in subscription_ids],
            ).delete()
            PublicWorkoutAccount.objects.filter(email=_EMAIL).delete()
            PublicWorkoutProgram.objects.filter(slug='bruno', program_id='rest-e2e-2026').delete()
            PublicWorkoutMovement.objects.filter(slug=_MOVEMENT_SLUG).delete()

    cleanup()
    yield
    cleanup()


def _prepare(rest_seconds):
    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutSubscription
    from public_workouts.push import subscribe
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program
    from shared_support.platform_cache import platform_cache

    platform_cache.clear()
    payload = build_example_payload()
    payload['program_id'] = 'rest-e2e-2026'
    movement = payload['days'][0]['blocks'][0]['movements'][0]
    movement['movement_slug'] = _MOVEMENT_SLUG
    movement['guided_prescription'] = {
        'version': 1, 'stages': [
            {'stage_id': 'top', 'role': 'top_set', 'min_sets': 3, 'max_sets': 3,
             'reps_min': 6, 'reps_max': 8, 'rest_seconds': rest_seconds,
             'load_rule': {'kind': 'manual'}},
        ],
    }
    publish_program(slug='bruno', payload=payload)
    account = PublicWorkoutAccount.objects.create(email=_EMAIL, onboarding_completed_at=timezone.now())
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    # Este aparelho já ativou os avisos antes do treino.
    subscribe(account_id=account.pk, data={'endpoint': _ENDPOINT, 'keys': {'p256dh': 'test', 'auth': 'test'}})
    token = PublicWorkoutLoginToken.objects.create(account=account, expires_at=timezone.now() + timedelta(hours=1))
    return account, token


def _open_guided(page: Page, live_server, token):
    page.add_init_script(PUSH_STUB)
    page.set_viewport_size({'width': 390, 'height': 844})
    enter_with_magic_link(page, f'{live_server.url}/treinos/login?token={token.token}&next=/renan/bruno')
    page.locator('[data-workout-cycle-nav][data-cycle-key="treino"]').click()
    expect(page.locator('[data-workout-guided]')).to_have_attribute('data-rest-alert-url', '/renan/bruno/push/descanso')
    page.locator('[data-workout-guided-start]').click()
    page.locator('[data-guided-countdown-skip]').click()
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible()


def _rest_call(method):
    return lambda response: response.request.method == method and response.url.endswith('/renan/bruno/push/descanso')


def _record_set(page: Page):
    page.locator('[data-workout-guided-weight]').fill('50')
    page.locator('[data-workout-guided-reps]').fill('7')
    with page.expect_response(_rest_call('POST')) as scheduled:
        page.locator('[data-workout-guided-set]').click()
    assert scheduled.value.status == 200


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True, **PUSH_SETTINGS)
def test_rest_alert_follows_plus_thirty_skip_and_end(page: Page, live_server):
    from public_workouts.models import PublicWorkoutRestAlert, PublicWorkoutRestAlertStatus

    account, token = _prepare(rest_seconds=30)
    _open_guided(page, live_server, token)

    before = timezone.now()
    _record_set(page)
    alert = PublicWorkoutRestAlert.objects.get(session__account=account)
    assert alert.status == PublicWorkoutRestAlertStatus.PENDING
    assert alert.subscription.endpoint == _ENDPOINT
    assert alert.set_number == 2 and alert.exercise_label
    assert before + timedelta(seconds=26) < alert.due_at < timezone.now() + timedelta(seconds=31)
    first_due = alert.due_at

    with page.expect_response(_rest_call('POST')):
        page.locator('[data-guided-add-rest]').click()
    alert.refresh_from_db()
    assert alert.status == PublicWorkoutRestAlertStatus.PENDING
    assert timedelta(seconds=27) < alert.due_at - first_due < timedelta(seconds=33)

    with page.expect_response(_rest_call('DELETE')):
        page.locator('[data-guided-skip-rest]').click()
    alert.refresh_from_db()
    assert alert.status == PublicWorkoutRestAlertStatus.CANCELLED

    # Próximo descanso agenda de novo; encerrar o treino cancela.
    expect(page.locator('[data-guided-screen="exercise"]')).to_be_visible()
    _record_set(page)
    alert.refresh_from_db()
    assert (alert.status, alert.set_number) == (PublicWorkoutRestAlertStatus.PENDING, 3)
    page.locator('[data-guided-open-sheet]').click()
    page.locator('[data-guided-open-summary]').click()
    with page.expect_response(_rest_call('DELETE')):
        page.locator('[data-workout-guided-partial]').click()
    alert.refresh_from_db()
    assert alert.status == PublicWorkoutRestAlertStatus.CANCELLED


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True, **PUSH_SETTINGS)
def test_visible_app_cancels_before_send_and_locking_the_screen_brings_the_push_back(page: Page, live_server):
    from public_workouts import rest_alerts
    from public_workouts.models import PublicWorkoutRestAlert, PublicWorkoutRestAlertStatus

    account, token = _prepare(rest_seconds=8)
    _open_guided(page, live_server, token)
    _record_set(page)
    alert = PublicWorkoutRestAlert.objects.get(session__account=account)

    # Tela à vista a 4 s do fim: o app cancela e o próprio bipe dá conta.
    with page.expect_response(_rest_call('DELETE'), timeout=8000):
        pass
    alert.refresh_from_db()
    assert alert.status == PublicWorkoutRestAlertStatus.CANCELLED
    assert alert.due_at - timezone.now() > timedelta(seconds=2), 'o cancelamento chega antes do horário de envio'

    # Bloqueou a tela depois do cancelamento: o aviso volta para o tempo que falta.
    with page.expect_response(_rest_call('POST')) as rescheduled:
        page.evaluate(_LOCK_SCREEN)
    assert rescheduled.value.status == 200
    alert.refresh_from_db()
    assert alert.status == PublicWorkoutRestAlertStatus.PENDING

    time.sleep(max(0.0, (alert.due_at - timezone.now()).total_seconds()) + 0.1)
    with patch('public_workouts.push.send', return_value=True) as send:
        assert rest_alerts.dispatch_due()['sent'] == 1
    assert send.call_args.kwargs['title'] == 'Descanso acabou'
    assert send.call_args.kwargs['body'].endswith('série 2')
    assert send.call_args.kwargs['tag'] == f'curva-rest-{alert.session_id}'
    alert.refresh_from_db()
    assert alert.status == PublicWorkoutRestAlertStatus.SENT
