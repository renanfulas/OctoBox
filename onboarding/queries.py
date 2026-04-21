"""
ARQUIVO: consultas de leitura do domínio onboarding.

POR QUE ELE EXISTE:
- dá ownership próprio para leads e intakes sem depender da fronteira de communications.

O QUE ESTE ARQUIVO FAZ:
1. resume métricas de entradas pendentes.
2. expõe listas curtas para triagem e workspaces operacionais.
3. monta a leitura principal da Central de Intake.

PONTOS CRÍTICOS:
- essas consultas abastecem shell, operação, onboarding e alunos; qualquer regressão aqui aparece como fila quebrada ou contagem errada.
"""

from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Count, Max, Q
from django.utils import timezone
from onboarding.attribution import summarize_acquisition_channels
from onboarding.facade import build_intake_queue_item
from onboarding.forms import IntakeCenterFilterForm, IntakeQuickCreateForm
from onboarding.models import IntakeSource, IntakeStatus, StudentIntake
from shared_support.kpi_icons import build_kpi_icon


def _intake_kpi_icon(name):
    icon_map = {
        'queue': 'queue',
        'conversation': 'conversation',
        'today': 'today',
        'owners': 'owners',
    }
    return build_kpi_icon(icon_map.get(name, ''))


def count_pending_intakes():
    return StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING],
        linked_student__isnull=True,
    ).count()


def build_onboarding_headline_metrics(*, today):
    return {
        'pending_intakes': count_pending_intakes(),
    }


def get_pending_intakes(*, limit=8):
    return StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING],
        linked_student__isnull=True,
    ).select_related('linked_student', 'assigned_to').order_by('status', '-created_at')[:limit]


def get_intake_conversion_queue(*, limit=8):
    return StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
        linked_student__isnull=True,
    ).select_related('linked_student', 'assigned_to').order_by('status', '-created_at')[:limit]


def _resolve_queue_ordering(*, sort_value):
    if sort_value == 'registration-oldest':
        return ('created_at', 'id')
    if sort_value == 'registration-newest':
        return ('-created_at', '-id')
    return ('status', '-created_at')


def _build_intake_radar_board(*, params, metrics_queryset, today):
    source_period = (params.get('source_period') or 'all').strip().lower()
    if source_period not in {'day', 'week', 'month', 'all'}:
        source_period = 'day'

    radar_queryset = metrics_queryset.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
    )
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    if source_period == 'week':
        radar_queryset = radar_queryset.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=today,
        )
        period_label = 'Semana'
        copy = 'Leia quem entrou nesta semana sem misturar volume antigo na decisão.'
    elif source_period == 'month':
        radar_queryset = radar_queryset.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=today,
        )
        period_label = 'Mês'
        copy = 'Leia o acumulado do mês atual para entender quais canais sustentam a captação agora.'
    elif source_period == 'all':
        period_label = 'Todos'
        copy = 'Leia o histórico inteiro para enxergar quais canais mais sustentam a captação.'
    else:
        radar_queryset = radar_queryset.filter(created_at__date=today)
        period_label = 'Hoje'
        copy = 'Compare quem entrou hoje em uma leitura curta, direta e acionável.'

    radar_rows = list(radar_queryset.values_list('source', 'raw_payload'))
    acquisition_counts = summarize_acquisition_channels(radar_rows)
    source_counts = dict(radar_queryset.values_list('source').annotate(total=Count('id')))
    total = len(radar_rows)

    base_params = params.copy() if hasattr(params, 'copy') else dict(params)
    base_params.pop('source_period', None)
    base_params['panel'] = 'tab-intake-source'

    periods = []
    for key, label in (('day', 'Hoje'), ('week', 'Semana'), ('month', 'Mês'), ('all', 'Todos')):
        period_params = base_params.copy()
        period_params['source_period'] = key
        periods.append(
            {
                'key': key,
                'label': label,
                'href': f"?{urlencode(period_params, doseq=True)}",
                'is_active': source_period == key,
            }
        )

    return {
        'key': 'intake-radar',
        'eyebrow': 'Radar comercial',
        'title': 'Canais de entrada',
        'copy': copy,
        'summary': f'{total} lead(s) em {period_label.lower()}.',
        'period': source_period,
        'period_label': period_label,
        'total': total,
        'periods': periods,
        'cards': [
            {'key': 'referral', 'label': 'Indicação', 'value': acquisition_counts.get('referral', 0)},
            {'key': 'instagram', 'label': 'Instagram', 'value': acquisition_counts.get('instagram', 0)},
            {'key': 'walk_in', 'label': 'Passei na frente', 'value': acquisition_counts.get('walk_in', 0)},
            {'key': 'google', 'label': 'Google', 'value': acquisition_counts.get('google', 0)},
            {'key': 'whatsapp', 'label': 'WhatsApp', 'value': acquisition_counts.get('whatsapp', 0)},
            {'key': 'website', 'label': 'Site', 'value': acquisition_counts.get('website', 0)},
            {'key': 'other', 'label': 'Outro', 'value': acquisition_counts.get('other', 0) + acquisition_counts.get('meta_ads', 0)},
        ],
        'analytics': {
            'missing_attribution_total': acquisition_counts.get('missing', 0),
            'operational_source_counts': {
                'manual': source_counts.get(IntakeSource.MANUAL, 0),
                'csv': source_counts.get(IntakeSource.CSV, 0),
                'whatsapp': source_counts.get(IntakeSource.WHATSAPP, 0),
                'import': source_counts.get(IntakeSource.IMPORT, 0),
            },
            'acquisition_channel_counts': acquisition_counts,
        },
    }


