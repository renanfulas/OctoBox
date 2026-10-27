from __future__ import annotations

import json
from unittest.mock import Mock, patch

from django.http import HttpResponseForbidden
from django.test import SimpleTestCase
from django_tenants.utils import schema_context

from shared_support.event_stream_tenants import current_event_tenant_schema
from shared_support.manager_event_stream import (
    build_manager_event_channel,
    build_manager_event_stream,
    publish_manager_stream_event,
)
from shared_support.student_event_stream import (
    build_student_event_channel,
    build_student_event_stream,
    publish_student_stream_event,
)


class TenantScopedEventStreamTests(SimpleTestCase):
    def test_active_schema_context_is_the_tenant_source_and_public_is_rejected(self):
        with schema_context('box_alpha'):
            self.assertEqual(current_event_tenant_schema(), 'box_alpha')
        with schema_context('public'):
            self.assertIsNone(current_event_tenant_schema())

    def test_same_student_id_uses_different_channels_per_box(self):
        with patch('shared_support.student_event_stream.current_event_tenant_schema', return_value='box_alpha'):
            alpha_channel = build_student_event_channel(42)
        with patch('shared_support.student_event_stream.current_event_tenant_schema', return_value='box_bravo'):
            bravo_channel = build_student_event_channel(42)

        self.assertEqual(alpha_channel, 'octobox:tenant:box_alpha:student:42:events')
        self.assertEqual(bravo_channel, 'octobox:tenant:box_bravo:student:42:events')
        self.assertNotEqual(alpha_channel, bravo_channel)

    def test_manager_channel_is_box_scoped(self):
        self.assertEqual(
            build_manager_event_channel(schema_name='box_alpha'),
            'octobox:tenant:box_alpha:operations:manager:events',
        )
        self.assertNotEqual(
            build_manager_event_channel(schema_name='box_alpha'),
            build_manager_event_channel(schema_name='box_bravo'),
        )

    def test_publishers_send_only_to_the_active_box_channel(self):
        redis = Mock()
        with (
            patch('shared_support.student_event_stream.current_event_tenant_schema', return_value='box_alpha'),
            patch('shared_support.student_event_stream.get_redis_client', return_value=redis),
        ):
            publish_student_stream_event(student_id=42, event_type='student.lock.acquired')
        self.assertEqual(redis.publish.call_args.args[0], 'octobox:tenant:box_alpha:student:42:events')
        self.assertEqual(json.loads(redis.publish.call_args.args[1])['student_id'], 42)

        redis.reset_mock()
        with (
            patch('shared_support.manager_event_stream.current_event_tenant_schema', return_value='box_bravo'),
            patch('shared_support.manager_event_stream.get_redis_client', return_value=redis),
        ):
            publish_manager_stream_event(event_type='student.payment.updated', meta={'student_id': 42})
        self.assertEqual(redis.publish.call_args.args[0], 'octobox:tenant:box_bravo:operations:manager:events')

    def test_publishers_fail_closed_without_a_box_context(self):
        redis = Mock()
        with (
            patch('shared_support.student_event_stream.current_event_tenant_schema', return_value=None),
            patch('shared_support.student_event_stream.get_redis_client', return_value=redis),
            self.assertLogs('shared_support.student_event_stream', level='WARNING'),
        ):
            publish_student_stream_event(student_id=42, event_type='student.lock.acquired')
        with (
            patch('shared_support.manager_event_stream.current_event_tenant_schema', return_value='public'),
            patch('shared_support.manager_event_stream.get_redis_client', return_value=redis),
            self.assertLogs('shared_support.manager_event_stream', level='WARNING'),
        ):
            publish_manager_stream_event(event_type='student.payment.updated')
        redis.publish.assert_not_called()

    def test_streams_require_tenant_context(self):
        with patch('shared_support.student_event_stream.current_event_tenant_schema', return_value=None):
            student_response = build_student_event_stream(student_id=42)
        with patch('shared_support.manager_event_stream.current_event_tenant_schema', return_value='public'):
            manager_response = build_manager_event_stream()

        self.assertIsInstance(student_response, HttpResponseForbidden)
        self.assertIsInstance(manager_response, HttpResponseForbidden)

    def test_stream_captures_box_channel_before_iterator_runs(self):
        redis = Mock()
        pubsub = Mock()
        redis.pubsub.return_value = pubsub
        pubsub.get_message.return_value = None

        with (
            patch('shared_support.manager_event_stream.current_event_tenant_schema', return_value='box_alpha'),
            patch('shared_support.manager_event_stream.get_redis_client', return_value=redis),
            patch('shared_support.manager_event_stream.inc_manager_sse_active_streams'),
            patch('shared_support.manager_event_stream.record_manager_sse_stream_connection'),
        ):
            response = build_manager_event_stream()
            with patch('shared_support.manager_event_stream.current_event_tenant_schema', return_value=None):
                iterator = iter(response.streaming_content)
                next(iterator)
        pubsub.subscribe.assert_called_once_with('octobox:tenant:box_alpha:operations:manager:events')
        response.close()

    def test_student_stream_captures_box_channel_before_iterator_runs(self):
        redis = Mock()
        pubsub = Mock()
        redis.pubsub.return_value = pubsub
        pubsub.get_message.return_value = None

        with (
            patch('shared_support.student_event_stream.current_event_tenant_schema', return_value='box_bravo'),
            patch('shared_support.student_event_stream.get_redis_client', return_value=redis),
            patch('shared_support.student_event_stream.inc_student_sse_active_streams'),
            patch('shared_support.student_event_stream.record_student_sse_stream_connection'),
        ):
            response = build_student_event_stream(student_id=42)
            with patch('shared_support.student_event_stream.current_event_tenant_schema', return_value=None):
                iterator = iter(response.streaming_content)
                next(iterator)
        pubsub.subscribe.assert_called_once_with('octobox:tenant:box_bravo:student:42:events')
        response.close()
