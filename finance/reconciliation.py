"""
ARQUIVO: reconciliacao Stripe<->DB (rede de seguranca de fidelidade).

POR QUE ELE EXISTE:
- O webhook + o dead-letter sweep cobrem o fluxo normal, mas um evento que a
  Stripe nunca enviou (ou que o sweep esgotou) deixaria o Payment divergente em
  silencio. Este job le o estado real na Stripe e REPORTA divergencias para o
  operador agir — read-only na v1 (nao muta status automaticamente).

O QUE ELE FAZ:
1. Itera os boxes ativos (Payment e TENANT_APP) via schema_context.
2. Para cada Payment com vinculo Stripe atualizado na janela, le o PaymentIntent
   na Stripe e compara com o status local.
3. Registra cada divergencia como audit event (payment_stripe_drift) e devolve um
   relatorio agregado.

PONTOS CRITICOS:
- Roda a partir do schema public (cron); Box e SHARED.
- Read-only: nenhuma baixa/estorno e aplicado aqui — so deteccao e trilha.
"""

from datetime import timedelta

from django.utils import timezone
from django_tenants.utils import schema_context


def _detect_drift(local_status, state) -> str | None:
    from finance.models import PaymentStatus

    pi_status = state.get('pi_status', '') or ''
    refunded = bool(state.get('refunded', False))

    if refunded and local_status != PaymentStatus.REFUNDED:
        return 'stripe_refunded_local_not'
    if local_status == PaymentStatus.REFUNDED and not refunded:
        return 'local_refunded_stripe_not'
    if local_status == PaymentStatus.PAID and pi_status and pi_status != 'succeeded':
        return 'local_paid_pi_not_succeeded'
    return None


def reconcile_stripe_payments(*, days: int = 7, limit: int = 100, now=None) -> dict:
    from auditing import log_audit_event
    from control.models import Box
    from finance.models import Payment
    from integrations.stripe.services import get_stripe_payment_state

    current = now or timezone.now()
    since = current - timedelta(days=days)
    checked = 0
    drift: list[dict] = []

    for box in Box.objects.filter(status=Box.Status.ACTIVE):
        with schema_context(box.schema_name):
            payments = (
                Payment.objects
                .exclude(stripe_payment_intent_id='')
                .filter(updated_at__gte=since)
                .order_by('-updated_at')[:limit]
            )
            for payment in payments:
                checked += 1
                state = get_stripe_payment_state(payment.stripe_payment_intent_id)
                if state is None:
                    continue
                reason = _detect_drift(payment.status, state)
                if reason is None:
                    continue
                entry = {
                    'box': box.schema_name,
                    'payment_id': payment.id,
                    'reason': reason,
                    'local_status': payment.status,
                    'pi_status': state.get('pi_status', ''),
                    'refunded': bool(state.get('refunded', False)),
                }
                drift.append(entry)
                log_audit_event(
                    actor=None,
                    action='payment_stripe_drift',
                    target=payment,
                    description=f'Divergencia Stripe<->DB: {reason}',
                    metadata=entry,
                )

    return {
        'checked_at': current.isoformat(),
        'checked': checked,
        'drift_count': len(drift),
        'drift': drift,
    }


