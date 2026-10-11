"""Acquisition cohorts, distinct visitors and first positive payments.

The cookie identifies a browser for 90 days, not a person. Browser signals
are diagnostic only: the financial ledger is the source of paid conversion.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Min, OuterRef, Q, Subquery
from django.utils import timezone

from .acquisition import tracking_enabled
from .models import (
    PublicWorkoutAcquisitionSession, PublicWorkoutFunnelEvent,
    PublicWorkoutPayment, PublicWorkoutPaymentStatus,
)


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

INFLUENCER_NAMES = {'jully': 'Jully'}
INFLUENCER_COMMISSION_RATE = Decimal('0.60')


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
        subscription_id=OuterRef('subscription_id'),
    ).order_by('paid_at', 'pk')
    sessions = PublicWorkoutAcquisitionSession.objects.filter(
        partner_code='',
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
        'id', 'account_id', 'subscription_id', 'first_seen_at', 'first_source', 'first_medium', 'first_campaign',
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
    own_positive_payments = positive_payments.filter(
        Q(subscription__acquisition_session__isnull=True)
        | Q(subscription__acquisition_session__partner_code='')
    )
    first_payments_in_period = own_positive_payments.values('subscription__account_id').annotate(
        first_paid=Min('paid_at'),
    ).filter(first_paid__gte=since)
    period_accounts = first_payments_in_period.values('subscription__account_id')
    total_new_payers = first_payments_in_period.count()
    linked_new_payers = PublicWorkoutAcquisitionSession.objects.filter(
        partner_code='',
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


def build_influencer_report(*, partner_code, at=None, window_days=30, conversion_days=7):
    """Build a partner-only acquisition cohort with first-invoice economics.

    Partner traffic is measured from the first partner touch, not from an
    earlier visit to the general Curva landing page. Only the first positive
    invoice may contribute revenue or the one-time commission estimate.
    """
    partner_code = (partner_code or '').strip().lower()
    if partner_code not in INFLUENCER_NAMES:
        raise ValueError('Unknown influencer')
    if not 1 <= window_days <= 90 or not 1 <= conversion_days <= 30:
        raise ValueError('Invalid analytics window')

    at = at or timezone.now()
    since = at - timedelta(days=window_days)
    positive_payments = PublicWorkoutPayment.objects.filter(
        paid_at__isnull=False, paid_at__lte=at, gross_amount__gt=0,
        status__in=(PublicWorkoutPaymentStatus.PAID, PublicWorkoutPaymentStatus.REFUNDED),
        subscription_id=OuterRef('subscription_id'),
    ).order_by('paid_at', 'pk')
    sessions = PublicWorkoutAcquisitionSession.objects.filter(
        partner_code=partner_code,
        partner_first_seen_at__gte=since,
        partner_first_seen_at__lte=at,
    ).annotate(
        first_paid_at=Subquery(positive_payments.values('paid_at')[:1]),
        first_payment_status=Subquery(positive_payments.values('status')[:1]),
        first_paid_amount=Subquery(positive_payments.values('gross_amount')[:1]),
    ).order_by('partner_first_seen_at', 'id').values(
        'id', 'account_id', 'partner_first_seen_at', 'first_paid_at',
        'first_payment_status', 'first_paid_amount',
    )
    session_rows = list(sessions.iterator(chunk_size=1000))
    session_ids = [row['id'] for row in session_rows]
    events_by_session = {}
    for row in PublicWorkoutFunnelEvent.objects.filter(
        partner_code=partner_code,
        acquisition_session_id__in=session_ids,
        occurred_at__gte=since,
        occurred_at__lte=at,
        event_type__in=('signup_submitted', 'checkout_started'),
    ).values('acquisition_session_id', 'event_type').annotate(first_event=Min('occurred_at')):
        events_by_session.setdefault(row['acquisition_session_id'], {})[row['event_type']] = row['first_event']

    paid_accounts = set()
    visitors = signups = checkouts = paid = mature_visitors = mature_paid = 0
    refunded = 0
    revenue = Decimal('0.00')
    commission_estimate = Decimal('0.00')
    for row in session_rows:
        started = row['partner_first_seen_at']
        first_paid_at = row['first_paid_at']
        if first_paid_at and first_paid_at < started:
            continue
        deadline = min(at, started + timedelta(days=conversion_days))
        mature = started + timedelta(days=conversion_days) <= at
        events = events_by_session.get(row['id'], {})
        did_signup = events.get('signup_submitted') is not None and started <= events['signup_submitted'] <= deadline
        did_checkout = events.get('checkout_started') is not None and started <= events['checkout_started'] <= deadline
        is_paid = bool(first_paid_at and started <= first_paid_at <= deadline)

        visitors += 1
        signups += int(did_signup)
        checkouts += int(did_checkout)
        mature_visitors += int(mature)
        account_id = row['account_id']
        unique_paid = bool(is_paid and account_id and account_id not in paid_accounts)
        paid += int(unique_paid)
        mature_paid += int(mature and unique_paid)
        if not unique_paid:
            continue
        paid_accounts.add(account_id)
        amount = row['first_paid_amount'] or Decimal('0.00')
        if row['first_payment_status'] == PublicWorkoutPaymentStatus.REFUNDED:
            refunded += 1
            continue
        revenue += amount
        commission_estimate += (amount * INFLUENCER_COMMISSION_RATE).quantize(Decimal('0.01'))

    clicks = PublicWorkoutFunnelEvent.objects.filter(
        partner_code=partner_code,
        event_type='influencer_link_clicked',
        occurred_at__gte=since,
        occurred_at__lte=at,
    ).count()
    return {
        'schema_version': 1,
        'tracking_enabled': tracking_enabled(),
        'partner_code': partner_code,
        'partner_name': INFLUENCER_NAMES[partner_code],
        'generated_at': at.isoformat(),
        'window_days': window_days,
        'conversion_days': conversion_days,
        'commission_rate_percent': int(INFLUENCER_COMMISSION_RATE * 100),
        'clicks': clicks,
        'visitors': visitors,
        'signups': signups,
        'checkouts': checkouts,
        'paid': paid,
        'mature_visitors': mature_visitors,
        'mature_paid': mature_paid,
        'pending_visitors': visitors - mature_visitors,
        'refunded_first_payments': refunded,
        'conversion_percent': percent(paid, visitors),
        'mature_conversion_percent': percent(mature_paid, mature_visitors),
        'revenue': revenue.quantize(Decimal('0.01')),
        'commission_estimate': commission_estimate.quantize(Decimal('0.01')),
        'steps': [
            {'label': 'Aberturas do link', 'visitors': clicks},
            {'label': 'Visitantes únicos', 'visitors': visitors},
            {'label': 'Cadastros', 'visitors': signups},
            {'label': 'Checkouts', 'visitors': checkouts},
            {'label': 'Primeiros pagamentos', 'visitors': paid},
        ],
    }
