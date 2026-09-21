"""Acquisition cohorts, distinct visitors and first positive payments.

The cookie identifies a browser for 90 days, not a person. Browser signals
are diagnostic only: the financial ledger is the source of paid conversion.
"""
from datetime import timedelta

from django.db.models import F, Min, OuterRef, Q, Subquery
from django.utils import timezone

from .acquisition import tracking_enabled
from .models import PublicWorkoutAcquisitionSession, PublicWorkoutPayment, PublicWorkoutPaymentStatus


SIGNALS = {
    'landing_viewed': 'Abriu a landing',
    'cta_clicked': 'Clicou para ver planos',
    'pricing_viewed': 'Visualizou os preços',
    'signup_started': 'Começou o formulário',
    'signup_submitted': 'Enviou o formulário',
    'tier_selected': 'Cadastro aceito pelo servidor',
    'checkout_started': 'Checkout criado',
    'checkout_redirected': 'Redirecionamento ao checkout',
    'checkout_authorized': 'Checkout confirmado pela Stripe',
    'signup_invalid': 'Validação impediu envio',
    'signup_failed': 'Falha percebida no formulário',
    'checkout_failed': 'Servidor não iniciou checkout',
    'payment_failed': 'Pagamento recusado ou falhou',
    'login_required': 'Precisou entrar na conta',
    'waitlist_joined': 'Entrou na lista de prioridade',
    'checkout_canceled': 'Voltou sem concluir checkout',
    'faq_opened': 'Abriu uma dúvida frequente',
}


def percent(value, total):
    return round(100 * value / total, 2) if total else None


