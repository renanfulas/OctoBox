"""
ARQUIVO: testes da idempotencia do gateway Stripe.

POR QUE ELE EXISTE:
- protege a geracao deterministica da idempotency_key na Stripe usando a lingua comum da mesh.
"""

from types import SimpleNamespace

from django.test import SimpleTestCase

from integrations.stripe.services import generate_idempotency_key


class IntegrationsStripeServicesTests(SimpleTestCase):
    def test_generate_idempotency_key_uses_canonical_builder_shape(self):
        payment = SimpleNamespace(id=31, version=5)

        result = generate_idempotency_key(payment, 'checkout')

        self.assertEqual(result, 'octobox_checkout_pay_31_v5')
