"""
ARQUIVO: testes da idempotencia do gateway Stripe.

POR QUE ELE EXISTE:
- protege a geracao deterministica da idempotency_key na Stripe usando a lingua comum da mesh.
- garante que o checkout consiga montar URLs de retorno validas no runtime atual.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from integrations.stripe.services import create_checkout_session, generate_idempotency_key


class IntegrationsStripeServicesTests(SimpleTestCase):
    def test_generate_idempotency_key_uses_canonical_builder_shape(self):
        payment = SimpleNamespace(id=31, version=5)

        result = generate_idempotency_key(payment, 'checkout')

        self.assertEqual(result, 'octobox_checkout_pay_31_v5')

    @patch('integrations.stripe.services.log_audit_event')
    @patch('integrations.stripe.services.stripe.checkout.Session.create')
    def test_create_checkout_session_uses_runtime_checkout_routes(self, session_create_mock, _audit_mock):
        request = RequestFactory().get('/')
        request.user = SimpleNamespace(id=9, is_authenticated=True)
        request.build_absolute_uri = lambda path='': f'https://octoboxfit.com.br{path}'

        session_create_mock.return_value = SimpleNamespace(
            id='cs_test_123',
            url='https://checkout.stripe.test/session/cs_test_123',
        )

        payment = SimpleNamespace(
            id=31,
            version=5,
            status='pending',
            amount=149.90,
            notes='Pagamento de teste',
            student=SimpleNamespace(id=7, full_name='Aluno Teste'),
            enrollment=None,
            installment_number=1,
            installment_total=1,
        )

        checkout_url = create_checkout_session(payment, request)

        self.assertEqual(checkout_url, 'https://checkout.stripe.test/session/cs_test_123')
        self.assertEqual(
            session_create_mock.call_args.kwargs['success_url'],
            'https://octoboxfit.com.br/financeiro/stripe/checkout/sucesso/31/?session_id={CHECKOUT_SESSION_ID}',
        )
        self.assertEqual(
            session_create_mock.call_args.kwargs['cancel_url'],
            'https://octoboxfit.com.br/financeiro/stripe/checkout/cancelado/31/',
        )