def build_acquisition_report(*, at=None, window_days=30, conversion_days=7):
    """First seen in [at-window, at]; conversion within N days of first seen.

    Repeated pageviews and recurring invoices never increase conversions.
    Refunded first payments remain acquisitions; refunds are shown separately.
    Existing payers at arrival are excluded from the acquisition denominator.
    """
    if not 1 <= window_days <= 90 or not 1 <= conversion_days <= 30:
        raise ValueError('Invalid analytics window')
    at = at or timezone.now()
    since = at - timedelta(days=window_days)
    positive_payments = PublicWorkoutPayment.objects.filter(
        paid_at__isnull=False, paid_at__lte=at, gross_amount__gt=0,
        status__in=(PublicWorkoutPaymentStatus.PAID, PublicWorkoutPaymentStatus.REFUNDED),
    )
    first_payment = positive_payments.filter(
        subscription__account_id=OuterRef('account_id'),
    ).order_by('paid_at', 'pk')
    sessions = PublicWorkoutAcquisitionSession.objects.filter(
        first_seen_at__gte=since, first_seen_at__lte=at,
    ).annotate(
        first_paid_at=Subquery(first_payment.values('paid_at')[:1]),
        first_payment_status=Subquery(first_payment.values('status')[:1]),
        **{
            'signal_' + key: Min('events__occurred_at', filter=Q(
                events__event_type=key, events__occurred_at__lte=at,
                events__occurred_at__gte=since,
            )) for key in SIGNALS
        },
    ).filter(signal_landing_viewed__isnull=False).values(
        'id', 'first_seen_at', 'first_source', 'first_medium', 'first_campaign',
        'landing_variant', 'first_paid_at', 'first_payment_status',
        *('signal_' + key for key in SIGNALS),
    )
    counts = [0, 0, 0, 0]
    mature_counts = [0, 0, 0, 0]
    signals = {key: 0 for key in SIGNALS}
    channels = {}
    refunded = excluded = 0
    observed_pairs = {
        ('pricing_viewed', 'signup_started'): [0, 0],
        ('signup_started', 'signup_submitted'): [0, 0],
        ('signup_submitted', 'checkout_started'): [0, 0],
    }
    for row in sessions.iterator(chunk_size=1000):
        start = row['first_seen_at']
        if row['first_paid_at'] and row['first_paid_at'] < start:
            excluded += 1
            continue
        deadline = min(at, start + timedelta(days=conversion_days))
        mature = start + timedelta(days=conversion_days) <= at
        seen = {key for key in SIGNALS if row['signal_' + key] is not None
                and start <= row['signal_' + key] <= deadline}
        paid = row['first_paid_at'] is not None and start <= row['first_paid_at'] <= deadline
        # A downstream commercial fact implies preceding commercial stages;
        # optional JS signals never gate payment conversion.
        checkout = 'checkout_started' in seen or paid
        accepted = 'tier_selected' in seen or checkout
        reached = (True, accepted, checkout, paid)
        for index, value in enumerate(reached):
            counts[index] += int(value)
            mature_counts[index] += int(value and mature)
        refunded += int(paid and row['first_payment_status'] == PublicWorkoutPaymentStatus.REFUNDED)
        for signal in seen:
            signals[signal] += 1
        for (before, after), values in observed_pairs.items():
            if mature and before in seen:
                values[0] += 1
                values[1] += int(after not in seen and not paid and not checkout)
        channel = (row['first_source'] or '(direto/desconhecido)', row['first_medium'],
                   row['first_campaign'], row['landing_variant'])
        item = channels.setdefault(channel, {'visitors': 0, 'paid': 0, 'mature_visitors': 0, 'mature_paid': 0})
        item['visitors'] += 1
        item['paid'] += int(paid)
        item['mature_visitors'] += int(mature)
        item['mature_paid'] += int(mature and paid)
    steps = []
    for index, label in enumerate(('Visitantes', 'Cadastro aceito', 'Checkout criado', 'Primeiro pagamento')):
        previous = counts[index - 1] if index else counts[0]
        steps.append({
            'label': label, 'visitors': counts[index],
            'visitor_percent': percent(counts[index], counts[0]),
            'previous_percent': percent(counts[index], previous),
            'mature_visitors': mature_counts[index],
            'not_advanced': mature_counts[index] - mature_counts[index + 1] if index < 3 else None,
            'not_advanced_percent': percent(mature_counts[index] - mature_counts[index + 1], mature_counts[index]) if index < 3 else None,
        })
    channel_rows = [
        dict(zip(('source', 'medium', 'campaign', 'variant'), key), **value,
             conversion_percent=percent(value['paid'], value['visitors']),
             mature_conversion_percent=percent(value['mature_paid'], value['mature_visitors']))
        for key, value in channels.items()
    ]
    # Period coverage is intentionally separate from cohort conversion.
    first_payments_in_period = positive_payments.values('subscription__account_id').annotate(
        first_paid=Min('paid_at'),
    ).filter(first_paid__gte=since)
    period_accounts = first_payments_in_period.values('subscription__account_id')
    total_new_payers = first_payments_in_period.count()
    linked_new_payers = PublicWorkoutAcquisitionSession.objects.filter(
        account_id__in=Subquery(period_accounts),
    ).annotate(first_paid=Subquery(first_payment.values('paid_at')[:1])).filter(
        events__event_type='landing_viewed', events__occurred_at__lte=F('first_paid'),
    ).values('account_id').distinct().count()
    return {
        'schema_version': 1, 'tracking_enabled': tracking_enabled(), 'generated_at': at.isoformat(),
        'window_days': window_days, 'conversion_days': conversion_days,
        'visitors': counts[0], 'paid': counts[3], 'conversion_percent': percent(counts[3], counts[0]),
        'mature_visitors': mature_counts[0], 'mature_paid': mature_counts[3],
        'mature_conversion_percent': percent(mature_counts[3], mature_counts[0]),
        'pending_visitors': counts[0] - mature_counts[0], 'excluded_existing_customers': excluded,
        'refunded_first_payments': refunded, 'steps': steps,
        'signals': [{'event': key, 'label': label, 'visitors': signals[key],
                     'visitor_percent': percent(signals[key], counts[0])} for key, label in SIGNALS.items()],
        'friction': [{'label': f'{SIGNALS[before]} → {SIGNALS[after]}', 'visitors': values[0],
                      'not_advanced': values[1], 'not_advanced_percent': percent(values[1], values[0])}
                     for (before, after), values in observed_pairs.items()],
        'channels': sorted(channel_rows, key=lambda item: (-item['visitors'], item['source'])),
        'coverage': {'new_payers_in_period': total_new_payers, 'linked_new_payers': linked_new_payers,
                     'linked_percent': percent(linked_new_payers, total_new_payers)},
    }
