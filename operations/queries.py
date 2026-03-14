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
from django.utils import timezone

from auditing.models import AuditEvent
from communications.queries import (
    build_communications_headline_metrics,
    get_pending_intakes,
    get_unlinked_whatsapp_contacts,
)
from finance.models import Payment, PaymentMethod, PaymentStatus
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


def build_owner_workspace_snapshot(*, today):
    communications_metrics = build_communications_headline_metrics(today=today)
    headline_metrics = {
        'students': Student.objects.count(),
        'pending_intakes': communications_metrics['pending_intakes'],
        'whatsapp_contacts': communications_metrics['whatsapp_contacts'],
        'messages_logged': communications_metrics['messages_logged'],
        'overdue_payments': Payment.objects.filter(
            status__in=[PaymentStatus.PENDING, PaymentStatus.OVERDUE],
            due_date__lt=today,
        ).count(),
    }
    return {
        'headline_metrics': headline_metrics,
        'hero_stats': [
            _build_hero_stat('Base ativa', headline_metrics['students']),
            _build_hero_stat('Entradas', headline_metrics['pending_intakes']),
            _build_hero_stat('Atrasos', headline_metrics['overdue_payments']),
            _build_hero_stat('WhatsApp', headline_metrics['whatsapp_contacts']),
        ],
        'metric_cards': [
            _build_metric_card('operation-kpi-card owner-amber', 'Alunos registrados', headline_metrics['students'], 'Tamanho da base principal que sustenta presença, retenção e receita.'),
            _build_metric_card('operation-kpi-card owner-blue', 'Entradas pendentes', headline_metrics['pending_intakes'], 'Leads e cadastros provisórios que ainda pedem conversão ou revisão.'),
            _build_metric_card('operation-kpi-card owner-green', 'Contatos no WhatsApp', headline_metrics['whatsapp_contacts'], 'Capilaridade do canal de conversa pronta para vínculo operacional.'),
            _build_metric_card('operation-kpi-card owner-slate', 'Mensagens logadas', headline_metrics['messages_logged'], 'Histórico acumulado para rastrear relacionamento e futuras automações.'),
            _build_metric_card('operation-kpi-card owner-amber', 'Cobranças em atraso', headline_metrics['overdue_payments'], 'Sinal direto da pressão financeira que já exige leitura de retenção.'),
        ],
        'owner_operational_focus': [
            {
                'label': 'Comece pelo funil que ainda pede dono',
                'summary': f"{headline_metrics['pending_intakes']} entrada(s) seguem abertas e mostram se o crescimento está virando operação ou só acúmulo.",
                'count': headline_metrics['pending_intakes'],
                'pill_class': 'warning' if headline_metrics['pending_intakes'] > 0 else 'success',
                'href': '#owner-growth-board',
                'href_label': 'Ver crescimento',
            },
            {
                'label': 'Depois confira o risco de caixa',
                'summary': f"{headline_metrics['overdue_payments']} cobrança(s) em atraso já ajudam a separar expansão saudável de pressão financeira escondida.",
                'count': headline_metrics['overdue_payments'],
                'pill_class': 'warning' if headline_metrics['overdue_payments'] > 0 else 'info',
                'href': '#owner-risk-board',
                'href_label': 'Ver risco financeiro',
            },
            {
                'label': 'Feche com maturidade estrutural',
                'summary': f"{headline_metrics['whatsapp_contacts']} contato(s) no canal e {headline_metrics['messages_logged']} log(s) mostram se a operação já conversa com escala, vínculo e histórico.",
                'count': headline_metrics['whatsapp_contacts'],
                'pill_class': 'accent',
                'href': '#owner-structure-board',
                'href_label': 'Ver estrutura pronta',
            },
        ],
        'decision_board': [
            'Central de entrada pronta para receber alunos antes do cadastro definitivo.',
            'Base de WhatsApp pronta para armazenar contatos, vínculo e logs.',
            'Permissões reais por papel já separadas em áreas operacionais.',
        ],
        'decision_board_count_label': '3 frentes',
        'owner_reading_order': [
            'Comece pela fila de entrada e confira se o funil continua girando sem acúmulo indevido.',
            'Olhe os atrasos financeiros para medir risco de caixa e necessidade de ação de retenção.',
            'Use a base de WhatsApp e os logs como termômetro da maturidade operacional do produto.',
        ],
        'owner_table_guides': [
            {
                'label': 'Crescimento que ainda pede dono',
                'value': f"{headline_metrics['pending_intakes']} entrada(s) aguardando leitura",
                'summary': 'Use este recorte para separar crescimento vivo de fila parada antes que a entrada perca temperatura comercial.',
                'pill_class': 'warning' if headline_metrics['pending_intakes'] > 0 else 'success',
                'href': '#owner-growth-board',
                'href_label': 'Ler crescimento agora',
            },
            {
                'label': 'Risco que pressiona caixa',
                'value': f"{headline_metrics['overdue_payments']} cobranca(s) em atraso",
                'summary': 'Aqui o owner ve cedo se a pressao financeira ainda esta sob controle ou se ja contamina retencao e previsibilidade.',
                'pill_class': 'warning' if headline_metrics['overdue_payments'] > 0 else 'info',
                'href': '#owner-risk-board',
                'href_label': 'Ver risco de caixa',
            },
            {
                'label': 'Estrutura pronta para escalar',
                'value': f"{headline_metrics['whatsapp_contacts']} contato(s) e {headline_metrics['messages_logged']} log(s)",
                'summary': 'Esse quadro mostra se a operacao ja ganhou memoria, conversa e base suficiente para crescer sem improviso fragil.',
                'pill_class': 'accent',
                'href': '#owner-structure-board',
                'href_label': 'Ver estrutura pronta',
            },
        ],
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
                'summary': f"{technical_metrics['eventos_24h']} evento(s) nas últimas 24h mostram se a investigação deve começar no agora ou no histórico amplo.",
                'pill_class': 'warning' if technical_metrics['eventos_24h'] > 0 else 'success',
                'href': '#dev-audit-board',
                'href_label': 'Ver eventos recentes',
            },
            {
                'label': 'Depois valide a cobertura de acesso',
                'summary': f"{technical_metrics['usuarios_com_papel']} usuário(s) com papel ajudam a medir se a fronteira operacional continua coerente.",
                'pill_class': 'info',
                'href': '#dev-boundary-board',
                'href_label': 'Ver fronteiras',
            },
            {
                'label': 'Feche com leitura sistêmica',
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
    first_intake = pending_intakes[0] if pending_intakes else None
    nearest_financial_alert = financial_alerts[0] if financial_alerts else None
    first_unlinked_contact = unlinked_whatsapp[0] if unlinked_whatsapp else None
    first_unlinked_payment = payments_without_enrollment[0] if payments_without_enrollment else None
    return {
        'pending_intakes': pending_intakes,
        'unlinked_whatsapp': unlinked_whatsapp,
        'financial_alerts': financial_alerts,
        'payments_without_enrollment': payments_without_enrollment,
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
                'summary': f'{len(pending_intakes)} entrada(s) já chegaram e pedem triagem antes de virarem fila morta.',
                'count': len(pending_intakes),
                'pill_class': 'warning' if len(pending_intakes) > 0 else 'success',
                'href': '#manager-intake-board',
                'href_label': 'Ver entradas',
            },
            {
                'label': 'Depois limpe vínculos quebrados',
                'summary': f'{len(unlinked_whatsapp)} contato(s) sem aluno e {len(payments_without_enrollment)} cobrança(s) sem matrícula ainda escondem atrito estrutural.',
                'count': len(unlinked_whatsapp) + len(payments_without_enrollment),
                'pill_class': 'info' if len(unlinked_whatsapp) or len(payments_without_enrollment) else 'success',
                'href': '#manager-link-board',
                'href_label': 'Ver vínculos pendentes',
            },
            {
                'label': 'Feche com cobrança em risco',
                'summary': f'{len(financial_alerts)} alerta(s) já mostram onde retenção e caixa podem pressionar se ninguém agir agora.',
                'count': len(financial_alerts),
                'pill_class': 'warning' if len(financial_alerts) > 0 else 'accent',
                'href': '#manager-finance-board',
                'href_label': 'Ver alertas financeiros',
            },
        ],
        'manager_execution_focus': [
            {
                'label': 'Fila mais quente',
                'summary': (
                    f'{first_intake.full_name} aparece no topo da triagem e ajuda a abrir a fila pelo caso mais quente do momento.'
                    if first_intake else
                    'Sem entrada pendente agora, então a triagem pode ceder espaço para vínculo e cobrança.'
                ),
                'pill_class': 'warning' if first_intake else 'success',
                'href': '#manager-intake-board',
                'href_label': 'Abrir triagem',
            },
            {
                'label': 'Estrutura que ainda atrita',
                'summary': f'{len(unlinked_whatsapp)} contato(s) sem aluno e {len(payments_without_enrollment)} cobrança(s) sem matrícula continuam sendo os dois vazamentos mais diretos da rotina.',
                'pill_class': 'info' if len(unlinked_whatsapp) or len(payments_without_enrollment) else 'success',
                'href': '#manager-link-board',
                'href_label': 'Ver vínculos e estrutura',
            },
            {
                'label': 'Cobrança mais sensível',
                'summary': (
                    f'{nearest_financial_alert.student.full_name} já aparece primeiro na fila e vence em {nearest_financial_alert.due_date.strftime("%d/%m/%Y")}. '
                    if nearest_financial_alert else
                    'Sem alerta financeiro aberto no momento.'
                ),
                'pill_class': 'warning' if nearest_financial_alert else 'accent',
                'href': '#manager-finance-board',
                'href_label': 'Abrir cobrança',
            },
        ],
        'manager_table_guides': [
            {
                'label': 'Triagem',
                'value': f'{len(pending_intakes)} caso(s)',
                'summary': (
                    f'Abra por {first_intake.full_name} e mantenha a fila andando a partir do topo.'
                    if first_intake else
                    'Sem fila aberta agora, então a triagem não é a prioridade desta rodada.'
                ),
                'href': '#manager-intake-board',
                'href_label': 'Ir para entradas',
                'pill_class': 'warning' if first_intake else 'success',
            },
            {
                'label': 'Estrutura',
                'value': f'{len(unlinked_whatsapp) + len(payments_without_enrollment)} atrito(s)',
                'summary': (
                    f'{(first_unlinked_contact.display_name or "Sem nome") if first_unlinked_contact else "o primeiro contato sem vínculo"} e {first_unlinked_payment.student.full_name if first_unlinked_payment else "a fila financeira"} ajudam a abrir os dois vazamentos mais prováveis.'
                    if first_unlinked_contact or first_unlinked_payment else
                    'Sem atrito estrutural no momento, então a base relacional está limpa para seguir operação.'
                ),
                'href': '#manager-link-board',
                'href_label': 'Ir para estrutura',
                'pill_class': 'info' if first_unlinked_contact or first_unlinked_payment else 'success',
            },
            {
                'label': 'Cobrança',
                'value': f'{len(financial_alerts)} alerta(s)',
                'summary': (
                    f'Comece por {nearest_financial_alert.student.full_name} para agir no vencimento mais próximo.'
                    if nearest_financial_alert else
                    'Sem alerta financeiro aberto, então cobrança pode ficar fora do foco imediato.'
                ),
                'href': '#manager-finance-board',
                'href_label': 'Ir para alertas',
                'pill_class': 'warning' if nearest_financial_alert else 'accent',
            },
        ],
        'manager_steps': [
            'Revisar entradas vindas de CSV, WhatsApp ou cadastro manual.',
            'Vincular contatos ao aluno definitivo quando houver match.',
            'Acompanhar inadimplência e preparar ações de retenção.',
        ],
        'manager_boundaries': [
            'Esta área não executa presença de aula em nome do coach.',
            'O foco aqui é entrada, vínculo, retenção e rotina financeira.',
            'A operação técnica do treino continua isolada na área do coach.',
        ],
        'manager_whatsapp_ready': [
            'Contato pode existir antes do aluno definitivo.',
            'Contato pode ser vinculado depois ao cadastro principal.',
            'Logs de mensagens podem ser armazenados sem quebrar o modelo atual.',
        ],
    }


