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
from student_app.models import ReplicationBatch, SessionWorkout, SessionWorkoutStatus, WeeklyWodPlan, WeeklyWodPlanStatus
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
def test_wod_planner_does_not_expose_bulk_delete_action(page: Page, live_server, e2e_owner_credentials, theme):
    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS['mobile'])
    _set_theme(page, theme)
    page.goto(f'{live_server.url}/operacao/wod/planner/')
    expect(page.get_by_role('button', name='Remover todos os WODs')).to_have_count(0)
    expect(page.locator('#planner-clear-week-dialog')).to_have_count(0)
    page.keyboard.press('d')
    expect(page.locator('#planner-clear-week-dialog')).to_have_count(0)
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
        page.locator('select[name="workout_program"]').select_option(label='CrossFit')
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
        page.locator('select[name="workout_program"]').select_option(label='CrossFit')
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
@pytest.mark.parametrize(
    ('program_slug', 'program_label', 'class_type'),
    (('crossfit', 'CrossFit', ClassType.CROSS), ('hyrox', 'HYROX', ClassType.HYROX)),
)
def test_smart_paste_golden_path_end_to_end(
    page: Page, live_server, e2e_owner_credentials, program_slug, program_label, class_type,
):
    """
    Fluxo principal ponta a ponta: colar um treino limpo (sem pendência de
    revisão) -> organizar -> conferir cobertura real sem gravar WODs. Usa CLEAN_SAMPLE_WOD (mesmo texto de
    tests/test_workout_smart_paste.py) para não depender de chave de API
    real em CI — todo movimento resolve pelo dicionário estático.
    """
    _login(page, live_server.url, e2e_owner_credentials)

    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")

    selected_week_start = datetime.strptime(
        page.locator('input[name="week_start"]').input_value(),
        '%d/%m/%Y',
    ).date()
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    ClassSession.objects.create(
        title=f'Smart Paste Golden Path {program_label}',
        class_type=class_type,
        coach=actor,
        scheduled_at=timezone.make_aware(
            datetime.combine(selected_week_start, datetime.min.time()).replace(hour=12)
        ),
        duration_minutes=60,
        capacity=16,
    )

    page.locator("textarea[name=source_text]").fill(CLEAN_SAMPLE_WOD)
    page.locator('select[name="workout_program"]').select_option(label=program_label)
    page.locator("form.smart-paste-form button[type=submit]").click()
    page.wait_for_load_state("networkidle")

    expect(page.locator(".smart-paste-confidence-strip")).to_contain_text("Leitura pronta")

    plan = WeeklyWodPlan.objects.get(created_by=actor)
    assert plan.workout_program_id, 'todo plano semanal precisa guardar sua trilha de modalidade'
    assert plan.workout_program.is_active
    assert plan.workout_program.slug == program_slug
    assert page.locator('form.smart-paste-confirm-form input[name="workout_program"]').input_value() == str(plan.workout_program_id)

    confirm_button = page.locator(
        'form.smart-paste-confirm-form button[name="action"][value="confirm_and_project"]'
    )
    expect(confirm_button).to_be_enabled()
    confirm_button.click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("#smart-paste-projection-panel")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("1 aula(s) pronta(s) para criar")).to_be_visible()
    expect(page.locator('dialog.smart-paste-week-dialog[open]')).to_be_visible()
    expect(page.get_by_role('button', name='Distribuir WODs às aulas')).to_be_visible()
    assert not SessionWorkout.objects.exists(), 'conferir a semana nao deve gravar WODs'

    assert _horizontal_overflow(page) <= 1, "overflow horizontal apos confirmar e abrir a replicacao"


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_requires_explicit_modality_in_browser(page: Page, live_server, e2e_owner_credentials):
    """A tela nova não pode manter um CrossFit oculto como destino padrão."""
    _login(page, live_server.url, e2e_owner_credentials)
    page.goto(f'{live_server.url}/operacao/wod/paste/')
    selector = page.locator('select[name="workout_program"]')
    expect(selector).to_be_visible()
    expect(selector).to_have_value('')
    expect(selector).to_have_attribute('required', 'required')

    page.locator('textarea[name="source_text"]').fill(CLEAN_SAMPLE_WOD)
    page.locator('form.smart-paste-form button[type="submit"]').click()

    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    assert not WeeklyWodPlan.objects.filter(created_by=actor).exists()
    expect(selector).to_be_focused()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_previews_distribution_before_planner_and_keeps_approval_gate(
    page: Page,
    live_server,
    e2e_owner_credentials,
):
    """A semana mostra os destinos antes de escrever os WODs e conserva a aprovação."""
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    today = timezone.localdate()
    # Diferencia a semana escolhida da sugestão padrão para detectar fallback silencioso.
    target_monday = today + timedelta(days=(7 - today.weekday()) % 7) + timedelta(days=7)
    session = ClassSession.objects.create(
        title='Smart Paste E2E CrossFit',
        class_type=ClassType.CROSS,
        coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_monday, datetime.min.time()).replace(hour=12)),
        duration_minutes=60,
        capacity=16,
    )
    # Estende o limite do picker até a semana seguinte, permitindo escolher
    # uma quarta-feira na semana-alvo e verificar o snap no fluxo completo.
    ClassSession.objects.create(
        title='Limite futuro do calendário WOD',
        class_type=ClassType.CROSS,
        coach=actor,
        scheduled_at=timezone.make_aware(
            datetime.combine(target_monday + timedelta(days=7), datetime.min.time()).replace(hour=12)
        ),
        duration_minutes=60,
        capacity=16,
    )

    _login(page, live_server.url, e2e_owner_credentials)
    page.goto(f"{live_server.url}/operacao/wod/paste/")
    page.wait_for_load_state("networkidle")
    target_wednesday = target_monday + timedelta(days=2)
    page.locator('#smart-paste-week-start-picker').evaluate(
        """(picker, value) => {
            picker.value = value;
            picker.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        target_wednesday.isoformat(),
    )
    expect(page.locator('input[name="week_start"]')).to_have_value(target_monday.strftime('%d/%m/%Y'))
    expect(page.locator('#smart-paste-week-start-picker')).to_have_value(target_monday.isoformat())
    expect(page.locator('[data-smart-date-monday-hint]')).to_contain_text('Ajustado para segunda')
    page.locator('input[name="label"]').fill('E2E Smart Paste Automático')
    page.locator('textarea[name="source_text"]').fill(CLEAN_SAMPLE_WOD)
    page.locator('select[name="workout_program"]').select_option(label='CrossFit')
    page.locator('form.smart-paste-form button[type="submit"]').click()
    page.wait_for_load_state("networkidle")

    page.locator(
        'form.smart-paste-confirm-form button[name="action"][value="confirm_and_project"]'
    ).click()
    expect(page.locator('#smart-paste-projection-panel')).to_be_visible()
    expect(page.get_by_text('1 aula(s) pronta(s) para criar')).to_be_visible()
    idempotency_field = page.locator('#smart-paste-distribute-form [name="idempotency_key"]')
    expect(idempotency_field).to_have_count(1)
    expect(idempotency_field).not_to_have_value('')
    expect(page.locator('#smart-paste-projection-panel #id_idempotency_key')).to_have_count(0)
    dialog = page.locator('dialog.smart-paste-week-dialog[open]')
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role('heading', name='Confira para onde cada WOD vai')).to_be_visible()
    assert not SessionWorkout.objects.filter(session=session).exists(), 'o preview nao deve gravar o WOD'

    dialog.locator('[data-weekday-filter="0"]').click()
    monday_destination = dialog.locator('.smart-paste-projection-card[data-weekday-index="0"]').filter(
        has_text='Smart Paste E2E CrossFit'
    )
    expect(monday_destination).to_be_visible()
    monday_destination.locator('details > summary').first.click()
    expect(monday_destination).to_contain_text('3x')
    for prescription in ('10 reps', '8 reps', '20 reps'):
        expect(monday_destination).to_contain_text(prescription)
    dialog.locator('[data-weekday-filter="all"]').click()

    page.set_viewport_size({'width': 375, 'height': 667})
    dialog_box = dialog.bounding_box()
    assert dialog_box
    assert dialog_box['x'] >= 0 and dialog_box['y'] >= 0
    assert dialog_box['x'] + dialog_box['width'] <= 376
    assert dialog_box['y'] + dialog_box['height'] <= 668
    expect(dialog.get_by_role('button', name='Voltar para revisar')).to_be_visible()
    expect(dialog.locator('.smart-paste-projection-card').first).to_contain_text('Smart Paste E2E CrossFit')

    dialog.get_by_role('button', name='Voltar para revisar').click()
    expect(page.locator('dialog.smart-paste-week-dialog[open]')).to_have_count(0)
    expect(page.locator('#smart-paste-projection-panel')).to_be_visible()
    open_review_button = page.get_by_role('button', name='Abrir revisão da semana')
    expect(open_review_button).to_be_focused()
    open_review_button.click()
    dialog = page.locator('dialog.smart-paste-week-dialog[open]')
    expect(dialog).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('dialog.smart-paste-week-dialog[open]')).to_have_count(0)
    expect(open_review_button).to_be_focused()
    open_review_button.click()
    dialog = page.locator('dialog.smart-paste-week-dialog[open]')

    distribution_button = page.get_by_role('button', name='Distribuir WODs às aulas')
    expect(dialog.locator('.smart-paste-unlinked-warning')).to_be_visible()
    acknowledgement = dialog.locator('[name="acknowledge_unlinked_movements"]')
    expect(acknowledgement).not_to_be_checked()
    expect(distribution_button).to_be_disabled()
    acknowledgement.check()
    expect(distribution_button).to_be_enabled()
    retry_key = dialog.locator('#smart-paste-distribute-form [name="idempotency_key"]').input_value()

    dropped_response = {}

    def commit_then_drop_response(route):
        upstream_response = route.fetch()
        dropped_response['status'] = upstream_response.status
        route.abort(error_code='failed')

    page.route('**/operacao/wod/paste/', commit_then_drop_response)
    with page.expect_event(
        'requestfailed',
        predicate=lambda request: request.url.split('?')[0].rstrip('/').endswith('/operacao/wod/paste'),
        timeout=10000,
    ):
        distribution_button.click()
    expect(dialog).to_be_visible()
    assert dropped_response.get('status') == 200, 'o servidor deve ter confirmado a gravação antes da queda simulada'
    assert SessionWorkout.objects.filter(session=session, status=SessionWorkoutStatus.PENDING_APPROVAL).exists()
    page.unroute('**/operacao/wod/paste/', commit_then_drop_response)
    expect(distribution_button).to_be_enabled()
    distribution_button.click()

    distribution_result = page.locator('#smart-paste-projection-panel .smart-paste-distribution-result')
    expect(distribution_result).to_be_visible()
    expect(distribution_result).to_contain_text('Resultado recuperado')
    expect(distribution_result).to_contain_text('1 WOD(s) criados')
    expect(distribution_result).to_contain_text('1 aguardando aprovação')
    expect(distribution_result).to_contain_text('0 publicados conforme a política do box')
    expect(page.locator('#smart-paste-projection-panel .smart-paste-projection-summary')).to_contain_text(
        '0 aula(s) pronta(s) para criar'
    )
    expect(page.locator('#smart-paste-distribute-form [data-action="distribute-week"]')).to_be_disabled()
    assert SessionWorkout.objects.filter(session=session, status=SessionWorkoutStatus.PENDING_APPROVAL).exists()
    plan = WeeklyWodPlan.objects.get(label='E2E Smart Paste Automático')
    assert plan.week_start == target_monday
    batch = ReplicationBatch.objects.get(weekly_plan=plan)
    assert batch.target_week_start == target_monday
    assert str(batch.idempotency_key) == retry_key
    assert SessionWorkout.objects.filter(session=session).count() == 1
    page.goto(f'{live_server.url}/operacao/wod/planner/?week={target_monday.isoformat()}')
    page.wait_for_load_state('networkidle')

    projected_cell = page.locator(
        '[data-wod-planner-cell][data-wod-state="pending"]'
    ).filter(has_text='E2E Smart Paste Automático')
    expect(projected_cell).to_be_visible()
    expect(projected_cell).to_have_attribute('data-planner-status-label', 'Aguardando aprovação')
    week_heading = page.locator('.wod-planner__toolbar h2')
    target_week_label = f'{target_monday:%d/%m} - {target_monday + timedelta(days=6):%d/%m}'
    previous_week = target_monday - timedelta(days=7)
    previous_week_label = f'{previous_week:%d/%m} - {previous_week + timedelta(days=6):%d/%m}'
    next_link = page.get_by_role('link', name='Próxima →')
    assert next_link.get_attribute('href').endswith(
        f'?week={(target_monday + timedelta(days=7)).isoformat()}'
    )
    next_link.click()
    expect(week_heading).to_have_text(
        f'{target_monday + timedelta(days=7):%d/%m} - {target_monday + timedelta(days=13):%d/%m}'
    )
    page.get_by_role('link', name='← Anterior').click()
    expect(week_heading).to_have_text(target_week_label)
    page.get_by_role('link', name='← Anterior').click()
    expect(week_heading).to_have_text(previous_week_label)
    page.get_by_role('link', name='Próxima →').click()
    expect(week_heading).to_have_text(target_week_label)
    expect(projected_cell).to_be_visible()
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
def test_custom_movement_requires_explicit_ack_in_mobile_distribution_dialog(
    page: Page,
    live_server,
    e2e_owner_credentials,
):
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    today = timezone.localdate()
    target_monday = today + timedelta(days=(7 - today.weekday()) % 7)
    session = ClassSession.objects.create(
        title='Smart Paste Custom E2E',
        class_type=ClassType.CROSS,
        coach=actor,
        scheduled_at=timezone.make_aware(datetime.combine(target_monday, datetime.min.time()).replace(hour=11)),
        duration_minutes=60,
        capacity=16,
    )
    plan = WeeklyWodPlan.objects.create(
        week_start=target_monday,
        label='Semana com movimento personalizado',
        source_text='Segunda\nWOD\n10 ski erg lateral',
        parsed_payload={
            'days': [{
                'weekday': 0,
                'weekday_label': 'Segunda',
                'blocks': [{
                    'kind': 'metcon',
                    'title': 'WOD',
                    'movements': [{
                        'movement_slug': 'custom',
                        'movement_label_raw': '10 ski erg lateral',
                        'reps_spec': '10',
                        'load_spec': '',
                        'notes': '',
                    }],
                }],
            }],
        },
        created_by=actor,
        status=WeeklyWodPlanStatus.CONFIRMED,
    )

    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size({'width': 375, 'height': 667})
    page.goto(f'{live_server.url}/operacao/wod/paste/')
    page.wait_for_load_state('networkidle')
    expect(page.locator('#smart-paste-projection-panel')).to_be_visible()
    page.locator('#smart-paste-projection-panel form').first.locator('button[type="submit"]').click()

    dialog = page.locator('dialog.smart-paste-week-dialog[open]')
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text('10 ski erg lateral')
    expect(dialog).to_contain_text('sem compatibilidade validada nem vídeo')
    expect(dialog).to_contain_text('aluno não terá demonstração no app')
    distribution_button = dialog.get_by_role('button', name='Distribuir WODs às aulas')
    expect(distribution_button).to_be_disabled()
    assert not SessionWorkout.objects.filter(session=session).exists()

    dialog.locator('[name="acknowledge_unlinked_movements"]').check()
    expect(distribution_button).to_be_enabled()
    distribution_button.click()
    expect(page.get_by_text('1 WOD(s) criados: 1 aguardando aprovacao e', exact=False)).to_be_visible()
    projected = SessionWorkout.objects.get(session=session)
    assert projected.blocks.first().movements.first().movement_slug == 'custom'
    assert plan.replication_batches.filter(sessions_created=1).exists()


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
    page.locator('select[name="workout_program"]').select_option(label='CrossFit')
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
    expect(page.locator(".smart-paste-resolution-notice:not([hidden])")).to_have_count(0)
    expect(
        page.locator('form.smart-paste-confirm-form button[name="action"][value="confirm_plan"]')
    ).to_be_enabled()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('theme', THEMES)
def test_weekly_normalization_review_is_explicit_and_mobile_safe(
    page: Page, live_server, e2e_owner_credentials, monkeypatch, theme: str,
):
    """Haiku's structural proposal is inspectable and coach-accepted before confirmation."""
    actor = get_user_model().objects.get(username=e2e_owner_credentials['username'])
    candidate = {
        'week_label': None,
        'parse_warnings': [],
        'days': [{
            'weekday': 0,
            'weekday_label': 'Segunda',
            'blocks': [{
                'kind': 'custom', 'title': 'Treino', 'notes': 'Movimento perdido',
                'timecap_min': None, 'rounds': None, 'interval_seconds': None,
                'score_type': None, 'format_spec': None, 'movements': [], 'sort_order': 0,
            }],
        }],
    }
    monkeypatch.setattr('operations.workout_board_views.detect_and_convert_smartplan_weekly', lambda _text: None)
    monkeypatch.setattr('operations.workout_board_views.parse_weekly_wod_text', lambda _text: {
        'week_label': None,
        'parse_warnings': [{'line_number': 2, 'line_text': 'Movimento perdido', 'message': 'linha solta'}],
        'days': [],
    })
    monkeypatch.setattr('operations.workout_board_views.parse_weekly_wod_freeform', lambda _text: {
        'week_label': None, 'parse_warnings': [], 'days': [],
    })
    monkeypatch.setattr('operations.workout_board_views._freeform_should_take_over', lambda _parsed, _freeform: False)
    monkeypatch.setattr('operations.workout_board_views.normalize_weekly_wod', lambda **_kwargs: {
        'status': 'normalized',
        'candidate': candidate,
        'changes': [{
            'line_number': 2,
            'source_text': 'Movimento perdido',
            'normalized_text': 'Anotação preservada no bloco de segunda-feira',
            'reason': 'O trecho não identificava um movimento estruturado.',
        }],
    })

    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS['mobile'])
    _set_theme(page, theme)
    page.goto(f'{live_server.url}/operacao/wod/paste/')
    page.locator('textarea[name="source_text"]').fill('Segunda\nMovimento perdido')
    page.locator('select[name="workout_program"]').select_option(label='CrossFit')
    page.locator('form.smart-paste-form button[type="submit"]').click()
    page.wait_for_load_state('networkidle')

    review = page.locator('.smart-paste-normalization-acknowledgement')
    expect(page.get_by_text('O Haiku organizou a estrutura. Confira as mudanças antes de continuar.')).to_be_visible()
    expect(page.get_by_role('heading', name='Revise a organização sugerida')).to_be_visible()
    expect(page.get_by_text('Compare cada alteração com o texto original', exact=False)).to_be_visible()
    expect(page.get_by_text('Original:', exact=False)).to_be_visible()
    expect(page.get_by_text('Anotação preservada no bloco de segunda-feira')).to_be_visible()
    expect(page.get_by_role('link', name='Recusar organização e ajustar o texto')).to_be_visible()
    expect(review.locator('input[type="checkbox"]')).to_have_attribute('required', '')
    assert review.evaluate('el => getComputedStyle(el).display') == 'flex'
    assert _horizontal_overflow(page) <= 1

    composer = page.locator('.smart-paste-form textarea[name="source_text"]')
    confirm = page.locator('form.smart-paste-confirm-form button[value="confirm_plan"]')
    expect(confirm).to_have_text('Aceitar e salvar rascunho')
    composer.fill('Segunda\nOutro treino que ainda não foi organizado')
    expect(page.locator('[data-smart-paste-stale-source-notice]')).to_be_visible()
    expect(confirm).to_be_disabled()
    composer.fill('Segunda\nMovimento perdido')
    expect(page.locator('[data-smart-paste-stale-source-notice]')).to_be_hidden()
    expect(confirm).to_be_enabled()
    week_field = page.locator('.smart-paste-form [name="week_start"]')
    original_week = week_field.input_value()
    week_field.fill('07/09/2026')
    expect(page.locator('[data-smart-paste-stale-source-notice]')).to_be_visible()
    expect(confirm).to_be_disabled()
    week_field.fill(original_week)
    expect(confirm).to_be_enabled()
    label_field = page.locator('.smart-paste-form [name="label"]')
    original_label = label_field.input_value()
    label_field.fill('Semana diferente')
    expect(page.locator('[data-smart-paste-stale-source-notice]')).to_be_visible()
    expect(confirm).to_be_disabled()
    label_field.fill(original_label)
    expect(confirm).to_be_enabled()
    review.locator('input[type="checkbox"]').check()
    confirm.click()
    page.wait_for_load_state('networkidle')
    plan = WeeklyWodPlan.objects.get(created_by=actor)
    assert plan.status == WeeklyWodPlanStatus.CONFIRMED
    assert plan.parsed_payload['weekly_normalization']['status'] == 'coach_accepted'


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_smart_paste_without_classes_stays_on_actionable_screen(page: Page, live_server, e2e_owner_credentials):
    """A semana pronta sem grade deve explicar o bloqueio sem jogar o usuário em um planner vazio."""
    _login(page, live_server.url, e2e_owner_credentials)
    page.set_viewport_size(VIEWPORTS['mobile'])
    page.goto(f'{live_server.url}/operacao/wod/paste/')
    page.locator('textarea[name="source_text"]').fill(CLEAN_SAMPLE_WOD)
    page.locator('select[name="workout_program"]').select_option(label='CrossFit')
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
    page.locator('select[name="workout_program"]').select_option(label='CrossFit')
    page.locator("form.smart-paste-form button[type=submit]").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_text("o limite e 500", exact=False)).to_be_visible(timeout=5_000)
