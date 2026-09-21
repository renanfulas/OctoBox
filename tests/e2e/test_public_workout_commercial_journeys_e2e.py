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