def build_coach_workspace_snapshot(*, today):
    sessions = ClassSession.objects.filter(scheduled_at__date=today).prefetch_related('attendances__student').order_by('scheduled_at')
    total_attendances = sum(session.attendances.count() for session in sessions)
    sessions_with_students = sum(1 for session in sessions if session.attendances.count() > 0)
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
                'summary': f'{len(sessions)} aula(s) definem o turno e mostram se o coach entra em dia cheio ou leitura leve.',
                'count': len(sessions),
                'pill_class': 'info' if len(sessions) > 0 else 'success',
                'href': '#coach-sessions-board',
                'href_label': 'Ver aulas do dia',
            },
            {
                'label': 'Depois veja onde já há presença real',
                'summary': f'{sessions_with_students} turma(s) já têm lista ativa e {total_attendances} presença(s) para registrar sem ruído administrativo.',
                'count': sessions_with_students,
                'pill_class': 'accent',
                'href': '#coach-sessions-board',
                'href_label': 'Abrir rotina de presença',
            },
            {
                'label': 'Feche com ocorrência técnica',
                'summary': f'{len(BehaviorCategory.choices)} categoria(s) cobrem o registro técnico sem misturar treino com financeiro ou recepção.',
                'count': len(BehaviorCategory.choices),
                'pill_class': 'warning',
                'href': '#coach-boundary-board',
                'href_label': 'Ver limites da área',
            },
        ],
        'coach_notes': [
            'Use check-in ao iniciar presença real do aluno.',
            'Use check-out ao encerrar a aula ou saída do aluno.',
            'Use falta quando a reserva existia e o aluno não compareceu.',
        ],
        'behavior_categories': BehaviorCategory.choices,
        'coach_boundaries': [
            'Esta área não mostra fila financeira nem central de entrada.',
            'O foco do coach aqui é turma, presença e leitura do dia.',
            'Ocorrências técnicas podem ser registradas sem expor dados administrativos.',
        ],
    }


