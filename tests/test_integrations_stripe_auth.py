"""
ARQUIVO: teste de gate — verify_stripe_webhook contra o SDK real da Stripe.

POR QUE ELE EXISTE:
- Bug real em producao (2026-08-28): verify_stripe_webhook fazia
  `dict(event)` sobre o StripeObject devolvido por
  stripe.Webhook.construct_event(). Na SDK 15.x, StripeObject nao
  implementa mais o protocolo de Mapping (sem keys()/__iter__
  compativel) — dict(event) estourava `KeyError: 0`, e TODO webhook
  assinado corretamente (ou seja, todo webhook real da Stripe) derrubava
  o endpoint com 500, sem nunca criar um PaymentWebhookEvent.
- Nunca foi pego porque TODOS os testes existentes (tests/test_error_scenarios.py
  e outros) mockam `verify_stripe_webhook` inteiro para isolar do SDK —
  documentado explicitamente como escolha de design ("mock de
  verify_stripe_webhook isola os testes do SDK da Stripe"). Isso e correto
  para testar a VIEW, mas deixou a funcao em si, e sua fronteira real com
  o SDK, sem nenhuma cobertura.
- Este arquivo testa verify_stripe_webhook chamando o SDK de verdade
  (stripe.Webhook.construct_event contra um payload assinado com HMAC
  real), sem mockar nada do lado da Stripe — exatamente o que faltava.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.test import SimpleTestCase

from integrations.stripe.auth import StripeWebhookAuthError, verify_stripe_webhook

_TEST_SECRET = 'whsec_test_secret_para_verificacao_de_assinatura'


def _sign(payload_bytes: bytes, *, secret: str = _TEST_SECRET, timestamp: str | None = None) -> str:
    timestamp = timestamp or str(int(time.time()))
    signed_payload = f'{timestamp}.'.encode('utf-8') + payload_bytes
    signature = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={signature}'


class VerifyStripeWebhookRealSdkTests(SimpleTestCase):
    """Sem mock de stripe.Webhook.construct_event — exercita o SDK de verdade."""

    def _payload(self) -> bytes:
        return json.dumps({
            'id': 'evt_test_real_sdk',
            'object': 'event',
            'type': 'checkout.session.completed',
            'created': int(time.time()),
            'livemode': False,
            'data': {'object': {'id': 'cs_test_x', 'amount_total': 100, 'metadata': {'payment_id': '1'}}},
        }).encode('utf-8')

    @patch('integrations.stripe.auth._WEBHOOK_SECRET', _TEST_SECRET)
    def test_valid_signature_returns_plain_dict_not_stripe_object(self):
        payload_bytes = self._payload()
        sig_header = _sign(payload_bytes)

        event = verify_stripe_webhook(payload_bytes, sig_header)

        self.assertIs(type(event), dict, 'evento deveria ser dict puro (nao StripeObject) — dict(event) quebra na SDK 15.x')
        self.assertEqual(event['id'], 'evt_test_real_sdk')
        self.assertEqual(event['type'], 'checkout.session.completed')
        self.assertIs(type(event['data']), dict)
        self.assertIs(type(event['data']['object']), dict)
        self.assertEqual(event['data']['object']['amount_total'], 100)
        self.assertEqual(event['data']['object']['metadata']['payment_id'], '1')

    @patch('integrations.stripe.auth._WEBHOOK_SECRET', _TEST_SECRET)
    def test_invalid_signature_raises_auth_error(self):
        payload_bytes = self._payload()

        with self.assertRaises(StripeWebhookAuthError):
            verify_stripe_webhook(payload_bytes, 't=123,v1=assinatura-forjada')

    @patch('integrations.stripe.auth._WEBHOOK_SECRET', _TEST_SECRET)
    def test_signature_from_different_secret_raises_auth_error(self):
        payload_bytes = self._payload()
        sig_header = _sign(payload_bytes, secret='whsec_outro_segredo_completamente_diferente')

        with self.assertRaises(StripeWebhookAuthError):
            verify_stripe_webhook(payload_bytes, sig_header)

    @patch('integrations.stripe.auth._WEBHOOK_SECRET', _TEST_SECRET)
    def test_malformed_payload_raises_auth_error(self):
        payload_bytes = b'isto nao e json valido'
        sig_header = _sign(payload_bytes)

        with self.assertRaises(StripeWebhookAuthError):
            verify_stripe_webhook(payload_bytes, sig_header)
