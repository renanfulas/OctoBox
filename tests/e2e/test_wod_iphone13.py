"""QA do WOD com perfil iPhone 13; executar com --browser webkit para Safari."""

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import re

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import expect

from operations.models import ClassSession, ClassType, WorkoutTemplate, WorkoutTemplateBlock, WorkoutTemplateMovement
from student_app.models import SessionWorkout, SessionWorkoutBlock, SessionWorkoutMovement, SessionWorkoutStatus, WodInputDraft


pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

NAVIGATION_TIMEOUT_MS = 15_000


@pytest.fixture
def iphone13_page(browser, playwright, request):
    profile = playwright.devices['iPhone 13'].copy()
    profile.pop('default_browser_type', None)
    context = browser.new_context(**profile, locale='pt-BR', timezone_id='America/Sao_Paulo')
    page = context.new_page()
    page.set_default_timeout(6000)
    page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
    try:
        yield page
    finally:
        screenshot(page, re.sub(r'[^a-zA-Z0-9_-]', '-', request.node.name) + '.png')
        context.close()


def login(page, live_server, credentials, theme):
    page.goto(f'{live_server.url}/login/funcionario/')
    page.locator('#id_username').fill(credentials['username'])
    page.locator('#id_password').fill(credentials['password'])
    # WebKit can need the full navigation budget for the login submit to finish.
    page.locator('button[type="submit"]').click(timeout=NAVIGATION_TIMEOUT_MS)
    page.wait_for_url('**/operacao/**', timeout=NAVIGATION_TIMEOUT_MS)
    page.evaluate('theme => localStorage.setItem("octobox-theme", theme)', theme)


def create_session(actor, day, title, class_type=ClassType.CROSS):
    return ClassSession.objects.create(
        title=title, coach=actor, class_type=class_type,
        scheduled_at=timezone.make_aware(datetime.combine(day, datetime.min.time()).replace(hour=12)),
        duration_minutes=60, capacity=16,
    )


def intent_form(page, intent):
    return page.locator(f'form:has(input[name="intent"][value="{intent}"])')


def submit(page, form, name):
    # tap() no WebKit pode retornar antes do POST terminar.
    with page.expect_navigation(wait_until='load'):
        form.get_by_role('button', name=name, exact=True).tap()


def screenshot(page, name):
    directory = Path('tmp/visual_contract/iphone13')
    directory.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=directory / name, animations='disabled')


def assert_no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth - innerWidth') <= 1


def assert_readable_button(button):
    colors = button.evaluate('''el => {
        const style = getComputedStyle(el);
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 1;
        const context = canvas.getContext('2d');
        function rgb(color) {
            context.clearRect(0, 0, 1, 1);
            context.fillStyle = color;
            context.fillRect(0, 0, 1, 1);
            return Array.from(context.getImageData(0, 0, 1, 1).data).slice(0, 3);
        }
        return [rgb(style.color), rgb(style.backgroundColor)];
    }''')
    def luminance(rgb):
        channels = [value / 255 for value in rgb]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    light, dark = sorted((luminance(color) for color in colors), reverse=True)
    assert (light + 0.05) / (dark + 0.05) >= 4.5, colors


@pytest.mark.parametrize('theme', ('light', 'dark'))
@pytest.mark.parametrize('supports_show_picker', (True, False))
def test_iphone13_native_calendar_receives_repeated_taps(
    iphone13_page, live_server, e2e_owner_credentials, theme, supports_show_picker,
):
    """Verifica toque real no input e sincronização; não automatiza o picker do iOS."""
    page = iphone13_page
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    login(page, live_server, e2e_owner_credentials, theme)
    page.goto(f'{live_server.url}/operacao/wod/paste/')
    field = page.locator('input[name="week_start"]')
    picker = page.locator('#smart-paste-week-start-picker')
    original = field.input_value()
    if not supports_show_picker:
        page.evaluate('HTMLInputElement.prototype.showPicker = undefined')
    picker.evaluate('el => { window.calendarTaps = []; el.addEventListener("click", event => calendarTaps.push(event.isTrusted)); }')
    for _ in range(3):
        picker.tap()
        expect(field).to_have_value(original)
        # WebKit no Windows não disponibiliza a folha nativa do iOS para automação.
        page.locator('input[name="label"]').tap()
    assert page.evaluate('calendarTaps') == [True, True, True]
    assert picker.evaluate('el => !el.hidden && el.tabIndex >= 0')
    picker.fill('2026-09-30')
    page.locator('input[name="label"]').tap()  # WebKit emite change ao encerrar a edição.
    expect(field).to_have_value('28/09/2026')
    expect(picker).to_have_value('2026-09-28')
    assert_no_overflow(page)
    assert not errors, errors
    page.locator('.smart-paste-date-field').scroll_into_view_if_needed()
    screenshot(page, f'calendar-{theme}-{supports_show_picker}.png')


