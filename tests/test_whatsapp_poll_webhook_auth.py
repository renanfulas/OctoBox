"""Pure tests for signed WhatsApp poll webhook authentication and routing."""

import hashlib
import hmac
import json
import unittest

from integrations.whatsapp.webhook_auth import authenticate_poll_webhook


class WhatsAppPollWebhookAuthTests(unittest.TestCase):
    secret = 'per-box-test-key-with-32-bytes-minimum'
    timestamp = '1792752000'
    event_id = 'evt_opaque_123'
    retired_secret = 'per-box-retired-key-with-32-bytes-minimum'
    other_box_secret = 'other-box-test-key-with-32-bytes-minimum'
    config = json.dumps({
        'instance-opaque-1': {
            'schema': 'box_alpha',
            'keys': {'key-2026-10': secret, 'key-2026-09': retired_secret},
        },
        'instance-opaque-2': {
            'schema': 'box_bravo',
            'keys': {'key-2026-10': other_box_secret},
        },
    })

    def _headers(self, body: bytes, *, event_id=None, timestamp=None):
        signed_event_id = event_id or self.event_id
        signed_timestamp = timestamp or self.timestamp
        message = (
            b'v1\n'
                + b'instance-opaque-1\n'
                + b'key-2026-10\n'
            + signed_timestamp.encode('ascii')
            + b'\n'
            + signed_event_id.encode('utf-8')
            + b'\n'
            + body
        )
        signature = hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()
        return {
            'X-OctoBox-Instance': 'instance-opaque-1',
            'X-OctoBox-Timestamp': signed_timestamp,
            'X-OctoBox-Event-Id': signed_event_id,
            'X-OctoBox-Key-Id': 'key-2026-10',
            'X-OctoBox-Signature': f'v1={signature}',
        }

    def test_valid_signature_routes_only_to_configured_schema(self):
        body = json.dumps({'event_id': self.event_id, 'voter_phone': '+5511999999999'}).encode()

        route, failure = authenticate_poll_webhook(
            headers=self._headers(body),
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(failure)
        self.assertEqual(route.schema_name, 'box_alpha')
        self.assertEqual(route.event_id, self.event_id)
        self.assertEqual(route.payload['event_id'], self.event_id)

    def test_modified_body_is_rejected(self):
        signed_body = json.dumps({'event_id': self.event_id}).encode()
        altered_body = json.dumps({'event_id': self.event_id, 'voter_phone': 'changed'}).encode()

        route, failure = authenticate_poll_webhook(
            headers=self._headers(signed_body),
            raw_body=altered_body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'signature-mismatch')
        self.assertEqual(failure.http_status, 401)

    def test_old_timestamp_is_rejected(self):
        body = json.dumps({'event_id': self.event_id}).encode()
        old_timestamp = str(int(self.timestamp) - 301)

        route, failure = authenticate_poll_webhook(
            headers=self._headers(body, timestamp=old_timestamp),
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'timestamp-outside-window')

    def test_signature_is_bound_to_instance_and_key_id(self):
        body = json.dumps({'event_id': self.event_id}).encode()
        headers = self._headers(body)
        headers['X-OctoBox-Instance'] = 'instance-opaque-2'
        other_instance_route, other_instance_failure = authenticate_poll_webhook(
            headers=headers,
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        headers = self._headers(body)
        headers['X-OctoBox-Key-Id'] = 'key-2026-09'
        other_key_route, other_key_failure = authenticate_poll_webhook(
            headers=headers,
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(other_instance_route)
        self.assertEqual(other_instance_failure.code, 'signature-mismatch')
        self.assertIsNone(other_key_route)
        self.assertEqual(other_key_failure.code, 'signature-mismatch')

    def test_body_event_id_must_match_signed_header(self):
        body = json.dumps({'event_id': 'evt_different'}).encode()

        route, failure = authenticate_poll_webhook(
            headers=self._headers(body),
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'event-id-mismatch')
        self.assertEqual(failure.http_status, 400)

    def test_unknown_instance_and_invalid_configuration_fail_closed(self):
        body = json.dumps({'event_id': self.event_id}).encode()
        headers = self._headers(body)
        headers['X-OctoBox-Instance'] = 'not-configured'

        unknown_route, unknown_failure = authenticate_poll_webhook(
            headers=headers,
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )
        invalid_route, invalid_failure = authenticate_poll_webhook(
            headers=self._headers(body),
            raw_body=body,
            instances_json='{broken',
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(unknown_route)
        self.assertEqual(unknown_failure.http_status, 401)
        self.assertIsNone(invalid_route)
        self.assertEqual(invalid_failure.http_status, 503)

    def test_duplicate_instance_route_configuration_fails_closed(self):
        body = json.dumps({'event_id': self.event_id}).encode()
        duplicate_config = (
            '{"instance-opaque-1":{"schema":"box_alpha","keys":{"key-2026-10":"'
            + self.secret
            + '"}},"instance-opaque-1":{"schema":"box_bravo","keys":{"key-2026-10":"'
            + self.secret
            + '"}}}'
        )

        route, failure = authenticate_poll_webhook(
            headers=self._headers(body),
            raw_body=body,
            instances_json=duplicate_config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'webhook-route-config-invalid')
        self.assertEqual(failure.http_status, 503)

    def test_hmac_secret_cannot_be_reused_across_boxes_or_key_ids(self):
        body = json.dumps({'event_id': self.event_id}).encode()
        duplicate_box_config = json.dumps({
            'instance-opaque-1': {'schema': 'box_alpha', 'keys': {'active': self.secret}},
            'instance-opaque-2': {'schema': 'box_bravo', 'keys': {'active': self.secret}},
        })
        duplicate_key_config = json.dumps({
            'instance-opaque-1': {
                'schema': 'box_alpha',
                'keys': {'active': self.secret, 'retired': self.secret},
            },
        })

        for config in (duplicate_box_config, duplicate_key_config):
            with self.subTest(config=config):
                route, failure = authenticate_poll_webhook(
                    headers=self._headers(body),
                    raw_body=body,
                    instances_json=config,
                    now_epoch=int(self.timestamp),
                )

                self.assertIsNone(route)
                self.assertEqual(failure.code, 'webhook-route-config-invalid')
                self.assertEqual(failure.http_status, 503)

    def test_duplicate_body_event_id_is_rejected_after_valid_signature(self):
        body = (
            '{"event_id":"evt_other","event_id":"'
            + self.event_id
            + '"}'
        ).encode()

        route, failure = authenticate_poll_webhook(
            headers=self._headers(body),
            raw_body=body,
            instances_json=self.config,
            now_epoch=int(self.timestamp),
        )

        self.assertIsNone(route)
        self.assertEqual(failure.code, 'invalid-json')
        self.assertEqual(failure.http_status, 400)


if __name__ == '__main__':
    unittest.main()
