"""
ARQUIVO: roteador de eventos Stripe para use cases do domínio finance.

POR QUE ELE EXISTE:
- Desacopla o envelope bruto do Stripe da lógica de negócio em finance/application/.
- A view cria o PaymentWebhookEvent; o router decide qual use case acionar.
- Segue a regra da Signal Mesh: payload externo não chega cru ao núcleo.

O QUE ESTE ARQUIVO FAZ:
1. Recebe um PaymentWebhookEvent já persistido.
2. Extrai o comando correto do payload normalizado.
3. Chama o use case correspondente.
4. Marca o evento como processado ou registra falha.

PONTOS CRITICOS:
- Nunca importar stripe diretamente aqui — o payload já está normalizado em JSON.
- Adicionar novos event_types como novas funções _handle_*, não como ifs crescentes.
"""

import logging
from datetime import datetime, timezone as dt_timezone

from integrations.mesh import FAILURE_KIND_NON_RETRYABLE, FAILURE_KIND_RETRYABLE

from .models import PaymentWebhookEvent

logger = logging.getLogger(__name__)


def route_payment_webhook_event(event: PaymentWebhookEvent) -> None:
    handler = _HANDLERS.get(event.event_type)
    if handler is None:
        event.mark_processed()
        return

    try:
        handler(event)
        event.mark_processed()
    except ValueError as exc:
        logger.error('route_payment_webhook_event: erro não reprocessável. event=%s err=%s', event.event_id, exc)
        event.register_failure(
            failure_kind=FAILURE_KIND_NON_RETRYABLE,
            error_message=str(exc),
        )
    except Exception as exc:
        logger.exception('route_payment_webhook_event: falha reprocessável. event=%s', event.event_id)
        event.register_failure(
            failure_kind=FAILURE_KIND_RETRYABLE,
            error_message=str(exc),
        )


def _handle_checkout_session_completed(event: PaymentWebhookEvent) -> None:
    """Roteia checkout.session.completed (e os dois eventos async irmaos) para
    o handler correto.

    O OctoBox tem dois fluxos de checkout que reusam o mesmo evento Stripe:
    1. Pagamento de aluno em mensalidade (metadata.payment_id) — reconcilia o
       Payment no schema do box (metadata.box_schema resolve o tenant).
    2. Cadastro de Early Adopter (metadata.pending_signup_id) — fluxo novo.

    A escolha e feita pela metadata da Session. Outros tipos sao logados e ignorados,
    nao falham para nao bloquear o webhook.

    Onda 3 (2026-08-26): esta mesma funcao tambem roteia
    checkout.session.async_payment_succeeded e ..._failed — Pix (e qualquer
    metodo delayed-notification) dispara checkout.session.completed NA HORA
    do clique com payment_status='unpaid', e o resultado real chega depois
    nesses dois eventos irmaos. O payload dos tres tem o mesmo formato
    (data.object = a Checkout Session, so payment_status muda), entao a
    mesma logica de roteamento por metadata serve para os tres — quem decide
    se reconcilia ou nao e _handle_student_payment, olhando payment_status.
    """
    session = event.payload.get('data', {}).get('object', {})
    metadata = session.get('metadata', {}) or {}

    if metadata.get('pending_signup_id'):
        _handle_early_adopter_signup(event, session, metadata)
        return

    if metadata.get('payment_id'):
        _handle_student_payment(event, session, metadata)
        return

    logger.info(
        'route_payment_webhook_event: session sem metadata reconhecivel. event=%s',
        event.event_id,
    )


