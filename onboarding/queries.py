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

from onboarding.facade import build_intake_queue_item
from onboarding.forms import IntakeCenterFilterForm, IntakeQuickCreateForm
from onboarding.models import IntakeSource, IntakeStatus, StudentIntake


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


def build_intake_center_snapshot(*, params=None, actor_role_slug='', today=None, queue_limit=12):
    today = today or timezone.localdate()
    queue_queryset = StudentIntake.objects.filter(
        status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
        linked_student__isnull=True,
    )
    filter_form = IntakeCenterFilterForm(
        params or None,
        status_choices=IntakeStatus.choices,
        source_choices=IntakeSource.choices,
    )

    if filter_form.is_valid():
        query = (filter_form.cleaned_data.get('query') or '').strip()
        status = filter_form.cleaned_data.get('status')
        source = filter_form.cleaned_data.get('source')
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
            queue_queryset = queue_queryset.filter(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING])
        elif semantic_stage == 'conversion-ready':
            queue_queryset = queue_queryset.filter(status=IntakeStatus.MATCHED)
        elif semantic_stage == 'resolved':
            queue_queryset = queue_queryset.filter(status__in=[IntakeStatus.APPROVED, IntakeStatus.REJECTED])
        if assignment == 'assigned':
            queue_queryset = queue_queryset.exclude(assigned_to__isnull=True)
        elif assignment == 'unassigned':
            queue_queryset = queue_queryset.filter(assigned_to__isnull=True)

    queue = list(
        queue_queryset.select_related('linked_student', 'assigned_to').order_by('status', '-created_at')[:queue_limit]
    )
    queue_items = [build_intake_queue_item(intake=intake, actor_role_slug=actor_role_slug) for intake in queue]
    source_counts = dict(
        queue_queryset.values_list('source').annotate(total=Count('id'))
    )
    # 🚀 Agregacao atomica (Epic 8 Performance) - Consolida 4 contagens em 1 única query.
    summary = StudentIntake.objects.aggregate(
        pending_total=Count('id', filter=Q(status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING], linked_student__isnull=True)),
        created_today=Count('id', filter=Q(created_at__date=today)),
        # Usamos o queue_queryset original para as metricas da fila filtrada
        matched_in_queue=Count('id', filter=Q(
            id__in=queue_queryset.values('id'), 
            status=IntakeStatus.MATCHED
        )),
        assigned_in_queue=Count('id', filter=Q(
            id__in=queue_queryset.values('id'),
            assigned_to__isnull=False
        ))
    )

    pending_count = summary['pending_total']
    matched_count = summary['matched_in_queue']
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
                'icon': 'alert-circle',
            },
            {
                'label': 'Prontos',
                'display_value': str(matched_count),
                'note': 'Pessoas aquecidas, triadas e prontas para criar a matricula e assinar o plano.',
                'data_action': 'open-tab-intake-conversion',
                'tone_class': 'kpi-cyan' if matched_count > 0 else 'kpi-green',
                'icon': 'check-circle',
            },
            {
                'label': 'Hoje',
                'display_value': str(created_today),
                'note': 'Volume diario e grafico de canais (Insta, Site, Balcao) para avaliar a atracao de hoje.',
                'data_action': 'open-tab-intake-source',
                'tone_class': 'kpi-cyan',
                'icon': 'trending-up',
            },
            {
                'label': 'Atribuidos',
                'display_value': str(assigned_count),
                'note': 'Mostra quantas entradas ja estao com alguem dono do atendimento.',
                'data_action': 'open-tab-intake-filters',
                'tone_class': 'kpi-purple',
                'icon': 'users',
            },
        ],
        'hero_stats': [
            {'label': 'Pendentes', 'value': pending_count},
            {'label': 'Na fila', 'value': len(queue)},
            {'label': 'Atribuídos', 'value': assigned_count},
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
        'conversion_rules': [
            {
                'title': '1. O que é um Contato?',
                'copy': 'É quem procurou o Box, mas ainda não é aluno. Ele fica nesta lista para você atender sem misturar com quem já treina.',
            },
            {
                'title': '2. Quando vira Aluno?',
                'copy': 'Quando você conversa com a pessoa e ela decide entrar. Aí você clica em "Converter" e abre o cadastro oficial.',
            },
            {
                'title': '3. Como funciona a Fila?',
                'copy': 'Os novos contatos chegam e ficam aguardando. Assim que você clica em "Atender", o contato fica sob seus cuidados.',
            },
            {
                'title': '4. Organização do Atendimento',
                'copy': 'Você atende, tira as dúvidas e faz a matrícula. Fica tudo num lugar só para garantir que ninguém saia sem resposta!',
            },
        ],
        'filter_form': filter_form,
        'create_form': IntakeQuickCreateForm(),
        'intake_queue': queue,
        'visible_queue_count': visible_queue_count,
        'queue_items': queue_items,
        'first_intake': first_intake,
        'matched_count': matched_count,
        'intake_operational_focus': [
            {
                'label': 'Comece pela fila aberta',
                'chip_label': 'Fila',
                'summary': (
                    f'{visible_queue_count} entrada(s) aparecem neste recorte da fila principal e pedem leitura antes de esfriarem ou virarem ruido operacional.'
                    if visible_queue_count > 0 else
                    'Nenhuma entrada aparece neste recorte da fila principal, entao a triagem nao pede pressao imediata agora.'
                ),
                'count': visible_queue_count,
                'pill_class': 'warning' if visible_queue_count > 0 else 'success',
                'href': '#intake-queue-board',
                'href_label': 'Ver fila principal',
            },
            {
                'label': 'Depois leia a origem do fluxo',
                'chip_label': 'Origens',
                'summary': 'A origem ajuda a separar gargalo de captação, canal ou passagem de bastão.',
                'pill_class': 'info' if created_today > 0 else 'accent',
                'href': '#intake-source-board',
                'href_label': 'Ver origens',
            },
            {
                'label': 'Feche pela regra de conversao',
                'chip_label': 'Conversão',
                'summary': f'{matched_count} caso(s) ja estao mais maduros e pedem conversao ou decisao final sem empurrar a fila para Alunos.',
                'count': matched_count,
                'pill_class': 'accent' if matched_count == 0 else 'success',
                'href': '#intake-conversion-board',
                'href_label': 'Ver regra de passagem',
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
