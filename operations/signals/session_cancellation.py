"""
ARQUIVO: gatilho canonico de cancelamento de sessao.

POR QUE ELE EXISTE:
- centraliza a deteccao de transicao scheduled/open/completed → canceled em um unico ponto.
- cria SessionCancellationEvent como fato imutavel apos a transicao persistida.
- emite o signal Django student_session_cancelled para que consumidores (push, banner) reajam independentemente.

O QUE ESTE ARQUIVO FAZ:
1. pre_save: captura status anterior no atributo _prev_status do instance.
2. post_save: aplica regra de dominio puro; se deve notificar, cria evento em on_commit e emite signal.
3. nao conhece pywebpush, nao conhece templates, nao conhece o consumidor.

PONTOS CRITICOS:
- o evento e criado em transaction.on_commit() para evitar criacao em rollback.
- UniqueConstraint em session_id previne double-fire em retries.
- o numero de presenças ativas e calculado aqui, antes do save, enquanto o estado ainda e consistente.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver
from django.utils import timezone

from operations.domain.session_cancellation_rules import (
    LAST_MINUTE_THRESHOLD_MINUTES,
    build_cancellation_decision,
)

# Signal publico consumido por push (Onda 3) e potencialmente outros listeners.
# kwargs: session, box_root_slug, copy_variant, attendance_count, scheduled_at
student_session_cancelled = Signal()


def _register(sender):
    """Conecta os hooks de pre_save e post_save ao model ClassSession."""

    @receiver(pre_save, sender=sender, weak=False)
    def _capture_previous_status(instance, **kwargs):
        if instance.pk:
            try:
                instance._prev_status = sender.objects.values_list('status', flat=True).get(pk=instance.pk)
            except sender.DoesNotExist:
                instance._prev_status = None
        else:
            instance._prev_status = None

    @receiver(post_save, sender=sender, weak=False)
    def _handle_session_saved(instance, created, **kwargs):
        prev_status = getattr(instance, '_prev_status', None) or ''
        new_status = instance.status

        active_statuses = ['booked', 'checked_in']
        attendance_qs = instance.attendances.filter(status__in=active_statuses)
        attendance_count = attendance_qs.count()
        had_checkin = attendance_qs.filter(status='checked_in').exists()

        now = timezone.now()
        session_time = getattr(instance, 'scheduled_at', now)
        lead_minutes = max(0, int((session_time - now).total_seconds() / 60))

        decision = build_cancellation_decision(
            prev_status=prev_status,
            new_status=new_status,
            attendance_count_active=attendance_count,
            cancel_lead_minutes=lead_minutes,
            had_checked_in_attendance=had_checkin,
        )

        if not decision.should_notify:
            return

        session_id = instance.pk
        copy_variant = decision.copy_variant
        box_root_slug = getattr(instance, 'box_root_slug', '') or ''
        session_title = getattr(instance, 'title', '') or ''

        def _commit():
            from operations.model_definitions import SessionCancellationEvent

            event, created_evt = SessionCancellationEvent.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'box_root_slug': box_root_slug,
                    'copy_variant': copy_variant,
                    'attendance_count_at_cancel': attendance_count,
                    'scheduled_at': session_time,
                    'session_title': session_title,
                },
            )
            if created_evt:
                student_session_cancelled.send(
                    sender=sender,
                    session=instance,
                    box_root_slug=box_root_slug,
                    copy_variant=copy_variant,
                    attendance_count=attendance_count,
                    scheduled_at=session_time,
                    cancellation_event=event,
                )

        transaction.on_commit(_commit)


def connect_session_cancellation_signal():
    """Chamado por OperationsConfig.ready() para registrar os hooks."""
    from operations.model_definitions import ClassSession
    _register(ClassSession)


__all__ = [
    'connect_session_cancellation_signal',
    'student_session_cancelled',
]