def reconcile_partner_statement(*, partner: str, rows, statement_reference: str = '', now=None) -> dict:
    """Bate o extrato oficial da Wellhub/TotalPass (manual por enquanto) contra
    o ledger interno de PartnerCheckInCharge. So aqui um check-in de parceiro
    vira receita reconhecida (status=RECONCILED, declared_value preenchido).

    rows: iteravel de dicts {'student_phone': str, 'date': 'YYYY-MM-DD' ou date,
    'value': Decimal-like}. Formato de entrada e deliberadamente generico —
    hoje alimentado por CSV manual (management command), amanha por uma API
    da propria operadora sem mudar esta funcao.
    """

    from datetime import datetime as dt

    from auditing import log_audit_event
    from control.models import Box
    from django_tenants.utils import schema_context
    from finance.model_definitions import PartnerCheckInCharge, PartnerCheckInStatus

    current = now or timezone.now()

    normalized_rows = []
    for row in rows:
        raw_date = row.get('date')
        row_date = dt.strptime(raw_date, '%Y-%m-%d').date() if isinstance(raw_date, str) else raw_date
        normalized_rows.append({
            'phone': (row.get('student_phone') or '').strip(),
            'date': row_date,
            'value': row.get('value'),
        })

    matched = 0
    orphans: list[dict] = []

    for box in Box.objects.filter(status=Box.Status.ACTIVE):
        with schema_context(box.schema_name):
            candidates = (
                PartnerCheckInCharge.objects
                .filter(
                    partner=partner,
                    status__in=[
                        PartnerCheckInStatus.PENDING,
                        PartnerCheckInStatus.REMINDED,
                        PartnerCheckInStatus.CONFIRMED,
                    ],
                )
                .select_related('attendance__session', 'enrollment__student')
            )
            by_key: dict[tuple, list] = {}
            for charge in candidates:
                phone = (getattr(charge.enrollment.student, 'phone', '') or '').strip()
                session_date = charge.attendance.session.scheduled_at.date()
                by_key.setdefault((phone, session_date), []).append(charge)

            for row in normalized_rows:
                bucket = by_key.get((row['phone'], row['date']))
                if not bucket:
                    orphans.append({'box': box.schema_name, **row})
                    continue
                charge = bucket.pop(0)
                charge.status = PartnerCheckInStatus.RECONCILED
                charge.declared_value = row['value']
                charge.reconciled_at = current
                charge.statement_reference = statement_reference
                charge.save(update_fields=['status', 'declared_value', 'reconciled_at', 'statement_reference', 'updated_at'])
                matched += 1
                log_audit_event(
                    actor=None,
                    action='partner_checkin_reconciled',
                    target=charge,
                    description=f'Check-in {partner} reconciliado via extrato {statement_reference}',
                    metadata={'box': box.schema_name, 'value': str(row['value'])},
                )

    return {
        'checked_at': current.isoformat(),
        'partner': partner,
        'matched': matched,
        'orphan_count': len(orphans),
        'orphans': orphans,
    }


def flag_stale_partner_checkins(*, older_than_days: int = 3, now=None) -> dict:
    """Presenca interna de aluno de parceiro sem confirmacao nem reconciliacao
    depois do prazo vira DISPUTED — sinal pro dono agir (cobrar o aluno
    direto, ou investigar por que o parceiro nao confirmou), nunca vira
    receita presumida."""

    from auditing import log_audit_event
    from control.models import Box
    from django_tenants.utils import schema_context
    from finance.model_definitions import PartnerCheckInCharge, PartnerCheckInStatus

    current = now or timezone.now()
    threshold = current - timedelta(days=older_than_days)
    flagged: list[dict] = []

    for box in Box.objects.filter(status=Box.Status.ACTIVE):
        with schema_context(box.schema_name):
            stale = PartnerCheckInCharge.objects.filter(
                status__in=[PartnerCheckInStatus.PENDING, PartnerCheckInStatus.REMINDED],
                created_at__lt=threshold,
            )
            for charge in stale:
                charge.status = PartnerCheckInStatus.DISPUTED
                charge.save(update_fields=['status', 'updated_at'])
                flagged.append({'box': box.schema_name, 'charge_id': charge.id})
                log_audit_event(
                    actor=None,
                    action='partner_checkin_unconfirmed',
                    target=charge,
                    description='Check-in de parceiro sem confirmacao nem reconciliacao apos o prazo.',
                    metadata={'box': box.schema_name},
                )

    return {
        'checked_at': current.isoformat(),
        'flagged_count': len(flagged),
        'flagged': flagged,
    }


__all__ = ['flag_stale_partner_checkins', 'reconcile_partner_statement', 'reconcile_stripe_payments']
