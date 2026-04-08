"""
ARQUIVO: consultas de leitura do dominio onboarding.

POR QUE ELE EXISTE:
- Da ownership proprio para leads e intakes sem depender da fronteira de communications.

O QUE ESTE ARQUIVO FAZ:
1. Resume metricas de entradas pendentes.
2. Expoe listas curtas para triagem e workspaces operacionais.
3. Monta a leitura principal da Central de Intake.

PONTOS CRITICOS:
- Essas consultas abastecem shell, operacao, onboarding e alunos; qualquer regressao aqui aparece como fila quebrada ou contagem errada.
"""

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.safestring import mark_safe

from onboarding.facade import build_intake_queue_item
from onboarding.forms import IntakeCenterFilterForm, IntakeQuickCreateForm
from onboarding.models import IntakeSource, IntakeStatus, StudentIntake


def _intake_kpi_icon(name):
    icons = {
        'queue': mark_safe(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><path d="M3 12h7"/><path d="M3 6h11"/><path d="M3 18h5"/><path d="m15 15 3 3 3-3"/><path d="M18 6v12"/></svg>'
        ),
        'conversation': mark_safe(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
        ),
        'today': mark_safe(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>'
        ),
        'owners': mark_safe(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 20h8"/><path d="M12 18v2"/><path d="M7 9h10"/><path d="M7 13h6"/></svg>'
        ),
    }
    return icons.get(name, '')


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


