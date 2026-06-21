"""
ARQUIVO: testes dos guardrails P0 de pagamento.

POR QUE EXISTE:
- checkout_rate_limit_exceeded: guard de card-testing compartilhado entre
  StripeCheckoutRedirectView e PaymentLinkView (views Django nao-DRF). Antes,
  o PaymentLinkView nao tinha limite e podia cunhar Sessions Stripe ilimitadas.
- PaymentBulkActionView.perform_action: mark_paid passou a setar paid_at (antes
  ficava nulo) e mark_cancelled usava PaymentStatus.CANCELLED (typo — o enum e
  CANCELED, 1 L), que levantava AttributeError ao cancelar em massa.
"""

from __future__ import annotations

from types import SimpleNamespace

from django.core.cache import cache
from django.db import transaction
from django.test import RequestFactory, TestCase

from api.v1.finance_views import PaymentBulkActionView
from finance.models import PaymentStatus
from shared_support.security.fintech_throttles import (
    CHECKOUT_RATE_LIMIT_MAX,
    checkout_rate_limit_exceeded,
)
from tests.factories import PaymentFactory


class CheckoutRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def _request(self, user_id):
        req = RequestFactory().get('/')
        req.user = SimpleNamespace(id=user_id)
        return req

    def test_allows_until_max_then_blocks(self):
        req = self._request(42)
        for _ in range(CHECKOUT_RATE_LIMIT_MAX):
            self.assertFalse(checkout_rate_limit_exceeded(req))
        self.assertTrue(checkout_rate_limit_exceeded(req))

    def test_counter_is_per_user(self):
        a = self._request(42)
        b = self._request(99)
        for _ in range(CHECKOUT_RATE_LIMIT_MAX):
            checkout_rate_limit_exceeded(a)
        self.assertTrue(checkout_rate_limit_exceeded(a))
        self.assertFalse(checkout_rate_limit_exceeded(b))


class PaymentBulkActionTests(TestCase):
    def _perform(self, payment, action):
        with transaction.atomic():
            PaymentBulkActionView().perform_action(payment.id, action, user=None)

    def test_mark_paid_sets_paid_at(self):
        payment = PaymentFactory(status=PaymentStatus.PENDING)
        self.assertIsNone(payment.paid_at)

        self._perform(payment, 'mark_paid')

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertIsNotNone(payment.paid_at)

    def test_mark_cancelled_uses_correct_enum(self):
        payment = PaymentFactory(status=PaymentStatus.PENDING)

        # Nao deve levantar AttributeError (regressao do typo CANCELLED).
        self._perform(payment, 'mark_cancelled')

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELED)

    def test_unknown_action_raises(self):
        payment = PaymentFactory(status=PaymentStatus.PENDING)
        with self.assertRaises(ValueError):
            self._perform(payment, 'mark_frobnicated')