@pytest.mark.parametrize('theme', ('light', 'dark'))
def test_iphone13_creates_and_edits_one_daily_workout(
    iphone13_page, live_server, e2e_owner_credentials, theme,
):
    page = iphone13_page
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    today = timezone.localdate()
    target = create_session(actor, today, 'WOD individual de segunda')
    neighbour = create_session(actor, today, 'HYROX no mesmo dia', ClassType.HYROX)
    tomorrow = create_session(actor, today + timedelta(days=1), 'WOD de amanhã')
    login(page, live_server, e2e_owner_credentials, theme)
    page.goto(f'{live_server.url}/operacao/wod/planner/?week={today.isoformat()}')
    cell = page.locator(f'[data-wod-planner-cell][data-planner-session-id="{target.id}"]')
    cell.locator('a[href$="/wod/"]').first.tap()
    expect(page.locator('.wod-step-intro')).to_contain_text('Aula sem WOD')
    form = intent_form(page, 'save_workout')
    form.locator('[name="title"]').fill('Força do dia — iPhone 13')
    form.locator('[name="coach_notes"]').fill('Preservar técnica e respeitar a carga individual.')
    submit(page, form, 'Salvar rascunho')
    form = intent_form(page, 'add_block')
    form.locator('[name="title"]').fill('Força principal')
    form.locator('[name="kind"]').select_option('strength')
    form.locator('[name="notes"]').fill('Descansar 90 segundos entre séries.')
    submit(page, form, 'Adicionar bloco')
    form = intent_form(page, 'add_movement')
    form.locator('[name="movement_label"]').fill('Deadlift')
    form.locator('[name="movement_label"]').press('Tab')
    expect(form.locator('[name="movement_slug"]')).to_have_value('deadlift')
    form.locator('[name="sets"]').fill('3')
    form.locator('[name="reps"]').fill('8')
    form.locator('[name="load_type"]').select_option('fixed_kg')
    form.locator('[name="load_value"]').fill('40.50')
    submit(page, form, 'Adicionar movimento')
    page.locator('[data-coach-wod-structure-open]').first.tap()
    form = intent_form(page, 'update_movement')
    expect(form.locator('[name="load_value"]')).to_have_value('40.50')
    form.locator('[name="reps"]').fill('10')
    submit(page, form, 'Salvar movimento')
    workout = SessionWorkout.objects.get(session=target)
    movement = SessionWorkoutMovement.objects.get(block__workout=workout)
    assert movement.reps == 10
    assert movement.sets == 3
    assert movement.load_value == Decimal('40.50')
    assert not SessionWorkout.objects.filter(session__in=(neighbour, tomorrow)).exists()
    assert_no_overflow(page)
    approval_form = intent_form(page, 'submit_for_approval')
    submit(page, approval_form, approval_form.get_by_role('button').first.inner_text())
    expect(page.locator('.wod-step-intro')).to_contain_text('Aguardando aprovação')
    workout.refresh_from_db()
    assert workout.status == SessionWorkoutStatus.PENDING_APPROVAL
    screenshot(page, f'daily-editor-{theme}.png')


def test_daily_draft_retries_after_committed_save_response_is_lost_and_recovers(
    iphone13_page, live_server, e2e_owner_credentials,
):
    """Draft diário sobrevive a ACK perdido, retry idempotente e reload no editor da aula."""
    page = iphone13_page
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    target = create_session(actor, timezone.localdate() + timedelta(days=1), 'Aula com draft recuperável')
    login(page, live_server, e2e_owner_credentials, 'light')
    page.goto(f'{live_server.url}/operacao/coach/aula/{target.id}/wod/')

    source = 'Aquecimento\n3 rounds\n10 agachamentos\n8 flexões — retry diário'
    field = page.locator('textarea[name="smartplan_paste"]')
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Edite o texto para iniciar', timeout=10_000)
    response = {}

    def commit_then_drop_save(route):
        if route.request.method != 'POST' or route.request.post_data_json.get('action') != 'save':
            route.continue_()
            return
        upstream = route.fetch()
        response['status'] = upstream.status
        response['request_id'] = route.request.post_data_json['request_id']
        route.abort(error_code='failed')

    page.route('**/operacao/wod/rascunho/', commit_then_drop_save)
    field.fill(source)
    field.blur()
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('O texto permanece neste campo', timeout=10_000)
    assert response.get('status') == 200, 'o servidor deve ter commitado o draft antes da resposta ser descartada'
    assert WodInputDraft.objects.filter(create_request_id=response['request_id']).count() == 1

    page.unroute('**/operacao/wod/rascunho/', commit_then_drop_save)
    field.focus()
    field.blur()  # retry deve conservar o create_request_id incerto
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor', timeout=10_000)
    assert WodInputDraft.objects.filter(create_request_id=response['request_id']).count() == 1
    assert WodInputDraft.objects.filter(source_text=source).count() == 1

    page.reload()
    expect(page.locator('textarea[name="smartplan_paste"]')).to_have_value(source, timeout=10_000)
    expect(page.locator('[data-wod-draft-status]')).to_contain_text('Rascunho recuperado do servidor', timeout=10_000)


