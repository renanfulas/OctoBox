"""L4: aluno com sessão antiga confirma o e-mail por código e ativa avisos, sem sair do app.

O push exige identidade verificada (#325). O link do e-mail abre fora do app
instalado (no iPhone, Safari e o app da tela inicial não compartilham
cookies), então o código chega no e-mail da conta e é digitado no próprio app.
Sessão sem identidade verificada (antiga ponte do link) não vale mais: o app
abre o login, e o código digitado ali devolve o aluno ao treino já verificado.
"""

import os

import pytest
from django.core import mail, signing
from django.test import override_settings
from playwright.sync_api import Page, expect

# Service worker e PushManager simulados: o Chromium de teste não fala com o
# serviço de push real. O mesmo stub do e2e de PWA/push existente.
PUSH_STUB = """(() => {
  let subscription = null;
  const device = {
    endpoint: 'https://fcm.googleapis.com/fcm/send/e2e-verify-device',
    toJSON() { return { endpoint: this.endpoint, keys: { p256dh: 'test', auth: 'test' } }; },
    async unsubscribe() { subscription = null; return true; },
  };
  const registration = { pushManager: {
    async getSubscription() { return subscription; },
    async subscribe() { subscription = device; return device; },
  } };
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: {
    async register() { return registration; },
    async getRegistration() { return registration; },
  } });
  window.PushManager = function () {};
  window.Notification = { permission: 'granted', requestPermission: async () => 'granted' };
})();"""


@pytest.fixture(autouse=True)
def _cleanup_push_verification_e2e(django_db_blocker):
    yield
    with django_db_blocker.unblock():
        from public_workouts.models import PublicWorkoutAccount, PublicWorkoutOutboxMessage, PublicWorkoutProgram

        ids = PublicWorkoutProgram.objects.filter(slug='bruno').values_list('pk', flat=True)
        PublicWorkoutOutboxMessage.objects.filter(
            aggregate_type='program', aggregate_id__in=[str(pk) for pk in ids],
        ).delete()
        PublicWorkoutProgram.objects.filter(slug='bruno').delete()
        PublicWorkoutAccount.objects.filter(email='push-verify-e2e@example.test').delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(
    DEBUG=True,
    STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='test-public',
    STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='test-private',
    STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:test@example.com',
    PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS='fcm.googleapis.com',
)
def test_old_session_confirms_email_code_in_app_and_activates_push(page: Page, live_server):
    from shared_support.platform_cache import platform_cache
    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutSubscription
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program
    from student_identity.public_workout_login import login_code_for_token
    from student_identity.public_workout_session import (
        PUBLIC_WORKOUT_SESSION_COOKIE_NAME, PUBLIC_WORKOUT_SESSION_SALT,
    )

    from django.utils import timezone

    platform_cache.clear()
    account = PublicWorkoutAccount.objects.create(
        email='push-verify-e2e@example.test', onboarding_completed_at=timezone.now(),
    )
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    publish_program(slug='bruno', payload=build_example_payload())
    # Sessão de quem entrou antes do #325: logado, mas sem a marca de identidade verificada.
    session = signing.dumps({'account_id': account.pk}, salt=PUBLIC_WORKOUT_SESSION_SALT, compress=True)
    page.context.add_cookies([{
        'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME, 'value': session, 'domain': 'localhost', 'path': '/',
    }])
    page.add_init_script(PUSH_STUB)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(f'{live_server.url}/renan/bruno')

    page.wait_for_url('**/treinos/login?next=/renan/bruno')
    page.locator('input[name="email"]').first.fill('push-verify-e2e@example.test')
    page.get_by_role('button', name='Enviar link').click()
    code_form = page.locator('[data-login-code]')
    expect(code_form).to_be_visible()
    assert mail.outbox[-1].to == ['push-verify-e2e@example.test']
    token = PublicWorkoutLoginToken.objects.filter(account=account).latest('created_at')
    code = login_code_for_token(token.token)
    assert code in mail.outbox[-1].body
    if screenshot_path := os.environ.get('CURVA_PUSH_VERIFY_SCREENSHOT'):
        code_form.screenshot(path=screenshot_path)

    code_form.locator('input[name="code"]').fill(code)
    code_form.locator('button[type="submit"]').click()
    page.wait_for_url('**/renan/bruno')

    # Sem sair do app: o treino volta verificado e o aparelho pode ser vinculado.
    expect(page.locator('[data-workout-push-verify]')).to_have_count(0)
    page.locator('[data-workout-push-enable]').click()
    page.locator('[data-workout-tab-target="workout-panel-perfil"]').click()
    expect(page.locator('[data-workout-push-profile-status]')).to_have_text('Avisos ativos neste dispositivo.')
    assert account.push_subscriptions.filter(revoked_at__isnull=True).count() == 1
