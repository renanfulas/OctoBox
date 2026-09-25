"""
ARQUIVO: contrato visual + fluxo E2E do Smart Paste semanal (operations).

POR QUE EXISTE:
- Sessão de QA manual em viewport mobile (390x844) achou um bug que nenhum
  teste unitário pegava: o campo "Início da semana" grava/exibe sempre
  dd/mm/aaaa desde o fix do calendário (PR #172/#246), mas o CSS que
  dimensiona esse input ficou parado no formato antigo "dd/mm" (width: 9ch)
  e cortava visualmente o último dígito do ano — "14/09/202" em vez de
  "14/09/2026", sem nenhum indício visual (text-overflow: clip). O valor
  gravado no backend sempre esteve correto, então nenhum teste de
  tests/test_workout_smart_paste.py (que só olha response.context / HTML
  bruto) conseguiria pegar isso — é 100% um bug de layout renderizado.
- Complementa esse teste dedicado com um contrato visual mais amplo
  (overflow horizontal, dialog de dia abre/fecha, bloco focável) e um
  golden path E2E do fluxo principal (colar -> organizar -> confirmar ->
  replicar), no mesmo padrão de tests/e2e/test_students_visual_contract.py.

O QUE ESTE ARQUIVO FAZ:
1. test_week_start_field_never_clips_the_year: regressão dedicada do bug
   acima. Mede scrollWidth vs clientWidth do input real (não confia no
   `value` do campo), parametrizado por viewport (mobile/desktop) e tema.
2. test_smart_paste_visual_baseline_contract: sem overflow horizontal em
   nenhum estado da tela, diálogo de dia abre via showModal(), foco de
   bloco expande a lista de movimentos.
3. test_smart_paste_golden_path_end_to_end: fluxo completo sem pendências
   de revisão (texto sem erros de digitação, resolvido só pelo dicionário
   estático — sem depender de chave de API real em CI): colar -> organizar
   -> confirmar rascunho -> painel de replicação aparece.
4. test_smart_paste_rejects_source_text_over_line_limit: hardening
   anti-spam (SMART_PASTE_MAX_LINES) tem que bloquear ANTES de qualquer
   chamada ao Haiku — cobre o guard mais barato de errar silenciosamente.

Ver docs/testing/e2e-guide.md para convenções gerais de teste E2E.
"""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Browser, Page, expect

from operations.models import ClassSession, ClassType, WorkoutTemplate
from student_app.models import SessionWorkout, SessionWorkoutStatus
from student_identity.infrastructure.session import build_student_session_value
from student_identity.models import StudentBoxMembership, StudentBoxMembershipStatus, StudentIdentity, StudentIdentityProvider, StudentIdentityStatus
from students.models import Student
from shared_support.box_runtime import get_box_runtime_slug


VIEWPORTS = {
    "mobile": {"width": 390, "height": 844},
    "iphone15": {"width": 393, "height": 852},
    "desktop": {"width": 1440, "height": 1100},
}

THEMES = ("light", "dark")

# Mesmo texto de tests/test_workout_smart_paste.py (SMART_PASTE_SAMPLE):
# todos os movimentos resolvem pelo dicionário estático, sem pendência de
# revisão e sem precisar de chave de API do Anthropic em CI.
CLEAN_SAMPLE_WOD = """Segunda
Mobilidade

Aquecimento
3x
10 lunges
8 front squat
20 sit up"""


def _login(page: Page, base_url: str, credentials: dict) -> None:
    page.goto(f"{base_url}/login/funcionario/")
    page.locator("#id_username").fill(credentials["username"])
    page.locator("#id_password").fill(credentials["password"])
    page.locator('button[type="submit"]').click()
    page.wait_for_url("**/operacao/**", timeout=15_000)


def _set_theme(page: Page, theme: str) -> None:
    page.evaluate(
        """theme => {
            window.localStorage.setItem("octobox-theme", theme);
            document.body.dataset.theme = theme;
        }""",
        theme,
    )


