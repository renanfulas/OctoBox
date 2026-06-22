"""
ARQUIVO: cobertura das views de entrada de pagamento (checkout + payment-link).

POR QUE EXISTE:
- StripeCheckoutRedirectView e PaymentLinkView sao os pontos onde o operador abre
  um checkout Stripe; estavam quase sem teste (47% / 72%). Cobrem-se aqui os
  caminhos sensiveis: rate-limit (card-testing), fatura ja paga, sucesso e falha
  do gateway. Tambem os branches no-op do PaymentBulkActionView (ja pago/cancelado).
"""

from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_OWNER
from api.v1.finance_views import PaymentBulkActionView
from finance.models import PaymentStatus
from tests.factories import PaymentFactory, StudentFactory, UserFactory


class PaymentEntryViewsTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command('bootstrap_roles')
        self.owner = UserFactory(username='cov-owner')
        self.owner.groups.add(Group.objects.get(name=ROLE_OWNER))
        self.student = StudentFactory()
        self.payment = PaymentFactory(student=self.student, status=PaymentStatus.PENDING)
        self.client.force_login(self.owner)

    # ── StripeCheckoutRedirectView ─────────────────────────────────────────
    @patch('finance.views.stripe_checkout.create_checkout_session',
           return_value='https://checkout.stripe.test/cs_redirect')
    def test_checkout_redirect_success(self, _mock):
        resp = self.client.post(reverse('finance-checkout-redirect', args=[self.payment.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'https://checkout.stripe.test/cs_redirect')

    def test_checkout_redirect_already_paid_returns_400(self):
        paid = PaymentFactory(student=self.student, status=PaymentStatus.PAID)
        resp = self.client.post(reverse('finance-checkout-redirect', args=[paid.pk]))
        self.assertEqual(resp.status_code, 400)

    @patch('finance.views.stripe_checkout.create_checkout_session',
           side_effect=RuntimeError('gateway indisponivel'))
    def test_checkout_redirect_gateway_error_returns_500(self, _mock):
        resp = self.client.post(reverse('finance-checkout-redirect', args=[self.payment.pk]))
        self.assertEqual(resp.status_code, 500)

    @patch('finance.views.stripe_checkout.checkout_rate_limit_exceeded', return_value=True)
    def test_checkout_redirect_rate_limited_returns_429(self, _mock):
        resp = self.client.post(reverse('finance-checkout-redirect', args=[self.payment.pk]))
        self.assertEqual(resp.status_code, 429)

    # ── PaymentLinkView ────────────────────────────────────────────────────
    @patch('api.v1.finance_views.create_checkout_session',
           return_value='https://checkout.stripe.test/cs_link')
    def test_payment_link_success_returns_url(self, _mock):
        resp = self.client.get(reverse('api-v1-payment-link', args=[self.payment.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['url'], 'https://checkout.stripe.test/cs_link')

    @patch('api.v1.finance_views.checkout_rate_limit_exceeded', return_value=True)
    def test_payment_link_rate_limited_returns_429(self, _mock):
        resp = self.client.get(reverse('api-v1-payment-link', args=[self.payment.pk]))
        self.assertEqual(resp.status_code, 429)

    @patch('api.v1.finance_views.create_checkout_session', side_effect=RuntimeError('boom'))
    def test_payment_link_gateway_error_returns_500(self, _mock):
        resp = self.client.get(reverse('api-v1-payment-link', args=[self.payment.pk]))
        self.assertEqual(resp.status_code, 500)

    # ── PaymentBulkActionView (branches no-op) ─────────────────────────────
    def test_bulk_mark_paid_is_noop_when_already_paid(self):
        paid = PaymentFactory(student=self.student, status=PaymentStatus.PAID)
        paid.paid_at = timezone.now()
        paid.save(update_fields=['paid_at'])
        original_paid_at = paid.paid_at

        with transaction.atomic():
            PaymentBulkActionView().perform_action(paid.id, 'mark_paid', user=None)

        paid.refresh_from_db()
        self.assertEqual(paid.status, PaymentStatus.PAID)
        self.assertEqual(paid.paid_at, original_paid_at)  # no-op: nao re-carimba paid_at

    def test_bulk_mark_cancelled_is_noop_when_already_cancelled(self):
        cancelled = PaymentFactory(student=self.student, status=PaymentStatus.CANCELED)

        with transaction.atomic():
            PaymentBulkActionView().perform_action(cancelled.id, 'mark_cancelled', user=None)

        cancelled.refresh_from_db()
        self.assertEqual(cancelled.status, PaymentStatus.CANCELED)
