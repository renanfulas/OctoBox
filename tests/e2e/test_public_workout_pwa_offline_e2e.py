"""End-to-end smoke for the public workout PWA cache lifecycle.

This covers a clean browser install, replacement of stale cache epochs, and
opening both the workout and offline fallback after network loss. It does not
replace the post-deploy check on a learner's already installed device.
"""

import time

import pytest
from django.test import override_settings
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def _cleanup_published_programs_after_e2e(django_db_blocker):
    yield
    with django_db_blocker.unblock():
        from public_workouts.models import PublicWorkoutProgram

        PublicWorkoutProgram.objects.filter(slug='bruno').delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_public_workout_pwa_installs_and_serves_workout_offline(page: Page, live_server):
    """The current worker precaches the shell and removes stale cache epochs."""
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    publish_program(slug='bruno', payload=build_example_payload())
    origin = live_server.url.rstrip('/')

    # Seed the browser origin with a prior installation's cache names before
    # registering the current worker. Activation must retain the current
    # STATIC/PAGE pair and delete both stale caches.
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
    assert "register('/renan/sw.js?slug=" in page.content()
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
    # A controlled online navigation puts this page in PAGE_CACHE before the
    # connection is cut.
    page.reload(wait_until='domcontentloaded')
    assert page.evaluate('Boolean(navigator.serviceWorker.controller)')

    cache_state = page.evaluate("""async () => {
      const names = await caches.keys();
      const staticName = names.find((name) => name.startsWith('public-workouts-') && name.endsWith('-static'));
      const pageName = names.find((name) => name.startsWith('public-workouts-') && name.endsWith('-pages'));
      const staticKeys = staticName ? await (await caches.open(staticName)).keys() : [];
      const pageKeys = pageName ? await (await caches.open(pageName)).keys() : [];
      return {
        names,
        staticName,
        pageName,
        staticUrls: staticKeys.map((request) => request.url),
        pageUrls: pageKeys.map((request) => new URL(request.url).pathname),
      };
    }""")

    assert cache_state['staticName'], f"current static cache missing: {cache_state['names']}"
    assert cache_state['pageName'], f"current page cache missing: {cache_state['names']}"
    assert cache_state['pageName'] == cache_state['staticName'].removesuffix('-static') + '-pages'
    assert 'public-workouts-previous-e5-static' not in cache_state['names']
    assert 'public-workouts-previous-e5-pages' not in cache_state['names']
    assert any('/static/css/public_workouts/workout-progress.css' in url for url in cache_state['staticUrls'])
    assert any('/static/js/public_workouts/load_tracker.js' in url for url in cache_state['staticUrls'])
    assert '/renan/bruno' in cache_state['pageUrls']
    assert not any(url.endswith('.json') and '/renan/' in url for url in cache_state['staticUrls'] + cache_state['pageUrls'])

    page.context.set_offline(True)
    try:
        page.goto(f'{origin}/renan/offline/', wait_until='domcontentloaded')
        expect(page.get_by_text('Sem conexão agora.')).to_be_visible()

        page.goto(f'{origin}/renan/bruno', wait_until='domcontentloaded')
        page.get_by_role('button', name='Cargas').click()
        expect(page.locator('#workout-panel-cargas')).to_be_visible()
        expect(page.locator('#workout-panel-cargas h2').first).to_have_text('Evolução de carga')
        assert page.locator('link[href*="workout-progress.css"]').first.evaluate('link => Boolean(link.sheet)')
    finally:
        page.context.set_offline(False)
