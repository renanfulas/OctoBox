"""Entrada na Curva pelo link mágico, do jeito que o aluno faz."""

from playwright.sync_api import Page


def enter_with_magic_link(page: Page, login_url: str) -> None:
    # O GET do link só mostra "Entrar como ..." (scanners de e-mail também o
    # abrem); quem consome o token é o botão.
    page.goto(login_url)
    page.locator('[data-login-confirm] button[type=submit]').click()
    page.wait_for_url(lambda url: '/treinos/login' not in url)
