"""
ARQUIVO: barramento SSE/PubSub dos eventos criticos da ficha do aluno.

POR QUE ELE EXISTE:
- centraliza o contrato de eventos em tempo real do drawer do aluno.
- usa Redis Pub/Sub como trilho quente e SSE como entrega ao navegador.

O QUE ESTE ARQUIVO FAZ:
1. Define canais por aluno para eventos criticos.
2. Publica payloads minimos e autoritativos no Redis.
3. Abre stream SSE para o frontend ouvir mudancas criticas.

PONTOS CRITICOS:
- evento nao substitui a verdade oficial; ele so aciona refresh de snapshot/fragments.
- se Redis falhar, o frontend degrada para polling sem quebrar o produto.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from django.http import StreamingHttpResponse
from django.utils import timezone

from monitoring.student_realtime_metrics import (
    dec_student_sse_active_streams,
    inc_student_sse_active_streams,
    record_student_sse_event_published,
    record_student_sse_stream_connection,
)
from shared_support.events import get_redis_client
from shared_support.student_snapshot_versions import serialize_version_value

logger = logging.getLogger(__name__)

SSE_RETRY_MS = 5000
SSE_KEEPALIVE_SECONDS = 15


def build_student_event_channel(student_id: int) -> str:
    return f'octobox:student:{student_id}:events'


def publish_student_stream_event(*, student_id: int, event_type: str, meta=None, snapshot_version=None, profile_version=None) -> None:
    """
    Publica um evento critico do aluno no Redis Pub/Sub.

    O payload e pequeno de proposito: o browser recebe o alerta e entao
    busca o snapshot/fragments oficiais no backend.
    """

    payload = {
        'event_id': uuid.uuid4().hex,
        'type': event_type,
        'student_id': int(student_id),
        'emitted_at': timezone.now().isoformat(),
        'snapshot_version': serialize_version_value(snapshot_version),
        'profile_version': serialize_version_value(profile_version),
        'meta': meta or {},
    }

    try:
        redis_conn = get_redis_client()
        redis_conn.publish(build_student_event_channel(student_id), json.dumps(payload))
        record_student_sse_event_published(event_type)
    except Exception as exc:
        logger.warning('student_event_stream: falha ao publicar evento %s do aluno %s: %s', event_type, student_id, exc)


def build_student_event_stream(*, student_id: int):
    """
    Gera um stream SSE ligado ao canal do aluno.

    Mantemos keepalive periodico para evitar timeout silencioso de proxy/cliente.
    """

    channel = build_student_event_channel(student_id)

    def event_iterator():
        try:
            redis_conn = get_redis_client()
            pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(channel)
            record_student_sse_stream_connection('opened')
            inc_student_sse_active_streams()
        except Exception as exc:
            record_student_sse_stream_connection('redis_error')
            logger.warning('student_event_stream: Redis indisponivel para stream do aluno %s: %s', student_id, exc)
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

                    event_type = payload.get('type') or 'student.event'
                    yield f'event: {event_type}\n'
                    yield f'data: {json.dumps(payload)}\n\n'
                    continue

                yield f': keepalive {int(time.time())}\n\n'
        finally:
            try:
                pubsub.close()
            except Exception:
                pass
            dec_student_sse_active_streams()
            record_student_sse_stream_connection('closed')

    response = StreamingHttpResponse(event_iterator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


__all__ = [
    'build_student_event_channel',
    'build_student_event_stream',
    'publish_student_stream_event',
]
