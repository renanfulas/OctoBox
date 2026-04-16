"""
ARQUIVO: processador dedicado para votos de enquete do WhatsApp.

POR QUE ELE EXISTE:
- isola a logica de ORM, consultas e fuso horario do arquivo de servicos/fachada.
- garante que a integracao permaneca testavel e modular.

O QUE ESTE ARQUIVO FAZ:
1. recebe o contrato de dados (`WhatsAppInboundPollVote`)
2. busca o aluno pelo telefone
3. busca a aula de hoje no horario correspondente
4. registra ou atualiza o status de presenca (`Attendance`)
"""

from datetime import datetime, time

from django.utils import timezone

from integrations.mesh import (
    classify_duplicate,
    classify_invalid_payload,
    classify_non_retryable,
    classify_retryable,
    decide_retry,
)
from operations.model_definitions import Attendance, AttendanceStatus, ClassSession
from students.model_definitions import Student

from .contracts import WhatsAppInboundPollVote, WhatsAppWebhookProcessingResult
from .models import WebhookDeliveryStatus, WebhookEvent


def _build_webhook_event_payload(*, poll_vote: WhatsAppInboundPollVote) -> dict:
    raw_payload = poll_vote.raw_payload or {}
    if raw_payload:
        normalized_payload = raw_payload
    else:
        normalized_payload = {
            'voter_phone': poll_vote.phone,
            'poll_name': poll_vote.poll_title,
            'option_text': poll_vote.option_voted,
            'event_id': poll_vote.event_id or poll_vote.external_id,
        }
    return {
        'kind': 'poll_vote',
        'raw_payload': normalized_payload,
    }


def _decision_to_result(
    *,
    accepted: bool,
    reason: str,
    failure_kind: str,
    retryable: bool,
    webhook_event: WebhookEvent | None,
    retry_reason: str,
) -> WhatsAppWebhookProcessingResult:
    if webhook_event:
        decision = webhook_event.register_failure(
            failure_kind=failure_kind,
            error_message=reason,
            reason=retry_reason,
        )
    else:
        decision = decide_retry(
            failure_kind=failure_kind,
            attempts=0,
            max_attempts=1,
            reason=retry_reason,
        )

    return WhatsAppWebhookProcessingResult(
        accepted=accepted,
        reason=reason,
        failure_kind=failure_kind,
        retryable=decision.should_retry if failure_kind == 'retryable' else retryable,
        retry_action=decision.action,
        attempt_number=decision.attempt_number,
        max_attempts=decision.max_attempts,
        next_retry_at=decision.next_retry_at.isoformat() if decision.next_retry_at else '',
    )


def process_poll_vote_webhook(*, poll_vote: WhatsAppInboundPollVote) -> WhatsAppWebhookProcessingResult:
    """
    Processa um voto de enquete do WhatsApp para registrar presenca.
    Deduplicacao baseada no event_id da Evolution API.
    """

    event_id = getattr(poll_vote, 'event_id', '') or getattr(poll_vote, 'external_id', '')
    if event_id:
        webhook_event, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={'provider': 'evolution', 'payload': _build_webhook_event_payload(poll_vote=poll_vote)},
        )
        if not created and webhook_event.status == WebhookDeliveryStatus.PROCESSED:
            failure = classify_duplicate(reason='duplicate-event')
            decision = decide_retry(
                failure_kind=failure.kind,
                attempts=webhook_event.attempts,
                max_attempts=webhook_event.max_retries,
                reason=failure.reason,
            )
            return WhatsAppWebhookProcessingResult(
                accepted=True,
                reason='Ignore: Evento ja processado (Idempotencia)',
                failure_kind=failure.kind,
                retryable=failure.retryable,
                retry_action=decision.action,
                attempt_number=decision.attempt_number,
                max_attempts=decision.max_attempts,
                next_retry_at=decision.next_retry_at.isoformat() if decision.next_retry_at else '',
            )
    else:
        webhook_event = None

    try:
        clean_phone = ''.join(filter(str.isdigit, poll_vote.phone))
        student = (
            Student.objects.filter(phone__icontains=clean_phone).first()
            or Student.objects.filter(whatsapp__icontains=clean_phone).first()
        )

        if not student:
            failure = classify_non_retryable(reason='student-not-found')
            return _decision_to_result(
                accepted=False,
                reason=f'Aluno nao encontrado para o telefone {poll_vote.phone}',
                failure_kind=failure.kind,
                retryable=failure.retryable,
                webhook_event=webhook_event,
                retry_reason=failure.reason,
            )

        try:
            hour_voted = int(poll_vote.option_voted.lower().replace('h', '').replace(':00', '').strip())
        except ValueError:
            failure = classify_invalid_payload(reason='invalid-poll-option')
            return _decision_to_result(
                accepted=False,
                reason=f'Formato de opcao de enquete invalido: {poll_vote.option_voted}',
                failure_kind=failure.kind,
                retryable=failure.retryable,
                webhook_event=webhook_event,
                retry_reason=failure.reason,
            )

        today = timezone.now().date()
        start_time = timezone.make_aware(datetime.combine(today, time(hour=hour_voted, minute=0)))
        end_time = timezone.make_aware(datetime.combine(today, time(hour=hour_voted, minute=59, second=59)))

        session = ClassSession.objects.filter(scheduled_at__range=(start_time, end_time)).first()
        if not session:
            failure = classify_non_retryable(reason='session-not-found')
            return _decision_to_result(
                accepted=False,
                reason=f'Nenhuma aula agendada para hoje ({today}) as {hour_voted}h',
                failure_kind=failure.kind,
                retryable=failure.retryable,
                webhook_event=webhook_event,
                retry_reason=failure.reason,
            )

        _, created = Attendance.objects.update_or_create(
            student=student,
            session=session,
            defaults={
                'status': AttendanceStatus.CHECKED_IN,
                'check_in_at': timezone.now(),
                'reservation_source': 'whatsapp_poll',
            },
        )

        if webhook_event:
            webhook_event.mark_processed()

        reason = (
            'Presenca criada via WhatsApp Poll'
            if created
            else 'Presenca atualizada para Check-in via WhatsApp Poll'
        )
        return WhatsAppWebhookProcessingResult(accepted=True, reason=reason)
    except Exception as exc:
        failure = classify_retryable(reason=exc.__class__.__name__.lower())
        return _decision_to_result(
            accepted=False,
            reason=str(exc),
            failure_kind=failure.kind,
            retryable=failure.retryable,
            webhook_event=webhook_event,
            retry_reason=failure.reason,
        )
