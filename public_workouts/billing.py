"""
ARQUIVO: regra de negocio de cobranca do corredor de treinos (Onda B2 do CORDA).

POR QUE ELE EXISTE:
- separa a decisao de negocio (quando cobrar, quando avisar, faixa de valor
  aceita) do transporte (Stripe, e-mail) e da view — testavel sem subir
  servidor nem falar com a Stripe.

PONTOS CRITICOS:
- `brazilian_holidays.py` so expoe get_brazilian_holiday_name — nao ha
  "proximo dia util" pronto no repo. _next_business_day abaixo e escrito
  aqui, dentro do corredor, porque e a unica coisa que precisa dele hoje;
  vira candidato a shared_support se um segundo consumidor aparecer.
- PublicWorkoutPaymentNotice.offset_days do plano (D-7,-3,-1,0,+2) — a
  data agendada nunca cai em fim de semana ou feriado; empurra pro
  proximo dia util (nunca faz sentido cobrar ou suspender num feriado).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from student_app.brazilian_holidays import get_brazilian_holiday_name

from .models import (
    PublicWorkoutPayment,
    PublicWorkoutPaymentNotice,
    PublicWorkoutPaymentStatus,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionEvent,
    PublicWorkoutSubscriptionStatus,
)
from .notifications import notify_payment_due

# D-7, D-3, D-1, D0 (vencimento), D+2 (trava) — mesma régua do box
# (finance/payment_notifications.py), adaptada ao vocabulario do corredor.
PUBLIC_WORKOUT_NOTICE_OFFSET_DAYS: tuple[int, ...] = (-7, -3, -1, 0, 2)

_DEFAULT_MIN_AMOUNT = Decimal('1.00')
_DEFAULT_MAX_AMOUNT = Decimal('2000.00')


class PublicWorkoutPaymentAmountError(ValueError):
    """Levantada quando o valor da cobranca esta fora da faixa aceita (P8 do CORDA)."""


def _is_business_day(day: date) -> bool:
    return day.weekday() < 5 and get_brazilian_holiday_name(day) is None


def _next_business_day(day: date) -> date:
    while not _is_business_day(day):
        day += timedelta(days=1)
    return day


def validate_payment_amount(amount: Decimal) -> None:
    """Guardrail de valor no SERVICO, nao so no form (P8 do CORDA).

    Levanta PublicWorkoutPaymentAmountError se `amount` estiver fora da
    faixa configurada. Faixa vem de settings para poder ajustar sem
    deploy de codigo; defaults sao so uma rede de seguranca ampla, nao um
    preco — o preco real e decisao de produto, fora deste modulo.
    """
    min_amount = Decimal(str(getattr(settings, 'PUBLIC_WORKOUT_PAYMENT_MIN_AMOUNT', _DEFAULT_MIN_AMOUNT)))
    max_amount = Decimal(str(getattr(settings, 'PUBLIC_WORKOUT_PAYMENT_MAX_AMOUNT', _DEFAULT_MAX_AMOUNT)))
    if amount is None or amount < min_amount or amount > max_amount:
        raise PublicWorkoutPaymentAmountError(
            f'amount {amount!r} fora da faixa aceita ({min_amount} a {max_amount})'
        )


def create_payment_with_notice_schedule(
    *,
    subscription,
    due_date: date,
    gross_amount: Decimal,
) -> PublicWorkoutPayment:
    """Cria o PublicWorkoutPayment e as 5 linhas da regua de avisos (D.5 do CORDA).

    Valida o valor ANTES de gravar (P8) — nunca cria cobranca fora de faixa
    pra "corrigir depois".
    """
    validate_payment_amount(gross_amount)

    payment = PublicWorkoutPayment.objects.create(
        subscription=subscription,
        due_date=due_date,
        gross_amount=gross_amount,
    )
    for offset_days in PUBLIC_WORKOUT_NOTICE_OFFSET_DAYS:
        scheduled_for = _next_business_day(due_date + timedelta(days=offset_days))
        PublicWorkoutPaymentNotice.objects.create(
            payment=payment,
            offset_days=offset_days,
            scheduled_for=scheduled_for,
        )
    return payment


def _mark_notice_sent_if_channels_ok(notice: PublicWorkoutPaymentNotice) -> bool:
    """Marca sent_at so se nenhum canal deu erro — transacional (D.2 frase 15).

    select_for_update trava a linha: se dois drains rodarem ao mesmo tempo,
    o segundo ve sent_at ja preenchido e nao reenvia (P1). Canal com erro
    nunca marca sent_at — fica pendente pro proximo drain (P2).
    """
    with transaction.atomic():
        locked = PublicWorkoutPaymentNotice.objects.select_for_update().get(pk=notice.pk)
        if locked.sent_at is not None:
            return False
        result = notify_payment_due(notice.payment, notice.offset_days)
        if any(status == 'error' for status in result.values()):
            return False
        locked.sent_at = timezone.now()
        locked.save(update_fields=['sent_at'])
        return True


def _suspend_if_still_unpaid(payment: PublicWorkoutPayment) -> bool:
    """D+2: suspende a assinatura se o pagamento CONTINUA sem confirmacao.

    Le o status do PublicWorkoutPayment de novo, travado, dentro da
    transacao — se o webhook confirmou o pagamento ha 1 minuto, o status
    ja mudou pra PAID e a suspensao nao acontece (P3 do CORDA).
    """
    with transaction.atomic():
        fresh_payment = (
            PublicWorkoutPayment.objects.select_related('subscription').select_for_update().get(pk=payment.pk)
        )
        if fresh_payment.status != PublicWorkoutPaymentStatus.PENDING:
            return False

        subscription = fresh_payment.subscription
        if subscription.status != PublicWorkoutSubscriptionStatus.ACTIVE:
            return False

        previous_status = subscription.status
        subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        subscription.suspended_at = timezone.now()
        subscription.save(update_fields=['status', 'suspended_at', 'updated_at'])
        PublicWorkoutSubscriptionEvent.objects.create(
            subscription=subscription,
            from_status=previous_status,
            to_status=subscription.status,
            reason=f'D+2 sem confirmacao de pagamento (payment_id={fresh_payment.id})',
        )
        return True


def drain_due_notices() -> dict:
    """Envia avisos vencidos e suspende assinaturas em D+2 sem pagamento.

    Duas varreduras independentes, cada uma idempotente pela sua propria
    trava (sent_at para avisos; subscription.status para suspensao) — uma
    nao depende do resultado da outra: um e-mail que falhou nao impede a
    suspensao, e uma suspensao que ja aconteceu nao reenvia o aviso.
    """
    today = timezone.localdate()

    due_notices = PublicWorkoutPaymentNotice.objects.filter(sent_at__isnull=True, scheduled_for__lte=today)
    sent = 0
    skipped = 0
    for notice in due_notices:
        if _mark_notice_sent_if_channels_ok(notice):
            sent += 1
        else:
            skipped += 1

    suspend_cutoff = today - timedelta(days=2)
    overdue_payments = PublicWorkoutPayment.objects.select_related('subscription').filter(
        status=PublicWorkoutPaymentStatus.PENDING,
        due_date__lte=suspend_cutoff,
        subscription__status=PublicWorkoutSubscriptionStatus.ACTIVE,
    )
    suspended = 0
    for overdue_payment in overdue_payments:
        if _suspend_if_still_unpaid(overdue_payment):
            suspended += 1

    return {'sent': sent, 'skipped': skipped, 'suspended': suspended}


def reactivate_subscription(subscription, *, reason: str) -> bool:
    """Reativa uma assinatura suspensa/em atraso — chamada pelo webhook
    handler e pela reconciliacao (Onda B2, Slice B) quando o pagamento
    confirma. Idempotente: so muda estado se nao estava ja ACTIVE."""
    if subscription.status not in (
        PublicWorkoutSubscriptionStatus.SUSPENDED,
        PublicWorkoutSubscriptionStatus.PAST_DUE,
    ):
        return False

    previous_status = subscription.status
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.suspended_at = None
    subscription.save(update_fields=['status', 'suspended_at', 'updated_at'])
    PublicWorkoutSubscriptionEvent.objects.create(
        subscription=subscription,
        from_status=previous_status,
        to_status=subscription.status,
        reason=reason,
    )
    return True


# ---------------------------------------------------------------------------
# Ciclo de vida da assinatura via Stripe (Onda B2, Fatia B do CORDA).
# Sem Connect Express (decisao do Renan + C5): conta unica, application_fee
# sempre 0, gross_amount == net_amount em todo PublicWorkoutPayment criado
# a partir daqui.
# ---------------------------------------------------------------------------


def get_or_create_subscription(*, account, plan_slug: str) -> PublicWorkoutSubscription:
    """Devolve a assinatura do corredor da conta, criando na primeira vez.

    `account` e OneToOne com PublicWorkoutSubscription — chamar de novo pra
    mesma conta sempre devolve a mesma linha, nunca cria duas (P6 do CORDA:
    duplo clique em "assinar" nao pode duplicar assinatura).
    """
    subscription, _ = PublicWorkoutSubscription.objects.get_or_create(
        account=account,
        defaults={'plan_slug': plan_slug},
    )
    return subscription


def link_stripe_ids(subscription, *, customer_id: str, stripe_subscription_id: str) -> None:
    """Grava customer_id/subscription_id da Stripe (checkout.session.completed).

    So update_fields — idempotente por natureza, reenviar o mesmo evento
    grava os mesmos valores de novo, sem efeito colateral extra.
    """
    subscription.stripe_customer_id = customer_id
    subscription.stripe_subscription_id = stripe_subscription_id
    subscription.save(update_fields=['stripe_customer_id', 'stripe_subscription_id', 'updated_at'])


def record_successful_invoice_payment(
    subscription,
    *,
    stripe_invoice_id: str,
    gross_amount: Decimal,
    due_date: date,
) -> PublicWorkoutPayment:
    """Confirma um ciclo de cobranca bem-sucedido (invoice.payment_succeeded).

    Idempotente por (subscription, stripe_invoice_id): a Stripe pode
    reenviar o mesmo evento (retry de webhook) sem criar segunda linha nem
    reenviar notificacao.

    Reativa a assinatura se ela estava suspensa/em atraso — o pagamento
    pode confirmar DEPOIS da trava de D+2 (P4 do CORDA); e o webhook,
    nao so a reconciliacao periodica, que devolve o acesso.

    Cobranca bem-sucedida NUNCA passa pela regua de avisos
    (create_payment_with_notice_schedule): nao ha o que avisar sobre um
    ciclo que ja funcionou sozinho. A regua so nasce em
    handle_failed_invoice_payment, abaixo — o aluno so ouve falar disso se
    algo precisou da atencao dele.
    """
    payment, _ = PublicWorkoutPayment.objects.get_or_create(
        subscription=subscription,
        stripe_invoice_id=stripe_invoice_id,
        defaults={'due_date': due_date, 'gross_amount': gross_amount},
    )
    if payment.status != PublicWorkoutPaymentStatus.PAID:
        payment.status = PublicWorkoutPaymentStatus.PAID
        payment.paid_at = timezone.now()
        # Sem Connect Express (C5): sem repasse, sem comissao. gross == net.
        payment.net_amount = gross_amount
        payment.application_fee_amount = Decimal('0')
        payment.save(update_fields=['status', 'paid_at', 'net_amount', 'application_fee_amount', 'updated_at'])

    reactivate_subscription(subscription, reason=f'invoice {stripe_invoice_id} paga')
    return payment


def handle_failed_invoice_payment(
    subscription,
    *,
    stripe_invoice_id: str,
    gross_amount: Decimal,
    due_date: date,
) -> PublicWorkoutPayment:
    """Registra uma tentativa de cobranca automatica que falhou (invoice.payment_failed).

    Idempotente por (subscription, stripe_invoice_id) — reenvio do mesmo
    evento nao cria uma segunda regua pro mesmo ciclo.
    """
    existing = PublicWorkoutPayment.objects.filter(
        subscription=subscription, stripe_invoice_id=stripe_invoice_id
    ).first()
    if existing is not None:
        payment = existing
    else:
        payment = create_payment_with_notice_schedule(subscription=subscription, due_date=due_date, gross_amount=gross_amount)
        payment.stripe_invoice_id = stripe_invoice_id
        payment.save(update_fields=['stripe_invoice_id', 'updated_at'])

    if subscription.status == PublicWorkoutSubscriptionStatus.ACTIVE:
        previous_status = subscription.status
        subscription.status = PublicWorkoutSubscriptionStatus.PAST_DUE
        subscription.save(update_fields=['status', 'updated_at'])
        PublicWorkoutSubscriptionEvent.objects.create(
            subscription=subscription,
            from_status=previous_status,
            to_status=subscription.status,
            reason=f'invoice {stripe_invoice_id} falhou',
        )
    return payment


def mark_subscription_canceled(subscription, *, reason: str) -> bool:
    """customer.subscription.deleted — cancelamento definitivo.

    Nunca reativa sozinho depois disso (diferente de SUSPENDED/PAST_DUE,
    que reactivate_subscription resolve): cancelamento e decisao do aluno
    ou do Stripe Customer Portal, uma nova assinatura exige novo checkout.
    Idempotente: so muda estado se ainda nao estava CANCELED.
    """
    if subscription.status == PublicWorkoutSubscriptionStatus.CANCELED:
        return False

    previous_status = subscription.status
    subscription.status = PublicWorkoutSubscriptionStatus.CANCELED
    subscription.canceled_at = timezone.now()
    subscription.save(update_fields=['status', 'canceled_at', 'updated_at'])
    PublicWorkoutSubscriptionEvent.objects.create(
        subscription=subscription,
        from_status=previous_status,
        to_status=subscription.status,
        reason=reason,
    )
    return True
