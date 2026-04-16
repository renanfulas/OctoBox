"""
ARQUIVO: testes da precedencia de idempotencia inbound de communications.

POR QUE ELE EXISTE:
- protege a reancoragem de communications na lingua comum de idempotency_key.
"""

from django.test import SimpleTestCase

from communications.infrastructure.django_inbound_idempotency import (
    resolve_inbound_message_idempotency_key,
)


class CommunicationsInboundIdempotencyTests(SimpleTestCase):
    def test_resolve_inbound_message_idempotency_key_prefers_external_message_id(self):
        result = resolve_inbound_message_idempotency_key(
            external_message_id='wamid.123',
            webhook_fingerprint='fingerprint-1',
        )

        self.assertEqual(result, 'wamid.123')

    def test_resolve_inbound_message_idempotency_key_falls_back_to_fingerprint(self):
        result = resolve_inbound_message_idempotency_key(
            external_message_id='',
            webhook_fingerprint='fingerprint-1',
        )

        self.assertEqual(result, 'fingerprint-1')
