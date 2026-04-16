"""
ARQUIVO: testes de roteamento da API v1 apos separacao por capacidade.

POR QUE ELE EXISTE:
- protege a reorganizacao interna da API v1 sem mudar contratos publicos.

O QUE ESTE ARQUIVO FAZ:
1. garante que os nomes de rota principais continuam resolvendo.
2. garante que cada rota aponta para o modulo mais coerente por capacidade.
"""

from django.test import SimpleTestCase
from django.urls import resolve, reverse


class ApiV1RoutingTests(SimpleTestCase):
    def test_whatsapp_poll_webhook_route_resolves_to_integrations_module(self):
        match = resolve(reverse('api-v1-whatsapp-poll-webhook'))

        self.assertEqual(match.func.view_class.__module__, 'api.v1.integrations_views')
        self.assertEqual(match.func.view_class.__name__, 'WhatsAppPollWebhookView')

    def test_init_system_route_resolves_to_internal_module(self):
        match = resolve(reverse('api-v1-init-system'))

        self.assertEqual(match.func.__module__, 'api.v1.internal_views')
        self.assertEqual(match.func.__name__, 'init_system_view')

    def test_payment_link_route_resolves_to_finance_module(self):
        match = resolve(reverse('api-v1-payment-link', args=[1]))

        self.assertEqual(match.func.view_class.__module__, 'api.v1.finance_views')
        self.assertEqual(match.func.view_class.__name__, 'PaymentLinkView')
