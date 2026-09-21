"""
ARQUIVO: avisos de cobranca do corredor de treinos (Onda B2 do CORDA, V4).

POR QUE ELE EXISTE:
- copia a FORMA de finance/payment_notifications.py::notify_payment_confirmed
  (D.00) — mesmo desenho de "por canal, nunca propaga, sempre loga" — mas
  chamando os senders proprios do corredor (student_identity/delivery_gateways.py,
  ja usado pelo login por e-mail da Onda B1), nunca editando finance/.

PONTOS CRITICOS:
- Falha de canal e logada e NUNCA propaga — nao pode derrubar o drain
  (mesma regra do box: "nao pode falhar o webhook", aqui "nao pode falhar
  o drain de avisos").
- So e-mail por enquanto: o corredor ainda nao tem push nem WhatsApp
  proprios (essa infraestrutura e do app do aluno de box). Adicionar
  canal aqui e trabalho de outra onda, nao invencao deste modulo.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from student_identity.delivery_gateways import StudentEmailDeliveryError, get_student_email_gateway

logger = logging.getLogger(__name__)

_OFFSET_LABELS = {
    -7: 'Seu pagamento vence em 7 dias',
    -3: 'Seu pagamento vence em 3 dias',
    -1: 'Seu pagamento vence amanha',
    0: 'Seu pagamento vence hoje',
    2: 'Seu treino foi pausado por falta de pagamento',
}


def _send_due_email(payment, offset_days: int) -> str:
    account = payment.subscription.account
    if not account or not account.email:
        return 'skipped'

    subject = _OFFSET_LABELS.get(offset_days, 'Aviso de cobranca — Treinos')
    body = (
        f'{subject}.\n\n'
        f'Valor: R$ {payment.gross_amount}\n'
        f'Vencimento: {payment.due_date.isoformat()}\n'
    )
    get_student_email_gateway().send(subject=subject, body=body, to_email=account.email)
    return 'sent'


def notify_payment_due(payment, offset_days: int) -> dict:
    """Dispara o aviso de cobranca ao aluno. Devolve o status por canal.

    Nunca levanta: quem chama (drain_public_workout_notices) decide o que
    fazer com o resultado — sent_at so e gravado se nenhum canal deu erro.
    """
    result = {'email': 'skipped'}

    try:
        result['email'] = _send_due_email(payment, offset_days)
    except StudentEmailDeliveryError:
        logger.exception('notify_payment_due: falha no e-mail. payment=%s offset_days=%s', payment.id, offset_days)
        result['email'] = 'error'
    except Exception:
        logger.exception(
            'notify_payment_due: falha inesperada no e-mail. payment=%s offset_days=%s', payment.id, offset_days
        )
        result['email'] = 'error'

    return result


def notify_program_ready(program, *, base_url: str) -> bool:
    """Envia uma unica vez o link autenticavel do programa publicado.

    A publicacao ja foi confirmada quando esta funcao roda. Falha de e-mail
    fica registrada e nunca desfaz o snapshot do treino.
    """
    from public_workouts.models import (
        PublicWorkoutLoginToken,
        PublicWorkoutProgramDelivery,
        PublicWorkoutSubscription,
    )

    subscription = PublicWorkoutSubscription.objects.select_related('account').filter(plan_slug=program.slug).first()
    if subscription is None:
        return False

    with transaction.atomic():
        delivery, _created = PublicWorkoutProgramDelivery.objects.select_for_update().get_or_create(program=program)
        if delivery.sent_at is not None:
            return True
        delivery.attempted_at = timezone.now()
        delivery.attempt_count += 1
        delivery.last_error = ''
        delivery.save(update_fields=['attempted_at', 'attempt_count', 'last_error'])

    token = PublicWorkoutLoginToken.objects.create(
        account=subscription.account,
        expires_at=timezone.now() + timezone.timedelta(minutes=15),
    )
    login_url = f'{base_url.rstrip("/")}/treinos/login?token={token.token}&next=/renan/{program.slug}'
    subject = 'Seu programa Curva esta pronto'
    body = (
        'Seu programa foi revisado e publicado.\n\n'
        f'Acesse com seguranca: {login_url}\n\n'
        'O link vale por 15 minutos. Se expirar, solicite outro na tela de login.'
    )
    try:
        get_student_email_gateway().send(subject=subject, body=body, to_email=subscription.account.email)
    except Exception as exc:
        logger.exception('notify_program_ready: falha no e-mail. program=%s', program.pk)
        PublicWorkoutProgramDelivery.objects.filter(program=program).update(last_error=str(exc)[:255])
        return False

    PublicWorkoutProgramDelivery.objects.filter(program=program).update(sent_at=timezone.now(), last_error='')
    return True


def notify_meal_plan_ready(meal_plan, *, base_url: str) -> bool:
    from public_workouts.models import (
        PublicWorkoutLoginToken,
        PublicWorkoutMealPlanDelivery,
        PublicWorkoutSubscription,
    )

    subscription = PublicWorkoutSubscription.objects.select_related('account').filter(
        account=meal_plan.account,
    ).first()
    if subscription is None:
        return False

    with transaction.atomic():
        delivery, _created = PublicWorkoutMealPlanDelivery.objects.select_for_update().get_or_create(
            meal_plan=meal_plan,
        )
        if delivery.sent_at is not None:
            return True
        delivery.attempted_at = timezone.now()
        delivery.attempt_count += 1
        delivery.last_error = ''
        delivery.save(update_fields=['attempted_at', 'attempt_count', 'last_error'])

    token = PublicWorkoutLoginToken.objects.create(
        account=subscription.account,
        expires_at=timezone.now() + timezone.timedelta(minutes=15),
    )
    login_url = f'{base_url.rstrip("/")}/treinos/login?token={token.token}&next=/treinos/minha-conta'
    try:
        get_student_email_gateway().send(
            subject='Seu plano alimentar Curva esta pronto',
            body=(
                'Seu plano alimentar foi revisado e publicado.\n\n'
                f'Acesse com seguranca: {login_url}\n\n'
                'O link vale por 15 minutos.'
            ),
            to_email=subscription.account.email,
        )
    except Exception as exc:
        logger.exception('notify_meal_plan_ready: falha no e-mail. meal_plan=%s', meal_plan.pk)
        PublicWorkoutMealPlanDelivery.objects.filter(meal_plan=meal_plan).update(last_error=str(exc)[:255])
        return False

    PublicWorkoutMealPlanDelivery.objects.filter(meal_plan=meal_plan).update(
        sent_at=timezone.now(), last_error='',
    )
    return True


def notify_waitlist_invitation(entry, *, base_url: str) -> bool:
    """Convida sem colocar PII ou token reutilizavel na URL."""
    from public_workouts.models import PublicWorkoutWaitlistStatus

    if entry.status == PublicWorkoutWaitlistStatus.CONVERTED:
        return True
    landing_url = f'{base_url.rstrip("/")}/treinos/?invite={entry.invite_token}#curva-precos'
    try:
        get_student_email_gateway().send(
            subject='Sua vaga no Curva esta disponivel',
            body=(
                f'Abrimos uma vaga para o plano {entry.get_tier_display()} que voce escolheu.\n\n'
                f'Contrate por aqui: {landing_url}\n\n'
                'A disponibilidade e limitada e sera revalidada no checkout.'
            ),
            to_email=entry.email,
        )
    except Exception:
        logger.exception('notify_waitlist_invitation: falha no e-mail. entry=%s', entry.pk)
        return False
    entry.status = PublicWorkoutWaitlistStatus.INVITED
    entry.invited_at = timezone.now()
    entry.expires_at = timezone.now() + timezone.timedelta(days=3)
    entry.save(update_fields=['status', 'invited_at', 'expires_at', 'updated_at'])
    return True


__all__ = [
    'notify_meal_plan_ready', 'notify_payment_due', 'notify_program_ready',
    'notify_waitlist_invitation',
]