def _handle_student_payment(event, session, metadata):
    from django_tenants.utils import schema_context

    from finance.application.commands import ReconcilePaymentCommand
    from finance.application.use_cases import execute_reconcile_payment_use_case

    payment_id = metadata.get('payment_id')
    version_locked = metadata.get('version_locked')
    amount_cents = session.get('amount_total')

    if not payment_id or version_locked is None or amount_cents is None:
        raise ValueError(f'Metadata incompleta no evento {event.event_id}: payment_id={payment_id}')

    box_schema = _resolve_box_schema(metadata.get('box_schema'), event)

    payment_intent_id = session.get('payment_intent') or ''
    session_id = session.get('id') or ''
    currency = session.get('currency') or 'brl'

    # Mapa public payment_intent -> box: fonte de verdade do roteamento de tenant
    # para eventos charge.* (refund/dispute) que NAO carregam nossa metadata.
    # Gravado em public (o router roda em public), antes do reconcile. Sempre
    # grava, mesmo se ainda nao pago — o payment_intent ja existe desde o
    # clique inicial do Pix, e os eventos async/refund precisam achar o box.
    _record_stripe_payment_ref(
        payment_intent_id=payment_intent_id,
        session_id=session_id,
        box_schema=box_schema,
        payment_id=int(payment_id),
    )

    # Pix (e qualquer metodo delayed-notification) dispara
    # checkout.session.completed NA HORA do clique com payment_status=
    # 'unpaid' — o dinheiro ainda nao chegou. Reconciliar aqui daria baixa
    # no Payment antes do pagamento ser confirmado de verdade. O resultado
    # real chega depois via checkout.session.async_payment_succeeded (dai
    # payment_status='paid', cai no reconcile abaixo) ou ..._failed (Payment
    # fica como estava — sem baixa, sem erro, so nao reconcilia). Cartao e
    # sincrono: payment_status ja vem 'paid' no completed, reconcile roda
    # na hora, comportamento inalterado.
    payment_status = session.get('payment_status')
    if payment_status != 'paid':
        logger.info(
            'route_payment_webhook_event: session ainda nao paga (payment_status=%s) — '
            'aguardando confirmacao assincrona. payment=%s event=%s',
            payment_status, payment_id, event.event_id,
        )
        return

    command = ReconcilePaymentCommand(
        payment_id=int(payment_id),
        amount_cents=int(amount_cents),
        stripe_event_id=event.event_id,
        version_locked=int(version_locked),
        stripe_session_id=session_id,
        stripe_payment_intent_id=payment_intent_id,
        currency=currency,
    )

    # O webhook chega no schema public (esta em PUBLIC_SCHEMA_PATHS), mas Payment
    # vive no schema do box (TENANT_APP). Sem este schema_context, o reconcile
    # faz SELECT em public e estoura 'relation does not exist'. O box e resolvido
    # pela metadata gravada no checkout (em contexto de tenant) e validado abaixo.
    with schema_context(box_schema):
        result = execute_reconcile_payment_use_case(command)
        # Confirmacao ao aluno na baixa (T5): so na primeira reconciliacao, dentro
        # do schema do box (dados do aluno). Nunca falha o webhook.
        if getattr(result, 'reconciled', False):
            _notify_student_payment_confirmed(result.payment_id, event)


def _notify_student_payment_confirmed(payment_id, event) -> None:
    from finance.models import Payment
    from finance.payment_notifications import notify_payment_confirmed

    try:
        payment = Payment.objects.select_related('student').get(pk=payment_id)
        notify_payment_confirmed(payment)
    except Exception:
        logger.exception(
            '_notify_student_payment_confirmed: falha ao confirmar baixa. payment=%s event=%s',
            payment_id, event.event_id,
        )


def _record_stripe_payment_ref(*, payment_intent_id, session_id, box_schema, payment_id) -> None:
    """Grava/atualiza o mapa public payment_intent -> box (StripePaymentRef).

    Sem payment_intent nao da pra mapear (ex.: Sessions antigas ou metodos sem PI):
    nesse caso o evento charge.* correspondente cairia no fallback de operador.
    """
    if not payment_intent_id:
        return
    from integrations.stripe.models import StripePaymentRef

    StripePaymentRef.objects.update_or_create(
        payment_intent_id=payment_intent_id,
        defaults={
            'session_id': session_id,
            'box_schema': box_schema,
            'payment_id': payment_id,
        },
    )


