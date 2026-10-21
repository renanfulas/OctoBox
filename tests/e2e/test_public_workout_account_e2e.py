from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import Page, expect

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutPayment,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_mobile_account_hub_never_renders_blank_and_explains_payment_state(page: Page, live_server, tmp_path):
    account = PublicWorkoutAccount.objects.create(email='e2e-curva-account@example.com')
    get_or_create_subscription(account=account, tier=PublicWorkoutTier.COMPLETO)
    try:
        page.set_viewport_size({'width': 390, 'height': 844})
        page.context.add_cookies([{
            'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
            'value': build_public_workout_session_value(account_id=account.pk),
            'url': live_server.url,
        }])
        page.goto(f'{live_server.url}/treinos/minha-conta')

        expect(page.locator('#journey-title')).to_have_text('Estamos confirmando sua assinatura')
        expect(page.locator('.curva-journey-card')).to_be_visible()
        expect(page.locator('body')).not_to_have_text('Server Error')
        page.screenshot(path=str(tmp_path / 'curva-minha-conta-mobile.png'), full_page=True)
    finally:
        account.delete()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_mobile_refund_card_is_visible_dark_and_has_no_horizontal_overflow(page: Page, live_server):
    account = PublicWorkoutAccount.objects.create(email='e2e-curva-refund@example.com')
    subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.save(update_fields=['status'])
    PublicWorkoutPayment.objects.create(
        subscription=subscription,
        due_date=date.today(),
        paid_at=timezone.now(),
        gross_amount=Decimal('97.00'),
        net_amount=Decimal('97.00'),
        status=PublicWorkoutPaymentStatus.PAID,
        stripe_invoice_id='in_e2e_refund',
    )
    try:
        page.set_viewport_size({'width': 390, 'height': 844})
        page.context.add_cookies([{
            'name': PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
            'value': build_public_workout_session_value(account_id=account.pk),
            'url': live_server.url,
        }])
        page.goto(f'{live_server.url}/treinos/minha-conta')

        refund_form = page.locator('.curva-refund-form')
        expect(refund_form).to_be_visible()
        expect(refund_form.locator('textarea')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        textarea_bg = refund_form.locator('textarea').evaluate(
            '(element) => getComputedStyle(element).backgroundColor'
        )
        assert textarea_bg not in ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)')
    finally:
        account.delete()
