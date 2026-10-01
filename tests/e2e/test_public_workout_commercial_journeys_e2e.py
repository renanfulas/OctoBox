"""Jornadas comerciais Curva no navegador, sem chamar a Stripe externa."""

import pytest
from playwright.sync_api import Page, expect

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)
from student_identity.public_workout_login import request_login_token


def _local_checkout_url(live_server):
    return f'{live_server.url}/treinos/minha-conta?checkout=retorno'


def _select_plan_and_submit(page: Page, *, tier: str, email: str):
    form = page.locator(f'[data-curva-signup-form][data-tier="{tier}"]')
    form.locator('input[type="email"]').fill(email)
    form.locator('input[name="accept_contract"]').check()
    form.locator('button[type="submit"]').click()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_new_customer_accepts_contract_and_reaches_hosted_checkout_return(
    page: Page, live_server, monkeypatch,
):
    email = 'new-commercial-e2e@example.test'
    monkeypatch.setattr(
        'student_identity.public_workout_views.start_subscription_checkout',
        lambda **_kwargs: _local_checkout_url(live_server),
    )
    try:
        page.goto(f'{live_server.url}/treinos/')
        _select_plan_and_submit(page, tier='essencial', email=email)
        page.wait_for_url('**/treinos/minha-conta?checkout=retorno')

        expect(page.locator('#journey-title')).to_have_text('Estamos confirmando sua assinatura')
        subscription = PublicWorkoutAccount.objects.get(email=email).subscription
        assert subscription.tier == PublicWorkoutTier.ESSENCIAL
        assert subscription.status == PublicWorkoutSubscriptionStatus.PENDING_PAYMENT
        assert subscription.contract_accepted_at is not None
        assert subscription.requires_login is True
    finally:
        PublicWorkoutAccount.objects.filter(email=email).delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_canceled_customer_renews_authenticated_without_login_loop(
    page: Page, live_server, monkeypatch,
):
    email = 'renew-commercial-e2e@example.test'
    account = PublicWorkoutAccount.objects.create(email=email)
    subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
    subscription.status = PublicWorkoutSubscriptionStatus.CANCELED
    subscription.save(update_fields=['status'])
    monkeypatch.setattr(
        'student_identity.public_workout_views.start_subscription_checkout',
        lambda **_kwargs: _local_checkout_url(live_server),
    )
    try:
        page.context.add_cookies([{
            'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
            'value': build_public_workout_session_value(account_id=account.pk),
            'url': live_server.url,
        }])
        page.goto(f'{live_server.url}/treinos/')
        _select_plan_and_submit(page, tier='completo', email=email)
        page.wait_for_url('**/treinos/minha-conta?checkout=retorno')

        expect(page.locator('#journey-title')).to_have_text('Estamos confirmando sua assinatura')
        subscription.refresh_from_db()
        assert subscription.tier == PublicWorkoutTier.COMPLETO
        assert subscription.status == PublicWorkoutSubscriptionStatus.PENDING_PAYMENT
        assert '/treinos/login' not in page.url
    finally:
        account.delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_active_customer_opens_billing_portal_to_change_plan(
    page: Page, live_server, monkeypatch,
):
    email = 'portal-commercial-e2e@example.test'
    account = PublicWorkoutAccount.objects.create(email=email)
    subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.COMPLETO)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.stripe_customer_id = 'cus_portal_e2e'
    subscription.save(update_fields=['status', 'stripe_customer_id'])
    monkeypatch.setattr(
        'student_identity.public_workout_views.start_customer_portal_session',
        lambda **_kwargs: f'{live_server.url}/treinos/minha-conta?portal=retorno',
    )
    try:
        page.context.add_cookies([{
            'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
            'value': build_public_workout_session_value(account_id=account.pk),
            'url': live_server.url,
        }])
        page.goto(f'{live_server.url}/treinos/minha-conta')
        expect(page.locator('[data-billing-portal]').first).to_be_visible()
        page.locator('[data-billing-portal]').first.click()
        page.wait_for_url('**/treinos/minha-conta?portal=retorno')
        expect(page.locator('body')).not_to_have_text('Server Error')
    finally:
        account.delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_returning_customer_enters_with_one_time_magic_link(page: Page, live_server):
    email = 'login-commercial-e2e@example.test'
    account = PublicWorkoutAccount.objects.create(email=email)
    get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
    token = request_login_token(email=email, base_url=live_server.url, next_url='/treinos/minha-conta')
    try:
        page.goto(f'{live_server.url}/treinos/login?token={token.token}&next=/treinos/minha-conta')
        page.wait_for_url('**/treinos/minha-conta')

        expect(page.locator('#journey-title')).to_have_text('Estamos confirmando sua assinatura')
        token.refresh_from_db()
        account.refresh_from_db()
        assert token.used_at is not None
        assert account.last_login_at is not None
    finally:
        account.delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_legacy_active_customer_with_custom_price_starts_checkout_from_the_app(
    page: Page, live_server, monkeypatch,
):
    """Achado real (Rafael, cliente legado — seed_legacy_workout_accounts):
    assinatura ja' nasce com status=ACTIVE mas SEM stripe_customer_id (nunca
    passou pelo checkout de verdade). Antes, "Pagamentos" na aba Perfil
    (/renan/<slug>) caia num link morto pro hub /treinos/minha-conta — o
    hub nao mostra nada sobre pagar porque get_customer_journey() so' trata
    status PAST_DUE/SUSPENDED/PENDING_PAYMENT, nunca "ACTIVE sem Stripe
    nenhum ainda". Depois que o Renan preenche custom_monthly_price no
    admin (PublicWorkoutSubscriptionAdmin), "Pagamentos" dispara o checkout
    de valor negociado (POST /treinos/checkout-personalizado,
    PublicWorkoutCustomCheckoutView) direto do app, sem ele precisar
    copiar/colar link no WhatsApp."""
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    email = 'legado-valor-negociado-e2e@example.test'
    publish_program(slug='bruno', payload=build_example_payload())
    account = PublicWorkoutAccount.objects.create(email=email)
    subscription = get_or_create_subscription(account=account, plan_slug='bruno', tier=PublicWorkoutTier.ESSENCIAL)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.custom_monthly_price = 150
    subscription.save(update_fields=['status', 'custom_monthly_price'])
    monkeypatch.setattr(
        'student_identity.public_workout_views.start_custom_price_subscription_checkout',
        lambda **_kwargs: f'{live_server.url}/treinos/minha-conta?checkout=retorno',
    )
    try:
        page.context.add_cookies([{
            'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
            'value': build_public_workout_session_value(account_id=account.pk),
            'url': live_server.url,
        }])
        page.goto(f'{live_server.url}/renan/bruno')
        page.locator('[data-workout-tab-target="workout-panel-perfil"]').click()

        pagamentos = page.locator('[data-workout-start-custom-checkout]')
        expect(pagamentos).to_be_visible()
        expect(pagamentos).to_contain_text('Pagar agora')
        pagamentos.click()

        page.wait_for_url('**/treinos/minha-conta?checkout=retorno')
        expect(page.locator('body')).not_to_have_text('Server Error')

        subscription.refresh_from_db()
        assert subscription.status == PublicWorkoutSubscriptionStatus.ACTIVE
    finally:
        account.delete()
        from public_workouts.models import PublicWorkoutProgram

        PublicWorkoutProgram.objects.filter(slug='bruno').delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_legacy_active_customer_without_custom_price_sees_talk_to_renan_message(
    page: Page, live_server,
):
    """Mesmo cenario acima, ANTES do Renan preencher custom_monthly_price
    no admin -- nunca mostra um botao que chamaria a view e falharia com
    404 'valor_nao_definido'."""
    from public_workouts.schema import build_example_payload
    from public_workouts.services import publish_program

    email = 'legado-sem-valor-e2e@example.test'
    publish_program(slug='bruno', payload=build_example_payload())
    account = PublicWorkoutAccount.objects.create(email=email)
    subscription = get_or_create_subscription(account=account, plan_slug='bruno', tier=PublicWorkoutTier.ESSENCIAL)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.save(update_fields=['status'])
    try:
        page.context.add_cookies([{
            'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
            'value': build_public_workout_session_value(account_id=account.pk),
            'url': live_server.url,
        }])
        page.goto(f'{live_server.url}/renan/bruno')
        page.locator('[data-workout-tab-target="workout-panel-perfil"]').click()

        perfil_panel = page.locator('#workout-panel-perfil')
        expect(perfil_panel.get_by_text('Fale com o Renan', exact=True)).to_be_visible()
        expect(page.locator('[data-workout-start-custom-checkout]')).to_have_count(0)
        expect(page.locator('[data-billing-portal]')).to_have_count(0)
    finally:
        from public_workouts.models import PublicWorkoutFunnelEvent, PublicWorkoutProgram

        # PublicWorkoutDetailView.get registra funnel event a cada visita --
        # FK pra subscription nao e CASCADE, precisa sair antes da conta.
        PublicWorkoutFunnelEvent.objects.filter(subscription=subscription).delete()
        account.delete()
        PublicWorkoutProgram.objects.filter(slug='bruno').delete()