def _resolve_box_schema(box_schema, event) -> str:
    """Valida o schema do box vindo da metadata contra um Box real.

    Defesa em profundidade: nunca abrir schema_context para um valor arbitrario.
    box_schema ausente/publico => Session criada antes do fix multi-tenant ou
    metadata adulterada. Falha NAO reprocessavel (ValueError) — o operador
    reconcilia manualmente e o evento fica no dead-letter com mensagem clara,
    em vez de falhar em silencio no schema public.
    """
    from django_tenants.utils import get_public_schema_name

    from control.models import Box

    if not box_schema or box_schema == get_public_schema_name():
        raise ValueError(
            f'Evento {event.event_id} sem box_schema valido na metadata — '
            f'impossivel reconciliar pagamento de aluno em multi-tenant '
            f'(box_schema={box_schema!r}).'
        )
    if not Box.objects.filter(schema_name=box_schema).exists():
        raise ValueError(
            f'Evento {event.event_id}: box_schema {box_schema!r} nao corresponde '
            f'a nenhum Box conhecido.'
        )
    return box_schema


def _handle_early_adopter_signup(event, session, metadata):
    """Marca o PendingSignup como pago e dispara email de ativacao.

    Falhas no envio do email sao logadas, mas nao falham o webhook — o
    operador pode reenviar manualmente pelo Django admin.
    """
    from signup.services import (
        generate_magic_token,
        mark_pending_signup_paid,
        send_onboarding_email,
    )

    pending_id = metadata.get('pending_signup_id')
    try:
        pending_id_int = int(pending_id)
    except (TypeError, ValueError):
        raise ValueError(f'pending_signup_id invalido no evento {event.event_id}: {pending_id!r}')

    pending = mark_pending_signup_paid(
        pending_signup_id=pending_id_int,
        stripe_session_id=session.get('id', ''),
        stripe_customer_id=session.get('customer', '') or '',
        stripe_subscription_id=session.get('subscription', '') or '',
    )
    if pending is None:
        return  # ja logado em mark_pending_signup_paid

    token = generate_magic_token(pending)
    activation_path = f'/onboarding/{token}/'
    site_url = _resolve_marketing_site_url()
    activation_url = f'{site_url}{activation_path}'

    sent = send_onboarding_email(pending, activation_url=activation_url)
    if not sent:
        logger.warning(
            '_handle_early_adopter_signup: email nao enviado para pending=%s. '
            'Operador pode reenviar pelo Django admin.',
            pending.pk,
        )


def _resolve_marketing_site_url() -> str:
    from django.conf import settings

    explicit = getattr(settings, 'MARKETING_SITE_URL', '').strip()
    if explicit:
        return explicit.rstrip('/')

    trusted = getattr(settings, 'CSRF_TRUSTED_ORIGINS', []) or []
    for origin in trusted:
        if 'octoboxfit' in origin and 'app.' not in origin:
            return origin.rstrip('/')

    return 'https://octoboxfit.com.br'




# ─────────────────────────────────────────────────────────────────────────────
# Ciclo de vida de billing do Box
#
# Tres eventos mexem no estado de billing de um Box:
#   invoice.payment_failed        -> SUSPENDED  (inadimplencia)
#   customer.subscription.deleted -> SUSPENDED  (cancelamento)
#   invoice.payment_succeeded     -> ACTIVE     (recuperacao)
#
# Todos passam pelos mesmos tres portoes, nesta ordem:
#   1. _resolve_box_for_billing — resolve o box, falhando FECHADO em ambiguidade.
#   2. _billing_event_is_stale  — descarta evento fora de ordem.
#   3. ARCHIVED e intocavel     — nenhum webhook ressuscita box arquivado.
# ─────────────────────────────────────────────────────────────────────────────


