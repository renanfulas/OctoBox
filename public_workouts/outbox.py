"""Transactional outbox do Curva, drenada sem broker externo."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PublicWorkoutOutboxMessage, PublicWorkoutOutboxStatus


TOPIC_PROGRAM_READY = 'program_ready'
TOPIC_MEAL_PLAN_READY = 'meal_plan_ready'
TOPIC_WAITLIST_INVITE = 'waitlist_invite'
TOPIC_STAFF_NEW_SUBSCRIPTION = 'staff_new_subscription'
MAX_ATTEMPTS = 5
PROCESSING_LEASE_MINUTES = 10
logger = logging.getLogger(__name__)


def enqueue_outbox(*, topic: str, aggregate_type: str, aggregate_id, version: int, payload=None):
    key = f'{topic}:{aggregate_type}:{aggregate_id}:v{version}'
    message, _created = PublicWorkoutOutboxMessage.objects.get_or_create(
        idempotency_key=key,
        defaults={
            'topic': topic, 'aggregate_type': aggregate_type,
            'aggregate_id': str(aggregate_id), 'version': version,
            'payload': payload or {},
        },
    )
    return message


def _dispatch(message) -> bool:
    # TOPIC_STAFF_NEW_SUBSCRIPTION nao usa base_url (nao carrega link
    # magico) — checar a variavel so' pros topicos que precisam dela, pra
    # um alerta interno de staff nunca falhar por uma config que nao lhe
    # diz respeito.
    if message.topic == TOPIC_STAFF_NEW_SUBSCRIPTION:
        from .models import PublicWorkoutSubscriptionEvent
        from .notifications import notify_staff_new_subscription

        event = PublicWorkoutSubscriptionEvent.objects.select_related('subscription__account').get(
            pk=message.aggregate_id,
        )
        results = notify_staff_new_subscription(event.subscription, previous_status=event.from_status)
        # Sem rastreio por destinatario (diferente de PublicWorkoutProgramDelivery):
        # um sucesso parcial conta como entregue pra nao reenviar pra quem
        # ja recebeu a cada retry — so falha total (ou lista vazia de nada
        # a enviar, que tambem nao e falha) volta pra fila.
        return (not results) or any(status == 'sent' for status in results.values())

    from .notifications import notify_meal_plan_ready, notify_program_ready, notify_waitlist_invitation

    base_url = str(getattr(settings, 'PUBLIC_WORKOUT_PUBLIC_BASE_URL', '') or '').strip()
    if not base_url:
        raise RuntimeError('PUBLIC_WORKOUT_PUBLIC_BASE_URL nao configurada')
    if message.topic == TOPIC_PROGRAM_READY:
        from .models import PublicWorkoutProgram
        return notify_program_ready(
            PublicWorkoutProgram.objects.get(pk=message.aggregate_id), base_url=base_url,
        )
    if message.topic == TOPIC_MEAL_PLAN_READY:
        from .models import PublicWorkoutMealPlan
        return notify_meal_plan_ready(
            PublicWorkoutMealPlan.objects.get(pk=message.aggregate_id), base_url=base_url,
        )
    if message.topic == TOPIC_WAITLIST_INVITE:
        from .models import PublicWorkoutWaitlistEntry
        return notify_waitlist_invitation(
            PublicWorkoutWaitlistEntry.objects.get(pk=message.aggregate_id), base_url=base_url,
        )
    raise RuntimeError(f'topico de outbox desconhecido: {message.topic}')


def drain_public_workout_outbox(*, limit: int = 25) -> dict[str, int]:
    counters = {'sent': 0, 'retried': 0, 'dead': 0, 'recovered': 0}
    now = timezone.now()
    stale_before = now - timedelta(minutes=PROCESSING_LEASE_MINUTES)
    recovered = PublicWorkoutOutboxMessage.objects.filter(
        status=PublicWorkoutOutboxStatus.PROCESSING,
        processing_started_at__lt=stale_before,
    ).update(
        status=PublicWorkoutOutboxStatus.PENDING,
        processing_started_at=None,
        next_attempt_at=now,
        last_error='lease de processamento expirou; mensagem recuperada',
    )
    counters['recovered'] = recovered
    if recovered:
        logger.warning('curva_outbox_lease_recovered count=%s', recovered)
    ids = list(PublicWorkoutOutboxMessage.objects.filter(
        status=PublicWorkoutOutboxStatus.PENDING,
        next_attempt_at__lte=now,
    ).order_by('next_attempt_at').values_list('id', flat=True)[:limit])
    for message_id in ids:
        with transaction.atomic():
            message = PublicWorkoutOutboxMessage.objects.select_for_update(skip_locked=True).filter(
                pk=message_id, status=PublicWorkoutOutboxStatus.PENDING,
            ).first()
            if message is None:
                continue
            message.status = PublicWorkoutOutboxStatus.PROCESSING
            message.processing_started_at = timezone.now()
            message.attempt_count += 1
            message.save(update_fields=['status', 'processing_started_at', 'attempt_count', 'updated_at'])
        try:
            delivered = _dispatch(message)
            if not delivered:
                raise RuntimeError('gateway nao confirmou a entrega')
        except Exception as exc:
            message.refresh_from_db()
            message.last_error = str(exc)[:255]
            message.processing_started_at = None
            if message.attempt_count >= MAX_ATTEMPTS:
                message.status = PublicWorkoutOutboxStatus.DEAD
                counters['dead'] += 1
            else:
                message.status = PublicWorkoutOutboxStatus.PENDING
                message.next_attempt_at = timezone.now() + timedelta(minutes=2 ** message.attempt_count)
                counters['retried'] += 1
            message.save(update_fields=[
                'status', 'processing_started_at', 'next_attempt_at', 'last_error', 'updated_at',
            ])
            logger.warning(
                'curva_outbox_delivery_failed message_id=%s topic=%s attempts=%s status=%s error_type=%s',
                message.pk, message.topic, message.attempt_count, message.status, type(exc).__name__,
            )
        else:
            message.status = PublicWorkoutOutboxStatus.SENT
            message.processing_started_at = None
            message.processed_at = timezone.now()
            message.last_error = ''
            message.save(update_fields=[
                'status', 'processing_started_at', 'processed_at', 'last_error', 'updated_at',
            ])
            counters['sent'] += 1
            logger.info(
                'curva_outbox_delivery_sent message_id=%s topic=%s attempts=%s',
                message.pk, message.topic, message.attempt_count,
            )
    if any(counters.values()):
        logger.info('curva_outbox_drain_summary counters=%s', counters)
    return counters


__all__ = ['drain_public_workout_outbox', 'enqueue_outbox']