def _build_reception_payment_reason(payment, *, today):
    if payment.status == PaymentStatus.OVERDUE:
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
    next_sessions = list(
        ClassSession.objects.filter(scheduled_at__date__gte=today)
        .prefetch_related('attendances')
        .order_by('scheduled_at')[:6]
    )
    active_students = Student.objects.count()
    overdue_payments = sum(1 for payment in payment_queue if payment.status == PaymentStatus.OVERDUE)
    due_today = sum(1 for payment in payment_queue if payment.status == PaymentStatus.PENDING and payment.due_date == today)
    first_intake = pending_intakes[0] if pending_intakes else None
    first_payment = payment_queue[0] if payment_queue else None
    next_session = next_sessions[0] if next_sessions else None

    reception_payment_queue = [
        {
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
            'student_href': f'/alunos/{payment.student.id}/editar/',
        }
        for payment in payment_queue
    ]

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


def build_reception_preview_workspace_snapshot(*, today):
    data = _build_reception_workspace_core(today=today)
    first_intake = data['first_intake']
    first_payment = data['first_payment']
    next_session = data['next_session']

    return {
        'hero_stats': data['hero_stats'],
        'metric_cards': data['metric_cards'],
        'reception_preview_focus': [
            {
                'label': 'Comece pelo balcao vivo',
                'summary': (
                    f'{first_intake.full_name} abre a fila de entrada e mostra como a Recepcao pode converter sem atrito.'
                    if first_intake else
                    'Sem entrada pendente agora, entao a triagem inicial nao e o ponto de pressao desta rodada.'
                ),
                'count': len(data['intakes']),
                'pill_class': 'warning' if first_intake else 'success',
                'href': '#reception-intake-board',
                'href_label': 'Ver entradas',
            },
            {
                'label': 'Depois leia o caixa curto',
                'summary': (
                    f'{first_payment.student.full_name} aparece primeiro na fila e mostra a logica de cobranca curta sem abrir a central completa.'
                    if first_payment else
                    'Sem cobranca curta em fila agora, entao o preview financeiro pode ficar em segundo plano.'
                ),
                'count': len(data['queue']),
                'pill_class': 'warning' if first_payment else 'info',
                'href': '#reception-payment-board',
                'href_label': 'Ver fila de cobranca',
            },
            {
                'label': 'Feche com a leitura da grade',
                'summary': (
                    f'{next_session.title} e a proxima aula visivel para orientar check-in e responder duvidas de rotina no balcao.'
                    if next_session else
                    'Sem aula futura cadastrada no recorte atual, entao a leitura da grade fica sem pressao imediata.'
                ),
                'count': len(data['sessions']),
                'pill_class': 'accent',
                'href': '#reception-class-grid-board',
                'href_label': 'Ver grade em leitura',
            },
        ],
        'reception_preview_boundaries': [
            'Este preview continua oculto da navegacao publica e existe so para lapidacao controlada.',
            'A Recepcao aqui combina aluno, grade em leitura e cobranca curta sem receber o financeiro inteiro.',
            'O marco simbolico continua reservado para quando a area estiver pronta para ser promovida a superficie oficial.',
        ],
        'reception_preview_payment_methods': data['payment_methods'],
        'reception_preview_queue': data['queue'],
        'reception_preview_intakes': data['intakes'],
        'reception_preview_sessions': data['sessions'],
    }


__all__ = [
    'build_coach_workspace_snapshot',
    'build_dev_workspace_snapshot',
    'build_manager_workspace_snapshot',
    'build_owner_workspace_snapshot',
    'build_reception_workspace_snapshot',
    'build_reception_preview_workspace_snapshot',
]