"""
ARQUIVO: lembrete de confirmacao de check-in de parceiro (Wellhub/TotalPass).

POR QUE ELE EXISTE:
- Alunos de parceiro precisam confirmar presenca no app da propria operadora
  (Wellhub/TotalPass) para o box receber por aquele acesso. Ninguem no OctoBox
  pode fazer essa confirmacao por eles (ver PONTOS CRITICOS) — o que da para
  fazer e lembrar o aluno na hora certa, com o minimo de fricção.

O QUE ELE FAZ:
1. Cria o PartnerCheckInCharge (ledger pendente) quando o Attendance de um
   aluno de parceiro recebe check_in_at.
2. Decide quando um lembrete e devido (0min / 10min / 30min apos o horario
   da aula), em funcao de quantos ja foram enviados.
3. Envia o lembrete (hoje: e-mail com deep link pro app do parceiro; mesmo
   padrao de fallback multi-canal de finance/payment_notifications.py) e
   avanca o estado do ledger.
4. Registra a confirmacao manual do aluno ("eu confirmei no Wellhub").

PONTOS CRITICOS:
- NUNCA automatizar o check-in dentro do app da Wellhub/TotalPass. O check-in
  deles e a propria barreira anti-fraude do parceiro; contorna-la e risco de
  fraude de check-in e de suspensao do contrato do box com a operadora. Este
  modulo so pode *lembrar* o aluno — a confirmacao continua manual, feita
  pelo aluno, no app deles.
- 'declared_value' e 'status=reconciled' so mudam em finance/reconciliation.py,
  a partir do extrato oficial do parceiro. Confirmacao do aluno (CONFIRMED)
  e so um sinal operacional — nunca e tratada como receita fechada.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# 0min (na hora da aula), 10min e 30min depois — ultima tentativa.
REMINDER_OFFSETS_MINUTES = (0, 10, 30)
MAX_REMINDER_ATTEMPTS = len(REMINDER_OFFSETS_MINUTES)

PARTNER_DEEP_LINKS = {
    'wellhub': 'https://gympass.page.link/checkin',
    'totalpass': 'https://totalpass.com.br/app',
}


def sync_partner_checkin_charge(attendance) -> object | None:
    """Cria (se necessario) o ledger de reconciliacao para um check-in de aluno
    de parceiro. Chamado pelo signal post_save de Attendance. No-op para aluno
    de pagamento direto ou attendance ainda sem check-in."""

    if not attendance.check_in_at:
        return None

    from finance.model_definitions import EnrollmentStatus, PartnerCheckInCharge, PaymentSource

    enrollment = (
        attendance.student.enrollments
        .filter(status=EnrollmentStatus.ACTIVE)
        .exclude(payment_source=PaymentSource.DIRECT)
        .order_by('-start_date')
        .first()
    )
    if enrollment is None:
        return None

    charge, _created = PartnerCheckInCharge.objects.get_or_create(
        attendance=attendance,
        defaults={
            'enrollment': enrollment,
            'partner': enrollment.payment_source,
        },
    )
    return charge


def next_reminder_offset_minutes(attempts_sent: int) -> int | None:
    if attempts_sent >= MAX_REMINDER_ATTEMPTS:
        return None
    return REMINDER_OFFSETS_MINUTES[attempts_sent]


def is_reminder_due(*, session_scheduled_at, attempts_sent: int, now) -> bool:
    offset = next_reminder_offset_minutes(attempts_sent)
    if offset is None:
        return False
    return now >= session_scheduled_at + timedelta(minutes=offset)


def send_due_partner_checkin_reminders(*, now=None, limit: int = 200) -> dict:
    """Itera os boxes ativos, dispara os lembretes devidos e devolve um
    relatorio agregado. Le e escreve dentro do mesmo schema_context por box
    (mesmo padrao de finance/reconciliation.py)."""

    from control.models import Box
    from django_tenants.utils import schema_context
    from finance.model_definitions import PartnerCheckInStatus

    current = now or timezone.now()
    checked = 0
    sent = 0
    reminders = []

    for box in Box.objects.filter(status=Box.Status.ACTIVE):
        with schema_context(box.schema_name):
            from finance.model_definitions import PartnerCheckInCharge

            charges = (
                PartnerCheckInCharge.objects
                .filter(status__in=[PartnerCheckInStatus.PENDING, PartnerCheckInStatus.REMINDED])
                .select_related('attendance__session', 'enrollment__student')
                .order_by('created_at')[:limit]
            )
            for charge in charges:
                checked += 1
                session = getattr(charge.attendance, 'session', None)
                if session is None:
                    continue
                if not is_reminder_due(
                    session_scheduled_at=session.scheduled_at,
                    attempts_sent=charge.reminder_attempts,
                    now=current,
                ):
                    continue
                channel_result = send_partner_checkin_reminder(charge, now=current)
                sent += 1
                reminders.append({
                    'box': box.schema_name,
                    'charge_id': charge.id,
                    'attempt': charge.reminder_attempts,
                    'channel': channel_result,
                })

    return {
        'checked_at': current.isoformat(),
        'checked': checked,
        'sent': sent,
        'reminders': reminders,
    }


def send_partner_checkin_reminder(charge, *, now=None) -> str:
    """Dispara UM lembrete pro aluno confirmar manualmente no app do parceiro
    e avanca reminder_attempts/status. Nunca chama a API do parceiro."""

    from finance.model_definitions import PartnerCheckInStatus, PaymentSource

    current = now or timezone.now()
    student = charge.enrollment.student
    partner_label = PaymentSource(charge.partner).label
    deep_link = PARTNER_DEEP_LINKS.get(charge.partner, '')

    result = 'skipped'
    email = (getattr(student, 'email', '') or '').strip()
    if email:
        try:
            result = _send_reminder_email(student, partner_label=partner_label, deep_link=deep_link)
        except Exception:
            logger.exception(
                'partner checkin reminder: falha no e-mail. charge=%s attempt=%s',
                charge.id, charge.reminder_attempts + 1,
            )
            result = 'error'
    else:
        logger.info('partner checkin reminder: aluno sem e-mail cadastrado. charge=%s', charge.id)

    charge.reminder_attempts += 1
    charge.last_reminder_at = current
    charge.status = PartnerCheckInStatus.REMINDED
    charge.save(update_fields=['reminder_attempts', 'last_reminder_at', 'status', 'updated_at'])
    return result


def _send_reminder_email(student, *, partner_label: str, deep_link: str) -> str:
    email = (getattr(student, 'email', '') or '').strip()
    if not email:
        return 'skipped'

    from signup.email_sender import send_html_email

    name = (getattr(student, 'full_name', '') or 'Aluno').strip()
    subject = f'Confirme seu check-in {partner_label} — OctoBox'
    text_body = (
        f'Ola {name}, vimos que voce chegou no box! Nao esqueca de confirmar '
        f'seu check-in no app {partner_label} pra garantir sua presenca: {deep_link}'
    )
    html_body = (
        f'<p>Ola {name},</p>'
        f'<p>Vimos que voce chegou no box! Nao esqueca de confirmar seu check-in '
        f'no app <strong>{partner_label}</strong> pra garantir sua presenca.</p>'
        f'<p><a href="{deep_link}">Abrir {partner_label}</a></p>'
    )
    send_html_email(subject=subject, text_body=text_body, html_body=html_body, to_email=email)
    return 'sent'


def confirm_partner_checkin(charge_id, *, now=None) -> bool:
    """Registra que o ALUNO confirmou manualmente no app do parceiro (ex.: ele
    tocou no link do lembrete). Sinal operacional apenas — nao e receita
    fechada; quem fecha e a reconciliacao com o extrato oficial."""

    from finance.model_definitions import PartnerCheckInCharge, PartnerCheckInStatus

    current = now or timezone.now()
    updated = (
        PartnerCheckInCharge.objects
        .filter(id=charge_id)
        .exclude(status=PartnerCheckInStatus.CONFIRMED)
        .update(status=PartnerCheckInStatus.CONFIRMED, confirmed_at=current)
    )
    return bool(updated)


__all__ = [
    'MAX_REMINDER_ATTEMPTS',
    'PARTNER_DEEP_LINKS',
    'REMINDER_OFFSETS_MINUTES',
    'confirm_partner_checkin',
    'is_reminder_due',
    'next_reminder_offset_minutes',
    'send_due_partner_checkin_reminders',
    'send_partner_checkin_reminder',
    'sync_partner_checkin_charge',
]