def _event_occurred_at(event: PaymentWebhookEvent):
    """Momento do evento no relogio da Stripe (nao o de chegada aqui).

    Retorna None se o envelope nao trouxer `created` utilizavel — nesse caso a
    guarda de ordenacao abre (fail-open): melhor processar do que travar billing.
    """
    created = event.payload.get('created')
    if not isinstance(created, int) or isinstance(created, bool):
        return None
    try:
        return datetime.fromtimestamp(created, tz=dt_timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _billing_event_is_stale(box, event: PaymentWebhookEvent) -> bool:
    """True se este evento e mais antigo que o ultimo ja aplicado neste box.

    Sem isto, um invoice.payment_succeeded da assinatura ANTIGA — reentregue
    pela Stripe ou pelo nosso proprio retry sweep — reativa um box cancelado.
    """
    occurred_at = _event_occurred_at(event)
    if occurred_at is None or box.billing_event_at is None:
        return False
    return occurred_at < box.billing_event_at


def _resolve_box_for_billing(subscription_id: str, customer_id: str, event: PaymentWebhookEvent):
    """Resolve o Box a partir dos ids da Stripe. Falha FECHADO em ambiguidade.

    Ordem: subscription_id (1:1 com box) e so entao customer_id (pode ser 1:N se
    o mesmo cliente tiver mais de um box). Se o customer_id casar com mais de um
    box, retorna None em vez de escolher um: suspender o box errado por causa de
    um `.first()` arbitrario e pior do que nao suspender nenhum.
    """
    from control.models import Box

    if subscription_id:
        por_assinatura = list(Box.objects.filter(stripe_subscription_id=subscription_id)[:2])
        if len(por_assinatura) > 1:
            # subscription_id deveria ser 1:1 com box. Se nao e, os dados estao
            # corrompidos e escolher um seria adivinhacao.
            logger.error(
                '_resolve_box_for_billing: subscription=%s casa com multiplos boxes — '
                'recusando agir. event=%s',
                subscription_id, event.event_id,
            )
            return None
        if por_assinatura:
            return por_assinatura[0]

    if not customer_id:
        return None

    candidates = list(Box.objects.filter(stripe_customer_id=customer_id)[:2])
    if len(candidates) > 1:
        logger.error(
            '_resolve_box_for_billing: customer=%s casa com multiplos boxes — '
            'recusando agir. event=%s subscription=%s',
            customer_id, event.event_id, subscription_id,
        )
        return None
    return candidates[0] if candidates else None


def _apply_billing_update(box, event: PaymentWebhookEvent, updates: dict) -> None:
    """Grava a mudanca de estado e avanca o relogio de billing do box, atomico.

    Sempre carimba billing_event_at, mesmo quando `updates` vem vazio: um evento
    que nao mudou nada ainda assim avanca o relogio e passa a barrar eventos
    anteriores a ele.
    """
    from control.models import Box

    occurred_at = _event_occurred_at(event)
    if occurred_at is not None:
        updates = {**updates, 'billing_event_at': occurred_at}
    if not updates:
        return
    Box.objects.filter(pk=box.pk).update(**updates)


def _suspend_box_for_billing(event: PaymentWebhookEvent, *, audit_kind: str, reason: str) -> None:
    """Caminho unico de suspensao por billing (inadimplencia ou cancelamento).

    SUSPENDED e nao ARCHIVED de proposito: preserva o schema intacto e mantem o
    caminho de volta automatico via invoice.payment_succeeded. Arquivar por
    webhook seria irreversivel (renomeia o schema) e nao cabe a um evento externo.
    """
    from control.models import Box
    from django.utils import timezone as dj_tz

    obj = event.payload.get('data', {}).get('object', {}) or {}
    subscription_id, customer_id = _extract_billing_ids(obj, event.event_type)

    if not subscription_id and not customer_id:
        logger.warning(
            '%s: evento sem subscription_id nem customer_id. event=%s',
            audit_kind, event.event_id,
        )
        return

    box = _resolve_box_for_billing(subscription_id, customer_id, event)
    if box is None:
        logger.info(
            '%s: nenhum Box resolvido. subscription=%s customer=%s event=%s',
            audit_kind, subscription_id, customer_id, event.event_id,
        )
        return

    if _billing_event_is_stale(box, event):
        logger.info(
            '%s: evento fora de ordem descartado. box=%s event=%s',
            audit_kind, box.slug, event.event_id,
        )
        return

    # ARCHIVED e terminal para webhooks: o schema foi renomeado para
    # archived_box_<slug>_<ts>, entao SUSPENDED aqui deixaria Box.status
    # apontando para um schema box_<slug> que nao existe mais. Volta so via
    # manage.py unarchive_box, com um humano no comando.
    if box.status == Box.Status.ARCHIVED:
        logger.warning(
            '%s: Box %s esta ARCHIVED — ignorado. event=%s',
            audit_kind, box.slug, event.event_id,
        )
        return

    if box.status == Box.Status.SUSPENDED:
        # Ja suspenso: nada muda, mas o relogio avanca para barrar eventos velhos.
        _apply_billing_update(box, event, {})
        logger.info('%s: Box %s ja estava SUSPENDED.', audit_kind, box.slug)
        return

    _apply_billing_update(box, event, {
        'status': Box.Status.SUSPENDED,
        'suspended_at': dj_tz.now(),
    })
    logger.warning(
        '%s: Box %s SUSPENSO (%s). event=%s', audit_kind, box.slug, reason, event.event_id,
    )
    _record_billing_audit(box, audit_kind, {
        'stripe_event_id': event.event_id,
        'event_type': event.event_type,
        'subscription_id': subscription_id,
        'customer_id': customer_id,
        'reason': reason,
    })


def _extract_billing_ids(obj: dict, event_type: str) -> tuple[str, str]:
    """Extrai (subscription_id, customer_id) do objeto do evento.

    O envelope difere por tipo: em `invoice.*` a assinatura vem em
    `object.subscription`; em `customer.subscription.*` o proprio objeto E a
    assinatura, entao o id esta em `object.id`.
    """
    customer_id = obj.get('customer') or ''
    if event_type.startswith('customer.subscription.'):
        return obj.get('id') or '', customer_id
    return obj.get('subscription') or '', customer_id


def _record_billing_audit(box, kind: str, payload: dict) -> None:
    """Audit em public. Nunca propaga: log de auditoria nao derruba o webhook."""
    from control.models import PlatformAuditEvent

    try:
        PlatformAuditEvent.objects.create(target_box=box, kind=kind, payload=payload)
    except Exception:
        logger.exception('_record_billing_audit: falha ao registrar %s para box=%s', kind, box.slug)


def _handle_invoice_payment_failed(event: PaymentWebhookEvent) -> None:
    """Suspende o Box quando a cobranca da assinatura falha (inadimplencia)."""
    _suspend_box_for_billing(
        event,
        audit_kind='box.suspended_payment_failed',
        reason='payment_failed',
    )


def _handle_subscription_deleted(event: PaymentWebhookEvent) -> None:
    """Suspende o Box quando a assinatura e cancelada.

    Antes disto, cancelar no Stripe nao produzia efeito nenhum: o box seguia
    ACTIVE e o dono continuava usando de graca indefinidamente. Cancelamento
    limpo nao gera invoice.payment_failed, entao nao havia nada que o pegasse.
    """
    _suspend_box_for_billing(
        event,
        audit_kind='box.suspended_subscription_canceled',
        reason='subscription_canceled',
    )


def _handle_invoice_payment_succeeded(event: PaymentWebhookEvent) -> None:
    """Reativa o Box quando a cobranca volta a passar.

    Cobre os dois caminhos de volta:
    - retry da MESMA assinatura apos falha  -> resolve por subscription_id;
    - cliente cancelou e assinou DE NOVO    -> a assinatura nova tem outro id, o
      box e resolvido pelo customer_id e o ponteiro stripe_subscription_id e
      religado aqui (rebind). Sem isso o box voltaria a ficar orfao no proximo
      ciclo, apontando para uma assinatura morta.
    """
    from control.models import Box

    invoice = event.payload.get('data', {}).get('object', {}) or {}
    subscription_id, customer_id = _extract_billing_ids(invoice, event.event_type)

    box = _resolve_box_for_billing(subscription_id, customer_id, event)
    if box is None:
        return  # nao e um box conhecido — ignorar silenciosamente

    if _billing_event_is_stale(box, event):
        logger.info(
            '_handle_invoice_payment_succeeded: evento fora de ordem descartado. '
            'box=%s event=%s',
            box.slug, event.event_id,
        )
        return

    if box.status == Box.Status.ARCHIVED:
        # Pagamento entrando para um box arquivado: nao reativa sozinho (o schema
        # foi renomeado). Registra para o operador decidir entre unarchive_box e
        # estornar a cobranca — silenciar aqui esconderia dinheiro sem entrega.
        logger.warning(
            '_handle_invoice_payment_succeeded: pagamento para Box ARCHIVED %s — '
            'requer unarchive manual. event=%s',
            box.slug, event.event_id,
        )
        _record_billing_audit(box, 'billing.payment_on_archived_box', {
            'stripe_event_id': event.event_id,
            'subscription_id': subscription_id,
            'customer_id': customer_id,
        })
        return

    updates = {}

    # Rebind so quando o box esta de fato "voltando": SUSPENDED, ou sem ponteiro
    # nenhum. Religar a assinatura de um box ACTIVE seria assumir que uma cobranca
    # desconhecida no mesmo customer passa a mandar no box — se o cliente tiver
    # mais de uma assinatura na Stripe, isso sequestraria o ponteiro. Nesse caso
    # so registramos para o operador olhar.
    pode_religar = (
        box.status == Box.Status.SUSPENDED or not box.stripe_subscription_id
    )
    if subscription_id and box.stripe_subscription_id != subscription_id and not pode_religar:
        logger.warning(
            '_handle_invoice_payment_succeeded: Box %s ACTIVE recebeu pagamento de '
            'assinatura diferente (box=%s, evento=%s) — ponteiro NAO alterado. event=%s',
            box.slug, box.stripe_subscription_id, subscription_id, event.event_id,
        )
        _record_billing_audit(box, 'billing.subscription_mismatch', {
            'stripe_event_id': event.event_id,
            'subscription_id_do_box': box.stripe_subscription_id,
            'subscription_id_do_evento': subscription_id,
            'customer_id': customer_id,
        })

    if subscription_id and box.stripe_subscription_id != subscription_id and pode_religar:
        updates['stripe_subscription_id'] = subscription_id
        logger.info(
            '_handle_invoice_payment_succeeded: religando Box %s a assinatura %s '
            '(anterior=%s). event=%s',
            box.slug, subscription_id, box.stripe_subscription_id or '-', event.event_id,
        )
        _record_billing_audit(box, 'billing.subscription_rebound', {
            'stripe_event_id': event.event_id,
            'subscription_id_anterior': box.stripe_subscription_id,
            'subscription_id_novo': subscription_id,
            'customer_id': customer_id,
        })

    reactivated = box.status == Box.Status.SUSPENDED
    if reactivated:
        updates['status'] = Box.Status.ACTIVE
        updates['suspended_at'] = None

    _apply_billing_update(box, event, updates)

    if reactivated:
        logger.info(
            '_handle_invoice_payment_succeeded: Box %s REATIVADO apos pagamento. event=%s',
            box.slug, event.event_id,
        )
        _record_billing_audit(box, 'box.reactivated_payment_recovered', {
            'stripe_event_id': event.event_id,
            'subscription_id': subscription_id,
        })


def _lookup_payment_ref(payment_intent_id):
    """Resolve o StripePaymentRef (mapa public payment_intent -> box) ou None."""
    if not payment_intent_id:
        return None
    from integrations.stripe.models import StripePaymentRef

    return StripePaymentRef.objects.filter(payment_intent_id=payment_intent_id).first()


def _handle_charge_refunded(event: PaymentWebhookEvent) -> None:
    """charge.refunded: reflete no OctoBox um estorno feito do lado da Stripe.

    O evento traz um charge com payment_intent; resolvemos o box pelo
    StripePaymentRef (gravado na reconciliacao do checkout) e marcamos o Payment
    como REFUNDED no schema do box. Charge sem ref conhecido (ex.: checkout de
    early adopter) e ignorado (no-op) para nao poluir o dead-letter.
    """
    from django_tenants.utils import schema_context
    from finance.application.use_cases import execute_refund_payment_from_stripe_use_case

    charge = event.payload.get('data', {}).get('object', {})
    payment_intent_id = charge.get('payment_intent') or ''
    ref = _lookup_payment_ref(payment_intent_id)
    if ref is None:
        logger.info(
            '_handle_charge_refunded: sem StripePaymentRef para pi=%s. event=%s (ignorado).',
            payment_intent_id, event.event_id,
        )
        return

    with schema_context(ref.box_schema):
        execute_refund_payment_from_stripe_use_case(
            payment_id=ref.payment_id,
            stripe_charge_id=charge.get('id') or '',
            stripe_event_id=event.event_id,
        )


def _handle_charge_dispute(event: PaymentWebhookEvent) -> None:
    """charge.dispute.created/closed: registra a disputa (chargeback) para
    observabilidade. Resolve o box via StripePaymentRef e grava audit event no
    schema do box. Nao muda o status do Payment — o desfecho financeiro chega
    como charge.refunded (perdida) ou nada (ganha).
    """
    from django_tenants.utils import schema_context

    dispute = event.payload.get('data', {}).get('object', {})
    payment_intent_id = dispute.get('payment_intent') or ''
    ref = _lookup_payment_ref(payment_intent_id)
    if ref is None:
        logger.info(
            '_handle_charge_dispute: sem StripePaymentRef para pi=%s. event=%s',
            payment_intent_id, event.event_id,
        )
        return

    logger.warning(
        '_handle_charge_dispute: DISPUTA box=%s payment=%s status=%s event=%s',
        ref.box_schema, ref.payment_id, dispute.get('status', ''), event.event_id,
    )
    with schema_context(ref.box_schema):
        _record_dispute_audit(ref.payment_id, dispute, event)


def _record_dispute_audit(payment_id, dispute, event) -> None:
    from auditing import log_audit_event
    from finance.models import Payment

    payment = Payment.objects.filter(pk=payment_id).first()
    if payment is None:
        return
    log_audit_event(
        actor=None,
        action='payment_dispute_via_stripe',
        target=payment,
        description=f'Disputa/chargeback Stripe ({event.event_type}) status={dispute.get("status", "")}',
        metadata={
            'stripe_event_id': event.event_id,
            'event_type': event.event_type,
            'dispute_status': dispute.get('status', ''),
            'dispute_reason': dispute.get('reason', ''),
        },
    )


_HANDLERS = {
    'checkout.session.completed': _handle_checkout_session_completed,
    # Onda 3: Pix (delayed-notification) confirma/expira DEPOIS do completed
    # inicial — mesmo roteador, mesmo payload shape (data.object = Session).
    'checkout.session.async_payment_succeeded': _handle_checkout_session_completed,
    'checkout.session.async_payment_failed': _handle_checkout_session_completed,
    'invoice.payment_failed': _handle_invoice_payment_failed,       # Sprint 3: suspende Box
    'invoice.payment_succeeded': _handle_invoice_payment_succeeded, # Sprint 3: reativa Box
    'customer.subscription.deleted': _handle_subscription_deleted,  # cancelamento: suspende Box
    'charge.refunded': _handle_charge_refunded,                     # P2.2: estorno do lado Stripe
    'charge.dispute.created': _handle_charge_dispute,               # P2.2: chargeback (observabilidade)
    'charge.dispute.closed': _handle_charge_dispute,
}

__all__ = ['route_payment_webhook_event']