def build_intake_center_snapshot(*, params=None, actor_role_slug='', today=None, queue_limit=12, queue_offset=0):
    today = today or timezone.localdate()
    params = params or {}
    queue_offset = max(int(queue_offset or 0), 0)
    base_queryset = StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
        linked_student__isnull=True,
    )
    queue_queryset = base_queryset
    metrics_queryset = base_queryset
    active_panel = (params.get('panel') or '').strip()
    semantic_stage = ''
    created_window = ''
    assignment = ''
    filter_form = IntakeCenterFilterForm(
        params or None,
        status_choices=tuple(choice for choice in IntakeStatus.choices if choice[0] != IntakeStatus.MATCHED),
        source_choices=IntakeSource.choices,
    )

    if filter_form.is_valid():
        query = (filter_form.cleaned_data.get('query') or '').strip()
        if query == '/':
            query = ''
        status = filter_form.cleaned_data.get('status')
        source = filter_form.cleaned_data.get('source')
        sort = filter_form.cleaned_data.get('sort')
        semantic_stage = filter_form.cleaned_data.get('semantic_stage') or ''
        created_window = filter_form.cleaned_data.get('created_window') or ''
        assignment = filter_form.cleaned_data.get('assignment')

        if query:
            search_filter = Q(full_name__icontains=query)
            queue_queryset = queue_queryset.filter(search_filter)
            metrics_queryset = metrics_queryset.filter(search_filter)
        if status:
            queue_queryset = queue_queryset.filter(status=status)
            metrics_queryset = metrics_queryset.filter(status=status)
        if source:
            queue_queryset = queue_queryset.filter(source=source)
            metrics_queryset = metrics_queryset.filter(source=source)
        if semantic_stage == 'new-leads':
            queue_queryset = queue_queryset.filter(status=IntakeStatus.NEW)
        elif semantic_stage == 'lead-open':
            queue_queryset = queue_queryset.filter(status__in=[IntakeStatus.REVIEWING, IntakeStatus.MATCHED])
        elif semantic_stage == 'resolved':
            queue_queryset = queue_queryset.filter(status__in=[IntakeStatus.APPROVED, IntakeStatus.REJECTED])
        if created_window == 'today':
            queue_queryset = queue_queryset.filter(created_at__date=today)
            metrics_queryset = metrics_queryset.filter(created_at__date=today)
        if assignment == 'assigned':
            queue_queryset = queue_queryset.exclude(assigned_to__isnull=True)
            metrics_queryset = metrics_queryset.exclude(assigned_to__isnull=True)
        elif assignment == 'unassigned':
            queue_queryset = queue_queryset.filter(assigned_to__isnull=True)
            metrics_queryset = metrics_queryset.filter(assigned_to__isnull=True)
    else:
        sort = ''

    queue_refresh_aggregate = queue_queryset.aggregate(
        total=Count('id'),
        latest_updated_at=Max('updated_at'),
    )
    queue_refresh_token = '{total}:{updated}'.format(
        total=queue_refresh_aggregate.get('total') or 0,
        updated=(queue_refresh_aggregate.get('latest_updated_at').isoformat() if queue_refresh_aggregate.get('latest_updated_at') else ''),
    )
    queue_total_count = queue_refresh_aggregate.get('total') or 0
    queue_end_offset = queue_offset + queue_limit

    queue = list(
        queue_queryset.select_related('linked_student', 'assigned_to').order_by(*_resolve_queue_ordering(sort_value=sort))[queue_offset:queue_end_offset]
    )
    queue_items = [
        build_intake_queue_item(intake=intake, actor_role_slug=actor_role_slug, today=today)
        for intake in queue
    ]
    radar_board = _build_intake_radar_board(params=params, metrics_queryset=metrics_queryset, today=today)
    summary = metrics_queryset.aggregate(
        lead_total=Count('id', filter=Q(status=IntakeStatus.NEW)),
        pending_total=Count('id', filter=Q(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING])),
        today_funnel_total=Count(
            'id',
            filter=Q(
                created_at__date=today,
                status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
            ),
        ),
        conversation_in_queue=Count(
            'id',
            filter=Q(status__in=[IntakeStatus.REVIEWING, IntakeStatus.MATCHED]),
        ),
        assigned_in_queue=Count(
            'id',
            filter=Q(assigned_to__isnull=False),
        ),
    )

    lead_count = summary['lead_total']
    pending_count = summary['pending_total']
    conversation_count = summary['conversation_in_queue']
    assigned_count = summary['assigned_in_queue']
    created_today = summary['today_funnel_total']
    visible_queue_count = len(queue_items)
    first_intake = queue[0] if queue else None

    return {
        'interactive_kpis': [
            {
                'label': 'Leads',
                'display_value': str(lead_count),
                'note': 'Leads que ainda pedem primeiro contato, agendamento ou direcionamento inicial.',
                'href': '?panel=tab-intake-queue&semantic_stage=new-leads',
                'target_panel': 'tab-intake-queue',
                'tone_class': 'kpi-blue',
                'icon': _intake_kpi_icon('queue'),
                'is_selected': active_panel == 'tab-intake-queue' and semantic_stage == 'new-leads',
            },
            {
                'label': 'Em conversa',
                'display_value': str(conversation_count),
                'note': 'Leads que já estão em conversa ativa e podem virar matrícula sem trocar de tela.',
                'href': '?panel=tab-intake-queue&semantic_stage=lead-open',
                'target_panel': 'tab-intake-queue',
                'tone_class': 'kpi-amber',
                'icon': _intake_kpi_icon('conversation'),
                'is_selected': active_panel == 'tab-intake-queue' and semantic_stage == 'lead-open',
            },
            {
                'label': 'Hoje',
                'display_value': str(created_today),
                'note': 'Conta apenas as entradas que chegaram hoje; esse número reinicia na virada do dia.',
                'href': '?panel=tab-intake-queue&created_window=today',
                'target_panel': 'tab-intake-queue',
                'tone_class': 'kpi-emerald',
                'icon': _intake_kpi_icon('today'),
                'is_selected': active_panel == 'tab-intake-queue' and created_window == 'today',
            },
            {
                'label': 'Captação',
                'display_value': str(radar_board['total']),
                'note': 'Abre o radar de origem para ler Instagram, WhatsApp, site, indicação e importação externa.',
                'href': '?panel=tab-intake-source',
                'target_panel': 'tab-intake-source',
                'tone_class': 'kpi-purple',
                'icon': _intake_kpi_icon('owners'),
                'is_selected': active_panel == 'tab-intake-source',
            },
        ],
        'hero_stats': [
            {'label': 'Pendentes', 'value': pending_count},
            {'label': 'Na fila', 'value': len(queue)},
            {'label': 'Captação', 'value': radar_board['total']},
            {'label': 'Hoje', 'value': created_today},
        ],
        'radar_board': radar_board,
        'filter_form': filter_form,
        'create_form': IntakeQuickCreateForm(),
        'intake_queue': queue,
        'visible_queue_count': visible_queue_count,
        'queue_total_count': queue_total_count,
        'queue_offset': queue_offset,
        'queue_limit': queue_limit,
        'queue_has_next': queue_end_offset < queue_total_count,
        'queue_next_offset': queue_end_offset if queue_end_offset < queue_total_count else None,
        'queue_refresh_token': queue_refresh_token,
        'queue_items': queue_items,
        'first_intake': first_intake,
        'intake_operational_focus': [
            {
                'label': 'Comece pela fila aberta',
                'chip_label': 'Fila',
                'summary': (
                    f'{visible_queue_count} entrada(s) aparecem neste recorte e pedem leitura antes de esfriar ou virar ruído operacional.'
                    if visible_queue_count > 0
                    else 'Nenhuma entrada aparece neste recorte da fila principal, então a triagem não pede pressão imediata agora.'
                ),
                'count': visible_queue_count,
                'pill_class': 'warning' if visible_queue_count > 0 else 'success',
                'href': '#intake-queue-board',
                'href_label': 'Ver fila principal',
            },
            {
                'label': 'Acompanhe quem já está aquecido',
                'chip_label': 'Contato ativo',
                'summary': (
                    f'{conversation_count} lead(s) já estão em conversa e podem ser convertidos sem depender de nova triagem.'
                    if conversation_count > 0
                    else 'Nenhum lead está marcado como conversa ativa agora, então a fila pede primeiro contato antes de virar matrícula.'
                ),
                'count': conversation_count,
                'pill_class': 'accent' if conversation_count == 0 else 'success',
                'href': '#intake-queue-board',
                'href_label': 'Voltar para fila',
            },
            {
                'label': 'Depois leia a origem do fluxo',
                'chip_label': 'Origens',
                'summary': 'A origem ajuda a separar gargalo de captação, canal ou passagem de bastão.',
                'pill_class': 'info' if created_today > 0 else 'accent',
                'href': '#intake-source-board',
                'href_label': 'Ver origens',
            },
        ],
    }


__all__ = [
    'build_intake_center_snapshot',
    'build_onboarding_headline_metrics',
    'count_pending_intakes',
    'get_intake_conversion_queue',
    'get_pending_intakes',
]
