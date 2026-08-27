"""
ARQUIVO: testes da idempotencia do gateway Stripe.

POR QUE ELE EXISTE:
- protege a geracao deterministica da idempotency_key na Stripe usando a lingua comum da mesh.
- garante que o checkout consiga montar URLs de retorno validas no runtime atual.
- Onda 3 (2026-08-26): garante o fallback de Pix. Confirmado por leitura direta
  da conta Stripe (capabilities) que Pix NAO esta ativo — pedir
  payment_method_types=['card','pix'] sem a capability derruba o
  Session.create() inteiro (StripeError), nao so o Pix.
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

    def _make_payment_and_request(self):
        request = RequestFactory().get('/')
        request.user = SimpleNamespace(id=9, is_authenticated=True)
        request.build_absolute_uri = lambda path='': f'https://octoboxfit.com.br{path}'
        payment = SimpleNamespace(
            id=31, version=5, status='pending', amount=149.90, notes='',
            student=SimpleNamespace(id=7, full_name='Aluno Teste'),
            enrollment=None, installment_number=1, installment_total=1,
        )
        return payment, request

    @patch('integrations.stripe.services.log_audit_event')
    @patch('integrations.stripe.services.stripe.checkout.Session.create')
    def test_checkout_does_not_pass_payment_method_types(self, session_create_mock, _audit_mock):
        """Onda 3: sem payment_method_types explícito — dynamic payment methods
        deixa a Stripe decidir por request com base no que está ativo na conta.
        Pedir ['card','pix'] sem a capability de Pix ativa derruba o
        Session.create() inteiro; omitir o parâmetro evita a classe inteira
        desse problema (e futuros, se outro método for desativado na conta).
        """
        session_create_mock.return_value = SimpleNamespace(id='cs_1', url='https://x/cs_1')
        payment, request = self._make_payment_and_request()

        create_checkout_session(payment, request)

        self.assertNotIn('payment_method_types', session_create_mock.call_args.kwargs)
