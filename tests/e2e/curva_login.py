"""Entrada na Curva pelo link mágico, do jeito que o aluno faz."""

import uuid

from playwright.sync_api import Page


def enter_with_magic_link(page: Page, login_url: str) -> None:
    # O GET do link só mostra "Entrar como ..." (scanners de e-mail também o
    # abrem); quem consome o token é o botão.
    page.goto(login_url)
    page.locator('[data-login-confirm] button[type=submit]').click()
    page.wait_for_url(lambda url: '/treinos/login' not in url)


def sign_in_owner(page: Page, base_url: str, plan_slug: str) -> None:
    """Conta + assinatura do slug e sessão verificada no navegador.

    `/renan/<slug>` exige login; use quando o teste não é sobre o login.
    """
    from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
    from student_identity.public_workout_session import (
        PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
        build_public_workout_session_value,
    )

    account = PublicWorkoutAccount.objects.create(email=f'{plan_slug}-e2e-{uuid.uuid4().hex[:8]}@example.test')
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)
    page.context.add_cookies([{
        'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
        'value': build_public_workout_session_value(account_id=account.pk, identity_verified=True),
        'url': base_url.rstrip('/'),
    }])
