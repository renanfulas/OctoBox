"""
ARQUIVO: snapshots de leitura do workspace operacional.

POR QUE ELE EXISTE:
- concentra a leitura operacional por papel fora de boxcore.operations.

O QUE ESTE ARQUIVO FAZ:
1. monta snapshots de owner, dev, manager e coach.
2. preserva consultas reutilizaveis fora da camada HTTP.

PONTOS CRITICOS:
- mudancas aqui afetam a leitura operacional por papel e a performance dessas telas.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from communications.queries import (
    build_communications_headline_metrics,
    get_unlinked_whatsapp_contacts,
)
from finance.models import Payment, PaymentMethod, PaymentStatus
from finance.overdue_metrics import get_overdue_payments_queryset, sum_overdue_amount
from onboarding.queries import get_pending_intakes
from operations.models import BehaviorCategory, ClassSession
from students.models import Student


def _build_hero_stat(label, value):
    return {'label': label, 'value': value}


def _build_metric_card(card_class, eyebrow, value, note):
    return {
        'card_class': card_class,
        'eyebrow': eyebrow,
        'display_value': value,
        'note': note,
    }


def _build_owner_focus_item(*, key, label, summary, count, pill_class, href, href_label, chip_label=''):
    return {
        'key': key,
        'label': label,
        'chip_label': chip_label,
        'summary': summary,
        'count': count,
        'pill_class': pill_class,
        'href': href,
        'href_label': href_label,
    }


def _build_decision_entry_context(entry_item=None, secondary_item=None):
    entry_item = entry_item or {}
    secondary_item = secondary_item or {}
    return {
        'entry_key': entry_item.get('key', ''),
        'entry_surface': entry_item.get('key', ''),
        'entry_href': entry_item.get('href', ''),
        'entry_href_label': entry_item.get('href_label', 'Abrir'),
        'entry_label': entry_item.get('label', ''),
        'entry_reason': entry_item.get('summary', ''),
        'entry_count': entry_item.get('count'),
        'entry_pill_class': entry_item.get('pill_class', 'accent'),
        'secondary_key': secondary_item.get('key', ''),
        'secondary_surface': secondary_item.get('key', ''),
        'secondary_href': secondary_item.get('href', ''),
        'secondary_href_label': secondary_item.get('href_label', 'Abrir'),
        'secondary_label': secondary_item.get('label', ''),
        'secondary_reason': secondary_item.get('summary', ''),
    }


def _build_owner_priority_context(primary_focus):
    primary_key = (primary_focus or {}).get('key')
    if primary_key == 'intakes':
        return {
            'title': 'Entre pela fila que traz nova receita.',
            'copy': 'Existe demanda esperando resposta agora.',
            'pill_label': 'Agora',
            'pill_class': 'accent',
        }
    if primary_key == 'payments':
        return {
            'title': 'Proteja a receita antes do restante.',
            'copy': 'Ha cobranca atrasada pedindo contato agora.',
            'pill_label': 'Agora',
            'pill_class': 'accent',
        }
    return {
        'title': 'Confirme a estrutura que sustenta o box.',
        'copy': 'Veja se WhatsApp, historico e estrutura continuam coerentes.',
        'pill_label': 'Agora',
        'pill_class': 'accent',
    }


def _build_manager_priority_context(*, pending_intakes_count, unlinked_whatsapp_count, payments_without_enrollment_count, financial_alerts_count):
    if pending_intakes_count > 0:
        return {
            'title': 'Triagem primeiro para nao deixar entrada esfriar.',
            'copy': 'A fila comercial esta viva e merece abrir antes dos vinculos e do caixa.',
            'pill_label': 'Triagem viva',
            'pill_class': 'warning',
        }
    if (unlinked_whatsapp_count + payments_without_enrollment_count) > 0:
        return {
            'title': 'Limpe vinculos quebrados antes de aprofundar o caixa.',
            'copy': 'Contato sem aluno e cobranca sem matricula escondem atrito estrutural que contamina o resto da leitura.',
            'pill_label': 'Vinculos',
            'pill_class': 'info',
        }
    if financial_alerts_count > 0:
        return {
            'title': 'O caixa ainda pede a ultima leitura do turno.',
            'copy': 'Sem triagem ou vinculo pressionando mais forte, os alertas financeiros viram a camada dominante.',
            'pill_label': 'Caixa',
            'pill_class': 'warning',
        }
    return {
        'title': 'A mesa esta limpa para leitura de manutencao.',
        'copy': 'Sem pressao dominante, a gerencia pode validar a operacao com mais calma e menos reatividade.',
        'pill_label': 'Estavel',
        'pill_class': 'success',
    }


def build_owner_workspace_snapshot(*, today):
    communications_metrics = build_communications_headline_metrics(today=today)
    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    overdue_amount = sum_overdue_amount(Payment.objects.all(), today=today)
    classes_today = ClassSession.objects.filter(scheduled_at__date=today).count()
    headline_metrics = {
        'students': Student.objects.count(),
        'pending_intakes': communications_metrics['pending_intakes'],
        'whatsapp_contacts': communications_metrics['whatsapp_contacts'],
        'messages_logged': communications_metrics['messages_logged'],
        'overdue_payments': overdue_payments.count(),
        'overdue_amount': overdue_amount,
    }
    focus_map = {
        'intakes': _build_owner_focus_item(
            key='intakes',
            label='Ver entradas',
            chip_label='Entradas',
            summary=(
                f"{headline_metrics['pending_intakes']} entrada(s) esperam resposta."
                if headline_metrics['pending_intakes']
                else 'Nenhuma entrada espera resposta agora.'
            ),
            count=headline_metrics['pending_intakes'],
            pill_class='danger' if headline_metrics['pending_intakes'] > 0 else 'success',
            href=reverse('intake-center'),
            href_label='Abrir entradas',
        ),
        'payments': _build_owner_focus_item(
            key='payments',
            label='Ver cobrancas',
            chip_label='Cobranças',
            summary=(
                f"{headline_metrics['overdue_payments']} cobranca(s) estao atrasadas e pedem contato."
                if headline_metrics['overdue_payments']
                else 'Nenhuma cobranca atrasada pede contato agora.'
            ),
            count=headline_metrics['overdue_payments'],
            pill_class='danger' if headline_metrics['overdue_payments'] > 0 else 'success',
            href=reverse('finance-center'),
            href_label='Abrir cobrancas',
        ),
        'structure': _build_owner_focus_item(
            key='structure',
            label='Ver estrutura',
            chip_label='Estrutura',
            summary=(
                f"{headline_metrics['whatsapp_contacts']} contato(s) com WhatsApp e {headline_metrics['messages_logged']} conversa(s) salvas."
            ),
            count=headline_metrics['whatsapp_contacts'],
            pill_class='success',
            href=reverse('student-directory'),
            href_label='Abrir estrutura',
        ),
    }
    if headline_metrics['pending_intakes'] > 0:
        focus_order = ['intakes', 'payments', 'structure']
    elif headline_metrics['overdue_payments'] > 0:
        focus_order = ['payments', 'intakes', 'structure']
    else:
        focus_order = ['structure', 'intakes', 'payments']
    owner_operational_focus = [focus_map[key] for key in focus_order]
    owner_priority_context = _build_owner_priority_context(owner_operational_focus[0] if owner_operational_focus else None)
    owner_decision_entry_context = _build_decision_entry_context(
        owner_operational_focus[0] if owner_operational_focus else None,
        owner_operational_focus[1] if len(owner_operational_focus) > 1 else None,
    )
    return {
        'headline_metrics': headline_metrics,
        'classes_today': classes_today,
        'metric_cards': [
            {
                **_build_metric_card('operation-kpi-card owner-amber', 'Total de alunos', headline_metrics['students'], 'Tamanho atual da base.'),
                'status_hint': 'neutral',
                'href': reverse('student-directory'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-blue', 'Entradas abertas', headline_metrics['pending_intakes'], 'Pessoas que ainda esperam resposta.'),
                'status_hint': 'clean' if headline_metrics['pending_intakes'] == 0 else 'attention',
                'href': reverse('intake-center'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-green', 'WhatsApp pronto', headline_metrics['whatsapp_contacts'], 'Contatos prontos para conversa.'),
                'status_hint': 'neutral',
                'href': reverse('whatsapp-workspace'),
            },
            {
                **_build_metric_card('operation-kpi-card owner-amber', 'Cobranças atrasadas', headline_metrics['overdue_payments'], 'Dinheiro que já deveria ter entrado.'),
                'submetric': {
                    'label': 'Caixa vencido',
                    'value': f"R$ {headline_metrics['overdue_amount']:.2f}".replace('.', ','),
                },
                'status_hint': 'clean' if headline_metrics['overdue_payments'] == 0 else 'attention',
                'href': reverse('finance-center'),
            },
        ],
        'owner_priority_context': owner_priority_context,
        'owner_decision_entry_context': owner_decision_entry_context,
        'owner_operational_focus': owner_operational_focus,
        'owner_secondary_focus': owner_operational_focus[1:],
    }


def build_dev_workspace_snapshot():
    technical_metrics = {
        'eventos_auditados': AuditEvent.objects.count(),
        'eventos_24h': AuditEvent.objects.filter(created_at__gte=timezone.now() - timedelta(days=1)).count(),
        'usuarios_com_papel': get_user_model().objects.filter(groups__isnull=False).distinct().count(),
    }
    recent_audit_events = list(AuditEvent.objects.select_related('actor')[:10])
    return {
        'technical_metrics': technical_metrics,
        'hero_stats': [
            _build_hero_stat('Auditados', technical_metrics['eventos_auditados']),
            _build_hero_stat('Últimas 24h', technical_metrics['eventos_24h']),
            _build_hero_stat('Usuários', technical_metrics['usuarios_com_papel']),
            _build_hero_stat('Auditoria', len(recent_audit_events)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card dev-steel', 'Eventos auditados', technical_metrics['eventos_auditados'], 'Histórico total sensível disponível para investigação, leitura forense e prova operacional.'),
            _build_metric_card('operation-kpi-card dev-cyan', 'Eventos nas últimas 24h', technical_metrics['eventos_24h'], 'Volume recente para avaliar movimentação real e detectar ondas anormais de alteração.'),
            _build_metric_card('operation-kpi-card dev-emerald', 'Usuários com papel', technical_metrics['usuarios_com_papel'], 'Cobertura atual de contas com fronteira operacional definida no sistema.'),
        ],
        'dev_operational_focus': [
            {
                'label': 'Comece pelo rastro recente',
                'chip_label': 'Auditoria',
                'summary': f"{technical_metrics['eventos_24h']} evento(s) nas últimas 24h mostram se a investigação deve começar no agora ou no histórico amplo.",
                'pill_class': 'warning' if technical_metrics['eventos_24h'] > 0 else 'success',
                'href': '#dev-audit-board',
                'href_label': 'Ver eventos recentes',
            },
            {
                'label': 'Depois valide a cobertura de acesso',
                'chip_label': 'Fronteiras',
                'summary': f"{technical_metrics['usuarios_com_papel']} usuário(s) com papel ajudam a medir se a fronteira operacional continua coerente.",
                'pill_class': 'info',
                'href': '#dev-boundary-board',
                'href_label': 'Ver fronteiras',
            },
            {
                'label': 'Feche com leitura sistêmica',
                'chip_label': 'Rastros',
                'summary': f"{technical_metrics['eventos_auditados']} rastro(s) auditado(s) sustentam manutenção, investigação e prova operacional sem virar chute técnico.",
                'pill_class': 'accent',
                'href': '#dev-read-board',
                'href_label': 'Ver trilha curta',
            },
        ],
        'recent_audit_events': recent_audit_events,
        'dev_boundaries': [
            'DEV investiga e mantém o sistema, mas não assume rotina de manager ou coach.',
            'O papel técnico deve operar com leitura ampla e escrita mínima, sempre com rastreabilidade.',
            'Acesso GOD continua fora da rotina e deve nascer depois com regra de contingência.',
        ],
        'dev_reads': [
            'Mapa do sistema para entender arquitetura e fluxo.',
            'Papéis e acessos para revisar fronteiras de permissão.',
            'Trilha de auditoria para investigar ações sensíveis recentes.',
        ],
        'dev_table_guides': [
            {
                'label': 'Rastro que deve abrir a investigacao',
                'value': f"{technical_metrics['eventos_24h']} evento(s) nas ultimas 24h",
                'summary': 'Comece por aqui quando precisar localizar alteracao recente antes de abrir historico inteiro e perder tempo tecnico.',
                'pill_class': 'warning' if technical_metrics['eventos_24h'] > 0 else 'success',
                'href': '#dev-audit-board',
                'href_label': 'Abrir rastros recentes',
            },
            {
                'label': 'Cobertura de fronteira atual',
                'value': f"{technical_metrics['usuarios_com_papel']} usuario(s) com papel",
                'summary': 'Use este ponto para validar se acesso continua com dono claro ou se alguma conta ja saiu da fronteira prevista.',
                'pill_class': 'info',
                'href': '#dev-boundary-board',
                'href_label': 'Ver fronteiras',
            },
            {
                'label': 'Base forense disponivel',
                'value': f"{technical_metrics['eventos_auditados']} rastro(s) auditado(s)",
                'summary': 'Esse volume sustenta manutencao e prova operacional sem depender de memoria tecnica, conversa paralela ou chute.',
                'pill_class': 'accent',
                'href': '#dev-read-board',
                'href_label': 'Ver trilha curta',
            },
        ],
    }


def build_manager_workspace_snapshot():
    pending_intakes = get_pending_intakes(limit=8)
    unlinked_whatsapp = get_unlinked_whatsapp_contacts(limit=8)
    financial_alerts = Payment.objects.select_related('student').filter(
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE]
    ).order_by('due_date')[:8]
    payments_without_enrollment = Payment.objects.select_related('student').filter(
        enrollment__isnull=True,
        status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
    ).order_by('due_date')[:8]
    manager_priority_context = _build_manager_priority_context(
        pending_intakes_count=len(pending_intakes),
        unlinked_whatsapp_count=len(unlinked_whatsapp),
        payments_without_enrollment_count=len(payments_without_enrollment),
        financial_alerts_count=len(financial_alerts),
    )
    if len(pending_intakes) > 0:
        manager_decision_entry_context = _build_decision_entry_context(
            {
                'href': '#manager-intake-board',
                'href_label': 'Ver entradas',
                'label': 'Comece pela entrada que pode esfriar',
                'summary': f'{len(pending_intakes)} entrada(s) jÃ¡ chegaram e pedem triagem antes de virarem fila morta.',
                'count': len(pending_intakes),
                'pill_class': 'warning',
            },
            {
                'href': '#manager-link-board',
                'href_label': 'Ver vÃ­nculos pendentes',
                'label': 'Depois limpe vÃ­nculos quebrados',
                'summary': f'{len(unlinked_whatsapp)} contato(s) sem aluno e {len(payments_without_enrollment)} cobranÃ§a(s) sem matrÃ­cula ainda escondem atrito estrutural.',
            },
        )
    elif (len(unlinked_whatsapp) + len(payments_without_enrollment)) > 0:
        manager_decision_entry_context = _build_decision_entry_context(
            {
                'href': '#manager-link-board',
                'href_label': 'Ver vÃ­nculos pendentes',
                'label': 'Depois limpe vÃ­nculos quebrados',
                'summary': f'{len(unlinked_whatsapp)} contato(s) sem aluno e {len(payments_without_enrollment)} cobranÃ§a(s) sem matrÃ­cula ainda escondem atrito estrutural.',
                'count': len(unlinked_whatsapp) + len(payments_without_enrollment),
                'pill_class': 'info',
            },
            {
                'href': '#manager-finance-board',
                'href_label': 'Ver alertas financeiros',
                'label': 'Feche com cobranÃ§a em risco',
                'summary': f'{len(financial_alerts)} alerta(s) jÃ¡ mostram onde retenÃ§Ã£o e caixa podem pressionar se ninguÃ©m agir agora.',
            },
        )
    else:
        manager_decision_entry_context = _build_decision_entry_context(
            {
                'href': '#manager-finance-board',
                'href_label': 'Ver alertas financeiros',
                'label': 'Feche com cobranÃ§a em risco',
                'summary': f'{len(financial_alerts)} alerta(s) jÃ¡ mostram onde retenÃ§Ã£o e caixa podem pressionar se ninguÃ©m agir agora.',
                'count': len(financial_alerts),
                'pill_class': 'accent',
            },
            {
                'href': '#manager-intake-board',
                'href_label': 'Ver entradas',
                'label': 'Comece pela entrada que pode esfriar',
                'summary': f'{len(pending_intakes)} entrada(s) jÃ¡ chegaram e pedem triagem antes de virarem fila morta.',
            },
        )
    return {
        'pending_intakes': pending_intakes,
        'unlinked_whatsapp': unlinked_whatsapp,
        'financial_alerts': financial_alerts,
        'payments_without_enrollment': payments_without_enrollment,
        'manager_priority_context': manager_priority_context,
        'manager_decision_entry_context': manager_decision_entry_context,
        'hero_stats': [
            _build_hero_stat('Entradas', len(pending_intakes)),
            _build_hero_stat('WhatsApp', len(unlinked_whatsapp)),
            _build_hero_stat('Sem vínculo', len(payments_without_enrollment)),
            _build_hero_stat('Alertas', len(financial_alerts)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card manager-coral', 'Entradas pendentes', len(pending_intakes), 'Pessoas que já chegaram ao sistema, mas ainda exigem triagem ou conversão.'),
            _build_metric_card('operation-kpi-card manager-sky', 'Contatos sem vínculo', len(unlinked_whatsapp), 'Conversas abertas que ainda precisam ser conectadas ao aluno principal.'),
            _build_metric_card('operation-kpi-card manager-gold', 'Pagamentos sem matrícula', len(payments_without_enrollment), 'Cobranças que podem contaminar leitura financeira enquanto não forem vinculadas.'),
            _build_metric_card('operation-kpi-card manager-steel', 'Alertas financeiros', len(financial_alerts), 'Fila de inadimplência e pendências para agir antes de escalar o problema.'),
        ],
        'manager_operational_focus': [
            {
                'label': 'Comece pela entrada que pode esfriar',
                'chip_label': 'Triagem',
                'summary': f'{len(pending_intakes)} entrada(s) já chegaram e pedem triagem antes de virarem fila morta.',
                'count': len(pending_intakes),
                'pill_class': 'warning' if len(pending_intakes) > 0 else 'success',
                'href': '#manager-intake-board',
                'href_label': 'Ver entradas',
            },
            {
                'label': 'Depois limpe vínculos quebrados',
                'chip_label': 'Vínculos',
                'summary': f'{len(unlinked_whatsapp)} contato(s) sem aluno e {len(payments_without_enrollment)} cobrança(s) sem matrícula ainda escondem atrito estrutural.',
                'count': len(unlinked_whatsapp) + len(payments_without_enrollment),
                'pill_class': 'info' if len(unlinked_whatsapp) or len(payments_without_enrollment) else 'success',
                'href': '#manager-link-board',
                'href_label': 'Ver vínculos pendentes',
            },
            {
                'label': 'Feche com cobrança em risco',
                'chip_label': 'Cobranças',
                'summary': f'{len(financial_alerts)} alerta(s) já mostram onde retenção e caixa podem pressionar se ninguém agir agora.',
                'count': len(financial_alerts),
                'pill_class': 'warning' if len(financial_alerts) > 0 else 'accent',
                'href': '#manager-finance-board',
                'href_label': 'Ver alertas financeiros',
            },
        ],
    }


def build_coach_workspace_snapshot(*, today):
    sessions = (
        ClassSession.objects.filter(scheduled_at__date=today)
        .prefetch_related('attendances__student')
        .annotate(attendance_cnt=Count('attendances'))
        .order_by('scheduled_at')
    )
    total_attendances = sum(session.attendance_cnt for session in sessions)
    sessions_with_students = sum(1 for session in sessions if session.attendance_cnt > 0)
    return {
        'sessions_today': sessions,
        'hero_stats': [
            _build_hero_stat('Aulas', len(sessions)),
            _build_hero_stat('Rotinas', 3),
            _build_hero_stat('Limites', 3),
            _build_hero_stat('Ocorrências', len(BehaviorCategory.choices)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card coach-mint', 'Aulas do dia', len(sessions), 'Quantidade de turmas que o coach precisa enxergar e conduzir hoje.'),
            _build_metric_card('operation-kpi-card coach-indigo', 'Guias de execução', 3, 'Passos operacionais para manter presença, saída e falta registradas corretamente.'),
            _build_metric_card('operation-kpi-card coach-orange', 'Fronteiras do papel', 3, 'Lembrete visual do que pertence ao coach e do que continua fora desta área.'),
        ],
        'coach_operational_focus': [
            {
                'label': 'Comece pela agenda de hoje',
                'chip_label': 'Turmas',
                'summary': f'{len(sessions)} aula(s) definem o turno e mostram se o coach entra em dia cheio ou leitura leve.',
                'count': len(sessions),
                'pill_class': 'info' if len(sessions) > 0 else 'success',
                'href': '#coach-sessions-board',
                'href_label': 'Ver aulas do dia',
            },
            {
                'label': 'Depois veja onde já há presença real',
                'chip_label': 'Presença',
                'summary': f'{sessions_with_students} turma(s) já têm lista ativa e {total_attendances} presença(s) para registrar sem ruído administrativo.',
                'count': sessions_with_students,
                'pill_class': 'accent',
                'href': '#coach-sessions-board',
                'href_label': 'Abrir rotina de presença',
            },
            {
                'label': 'Feche com ocorrência técnica',
                'chip_label': 'Ocorrências',
                'summary': f'{len(BehaviorCategory.choices)} categoria(s) cobrem o registro técnico sem misturar treino com financeiro ou recepção.',
                'count': len(BehaviorCategory.choices),
                'pill_class': 'warning',
                'href': '#coach-boundary-board',
                'href_label': 'Ver limites da área',
            },
        ],
        'behavior_categories': BehaviorCategory.choices,
    }


def _build_reception_payment_reason(payment, *, today):
    if payment.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE] and payment.due_date < today:
        delay_days = max((today - payment.due_date).days, 0)
        return f'Pagamento vencido ha {delay_days} dia(s) e ja pede abordagem curta de balcao.'
    if payment.status == PaymentStatus.PENDING and payment.due_date == today:
        return 'Pagamento vence hoje e pode ser resolvido no proprio atendimento.'
    if payment.status == PaymentStatus.PENDING and payment.due_date > today:
        return f'Pagamento vence em {(payment.due_date - today).days} dia(s) e pode ser antecipado durante a passagem pelo caixa.'
    return 'Pagamento pede leitura operacional antes de escalar para o financeiro completo.'


def _build_reception_workspace_core(*, today):
    pending_intakes = list(get_pending_intakes(limit=6))
    payment_queue = list(
        Payment.objects.select_related('student', 'enrollment__plan')
        .filter(status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE])
        .order_by('due_date')[:6]
    )
    overdue_payments_queryset = get_overdue_payments_queryset(Payment.objects.all(), today=today)
    next_sessions = list(
        ClassSession.objects.filter(scheduled_at__date__gte=today)
        .prefetch_related('attendances')
        .order_by('scheduled_at')[:6]
    )
    active_students = Student.objects.count()
    overdue_payments = overdue_payments_queryset.count()
    due_today = sum(1 for payment in payment_queue if payment.status == PaymentStatus.PENDING and payment.due_date == today)
    first_intake = pending_intakes[0] if pending_intakes else None
    first_payment = payment_queue[0] if payment_queue else None
    next_session = next_sessions[0] if next_sessions else None

    from django.utils import timezone
    from datetime import timedelta
    from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours
    from communications.model_definitions.whatsapp import WhatsAppMessageLog, MessageDirection
    
    repeat_block_hours = get_operational_whatsapp_repeat_block_hours()
    
    # 🚀 Performance AAA (Ghost Hardening): Bulk WhatsApp Log Pre-fetch
    # Buscamos todos os logs relevantes da fila inteira em uma tacada só.
    student_ids = [p.student_id for p in payment_queue]
    recent_cutoff = timezone.now() - timedelta(hours=repeat_block_hours) if repeat_block_hours > 0 else None
    
    all_outbound_logs = list(WhatsAppMessageLog.objects.filter(
        contact__linked_student_id__in=student_ids,
        direction=MessageDirection.OUTBOUND
    ).values('contact__linked_student_id', 'created_at'))
    
    # Agrupamos por aluno para busca O(1) no loop
    log_stats_map = {}
    for log in all_outbound_logs:
        s_id = log['contact__linked_student_id']
        if s_id not in log_stats_map:
            log_stats_map[s_id] = {'total': 0, 'recent': 0}
        log_stats_map[s_id]['total'] += 1
        if recent_cutoff and log['created_at'] >= recent_cutoff:
            log_stats_map[s_id]['recent'] += 1

    reception_payment_queue = []
    for payment in payment_queue:
        days_overdue = max((today - payment.due_date).days, 0)
        clean_phone = "".join(filter(str.isdigit, payment.student.phone or ''))
        if clean_phone and not clean_phone.startswith('55'):
            clean_phone = f'55{clean_phone}'
            
        is_whatsapp_locked = False
        sent_count = 0
        if clean_phone:
            stats = log_stats_map.get(payment.student.id, {'total': 0, 'recent': 0})
            sent_count = stats['total']
            is_whatsapp_locked = stats['recent'] > 0

        student_edit_href = reverse('student-quick-update', args=[payment.student.id])
        reception_payment_queue.append({
            'payment_id': payment.id,
            'student_id': payment.student.id,
            'student_name': payment.student.full_name,
            'plan_name': payment.enrollment.plan.name if payment.enrollment and payment.enrollment.plan else 'Sem plano vinculado',
            'status_label': payment.get_status_display(),
            'status_class': 'warning' if payment.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE] else 'info',
            'due_date': payment.due_date,
            'amount': payment.amount,
            'method': payment.method,
            'method_label': payment.get_method_display(),
            'reference': payment.reference,
            'notes': payment.notes,
            'reason': _build_reception_payment_reason(payment, today=today),
            'student_href': student_edit_href,
            'clean_phone': clean_phone,
            'is_late_10_days': days_overdue >= 10,
            'is_whatsapp_locked': is_whatsapp_locked,
            'is_reception_blocked': sent_count >= 2,
            'repeat_block_hours': repeat_block_hours,
        })

    return {
        'pending_intakes': pending_intakes,
        'payment_queue': payment_queue,
        'next_sessions': next_sessions,
        'first_intake': first_intake,
        'first_payment': first_payment,
        'next_session': next_session,
        'active_students': active_students,
        'overdue_payments': overdue_payments,
        'due_today': due_today,
        'hero_stats': [
            _build_hero_stat('Entradas', len(pending_intakes)),
            _build_hero_stat('Atrasos', overdue_payments),
            _build_hero_stat('Vence hoje', due_today),
            _build_hero_stat('Aulas proximas', len(next_sessions)),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card manager-coral', 'Entradas prontas', len(pending_intakes), 'Contatos que a recepcao poderia transformar em aluno definitivo sem sair da cadencia de atendimento.'),
            _build_metric_card('operation-kpi-card manager-gold', 'Cobrancas curtas', len(payment_queue), 'Fila curta de caixa para resolver no balcao sem abrir o financeiro inteiro.'),
            _build_metric_card('operation-kpi-card manager-sky', 'Base alcançada', active_students, 'Volume de alunos que ja sustenta busca rapida, RM visivel e atendimento orientado.'),
            _build_metric_card('operation-kpi-card coach-indigo', 'Proximas aulas', len(next_sessions), 'Leitura guiada da grade para orientar check-in e responder duvidas sem virar agenda tecnica.'),
        ],
        'payment_methods': list(PaymentMethod.choices),
        'queue': reception_payment_queue,
        'intakes': pending_intakes,
        'sessions': next_sessions,
    }


def build_reception_workspace_snapshot(*, today):
    data = _build_reception_workspace_core(today=today)
    first_intake = data['first_intake']
    first_payment = data['first_payment']
    next_session = data['next_session']

    return {
        'hero_stats': data['hero_stats'],
        'metric_cards': data['metric_cards'],
        'reception_focus': [
            {
                'label': 'Comece por quem acabou de chegar',
                'chip_label': 'Chegada',
                'summary': (
                    f'{first_intake.full_name} abre a fila e mostra o melhor ponto para acolher, localizar e converter sem esfriar o atendimento.'
                    if first_intake else
                    'Sem entrada pendente agora, entao o balcao pode priorizar caixa curto e orientacao de aulas.'
                ),
                'count': len(data['intakes']),
                'pill_class': 'warning' if first_intake else 'success',
                'href': '#reception-intake-board',
                'href_label': 'Ver entradas',
            },
            {
                'label': 'Depois resolva o caixa curto',
                'chip_label': 'Cobranças',
                'summary': (
                    f'{first_payment.student.full_name} aparece primeiro na fila e ajuda a validar se a cobranca esta clara o suficiente para ser resolvida no balcao.'
                    if first_payment else
                    'Sem cobranca curta em fila agora, entao o atendimento pode seguir sem pressao financeira imediata.'
                ),
                'count': len(data['queue']),
                'pill_class': 'warning' if first_payment else 'info',
                'href': '#reception-payment-board',
                'href_label': 'Ver cobranca curta',
            },
            {
                'label': 'Feche orientando a proxima aula',
                'chip_label': 'Aulas',
                'summary': (
                    f'{next_session.title} e a proxima aula visivel para responder horario, coach e duvida rapida sem abrir gestao de agenda.'
                    if next_session else
                    'Sem aula futura no recorte atual, entao a leitura da grade nao e o ponto de pressao desta rodada.'
                ),
                'count': len(data['sessions']),
                'pill_class': 'accent',
                'href': '#reception-class-grid-board',
                'href_label': 'Ver grade em leitura',
            },
        ],
        'reception_boundaries': [
            'A Recepcao acolhe, localiza, cadastra e encaminha sem assumir o papel do manager.',
            'A grade aqui continua em leitura apenas: orientar o balcao nao significa gerenciar agenda.',
            'A cobranca curta resolve pagamento e ajuste simples sem abrir o centro financeiro completo.',
        ],
        'reception_payment_methods': data['payment_methods'],
        'reception_queue': data['queue'],
        'reception_intakes': data['intakes'],
        'reception_sessions': data['sessions'],
    }


__all__ = [
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
    'build_reception_workspace_snapshot',
]
