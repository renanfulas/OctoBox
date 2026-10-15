"""Browser smoke for the public workout PWA cache and offline fallback.

The worker retains static assets and removes old page caches containing
private workout HTML. A separate guided-session journey covers local resume.
"""

import time

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def _cleanup_published_programs_after_e2e(django_db_blocker):
    yield
    with django_db_blocker.unblock():
        from public_workouts.models import PublicWorkoutOutboxMessage, PublicWorkoutProgram

        ids = PublicWorkoutProgram.objects.filter(slug='bruno').values_list('pk', flat=True)
        PublicWorkoutOutboxMessage.objects.filter(
            aggregate_type='program', aggregate_id__in=[str(pk) for pk in ids],
        ).delete()
        PublicWorkoutProgram.objects.filter(slug='bruno').delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_public_workout_pwa_installs_and_opens_offline_shell_without_private_html(page: Page, live_server):
    """The worker precaches static assets and removes old page caches."""
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())
    origin = live_server.url.rstrip('/')

    # Seed the browser origin with a prior installation's cache names before
    # registering the current worker. Activation must delete both stale
    # caches, including the old cache of private workout pages.
    browser_events = []
    page.on('console', lambda message: browser_events.append(f'console {message.type}: {message.text}'))
    page.on('pageerror', lambda error: browser_events.append(f'pageerror: {error}'))
    page.on(
        'requestfailed',
        lambda request: browser_events.append(f'requestfailed: {request.url} ({request.failure})'),
    )
    page.on(
        'response',
        lambda response: browser_events.append(f'sw response {response.status}: {response.url}')
        if '/renan/sw.js' in response.url else None,
    )
    page.goto(f'{origin}/renan/offline/')
    page.evaluate("""async () => {
      await caches.open('public-workouts-previous-e5-static');
      await caches.open('public-workouts-previous-e5-pages');
    }""")

    page.goto(f'{origin}/renan/bruno')
    assert page.locator('link[rel="manifest"]').get_attribute('href') == '/renan/bruno/manifest.webmanifest'
    assert page.locator('script[src*="workout-pwa.js"]').count() == 1
    deadline = time.monotonic() + 20
    worker_state = {}
    while time.monotonic() < deadline:
        worker_state = page.evaluate("""async () => {
          const registrations = await navigator.serviceWorker.getRegistrations();
          return {
            controller: navigator.serviceWorker.controller?.state || null,
            registrations: registrations.map((registration) => ({
              scope: registration.scope,
              installing: registration.installing?.state || null,
              waiting: registration.waiting?.state || null,
              active: registration.active?.state || null,
            })),
          };
        }""")
        if any(registration['active'] == 'activated' for registration in worker_state['registrations']):
            break
        page.wait_for_timeout(500)
    assert any(registration['active'] == 'activated' for registration in worker_state['registrations']), (
        f"service worker not active after 20 seconds: {worker_state}; "
        f"browser={page.evaluate('() => ({secure: isSecureContext, supported: Boolean(navigator.serviceWorker), plan: document.body.dataset.planSlug})')}; "
        f"events={browser_events}"
    )
    # An online visit must not store the student's HTML in Cache Storage.
    page.reload(wait_until='domcontentloaded')
    assert page.evaluate('Boolean(navigator.serviceWorker.controller)')

    cache_state = page.evaluate("""async () => {
      const names = await caches.keys();
      const staticName = names.find((name) => name.startsWith('public-workouts-') && name.endsWith('-static'));
      const pageName = names.find((name) => name.startsWith('public-workouts-') && name.endsWith('-pages'));
      const staticKeys = staticName ? await (await caches.open(staticName)).keys() : [];
      return {
        names,
        staticName,
        pageName,
        staticUrls: staticKeys.map((request) => request.url),
      };
    }""")

    assert cache_state['staticName'], f"current static cache missing: {cache_state['names']}"
    assert cache_state['pageName'] is None, f"private page cache must be absent: {cache_state['names']}"
    assert 'public-workouts-previous-e5-static' not in cache_state['names']
    assert 'public-workouts-previous-e5-pages' not in cache_state['names']
    assert any('/static/css/public_workouts/workout-progress.css' in url for url in cache_state['staticUrls'])
    assert any('/static/js/public_workouts/load_tracker.js' in url for url in cache_state['staticUrls'])
    assert not any('/renan/bruno' in url and not url.endswith('.webmanifest') for url in cache_state['staticUrls'])
    assert not any(url.endswith('.json') and '/renan/' in url for url in cache_state['staticUrls'])

    page.context.set_offline(True)
    try:
        page.goto(f'{origin}/renan/offline/', wait_until='domcontentloaded')
        expect(page.get_by_text('Sem conexão agora.')).to_be_visible()
        expect(page.locator('[data-offline-open]')).to_be_hidden()
        assert page.locator('#workout-panel-cargas').count() == 0
    finally:
        page.context.set_offline(False)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_installed_app_hides_home_invite_and_shows_state_in_profile(page: Page, live_server):
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())
    page.add_init_script("Object.defineProperty(navigator, 'standalone', { value: true });")
    page.goto(f'{live_server.url.rstrip("/")}/renan/bruno')

    expect(page.locator('[data-workout-install]')).to_be_hidden()
    expect(page.locator('[data-workout-install-profile-button]')).to_be_hidden()
    expect(page.locator('[data-workout-install-status]')).to_have_text('App instalado neste dispositivo.')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_accepted_install_prompt_leaves_home_and_updates_profile(page: Page, live_server):
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())
    page.goto(f'{live_server.url.rstrip("/")}/renan/bruno')
    page.evaluate("""() => {
      const event = new Event('beforeinstallprompt');
      event.prompt = () => Promise.resolve();
      event.userChoice = Promise.resolve({ outcome: 'accepted' });
      window.dispatchEvent(event);
    }""")

    expect(page.locator('[data-workout-install]')).to_be_visible()
    page.locator('[data-workout-install-button]').click()
    expect(page.locator('[data-workout-install]')).to_be_hidden()
    expect(page.locator('[data-workout-install-status]')).to_have_text('Concluindo instalação…')
    page.evaluate("window.dispatchEvent(new Event('appinstalled'))")
    expect(page.locator('[data-workout-install-status]')).to_have_text('App instalado neste dispositivo.')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(
    DEBUG=True,
    STUDENT_WEB_PUSH_VAPID_PUBLIC_KEY='test-public',
    STUDENT_WEB_PUSH_VAPID_PRIVATE_KEY='test-private',
    STUDENT_WEB_PUSH_VAPID_CLAIMS_SUBJECT='mailto:test@example.com',
    PUBLIC_WORKOUT_PUSH_ALLOWED_HOSTS='fcm.googleapis.com',
)
def test_push_activation_moves_home_invite_to_profile_controls(page: Page, live_server):
    from datetime import timedelta
    from django.urls import reverse
    from django.utils import timezone
    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoginToken, PublicWorkoutSubscription
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    account = PublicWorkoutAccount.objects.create(email='push-profile@example.test')
    PublicWorkoutSubscription.objects.create(account=account, plan_slug='bruno')
    publish_program(slug='bruno', payload=build_example_payload())
    token = PublicWorkoutLoginToken.objects.create(
        account=account, expires_at=timezone.now() + timedelta(minutes=15),
    )
    page.add_init_script("""(() => {
      let subscription = null;
      const device = {
        endpoint: 'https://fcm.googleapis.com/fcm/send/e2e-device',
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
    })();""")
    page.route('**/renan/bruno/push', lambda route: route.fulfill(status=200, content_type='application/json', body='{}'))
    origin = live_server.url.rstrip('/')
    login = reverse('public-workout-login')
    page.goto(f'{origin}{login}?token={token.token}&next=/renan/bruno')

    expect(page.locator('[data-workout-push-home]')).to_be_visible()
    page.locator('[data-workout-push-enable]').click()
    expect(page.locator('[data-workout-push-home]')).to_be_hidden()
    page.locator('[data-workout-tab-target="workout-panel-perfil"]').click()
    expect(page.locator('[data-workout-push-profile-status]')).to_have_text('Avisos ativos neste dispositivo.')
    expect(page.locator('[data-workout-push-disable]')).to_be_visible()
    page.locator('[data-workout-push-disable]').click()
    expect(page.locator('[data-workout-push-profile-enable]')).to_be_visible()
    page.locator('[data-workout-tab-target="workout-panel-inicio"]').click()
    expect(page.locator('[data-workout-push-home]')).to_be_visible()
