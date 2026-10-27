"""Real browser + production JS, with a controlled draft API and no database."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

SCRIPT = Path(__file__).resolve().parents[2] / 'static/js/operations/wod_input_draft.js'
ORIGIN = 'https://wod-review.test'
HTML = '''<form data-wod-input-draft data-draft-url="/draft/" data-draft-kind="daily" data-session-id="1">
<input name="csrfmiddlewaretoken" value="synthetic-test-token">
<textarea data-wod-draft-source></textarea><p data-wod-draft-status></p>
<button type="button" data-wod-draft-recover hidden>Recuperar</button>
<button type="button" data-wod-draft-discard hidden>Descartar</button></form>'''


@pytest.fixture(scope='session')
def base_url():
    # Override the E2E live_server fixture: this regression isolates browser
    # ordering against a controlled API, without creating a database.
    return ORIGIN


@pytest.fixture
def draft_browser_factory(page):
    state = {
        'draft': {'draft_id': 'synthetic-draft', 'version': 1, 'source_text': 'Texto salvo'},
        'pending_discard': None, 'saves': [], 'discards': 0,
        'hold_get': False, 'pending_get': None, 'get_failure': None,
    }

    def api(route):
        if route.request.method == 'GET':
            if state['get_failure'] == 'network_error':
                route.abort()
                return
            if state['get_failure'] == 'http_error':
                route.fulfill(status=503, json={'ok': False, 'draft': state['draft']})
                return
            if state['get_failure'] == 'discarded':
                route.fulfill(json={'ok': True, 'draft': None})
                return
            if state['hold_get']:
                state['pending_get'] = route
                return
            route.fulfill(json={'ok': True, 'draft': state['draft']})
            return
        body = route.request.post_data_json
        if body['action'] == 'discard':
            state['discards'] += 1
            state['pending_discard'] = route
            return
        state['saves'].append(body)
        draft = state['draft']
        if draft and (body['draft_id'] != draft['draft_id'] or body['expected_version'] != draft['version']):
            route.fulfill(status=409, json={'ok': False, 'code': 'stale_version'})
            return
        state['draft'] = {
            'draft_id': draft['draft_id'] if draft else 'synthetic-new-draft',
            'version': draft['version'] + 1 if draft else 1,
            'source_text': body['source_text'],
        }
        route.fulfill(json={'ok': True, 'draft': state['draft']})

    page.route(ORIGIN + '/', lambda route: route.fulfill(content_type='text/html', body=HTML))
    page.route(ORIGIN + '/draft/**', api)
    page.on('dialog', lambda dialog: dialog.accept())
    def start(initial_text='', hold_get=False):
        state['hold_get'] = hold_get
        page.goto(ORIGIN + '/')
        page.locator('[data-wod-draft-source]').fill(initial_text)
        with page.expect_request(lambda request: '/draft/' in request.url):
            page.add_script_tag(path=str(SCRIPT))
        if not hold_get:
            if initial_text:
                expect(page.locator('[data-wod-draft-recover]')).to_be_visible()
            else:
                expect(page.locator('[data-wod-draft-source]')).to_have_value('Texto salvo')
        return page, state

    return start


@pytest.fixture
def draft_browser(draft_browser_factory):
    return draft_browser_factory()


def test_typing_while_discard_response_is_pending_preserves_and_saves_new_text(draft_browser):
    page, state = draft_browser
    field = page.locator('[data-wod-draft-source]')
    with page.expect_request(lambda request: request.method == 'POST'):
        page.locator('[data-wod-draft-discard]').click()
    field.fill('Texto novo escrito enquanto descarta')
    field.blur()
    assert not state['saves'], 'a gravação deve aguardar a confirmação do descarte'
    state['draft'] = None
    state['pending_discard'].fulfill(json={'ok': True, 'draft': None})
    expect(field).to_have_value('Texto novo escrito enquanto descarta')
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor')
    assert state['draft']['source_text'] == 'Texto novo escrito enquanto descarta'


def test_discard_without_new_edits_clears_saved_draft(draft_browser):
    page, state = draft_browser
    with page.expect_request(lambda request: request.method == 'POST'):
        page.locator('[data-wod-draft-discard]').click()
    state['draft'] = None
    state['pending_discard'].fulfill(json={'ok': True, 'draft': None})
    expect(page.locator('[data-wod-draft-source]')).to_have_value('')
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho descartado')
    assert not state['saves']


def test_failed_discard_preserves_text_and_allows_later_save(draft_browser):
    page, state = draft_browser
    field = page.locator('[data-wod-draft-source]')
    with page.expect_request(lambda request: request.method == 'POST'):
        page.locator('[data-wod-draft-discard]').click()
    field.fill('Nova edição preservada após falha')
    field.blur()
    state['pending_discard'].fulfill(status=503, json={'ok': False})
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Recarregue a página')
    expect(field).to_have_value('Nova edição preservada após falha')
    assert state['draft']['source_text'] == 'Texto salvo'
    field.focus()
    field.blur()
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor')
    assert state['draft']['source_text'] == 'Nova edição preservada após falha'


def test_repeated_discard_click_is_serialized(draft_browser):
    page, state = draft_browser
    button = page.locator('[data-wod-draft-discard]')
    with page.expect_request(lambda request: request.method == 'POST'):
        button.click()
    button.click()
    state['draft'] = None
    state['pending_discard'].fulfill(json={'ok': True, 'draft': None})
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho descartado')
    assert state['discards'] == 1


def test_successful_save_retires_previous_recovery_candidate(draft_browser_factory):
    page, state = draft_browser_factory(initial_text='Texto vindo do formulário')
    field = page.locator('[data-wod-draft-source]')
    field.fill('Edição nova aceita pelo servidor')
    field.blur()
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor')
    assert state['draft']['source_text'] == 'Edição nova aceita pelo servidor'
    expect(page.locator('[data-wod-draft-recover]')).to_be_hidden()


def test_late_initial_load_does_not_restore_text_cleared_by_user(draft_browser_factory):
    page, state = draft_browser_factory(hold_get=True)
    field = page.locator('[data-wod-draft-source]')
    field.fill('Texto digitado antes da resposta')
    field.fill('')
    field.blur()
    assert not state['saves']
    state['pending_get'].fulfill(json={'ok': True, 'draft': state['draft']})
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor')
    expect(field).to_have_value('')
    assert state['draft']['source_text'] == ''


def test_recovering_current_conflict_still_allows_next_save(draft_browser):
    page, state = draft_browser
    state['draft'] = {**state['draft'], 'version': 2, 'source_text': 'Versão da outra aba'}
    field = page.locator('[data-wod-draft-source]')
    field.fill('Edição local que conflita')
    field.blur()
    recover = page.locator('[data-wod-draft-recover]')
    expect(recover).to_be_visible()
    recover.click()
    expect(field).to_have_value('Versão da outra aba')
    field.fill('Edição após recuperar conflito')
    field.blur()
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor')
    expect(recover).to_be_hidden()
    assert state['draft']['version'] == 3
    assert state['draft']['source_text'] == 'Edição após recuperar conflito'


def test_conflict_hides_old_recovery_until_current_revision_arrives(draft_browser_factory):
    page, state = draft_browser_factory(initial_text='Texto local inicial')
    state['draft'] = {**state['draft'], 'version': 2, 'source_text': 'Revisão atual da outra aba'}
    state['hold_get'] = True
    field = page.locator('[data-wod-draft-source]')
    with page.expect_request(lambda request: request.method == 'GET' and '/draft/' in request.url):
        field.fill('Edição que provoca conflito')
        field.blur()
    expect(page.locator('[data-wod-draft-recover]')).to_be_hidden()
    expect(field).to_have_value('Edição que provoca conflito')
    state['pending_get'].fulfill(json={'ok': True, 'draft': state['draft']})
    recover = page.locator('[data-wod-draft-recover]')
    expect(recover).to_be_visible()
    recover.click()
    expect(field).to_have_value('Revisão atual da outra aba')


@pytest.mark.parametrize('response', ('network_error', 'http_error', 'discarded'))
def test_failed_conflict_refresh_preserves_text_without_stale_recovery(draft_browser, response):
    page, state = draft_browser
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    state['draft'] = {**state['draft'], 'version': 2, 'source_text': 'Outra aba'}
    state['get_failure'] = response
    field = page.locator('[data-wod-draft-source]')
    with page.expect_request(lambda request: request.method == 'GET' and '/draft/' in request.url):
        field.fill('Texto local que precisa ser preservado')
        field.blur()
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Copie seu texto e recarregue')
    expect(field).to_have_value('Texto local que precisa ser preservado')
    expect(page.locator('[data-wod-draft-recover]')).to_be_hidden()
    assert not errors
    assert len(state['saves']) == 1
