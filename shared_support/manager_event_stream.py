"""
ARQUIVO: barramento SSE/PubSub dos eventos criticos do workspace do manager.

POR QUE ELE EXISTE:
- centraliza o contrato realtime nativo dos quatro boards do manager.
- usa Redis Pub/Sub como trilho quente e SSE como entrega ao navegador.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from django.http import StreamingHttpResponse
from django.utils import timezone

from monitoring.manager_realtime_metrics import (
    dec_manager_sse_active_streams,
    inc_manager_sse_active_streams,
    record_manager_sse_event_published,
    record_manager_sse_stream_connection,
)
from shared_support.events import get_redis_client

logger = logging.getLogger(__name__)

SSE_RETRY_MS = 5000
SSE_KEEPALIVE_SECONDS = 15
MANAGER_EVENT_CHANNEL = 'octobox:operations:manager:events'


def publish_manager_stream_event(*, event_type: str, meta=None) -> None:
    payload = {
        'event_id': uuid.uuid4().hex,
        'type': event_type,
        'emitted_at': timezone.now().isoformat(),
        'meta': meta or {},
    }
    try:
        redis_conn = get_redis_client()
        redis_conn.publish(MANAGER_EVENT_CHANNEL, json.dumps(payload))
        record_manager_sse_event_published(event_type)
    except Exception as exc:
        logger.warning('manager_event_stream: falha ao publicar evento %s: %s', event_type, exc)


def build_manager_event_stream():
    def event_iterator():
        try:
            redis_conn = get_redis_client()
            pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(MANAGER_EVENT_CHANNEL)
            record_manager_sse_stream_connection('opened')
            inc_manager_sse_active_streams()
        except Exception as exc:
            record_manager_sse_stream_connection('redis_error')
            logger.warning('manager_event_stream: Redis indisponivel: %s', exc)
            yield f'retry: {SSE_RETRY_MS}\n'
            yield 'event: stream.error\n'
            yield 'data: {"status":"redis_unavailable"}\n\n'
            return

        try:
            yield f'retry: {SSE_RETRY_MS}\n'
            yield 'event: stream.ready\n'
            yield 'data: {"status":"connected"}\n\n'

            while True:
                message = pubsub.get_message(timeout=SSE_KEEPALIVE_SECONDS)
                if message and message.get('type') == 'message':
                    raw_data = message.get('data')
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode('utf-8')
                    try:
                        payload = json.loads(raw_data)
                    except (TypeError, ValueError):
                        continue

                    event_type = payload.get('type') or 'manager.event'
                    yield f'event: {event_type}\n'
                    yield f'data: {json.dumps(payload)}\n\n'
                    continue

                yield f': keepalive {int(time.time())}\n\n'
        finally:
            try:
                pubsub.close()
            except Exception:
                pass
            dec_manager_sse_active_streams()
            record_manager_sse_stream_connection('closed')

    response = StreamingHttpResponse(event_iterator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


__all__ = [
    'build_manager_event_stream',
    'publish_manager_stream_event',
]
