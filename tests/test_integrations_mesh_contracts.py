"""
ARQUIVO: testes dos contratos compartilhados da Signal Mesh.

POR QUE ELE EXISTE:
- protege a precedencia canonica de idempotency_key entre canais.
"""

from django.test import SimpleTestCase

from integrations.mesh import (
    build_idempotency_key,
    calculate_signal_fingerprint,
    resolve_idempotency_key,
)


class IntegrationsMeshContractsTests(SimpleTestCase):
    def test_resolve_idempotency_key_prefers_explicit_key(self):
        result = resolve_idempotency_key(
            explicit_key='idem-explicit',
            event_id='evt-1',
            external_id='ext-1',
            message_id='msg-1',
            provider_reference='prov-1',
            fingerprint='fp-1',
        )

        self.assertEqual(result, 'idem-explicit')

    def test_resolve_idempotency_key_falls_back_in_documented_order(self):
        result = resolve_idempotency_key(
            event_id='evt-1',
            external_id='ext-1',
            message_id='msg-1',
            provider_reference='prov-1',
            fingerprint='fp-1',
        )

        self.assertEqual(result, 'evt-1')

    def test_build_idempotency_key_builds_deterministic_value(self):
        result = build_idempotency_key(
            namespace='octobox',
            action='checkout',
            primary_reference='pay_17',
            version_reference='4',
        )

        self.assertEqual(result, 'octobox_checkout_pay_17_v4')

    def test_calculate_signal_fingerprint_is_deterministic(self):
        payload = {'b': 2, 'a': 1}

        result_a = calculate_signal_fingerprint(payload)
        result_b = calculate_signal_fingerprint({'a': 1, 'b': 2})

        self.assertEqual(result_a, result_b)
