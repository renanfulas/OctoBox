"""
ARQUIVO: processador dedicado para votos de enquete do WhatsApp.

POR QUE ELE EXISTE:
- Isola a lógica de ORM, consultas e fuso horário do arquivo de serviços/fachada.
- Garante que a integração permaneça testável e modular.

O QUE ESTE ARQUIVO FAZ:
1. Recebe o contrato de dados (InboundPollVote).
2. Busca o aluno pelo telefone.
3. Busca a aula hoje no horário correspondente.
4. Registra ou atualiza o status de presença (Attendance).
"""

from datetime import datetime, time

from django.utils import timezone

from operations.model_definitions import Attendance, AttendanceStatus, ClassSession
from students.model_definitions import Student

from .models import WebhookEvent, WebhookDeliveryStatus
from .contracts import WhatsAppInboundPollVote, WhatsAppWebhookProcessingResult


def process_poll_vote_webhook(*, poll_vote: WhatsAppInboundPollVote) -> WhatsAppWebhookProcessingResult:
    """
    Processa um voto de enquete do WhatsApp para registrar presenca.
    Deduplicacao baseada no event_id da Evolution API.
    """
    # 0. Idempotencia (EPIC 8 / EPIC 12)
    event_id = getattr(poll_vote, 'event_id', None)
    if event_id:
        webhook_event, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={'provider': 'evolution', 'payload': {'poll_vote': str(poll_vote)}}
        )
        if not created and webhook_event.status == WebhookDeliveryStatus.PROCESSED:
            return WhatsAppWebhookProcessingResult(accepted=True, reason="Ignore: Evento ja processado (Idempotencia)")
    else:
        webhook_event = None

    # 1. Buscar Aluno pelo Telefone
    clean_phone = ''.join(filter(str.isdigit, poll_vote.phone))
    student = (
        Student.objects.filter(phone__icontains=clean_phone).first()
        or Student.objects.filter(whatsapp__icontains=clean_phone).first()
    )

    if not student:
        return WhatsAppWebhookProcessingResult(
            accepted=False, reason=f"Aluno nao encontrado para o telefone {poll_vote.phone}"
        )

    # 2. Parse Horário da Aula (ex: "18h" -> 18)
    try:
        hour_voted = int(poll_vote.option_voted.lower().replace('h', '').replace(':00', '').strip())
    except ValueError:
        return WhatsAppWebhookProcessingResult(
            accepted=False, reason=f"Formato de opcao de enquete invalido: {poll_vote.option_voted}"
        )

    # 3. Buscar Aula Hoje com esse Horário (Range imune a bugs de SQLite)
    today = timezone.now().date()
    start_time = timezone.make_aware(datetime.combine(today, time(hour=hour_voted, minute=0)))
    end_time = timezone.make_aware(datetime.combine(today, time(hour=hour_voted, minute=59, second=59)))

    session = ClassSession.objects.filter(scheduled_at__range=(start_time, end_time)).first()

    if not session:
        return WhatsAppWebhookProcessingResult(
            accepted=False, reason=f"Nenhuma aula agendada para hoje ({today}) as {hour_voted}h"
        )

    # 4. Registrar/Atualizar Presenca
    attendance, created = Attendance.objects.update_or_create(
        student=student,
        session=session,
        defaults={
            'status': AttendanceStatus.CHECKED_IN,
            'check_in_at': timezone.now(),
            'reservation_source': 'whatsapp_poll',
        },
    )

    reason = "Presenca criada via WhatsApp Poll" if created else "Presenca atualizada para Check-in via WhatsApp Poll"
    
    if webhook_event:
        webhook_event.status = WebhookDeliveryStatus.PROCESSED
        webhook_event.save(update_fields=['status'])

    return WhatsAppWebhookProcessingResult(accepted=True, reason=reason)
