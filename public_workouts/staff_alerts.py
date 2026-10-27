"""Aviso interno quando um work item de onboarding do Curva entra na fila.

Separado de notifications.py (teto de tamanho em tests/test_file_size_ratchet.py);
reusa o mesmo esqueleto de e-mail da marca.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone

from .notifications import _curva_email_shell, _html_escape

logger = logging.getLogger(__name__)


def _staff_summary_row(label: str, value: str, *, first: bool = False) -> str:
    border = '' if first else 'border-top:1px solid #273044;'
    background = 'background:#151f30;' if first else ''
    return f"""
                <tr>
                  <td style="{background}{border}padding:14px 18px;">
                    <p style="margin:0 0 4px;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#a4afc2;font-weight:700;">
                      {_html_escape(label)}
                    </p>
                    <p style="margin:0;font-size:17px;font-weight:700;color:#f3f6fb;letter-spacing:-0.01em;">
                      {_html_escape(value)}
                    </p>
                  </td>
                </tr>"""


def notify_staff_work_item_opened(item, *, base_url: str = '') -> dict:
    """Avisa a equipe que um work item de onboarding entrou na fila.

    Nasce quando pagamento e anamnese estao em dia (ensure_required_work_items):
    sem isto, a anamnese respondida depois do pagamento abria trabalho em
    silencio. Nunca inclui respostas da anamnese (dado de saude) — so o
    necessario para achar o aluno e o prazo. Item ja concluido ou cancelado
    quando a outbox drena nao gera e-mail.
    """
    from django.urls import reverse

    from signup.email_sender import send_html_email

    from .models import PublicWorkoutWorkItemStatus

    if item.status in (PublicWorkoutWorkItemStatus.DONE, PublicWorkoutWorkItemStatus.CANCELED):
        return {}
    email = item.account.email
    task_label = item.get_item_type_display()
    tier_label = item.subscription.get_tier_display()
    due_label = timezone.localtime(item.due_at).strftime('%d/%m %H:%M')
    owner_label = item.assigned_to.name if item.assigned_to_id else 'sem responsável'
    detail_url = (
        f'{base_url.rstrip("/")}'
        f'{reverse("public-workout-coach-student-detail", kwargs={"account_id": item.account_id})}'
        if base_url else ''
    )

    subject = f'Trabalho aberto — {task_label}: {email} (prazo {due_label})'
    body = (
        f'Pagamento e anamnese em dia: o trabalho entrou na fila.\n\n'
        f'Aluno: {email}\n'
        f'Plano: {tier_label}\n'
        f'Tarefa: {task_label}\n'
        f'Prazo interno: {due_label}\n'
        f'Responsavel: {owner_label}\n'
        + (f'\nFicha do aluno: {detail_url}\n' if detail_url else '')
    )
    rows = ''.join((
        _staff_summary_row('Aluno', email, first=True),
        _staff_summary_row('Plano', tier_label),
        _staff_summary_row('Tarefa', task_label),
        _staff_summary_row('Prazo interno', due_label),
        _staff_summary_row('Responsável', owner_label),
    ))
    detail_link = (
        f"""
              <p style="margin:0 0 8px;font-size:15px;line-height:1.6;">
                <a href="{_html_escape(detail_url)}" style="color:#00e5ff;font-weight:700;">Abrir ficha do aluno →</a>
              </p>"""
        if detail_url else ''
    )
    card_html = f"""\
              <p style="margin:0 0 16px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#00e5ff;font-weight:800;">
                ✦ Fila Curva
              </p>
              <h1 class="h1" style="margin:0 0 18px;font-size:32px;line-height:1.08;letter-spacing:-0.04em;font-weight:800;color:#f3f6fb;">
                {_html_escape(task_label)}
              </h1>
              <p style="margin:0 0 28px;font-size:16px;line-height:1.6;color:#a4afc2;">
                Pagamento e anamnese em dia: o trabalho entrou na fila.
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 28px;border:1px solid #273044;border-radius:14px;overflow:hidden;">{rows}
              </table>{detail_link}"""
    html_body = _curva_email_shell(
        title='Trabalho aberto — Curva',
        preheader=f'{task_label} para {email} até {due_label}.',
        card_html=card_html,
        footer_text='— Curva Treino &amp; Nutrição · aviso interno, não repasse ao aluno',
    )
    result = {}
    for staff_email in getattr(settings, 'PUBLIC_WORKOUT_STAFF_ALERT_EMAILS', []):
        try:
            send_html_email(subject=subject, text_body=body, html_body=html_body, to_email=staff_email)
            result[staff_email] = 'sent'
        except Exception:
            logger.exception(
                'notify_staff_work_item_opened: falha no e-mail. item=%s staff_email=%s', item.pk, staff_email,
            )
            result[staff_email] = 'error'
    return result


__all__ = ['notify_staff_work_item_opened']
