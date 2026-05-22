"""
ARQUIVO: POC E2E — fluxo de login do funcionário (Fase 8).

POR QUE EXISTE:
- Demonstra que o stack completo funciona end-to-end: browser → Django →
  autenticação → resolução de tenant → redirect para workspace.
- Serve como template para futuros testes E2E (ver docs/testing/e2e-guide.md).

O QUE ESTE ARQUIVO FAZ:
1. Navega para a tela de login do funcionário (/login/funcionario/).
2. Preenche credenciais de um Owner pré-criado pelo fixture e2e_owner_credentials.
3. Submete o formulário.
4. Verifica que o browser saiu da tela de login e chegou ao workspace operacional.

PONTOS CRÍTICOS:
- Este teste requer live_server (servidor Django real em thread separada).
  NAO roda com --nomigrations — precisa do schema box_test migrado.
- O TenantBySessionMiddleware resolve o tenant via Membership. Sem o fixture
  e2e_owner_credentials criar a Membership, o login resultaria em 403.
- Executar localmente:
    pytest tests/e2e/ --create-db --migrations --headed
  (--headed abre o browser visivelmente para debug).
- Em CI: ver .github/workflows/e2e-nightly.yml (headless, Chromium only).
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_staff_login_reaches_operational_workspace(
    page: Page,
    live_server,
    e2e_owner_credentials,
):
    """
    E2E — fluxo completo de login do funcionário.

    Verifica que um Owner autenticado:
    1. Consegue ver a tela de login.
    2. Preenche e submete as credenciais corretamente.
    3. É redirecionado para o workspace operacional (fora da tela de login).

    Este é o caminho crítico mais fundamental do OctoBox: sem login funcionando,
    nenhuma outra funcionalidade é acessível.
    """
    creds = e2e_owner_credentials

    # ── 1. Página de login carrega ─────────────────────────────────────────
    page.goto(f'{live_server.url}/login/funcionario/')

    expect(page).to_have_title('Entrar na equipe | OctoBox')
    expect(page.locator('form')).to_be_visible()

    # ── 2. Preenche as credenciais ─────────────────────────────────────────
    page.locator('#id_username').fill(creds['username'])
    page.locator('#id_password').fill(creds['password'])

    # ── 3. Submete o formulário ────────────────────────────────────────────
    page.locator('button[type="submit"]').click()

    # ── 4. Aguarda redirect e verifica destino ─────────────────────────────
    # Após login bem-sucedido: /login/funcionario/ → /operacao/ → /operacao/owner/
    # Playwright segue os redirects automaticamente.
    page.wait_for_url('**/operacao/**', timeout=15_000)

    assert '/login/' not in page.url, (
        f'Login falhou ou não redirecionou corretamente. URL atual: {page.url}'
    )
    assert '/operacao/' in page.url, (
        f'Workspace operacional não foi atingido. URL atual: {page.url}'
    )