def _horizontal_overflow(page: Page) -> int:
    return page.evaluate(
        "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"
    )


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS.items())
@pytest.mark.parametrize("theme", THEMES)
def test_week_start_field_never_clips_the_year(
    browser: Browser,
    live_server,
    e2e_owner_credentials,
    viewport_name: str,
    viewport: dict[str, int],
    theme: str,
):
    """
    Regressão: o input "Início da semana" precisa caber dd/mm/aaaa inteiro.

    O form já chega da view com o valor inicial formatado (próxima segunda,
    10 caracteres) — não precisa colar nada para reproduzir o bug original.
    """
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    try:
        _login(page, live_server.url, e2e_owner_credentials)
        _set_theme(page, theme)

        page.goto(f"{live_server.url}/operacao/wod/paste/")
        page.wait_for_load_state("networkidle")

        field = page.locator("input[data-smart-date-input]").first
        expect(field).to_be_visible()

        value = field.input_value()
        assert len(value) == 10, f"esperava dd/mm/aaaa (10 chars), recebeu {value!r}"

        overflow = page.evaluate(
            "(el) => Math.max(0, el.scrollWidth - el.clientWidth)",
            field.element_handle(),
        )
        assert overflow <= 1, (
            f"campo 'Início da semana' corta o valor {value!r} visualmente "
            f"({overflow}px de overflow) em viewport={viewport_name} tema={theme} — "
            "o CSS de .smart-paste-date-input-wrap input[data-smart-date-input] "
            "ficou pequeno demais para dd/mm/aaaa"
        )
    finally:
        context.close()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_calendar_selection_keeps_year_and_snaps_to_monday(page: Page, live_server, e2e_owner_credentials):
    """QA do calendário: a seleção nativa preserva o ano e sempre grava a segunda da semana."""
    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS["mobile"])
    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")

    # 30/09/2026 é quarta-feira. O evento é o mesmo emitido pelo picker
    # nativo após o coach escolher o dia; não dependemos da UI do SO.
    page.locator("#smart-paste-week-start-picker").evaluate(
        """picker => {
            picker.value = '2026-09-30';
            picker.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )

    field = page.locator("input[data-smart-date-input]").first
    expect(field).to_have_value("28/09/2026")
    expect(page.locator("#smart-paste-week-start-picker")).to_have_value("2026-09-28")


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_planner_day_apply_modes_can_be_selected_with_keyboard(page: Page, live_server, e2e_owner_credentials):
    """Os modos de aplicação são rádios nativos acessíveis por Tab e setas."""
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    WorkoutTemplate.objects.create(name='Template de teclado E2E', created_by=actor, is_active=True)

    _login(page, live_server.url, e2e_owner_credentials)
    page.goto(f'{live_server.url}/operacao/wod/planner/')
    page.locator('[data-wod-day-apply-trigger]').first.click()
    dialog = page.locator('[data-wod-day-apply-dialog]')
    expect(dialog).to_be_visible()
    assert dialog.get_attribute('data-apply-url') == '/operacao/wod/planner/dia/aplicar/'

    replace_empty = dialog.locator('input[name="wod_day_apply_mode"][value="replace_empty"]')
    overwrite = dialog.locator('input[name="wod_day_apply_mode"][value="overwrite"]')
    page.keyboard.press('Tab')
    expect(replace_empty).to_be_focused()
    page.keyboard.press('ArrowDown')
    expect(overwrite).to_be_checked()
    expect(overwrite).to_be_focused()
    assert overwrite.locator('xpath=..').evaluate('el => getComputedStyle(el).outlineStyle') != 'none'
    assert dialog.locator('.wod-day-apply__search').evaluate(
        'el => getComputedStyle(el).backgroundColor'
    ) != 'rgba(0, 0, 0, 0)'


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('theme', THEMES)
def test_wod_template_archive_dialog_has_readable_colors(page: Page, live_server, e2e_owner_credentials, theme):
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    WorkoutTemplate.objects.create(name='Template para arquivo E2E', created_by=actor, is_active=True)

    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS['mobile'])
    _set_theme(page, theme)
    page.goto(f'{live_server.url}/operacao/wod/templates/')
    page.locator('[data-wod-archive-all-open]').click()
    dialog = page.locator('[data-wod-archive-all-dialog]')
    expect(dialog).to_be_visible()
    bounds = dialog.bounding_box()
    assert bounds and 0 <= bounds['y'] < VIEWPORTS['mobile']['height']
    assert bounds['y'] + bounds['height'] <= VIEWPORTS['mobile']['height'] + 1
    dialog.locator('[data-wod-archive-confirm-input]').fill('ARQUIVAR')
    button = dialog.locator('[data-wod-archive-submit]')
    expect(button).to_be_enabled()
    assert button.evaluate('el => getComputedStyle(el).backgroundImage') == 'none'
    color = button.evaluate('''el => {
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 1;
        const context = canvas.getContext('2d');
        context.fillStyle = getComputedStyle(el).color;
        context.fillRect(0, 0, 1, 1);
        return Array.from(context.getImageData(0, 0, 1, 1).data).slice(0, 3);
    }''')
    assert max(color) < 100, color
    assert _horizontal_overflow(page) <= 1
    screenshot_dir = Path('tmp') / 'visual_contract' / 'smart_paste'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=screenshot_dir / f'wod-template-archive-mobile-{theme}.png')


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('theme', THEMES)
def test_wod_planner_danger_action_is_visible_and_uses_semantic_surface(page: Page, live_server, e2e_owner_credentials, theme):
    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS['mobile'])
    _set_theme(page, theme)
    page.goto(f'{live_server.url}/operacao/wod/planner/')
    button = page.locator('.wod-planner__btn-danger')
    expect(button).to_be_visible()
    assert button.evaluate('el => getComputedStyle(el).backgroundImage') == 'none'
    assert _horizontal_overflow(page) <= 1


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width', (320, 375, 430))
@pytest.mark.parametrize('theme', THEMES)
def test_wod_mobile_width_contract(browser: Browser, live_server, e2e_owner_credentials, width, theme):
    """Use a touch viewport to catch controls clipped on compact phones."""
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    WorkoutTemplate.objects.create(name=f'Template mobile {width} {theme}', created_by=actor, is_active=True)
    context = browser.new_context(
        viewport={'width': width, 'height': 740},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
    )
    page = context.new_page()
    try:
        _login(page, live_server.url, e2e_owner_credentials)
        _set_theme(page, theme)
        for path, selector in (
            ('paste/', '.smart-paste-form-card'),
            ('planner/', '.wod-planner-shell'),
            ('aprovacoes/', '.coach-wod-editor-shell'),
            ('templates/', '.coach-wod-editor-shell'),
        ):
            page.goto(f'{live_server.url}/operacao/wod/{path}')
            expect(page.locator(selector).first).to_be_visible()
            assert _horizontal_overflow(page) <= 1, f'{path}: overflow em {width}px no tema {theme}'

        page.locator('[data-wod-archive-all-open]').click()
        dialog = page.locator('[data-wod-archive-all-dialog]')
        expect(dialog).to_be_visible()
        bounds = dialog.bounding_box()
        assert bounds['x'] >= -1 and bounds['x'] + bounds['width'] <= width + 1, bounds
        assert _horizontal_overflow(page) <= 1
        confirm_input = dialog.locator('[data-wod-archive-confirm-input]')
        if theme == 'dark':
            placeholder_color = confirm_input.evaluate('''el => {
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 1;
                const context = canvas.getContext('2d');
                context.fillStyle = getComputedStyle(el, '::placeholder').color;
                context.fillRect(0, 0, 1, 1);
                return Array.from(context.getImageData(0, 0, 1, 1).data).slice(0, 3);
            }''')
            assert min(placeholder_color) >= 140, placeholder_color
        confirm_input.fill('ARQUIVAR')
        expect(dialog.locator('[data-wod-archive-submit]')).to_be_enabled()
        if (width, theme) in ((320, 'dark'), (430, 'light')):
            screenshot_dir = Path('tmp') / 'visual_contract' / 'smart_paste'
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=screenshot_dir / f'wod-template-archive-touch-{width}-{theme}.png')
    finally:
        context.close()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS.items())
@pytest.mark.parametrize("theme", THEMES)
def test_smart_paste_visual_baseline_contract(
    browser: Browser,
    live_server,
    e2e_owner_credentials,
    viewport_name: str,
    viewport: dict[str, int],
    theme: str,
):
    """
    Contrato visual amplo: sem overflow horizontal, diálogo de dia abre e
    fecha de verdade (showModal/close), bloco focável expande a lista de
    movimentos. Roda com um plano já confirmado (pula direto pro estado
    "com pendência" via um movimento cujo slug não existe no dicionário
    estático, o mesmo cenário que motivou o dialog no design "Onda 2").
    """
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    try:
        _login(page, live_server.url, e2e_owner_credentials)
        _set_theme(page, theme)

        page.goto(f"{live_server.url}/operacao/wod/paste/")
        page.wait_for_load_state("networkidle")
        assert page.locator('.smart-paste-layout').evaluate('el => getComputedStyle(el).display') == 'grid'
        assert page.locator('.smart-paste-card').first.evaluate('el => getComputedStyle(el).display') == 'flex'
        assert _horizontal_overflow(page) <= 1, "overflow horizontal na tela vazia do Smart Paste"

        page.locator("textarea[name=source_text]").fill(
            "Segunda:\nAquecimento\n3 rounds\n10 agachamnto\n8 push up\n5 pull up\n"
        )
        page.locator("form.smart-paste-form button[type=submit]").click()
        page.wait_for_load_state("networkidle")
        assert _horizontal_overflow(page) <= 1, "overflow horizontal apos organizar o texto"

        day_chip = page.locator("[data-action='open-day-dialog']").first
        expect(day_chip).to_be_visible()
        day_chip.click()

        dialog = page.locator("dialog.smart-paste-day-dialog[open]")
        expect(dialog).to_be_visible(timeout=5_000)
        assert dialog.evaluate('el => el.parentElement === document.body'), "dialog deve sair do card com blur no Safari"
        dialog_bounds = dialog.bounding_box()
        header_bounds = dialog.locator('.smart-paste-day-dialog__head').bounding_box()
        assert dialog_bounds and header_bounds
        assert 0 <= dialog_bounds['x'] < viewport['width']
        assert 0 <= dialog_bounds['y'] < viewport['height']
        assert dialog_bounds['x'] + dialog_bounds['width'] <= viewport['width'] + 1
        assert dialog_bounds['y'] + dialog_bounds['height'] <= viewport['height'] + 1
        assert header_bounds['y'] >= 0 and header_bounds['y'] < viewport['height']
        assert dialog.locator('.smart-paste-day-dialog__head h3').is_visible()
        assert _horizontal_overflow(page) <= 1, "overflow horizontal com o dialog de dia aberto"

        block_surface = dialog.locator("[data-action='focus-block']").first
        expect(block_surface).to_be_visible()
        block_surface.scroll_into_view_if_needed()
        block_surface.click()

        detail = dialog.locator(".smart-paste-block-detail").first
        expect(detail).to_be_visible(timeout=5_000)
        expect(detail.locator(".smart-paste-movement-list li").first).to_be_visible()

        # Evidência visual do estado que historicamente virava uma superfície
        # branca no celular: dialog aberto + card de pendência expandido.
        screenshot_dir = Path("tmp") / "visual_contract" / "smart_paste"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=screenshot_dir / f"smart-paste-dialog-{viewport_name}-{theme}.png")

        back_button = dialog.locator("[data-action='unfocus-block']").first
        back_button.click()
        expect(detail).to_be_hidden(timeout=5_000)

        close_button = dialog.locator("[data-action='close-dialog']").first
        close_button.click()
        expect(dialog).to_have_count(0, timeout=5_000)
        expect(page.locator('#smart-paste-preview-panel dialog.smart-paste-day-dialog').first).to_be_attached()

        page.screenshot(path=screenshot_dir / f"smart-paste-{viewport_name}-{theme}.png")
        if theme == "dark":
            heading_color = page.locator(".smart-paste-warning-card--focus h3").evaluate(
                "el => getComputedStyle(el).color"
            )
            channels = [int(value) for value in heading_color.removeprefix("rgb(").rstrip(")").split(", ")]
            assert min(channels) >= 170, f"heading da pendência sem contraste no tema escuro: {heading_color}"
    finally:
        context.close()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_iphone_dialog_review_survives_htmx_swap(browser: Browser, live_server, e2e_owner_credentials):
    """A revisão feita no modal portado volta ao preview antes do swap HTMX."""
    context = browser.new_context(
        viewport=VIEWPORTS['iphone15'],
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True,
    )
    page = context.new_page()
    try:
        _login(page, live_server.url, e2e_owner_credentials)
        page.goto(f'{live_server.url}/operacao/wod/paste/')
        page.locator('textarea[name="source_text"]').fill(
            'Segunda:\nAquecimento\n3 rounds\n10 movimento inventado xyz\n8 push up\n'
        )
        page.locator('form.smart-paste-form button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        page.locator('[data-action="open-day-dialog"]').first.click()
        dialog = page.locator('dialog.smart-paste-day-dialog[open]')
        dialog.locator('[data-action="focus-block"]').first.click()
        dialog.locator('details[data-smart-paste-review-target]').first.locator(':scope > summary').click()
        form = dialog.locator('form.smart-paste-inline-review-form').first
        form.locator('[data-action="use-custom-movement"]').click()
        expect(form.locator('[name="movement_slug"]')).to_have_value('custom')
        form.locator('button[type="submit"]').click()
        expect(page.locator('#smart-paste-preview-panel')).to_be_visible()
        expect(page.locator('body > dialog.smart-paste-day-dialog')).to_have_count(0)
        expect(page.locator('#smart-paste-preview-panel .smart-paste-day-chip__status').first).to_contain_text('Leitura pronta')
    finally:
        context.close()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_golden_path_end_to_end(page: Page, live_server, e2e_owner_credentials):
    """
    Fluxo principal ponta a ponta: colar um treino limpo (sem pendência de
    revisão) -> organizar -> confirmar rascunho semanal -> painel de
    replicação aparece. Usa CLEAN_SAMPLE_WOD (mesmo texto de
    tests/test_workout_smart_paste.py) para não depender de chave de API
    real em CI — todo movimento resolve pelo dicionário estático.
    """
    _login(page, live_server.url, e2e_owner_credentials)

    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")

    page.locator("textarea[name=source_text]").fill(CLEAN_SAMPLE_WOD)
    page.locator("form.smart-paste-form button[type=submit]").click()
    page.wait_for_load_state("networkidle")

    expect(page.locator(".smart-paste-confidence-strip")).to_contain_text("Leitura pronta")

    # Keep this test on the explicit confirm-only path; the adjacent primary
    # action now retries Haiku and immediately projects to the Planner.
    confirm_button = page.locator(
        'form.smart-paste-confirm-form button[name="action"][value="confirm_plan"]'
    )
    expect(confirm_button).to_be_enabled()
    confirm_button.click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("#smart-paste-projection-panel")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("Montar preview de replicacao", exact=False)).to_be_visible()

    assert _horizontal_overflow(page) <= 1, "overflow horizontal apos confirmar e abrir a replicacao"


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_auto_send_reaches_planner_and_keeps_approval_gate(
    page: Page,
    live_server,
    e2e_owner_credentials,
):
    """A ação automática coloca o WOD na aula certa e conserva a aprovação."""
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    today = timezone.localdate()
    target_monday = today + timedelta(days=(7 - today.weekday()) % 7)
    session = ClassSession.objects.create(
        title='Smart Paste E2E CrossFit',
        class_type=ClassType.CROSS,
        coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_monday, datetime.min.time()).replace(hour=12)),
        duration_minutes=60,
        capacity=16,
    )

    _login(page, live_server.url, e2e_owner_credentials)
    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")
    page.locator('input[name="week_start"]').fill(target_monday.strftime('%d/%m/%Y'))
    page.locator('input[name="label"]').fill('E2E Smart Paste Automático')
    page.locator('textarea[name="source_text"]').fill(CLEAN_SAMPLE_WOD)
    page.locator('form.smart-paste-form button[type="submit"]').click()
    page.wait_for_load_state("networkidle")

    page.locator(
        'form.smart-paste-confirm-form button[name="action"][value="confirm_and_project"]'
    ).click()
    page.wait_for_url(f"**/operacao/wod/planner/?week={target_monday.isoformat()}", timeout=15_000)

    projected_cell = page.locator(
        '[data-wod-planner-cell][data-wod-state="pending"]'
    ).filter(has_text='E2E Smart Paste Automático')
    expect(projected_cell).to_be_visible()
    expect(projected_cell).to_have_attribute('data-planner-status-label', 'Aguardando aprovação')
    screenshot_dir = Path('tmp') / 'visual_contract' / 'smart_paste'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=screenshot_dir / 'planner-pending-desktop.png', full_page=True)
    page.set_viewport_size(VIEWPORTS['mobile'])
    _set_theme(page, 'dark')
    assert _horizontal_overflow(page) <= 1
    assert page.locator('.wod-planner__grid').evaluate(
        'el => getComputedStyle(el).gridTemplateColumns.split(" ").length'
    ) == 1
    expect(projected_cell.locator('.wod-planner__cell-state')).to_be_visible()
    page.screenshot(path=screenshot_dir / 'planner-pending-mobile-dark.png', full_page=True)

    workout = SessionWorkout.objects.get(session=session)
    page.set_viewport_size(VIEWPORTS['desktop'])
    _set_theme(page, 'light')
    page.goto(f'{live_server.url}/operacao/wod/aprovacoes/')
    page.wait_for_load_state('networkidle')
    approve_form = page.locator(f'form.coach-wod-approve-form[action*="/{workout.id}/approve/"]')
    expect(approve_form).to_be_visible()
    body_font = page.locator('body').evaluate('el => getComputedStyle(el).fontFamily')
    assert page.locator('.wod-inbox__item').first.evaluate('el => getComputedStyle(el).fontFamily') == body_font
    assert approve_form.get_by_role('button', name='Aprovar e publicar').evaluate(
        'el => getComputedStyle(el).fontFamily'
    ) == body_font
    page.screenshot(path=screenshot_dir / 'approval-desktop.png', full_page=True)
    page.set_viewport_size(VIEWPORTS['mobile'])
    _set_theme(page, 'dark')
    assert _horizontal_overflow(page) <= 1
    for selector in (
        '.wod-inbox__preview-card .coach-wod-editor-head h2',
        '.wod-inbox__preview-card .coach-wod-review-digest > p:not(.eyebrow)',
        '.wod-inbox__preview-card .coach-wod-timeline-body p',
    ):
        minimum_channel = page.locator(selector).first.evaluate(
            r'el => Math.min(...getComputedStyle(el).color.match(/\d+/g).slice(0, 3).map(Number))'
        )
        assert minimum_channel >= 140, f'texto ilegível no preview escuro: {selector}'
    form_field_background = approve_form.locator('input[name="approval_reason_note"]').evaluate(
        'el => getComputedStyle(el).backgroundColor'
    )
    assert page.locator('.wod-inbox__preview-card select[name="rejection_category"]').bounding_box()['height'] <= 64
    assert page.locator('.wod-inbox__preview-card input[name="rejection_reason"]').bounding_box()['height'] <= 64
    page.screenshot(path=screenshot_dir / 'approval-mobile-dark.png', full_page=True)
    assert not form_field_background.startswith('rgb(255'), (
        f'campo de aprovação branco no tema escuro: {form_field_background}'
    )
    confirmation = approve_form.locator('input[name="confirm_sensitive_changes"]')
    if confirmation.count():
        confirmation.check()
    with page.expect_response(
        lambda response: '/approve/' in response.url and response.request.method == 'POST',
        timeout=15_000,
    ) as approval_response:
        approve_form.get_by_role('button', name='Aprovar e publicar').click()
    assert approval_response.value.status in (200, 302), (
        f'aprovação retornou HTTP {approval_response.value.status}'
    )
    page.wait_for_load_state('networkidle')
    workout.refresh_from_db()
    assert workout.status == SessionWorkoutStatus.PUBLISHED

    student_token = uuid4().hex[:10]
    student = Student.objects.create(full_name='Aluno E2E WOD', phone=f'55119{int(student_token, 16) % 100000000:08d}', email=f'aluno-e2e-{student_token}@example.test')
    box_slug = get_box_runtime_slug()
    identity = StudentIdentity.objects.create(
        student_id=student.id,
        student_name=student.full_name,
        box_root_slug=box_slug,
        primary_box_root_slug=box_slug,
        provider=StudentIdentityProvider.GOOGLE,
        provider_subject=f'e2e-wod-published-{student_token}',
        email=student.email,
        status=StudentIdentityStatus.ACTIVE,
    )
    StudentBoxMembership.objects.create(
        identity=identity,
        student_id=student.id,
        box_root_slug=box_slug,
        status=StudentBoxMembershipStatus.ACTIVE,
    )
    page.context.add_cookies([{
        'name': 'octobox_student_session',
        'value': build_student_session_value(identity_id=identity.id, box_root_slug=box_slug),
        'url': live_server.url,
    }])
    page.goto(f'{live_server.url}/aluno/wod/?session_id={session.id}')
    expect(page.get_by_text('E2E Smart Paste Automático', exact=False).first).to_be_visible()

    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    next_month_session = ClassSession.objects.create(
        title='Cross próximo mês E2E',
        class_type=ClassType.CROSS,
        scheduled_at=timezone.make_aware(datetime.combine(next_month + timedelta(days=7), datetime.min.time()).replace(hour=10)),
        duration_minutes=60,
        capacity=16,
    )
    SessionWorkout.objects.create(
        session=next_month_session,
        title='WOD próximo mês E2E',
        status=SessionWorkoutStatus.PUBLISHED,
    )
    page.goto(f'{live_server.url}/aluno/grade/')
    page.set_viewport_size(VIEWPORTS['mobile'])
    page.locator('[data-month-toggle]').click()
    expect(page.locator('[data-month-toggle]')).to_have_attribute('aria-expanded', 'true')
    page.get_by_role('link', name='Próximo mês').click()
    page.wait_for_url(f'**/aluno/grade/?month={next_month:%Y-%m}', timeout=15_000)
    assert _horizontal_overflow(page) <= 1
    future_wod_day = page.locator('.student-month-day.has-wod[data-wod-href*="session_id=%s"]' % next_month_session.id)
    expect(future_wod_day).to_be_visible()
    page.screenshot(path=screenshot_dir / 'student-next-month-mobile.png')
    future_wod_day.click()
    expect(page.get_by_text('WOD próximo mês E2E', exact=False).first).to_be_visible()

    second_session = ClassSession.objects.create(
        title='Cross extra próximo mês E2E',
        class_type=ClassType.CROSS,
        scheduled_at=timezone.make_aware(datetime.combine(next_month + timedelta(days=7), datetime.min.time()).replace(hour=18)),
        duration_minutes=60,
        capacity=16,
    )
    SessionWorkout.objects.create(
        session=second_session,
        title='WOD extra próximo mês E2E',
        status=SessionWorkoutStatus.PUBLISHED,
    )
    page.goto(f'{live_server.url}/aluno/grade/?month={next_month:%Y-%m}')
    multi_day = page.locator('.student-month-day[data-day-picker]')
    expect(multi_day).to_be_visible()
    multi_day.click()
    picker = page.locator('#studentMonthPicker')
    expect(picker).to_be_visible()
    expect(picker.locator('a.student-month-picker__item')).to_have_count(2)
    assert picker.locator('a.student-month-picker__item').first.get_attribute('href').startswith('/aluno/wod/?session_id=')
    assert _horizontal_overflow(page) <= 1
    page.keyboard.press('Escape')
    expect(picker).to_be_hidden()
    expect(multi_day).to_be_focused()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_unresolved_movement_has_visible_mobile_review_form(page: Page, live_server, e2e_owner_credentials, monkeypatch):
    """A pendencia permanece corrigivel no mobile sem depender do dialog oculto."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS["mobile"])
    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")

    page.locator("textarea[name=source_text]").fill("Segunda\nWOD\n10 movimento inventado xyz")
    page.locator("form.smart-paste-form button[type=submit]").click()
    page.wait_for_load_state("networkidle")

    queue = page.locator(".smart-paste-review-queue")
    expect(queue).to_be_visible()
    expect(page.get_by_text("Revisão automática indisponível")).to_be_visible()
    expect(page.locator(".smart-paste-day-chip__preview").first).to_contain_text("movimento inventado xyz")
    expect(page.get_by_role('button', name='Tentar correção automática')).to_be_visible()
    expect(queue.locator("input[name=movement_slug]")).to_be_visible()
    assert page.locator(".topbar").evaluate("el => getComputedStyle(el).position") == "static"
    assert page.locator("#smart-paste-preview-panel").bounding_box()["y"] < page.locator(".smart-paste-form-card").bounding_box()["y"]

    queue.locator('[data-action="use-custom-movement"]').click()
    expect(queue.locator('input[name="movement_slug"]')).to_have_value('custom')
    queue.locator("button[type=submit]").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(".smart-paste-review-queue")).to_have_count(0)
    expect(page.locator(".smart-paste-resolution-notice")).to_have_count(0)
    expect(
        page.locator('form.smart-paste-confirm-form button[name="action"][value="confirm_plan"]')
    ).to_be_enabled()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_without_classes_stays_on_actionable_screen(page: Page, live_server, e2e_owner_credentials):
    """A semana pronta sem grade deve explicar o bloqueio sem jogar o usuário em um planner vazio."""
    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS['mobile'])
    page.goto(f'{live_server.url}/operacao/wod/paste/')
    page.locator('textarea[name="source_text"]').fill(CLEAN_SAMPLE_WOD)
    page.locator('form.smart-paste-form button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    page.locator('form.smart-paste-confirm-form button[value="confirm_and_project"]').click()

    expect(page.locator('.smart-paste-projection-blocker')).to_be_visible()
    expect(page.get_by_role('link', name='Abrir Grade de aulas')).to_be_visible()
    assert '/operacao/wod/paste/' in page.url


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_rejects_source_text_over_line_limit(page: Page, live_server, e2e_owner_credentials):
    """
    Hardening anti-spam: texto colado acima de SMART_PASTE_MAX_LINES (500)
    é rejeitado pela validação de form, ANTES de qualquer chamada ao Haiku.
    Cola texto obviamente fora do escopo de treino para simular o caso real
    (usuário colando o board inteiro, um PDF, spam) que o guard existe para
    barrar sem gastar chamada de API.
    """
    _login(page, live_server.url, e2e_owner_credentials)

    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")

    oversized_text = "\n".join(f"linha de lixo aleatorio numero {i}" for i in range(501))
    page.locator("textarea[name=source_text]").fill(oversized_text)
    page.locator("form.smart-paste-form button[type=submit]").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_text("o limite e 500", exact=False)).to_be_visible(timeout=5_000)
