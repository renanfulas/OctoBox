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

from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect


VIEWPORTS = {
    "mobile": {"width": 390, "height": 844},
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

        page.screenshot(path=screenshot_dir / f"smart-paste-{viewport_name}-{theme}.png")
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

    confirm_button = page.locator("form.smart-paste-confirm-form button[type=submit]")
    expect(confirm_button).to_be_enabled()
    confirm_button.click()
    page.wait_for_load_state("networkidle")

    expect(page.locator("#smart-paste-projection-panel")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("Montar preview de replicacao", exact=False)).to_be_visible()

    assert _horizontal_overflow(page) <= 1, "overflow horizontal apos confirmar e abrir a replicacao"


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
    expect(queue.locator("input[name=movement_slug]")).to_be_visible()
    assert page.locator(".topbar").evaluate("el => getComputedStyle(el).position") == "static"
    assert page.locator("#smart-paste-preview-panel").bounding_box()["y"] < page.locator(".smart-paste-form-card").bounding_box()["y"]

    queue.locator("input[name=movement_slug]").fill("front_squat")
    queue.locator("button[type=submit]").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(".smart-paste-review-queue")).to_have_count(0)
    expect(page.locator(".smart-paste-resolution-notice")).to_have_count(0)
    expect(page.locator(".smart-paste-confirm-form button[type=submit]")).to_be_enabled()


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