def test_daily_draft_can_be_edited_after_recovering_a_conflict(
    iphone13_page, live_server, e2e_owner_credentials,
):
    page = iphone13_page
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    target = create_session(actor, timezone.localdate(), 'Recuperação de conflito entre abas')
    login(page, live_server, e2e_owner_credentials, 'light')
    editor_url = f'{live_server.url}/operacao/coach/aula/{target.id}/wod/'
    page.goto(editor_url)
    source = page.locator('textarea[name="smartplan_paste"]')
    status = page.locator('[data-wod-draft-status]')
    expect(status).to_contain_text('Edite o texto para iniciar')
    source.fill('Texto inicial')
    source.blur()
    expect(status).to_contain_text('Rascunho salvo no servidor')

    other = page.context.new_page()
    try:
        other.goto(editor_url)
        other_source = other.locator('textarea[name="smartplan_paste"]')
        expect(other_source).to_have_value('Texto inicial')
        other_source.fill('Texto atualizado na segunda aba')
        other_source.blur()
        expect(other.locator('[data-wod-draft-status]')).to_contain_text('Rascunho salvo no servidor')

        source.fill('Edição concorrente na primeira aba')
        source.blur()
        recover = page.locator('[data-wod-draft-recover]')
        expect(recover).to_be_visible()
        recover.click()
        expect(source).to_have_value('Texto atualizado na segunda aba')
        source.fill('Nova edição após recuperar')
        source.blur()
        expect(status).to_contain_text('Rascunho salvo no servidor', timeout=10_000)
        page.reload()
        expect(source).to_have_value('Nova edição após recuperar')
    finally:
        other.close()


@pytest.mark.parametrize('theme', ('light', 'dark'))
def test_iphone13_raw_daily_paste_preserves_text_and_requires_confirmation(
    iphone13_page, live_server, e2e_owner_credentials, theme,
):
    page = iphone13_page
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    target = create_session(actor, timezone.localdate(), 'WOD colado do dia')
    login(page, live_server, e2e_owner_credentials, theme)
    page.goto(f'{live_server.url}/operacao/coach/aula/{target.id}/wod/')
    raw = 'Aquecimento\n3 rounds\n10 agachamentos\n8 flexões\n\nWOD\n5 rounds\n200m corrida'
    page.locator('textarea[name="smartplan_paste"]').fill(raw)
    submit(page, intent_form(page, 'apply_smartplan_paste'), 'Publicar com SmartPlan')
    popup = page.locator('[data-panel="wod-smartplan-popup"]')
    expect(popup).to_be_visible()
    assert popup.evaluate('el => el.tagName === "DIALOG" && el.open && el.parentElement === document.body')
    panel = popup.locator('.wod-smartplan-popup__panel')
    assert panel.evaluate('el => getComputedStyle(el).backgroundColor') != 'rgba(0, 0, 0, 0)'
    assert_readable_button(popup.get_by_role('button', name='Publicar mesmo assim'))
    expect(page.locator('textarea[name="smartplan_paste"]')).to_have_value(raw)
    assert not SessionWorkout.objects.filter(session=target).exists()
    assert_no_overflow(page)
    screenshot(page, f'daily-paste-warning-{theme}.png')
    submit(page, popup, 'Publicar mesmo assim')
    expect(page.locator('.wod-step-intro')).to_contain_text('Aguardando aprovação')
    workout = SessionWorkout.objects.get(session=target)
    assert workout.coach_notes.splitlines() == raw.splitlines()
    assert not workout.is_normalized