def build_intake_center_snapshot(*, params=None, actor_role_slug='', today=None, queue_limit=12):
    today = today or timezone.localdate()
    queue_queryset = StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
        linked_student__isnull=True,
    )
    filter_form = IntakeCenterFilterForm(
        params or None,
        status_choices=tuple(choice for choice in IntakeStatus.choices if choice[0] != IntakeStatus.MATCHED),
        source_choices=IntakeSource.choices,
    )

    if filter_form.is_valid():
        query = (filter_form.cleaned_data.get('query') or '').strip()
        status = filter_form.cleaned_data.get('status')
        source = filter_form.cleaned_data.get('source')
        sort = filter_form.cleaned_data.get('sort')
        semantic_stage = filter_form.cleaned_data.get('semantic_stage')
        assignment = filter_form.cleaned_data.get('assignment')

        if query:
            queue_queryset = queue_queryset.filter(
                Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query)
            )
        if status:
            queue_queryset = queue_queryset.filter(status=status)
        if source:
            queue_queryset = queue_queryset.filter(source=source)
        if semantic_stage == 'lead-open':
            queue_queryset = queue_queryset.filter(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED])
        elif semantic_stage == 'resolved':
            queue_queryset = queue_queryset.filter(status__in=[IntakeStatus.APPROVED, IntakeStatus.REJECTED])
        if assignment == 'assigned':
            queue_queryset = queue_queryset.exclude(assigned_to__isnull=True)
        elif assignment == 'unassigned':
            queue_queryset = queue_queryset.filter(assigned_to__isnull=True)
    else:
        sort = ''

    queue = list(
        queue_queryset.select_related('linked_student', 'assigned_to').order_by(*_resolve_queue_ordering(sort_value=sort))[:queue_limit]
    )
    queue_items = [
        build_intake_queue_item(intake=intake, actor_role_slug=actor_role_slug, today=today)
        for intake in queue
    ]
    source_counts = dict(queue_queryset.values_list('source').annotate(total=Count('id')))
    summary = StudentIntake.objects.aggregate(
        pending_total=Count('id', filter=Q(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING], linked_student__isnull=True)),
        created_today=Count('id', filter=Q(created_at__date=today)),
        conversation_in_queue=Count(
            'id',
            filter=Q(
                id__in=queue_queryset.values('id'),
                status__in=[IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
            ),
        ),
        assigned_in_queue=Count(
            'id',
            filter=Q(
                id__in=queue_queryset.values('id'),
                assigned_to__isnull=False,
            ),
        ),
    )

    pending_count = summary['pending_total']
    conversation_count = summary['conversation_in_queue']
    assigned_count = summary['assigned_in_queue']
    created_today = summary['created_today']
    visible_queue_count = len(queue_items)
    first_intake = queue[0] if queue else None

    return {
        'interactive_kpis': [
            {
                'label': 'Fila aberta',
                'display_value': str(pending_count),
                'note': 'Leads aguardando primeiro contato, agendamento ou direcionamento basico no balcao.',
                'data_action': 'open-tab-intake-queue',
                'tone_class': 'kpi-red' if pending_count > 0 else 'kpi-green',
                'icon': _intake_kpi_icon('queue'),
            },
            {
                'label': 'Em conversa',
                'display_value': str(conversation_count),
                'note': 'Leads que ja estao em contato ativo com a equipe e podem virar matricula sem trocar de tela.',
                'data_action': 'open-tab-intake-queue',
                'tone_class': 'kpi-cyan' if conversation_count > 0 else 'kpi-green',
                'icon': _intake_kpi_icon('conversation'),
            },
            {
                'label': 'Hoje',
                'display_value': str(created_today),
                'note': 'Volume diario e grafico de canais (Insta, Site, Balcao) para avaliar a atracao de hoje.',
                'data_action': 'open-tab-intake-source',
                'tone_class': 'kpi-cyan',
                'icon': _intake_kpi_icon('today'),
            },
            {
                'label': 'Atribuidos',
                'display_value': str(assigned_count),
                'note': 'Mostra quantas entradas ja estao com alguem dono do atendimento.',
                'data_action': 'open-tab-intake-filters',
                'tone_class': 'kpi-purple',
                'icon': _intake_kpi_icon('owners'),
            },
        ],
        'hero_stats': [
            {'label': 'Pendentes', 'value': pending_count},
            {'label': 'Na fila', 'value': len(queue)},
            {'label': 'Atribuidos', 'value': assigned_count},
            {'label': 'Hoje', 'value': created_today},
        ],
        'source_breakdown': [
            {
                'label': dict(IntakeSource.choices)[choice],
                'value': source_counts.get(choice, 0),
                'note': 'Mostra quantos contatos vieram por aqui.',
            }
            for choice, _label in IntakeSource.choices
        ],
        'filter_form': filter_form,
        'create_form': IntakeQuickCreateForm(),
        'intake_queue': queue,
        'visible_queue_count': visible_queue_count,
        'queue_items': queue_items,
        'first_intake': first_intake,
        'intake_operational_focus': [
            {
                'label': 'Comece pela fila aberta',
                'chip_label': 'Fila',
                'summary': (
                    f'{visible_queue_count} entrada(s) aparecem neste recorte da fila principal e pedem leitura antes de esfriarem ou virarem ruido operacional.'
                    if visible_queue_count > 0
                    else 'Nenhuma entrada aparece neste recorte da fila principal, entao a triagem nao pede pressao imediata agora.'
                ),
                'count': visible_queue_count,
                'pill_class': 'warning' if visible_queue_count > 0 else 'success',
                'href': '#intake-queue-board',
                'href_label': 'Ver fila principal',
            },
            {
                'label': 'Acompanhe quem ja esta em conversa',
                'chip_label': 'Contato ativo',
                'summary': (
                    f'{conversation_count} lead(s) ja estao em conversa e podem ser convertidos sem depender de uma etapa intermediaria.'
                    if conversation_count > 0
                    else 'Nenhum lead esta marcado como conversa ativa agora, entao a fila pede primeiro contato antes de virar matricula.'
                ),
                'count': conversation_count,
                'pill_class': 'accent' if conversation_count == 0 else 'success',
                'href': '#intake-queue-board',
                'href_label': 'Voltar para fila',
            },
            {
                'label': 'Depois leia a origem do fluxo',
                'chip_label': 'Origens',
                'summary': 'A origem ajuda a separar gargalo de captacao, canal ou passagem de bastao.',
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
