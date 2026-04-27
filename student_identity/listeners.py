"""
ARQUIVO: listeners de signals externos para o dominio student_identity.

POR QUE ELE EXISTE:
- conecta signals emitidos por outros apps (operations, finance) a acoes de notificacao de alunos.
- mantém a fronteira clara: operations nao conhece student_identity; student_identity ouve sem criar dependencia circular.

O QUE ESTE ARQUIVO FAZ:
1. registra listener para o signal student_session_cancelled emitido por operations.
2. delega a composicao do payload para push_messages.session_cancelled.
3. delega a entrega para push_notifications.send_student_web_push_notification.

PONTOS CRITICOS:
- importacoes de operations feitas localmente para evitar import circular no setup do Django.
- falha de push e auditada e silenciosa; nao propaga excecao para o signal sender.
- push_sent_count no SessionCancellationEvent e atualizado apos entrega.
"""

from __future__ import annotations


def _on_session_cancelled(*, sender, session, box_root_slug, copy_variant, attendance_count, scheduled_at, cancellation_event, **kwargs):
    from student_identity.models import StudentPushSubscription
    from student_identity.push_messages.session_cancelled import build_session_cancelled_payload
    from student_identity.push_notifications import send_student_web_push_notification

    from operations.model_definitions import Attendance

    student_ids = list(
        Attendance.objects.filter(
            session_id=session.pk,
            status__in=['booked', 'checked_in'],
        ).values_list('student_id', flat=True)
    )

    if not student_ids:
        return

    subscriptions = StudentPushSubscription.objects.filter(
        identity__student_id__in=student_ids,
        box_root_slug=box_root_slug,
        revoked_at__isnull=True,
    ).select_related('identity__student')

    session_time_label = ''
    if scheduled_at and hasattr(scheduled_at, 'strftime'):
        session_time_label = scheduled_at.strftime('%d/%m %H:%M')

    payload = build_session_cancelled_payload(
        session_id=session.pk,
        session_title=getattr(session, 'title', '') or '',
        session_time_label=session_time_label,
        copy_variant=copy_variant,
    )

    sent = 0
    for sub in subscriptions:
        ok = send_student_web_push_notification(
            subscription=sub,
            title=payload.title,
            body=payload.body,
            url=payload.url,
            tag=payload.tag,
        )
        if ok:
            sent += 1

    if sent:
        from operations.model_definitions import SessionCancellationEvent
        SessionCancellationEvent.objects.filter(pk=cancellation_event.pk).update(push_sent_count=sent)


def connect_student_identity_listeners():
    """Chamado por StudentIdentityConfig.ready()."""
    from operations.signals.session_cancellation import student_session_cancelled
    student_session_cancelled.connect(_on_session_cancelled, weak=False)


__all__ = ['connect_student_identity_listeners']