@pytest.mark.parametrize('theme', ('light', 'dark'))
def test_iphone13_day_template_refreshes_calendar_and_undo_restores_draft(
    iphone13_page, live_server, e2e_owner_credentials, theme,
):
    page = iphone13_page
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    today = timezone.localdate()
    target_day = today + timedelta(days=1)
    # Day apply preserves classes that are already concluded. Use a future
    # fixture day so this browser scenario stays valid after noon as well.
    target = create_session(actor, target_day, 'Aula com rascunho')
    neighbour = create_session(actor, target_day, 'HYROX separado', ClassType.HYROX)
    workout = SessionWorkout.objects.create(session=target, title='Treino original', coach_notes='Notas originais', created_by=actor, version=3)
    original_block = SessionWorkoutBlock.objects.create(workout=workout, title='Bloco original', kind='metcon', sort_order=1)
    original_movement = SessionWorkoutMovement.objects.create(block=original_block, movement_slug='push_up', movement_label='Flexão', reps_spec='10-8-6', sort_order=1)
    template = WorkoutTemplate.objects.create(name='Template para o dia', created_by=actor)
    block = WorkoutTemplateBlock.objects.create(template=template, title='Força nova', kind='strength', sort_order=1)
    WorkoutTemplateMovement.objects.create(block=block, movement_slug='deadlift', movement_label='Deadlift', reps=8, sort_order=1)
    login(page, live_server, e2e_owner_credentials, theme)
    page.goto(f'{live_server.url}/operacao/wod/planner/?week={target_day.isoformat()}')
    page.locator(f'[data-wod-day-apply-trigger][data-date="{target_day.isoformat()}"]').tap()
    dialog = page.locator('[data-wod-day-apply-dialog]')
    apply = dialog.locator(f'[data-wod-day-apply-select][data-template-id="{template.id}"]')
    apply.tap()
    expect(dialog.locator('[data-wod-day-apply-error]')).to_contain_text('Escolha o programa antes de conferir os destinos')
    workout.refresh_from_db()
    assert workout.title == 'Treino original'
    dialog.locator('[data-wod-day-apply-program]').select_option(label='CrossFit')
    dialog.locator('label:has([value="overwrite"])').tap()
    apply.tap()
    review = dialog.locator('[data-wod-day-apply-review]')
    expect(review).to_be_visible()
    with page.expect_navigation(wait_until='load'):
        dialog.locator('[data-wod-day-apply-confirm]').tap()
    cell = page.locator(f'[data-wod-planner-cell][data-planner-session-id="{target.id}"]')
    expect(cell).to_contain_text('Template para o dia')
    toast = page.locator('[data-wod-day-apply-toast]')
    expect(toast).to_contain_text('1 aula(s)')
    toast_layout = toast.evaluate('''el => {
        const rect = node => {
            const box = node.getBoundingClientRect();
            return { left: box.left, right: box.right, width: box.width, height: box.height, top: box.top, bottom: box.bottom, centerY: (box.top + box.bottom) / 2 };
        };
        const color = getComputedStyle(el).backgroundColor;
        const parts = color.match(/rgba?\\((.*)\\)/)?.[1].split(/[,\\s/]+/).filter(Boolean) || [];
        const message = el.querySelector('[data-wod-day-apply-toast-msg]');
        const undo = el.querySelector('[data-wod-day-apply-undo-btn]');
        const close = el.querySelector('[data-wod-day-apply-toast-close]');
        const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number).map(channel => channel / 255).map(channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
        const luminance = value => rgb(value).reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
        const textColor = getComputedStyle(message).color;
        const light = Math.max(luminance(textColor), luminance(color));
        const dark = Math.min(luminance(textColor), luminance(color));
        return {
            display: getComputedStyle(el).display,
            backgroundAlpha: parts.length >= 4 ? Number(parts[3]) : 1,
            textContrast: (light + 0.05) / (dark + 0.05),
            toast: rect(el), message: rect(message), undo: rect(undo), close: rect(close),
            viewportWidth: document.documentElement.clientWidth,
        };
    }''')
    assert toast_layout['display'] == 'grid'
    assert toast_layout['backgroundAlpha'] == 1
    assert toast_layout['textContrast'] >= 4.5
    assert toast_layout['message']['bottom'] <= toast_layout['undo']['top']
    assert abs(toast_layout['undo']['centerY'] - toast_layout['close']['centerY']) <= 1
    assert toast_layout['undo']['height'] >= 44
    assert toast_layout['close']['height'] >= 44
    assert toast_layout['undo']['left'] >= toast_layout['toast']['left'], toast_layout
    assert toast_layout['close']['right'] <= toast_layout['toast']['right'], toast_layout
    assert toast_layout['toast']['width'] <= toast_layout['viewportWidth']
    assert not SessionWorkout.objects.filter(session=neighbour).exists()
    assert_no_overflow(page)
    screenshot(page, f'day-applied-{theme}.png')
    with page.expect_navigation(wait_until='load'):
        page.locator('[data-wod-day-apply-undo-btn]').tap()
    expect(cell).to_contain_text('Treino original')
    workout.refresh_from_db()
    original_movement.refresh_from_db()
    assert workout.coach_notes == 'Notas originais'
    assert workout.version > 3
    assert original_movement.reps_spec == '10-8-6'
    screenshot(page, f'day-undone-{theme}.png')
