"""Synthetic contract tests for the disabled Evolution JWT-to-HMAC bridge primitives."""

import base64
import hashlib
import hmac
import json
import unittest

from integrations.whatsapp.evolution_bridge import (
    authenticate_evolution_callback,
    sign_normalized_poll_payload,
)
from integrations.whatsapp.webhook_auth import authenticate_poll_webhook


def _segment(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def _jwt(secret, *, now=1_792_752_000, header=None, claims=None):
    jwt_header = {'alg': 'HS256', 'typ': 'JWT'}
    jwt_claims = {
        'iat': now,
        'exp': now + 600,
        'app': 'evolution',
        'action': 'webhook',
    }
    jwt_header.update(header or {})
    jwt_claims.update(claims or {})
    signing_input = f'{_segment(json.dumps(jwt_header, separators=(",", ":")).encode())}.{_segment(json.dumps(jwt_claims, separators=(",", ":")).encode())}'
    signature = hmac.new(secret.encode(), signing_input.encode('ascii'), hashlib.sha256).digest()
    return f'{signing_input}.{_segment(signature)}'


def _jwt_with_raw_json(secret, header_json, claims_json):
    signing_input = f'{_segment(header_json.encode())}.{_segment(claims_json.encode())}'
    signature = hmac.new(secret.encode(), signing_input.encode('ascii'), hashlib.sha256).digest()
    return f'{signing_input}.{_segment(signature)}'


class EvolutionBridgeTests(unittest.TestCase):
    now = 1_792_752_000
    jwt_secret_a = 'evolution-jwt-secret-alpha-32-bytes-minimum'
    hmac_secret_a = 'octobox-hmac-secret-alpha-32-bytes-minimum'
    jwt_secret_b = 'evolution-jwt-secret-bravo-32-bytes-minimum'
    hmac_secret_b = 'octobox-hmac-secret-bravo-32-bytes-minimum'

    def setUp(self):
        self.config = json.dumps({
            'instance-alpha': {
                'schema': 'box_alpha',
                'evolution_jwt_secret': self.jwt_secret_a,
                'active_hmac_key_id': 'hmac-2026-10',
                'keys': {'hmac-2026-10': self.hmac_secret_a},
            },
            'instance-bravo': {
                'schema': 'box_bravo',
                'evolution_jwt_secret': self.jwt_secret_b,
                'active_hmac_key_id': 'hmac-2026-10',
                'keys': {'hmac-2026-10': self.hmac_secret_b},
            },
        })

    def _auth(self, *, instance='instance-alpha', secret=None, token=None, config=None):
        return authenticate_evolution_callback(
            headers={
                'X-OctoBox-Instance': instance,
                'Authorization': f'Bearer {token or _jwt(secret or self.jwt_secret_a, now=self.now)}',
            },
            instances_json=config or self.config,
            now_epoch=self.now,
        )

    def test_valid_jwt_resolves_only_the_configured_instance(self):
        route, failure = self._auth()

        self.assertIsNone(failure)
        self.assertEqual(route.schema_name, 'box_alpha')
        self.assertEqual(route.key_id, 'hmac-2026-10')
        self.assertNotIn(self.jwt_secret_a, repr(route))
        self.assertNotIn(self.hmac_secret_a, repr(route))

    def test_jwt_signed_for_other_instance_cannot_route_cross_tenant(self):
        route, failure = self._auth(instance='instance-bravo', secret=self.jwt_secret_a)

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'evolution-jwt-signature-mismatch')

    def test_expired_future_and_long_lived_tokens_are_rejected(self):
        cases = (
            (_jwt(self.jwt_secret_a, now=self.now, claims={'exp': self.now}), 'evolution-jwt-expired'),
            (_jwt(self.jwt_secret_a, now=self.now, claims={'iat': self.now + 61}), 'evolution-jwt-issued-in-future'),
            (_jwt(self.jwt_secret_a, now=self.now, claims={'exp': self.now + 601}), 'evolution-jwt-lifetime-too-long'),
        )
        for token, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                route, failure = self._auth(token=token)
                self.assertIsNone(route)
                self.assertEqual(failure.code, expected_code)

    def test_wrong_purpose_and_non_hs256_tokens_are_rejected(self):
        wrong_action = self._auth(token=_jwt(
            self.jwt_secret_a,
            now=self.now,
            claims={'action': 'api'},
        ))
        wrong_algorithm = self._auth(token=_jwt(
            self.jwt_secret_a,
            now=self.now,
            header={'alg': 'none'},
        ))

        self.assertEqual(wrong_action[1].code, 'invalid-evolution-jwt-purpose')
        self.assertEqual(wrong_algorithm[1].code, 'invalid-evolution-jwt')

    def test_duplicate_json_keys_in_jwt_header_or_claims_are_rejected(self):
        header = _jwt_with_raw_json(
            self.jwt_secret_a,
            '{"alg":"none","alg":"HS256","typ":"JWT"}',
            json.dumps({
                'iat': self.now,
                'exp': self.now + 600,
                'app': 'evolution',
                'action': 'webhook',
            }, separators=(',', ':')),
        )
        claims = _jwt_with_raw_json(
            self.jwt_secret_a,
            json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')),
            '{"iat":' + str(self.now)
            + ',"exp":' + str(self.now + 600)
            + ',"exp":' + str(self.now + 600)
            + ',"app":"evolution","action":"webhook"}',
        )

        _, header_failure = self._auth(token=header)
        _, claims_failure = self._auth(token=claims)

        self.assertEqual(header_failure.code, 'invalid-evolution-jwt')
        self.assertEqual(claims_failure.code, 'invalid-evolution-jwt')

    def test_jwt_and_receiver_hmac_secrets_must_be_distinct(self):
        config = json.loads(self.config)
        config['instance-alpha']['keys']['retired-key'] = self.jwt_secret_a

        route, failure = self._auth(config=json.dumps(config))

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'webhook-secrets-must-be-distinct')

    def test_duplicate_instance_route_configuration_fails_closed(self):
        duplicate_config = (
            '{"instance-alpha":{"schema":"box_alpha","evolution_jwt_secret":"'
            + self.jwt_secret_a
            + '","active_hmac_key_id":"hmac-2026-10","keys":{"hmac-2026-10":"'
            + self.hmac_secret_a
            + '"}},"instance-alpha":{"schema":"box_bravo","evolution_jwt_secret":"'
            + self.jwt_secret_a
            + '","active_hmac_key_id":"hmac-2026-10","keys":{"hmac-2026-10":"'
            + self.hmac_secret_a
            + '"}}}'
        )

        route, failure = self._auth(config=duplicate_config)

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'webhook-route-config-invalid')
        self.assertEqual(failure.http_status, 503)

    def test_evolution_and_hmac_secrets_cannot_be_reused_across_instances(self):
        config = json.loads(self.config)
        config['instance-bravo']['keys']['hmac-2026-10'] = self.hmac_secret_a

        route, failure = self._auth(config=json.dumps(config))

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'webhook-route-config-invalid')
        self.assertEqual(failure.http_status, 503)

    def test_signed_normalized_payload_roundtrips_through_existing_receiver(self):
        route, failure = self._auth()
        self.assertIsNone(failure)
        payload = {
            'event_id': 'evolution:instance-alpha:vote-opaque-123',
            'voter_phone': '+5511999999999',
            'poll_name': 'Check-in 23/10',
            'option_text': '18h',
        }

        raw_body, headers, sign_failure = sign_normalized_poll_payload(
            route=route,
            payload=payload,
            now_epoch=self.now,
        )
        receiver_route, receiver_failure = authenticate_poll_webhook(
            headers=headers,
            raw_body=raw_body,
            instances_json=json.dumps({
                'instance-alpha': {
                    'schema': 'box_alpha',
                    'keys': {'hmac-2026-10': self.hmac_secret_a},
                },
            }),
            now_epoch=self.now,
        )

        self.assertIsNone(sign_failure)
        self.assertIsNone(receiver_failure)
        self.assertEqual(receiver_route.payload, payload)
        self.assertEqual(receiver_route.schema_name, 'box_alpha')

    def test_signer_requires_stable_event_id_and_rejects_non_json_payload(self):
        route, failure = self._auth()
        self.assertIsNone(failure)

        _, _, missing_id = sign_normalized_poll_payload(route=route, payload={'poll_name': 'x'}, now_epoch=self.now)
        _, _, invalid_json = sign_normalized_poll_payload(
            route=route,
            payload={'event_id': 'evt-1', 'value': float('nan')},
            now_epoch=self.now,
        )

        self.assertEqual(missing_id.code, 'stable-event-id-required')
        self.assertEqual(invalid_json.code, 'normalized-payload-invalid')


if __name__ == '__main__':
    unittest.main()
