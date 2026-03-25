"""
ARQUIVO: montagem dos atalhos operacionais do shell autenticado.

POR QUE ELE EXISTE:
- Padroniza os botões centrais do OctoBox no topo das páginas para levar o usuario direto ao ponto quente, ao pendente e à próxima ação.
- Exibe contagem real de pendências quando disponível; chips sem contagem mostram apenas o label.

O QUE ESTE ARQUIVO FAZ:
1. Normaliza o contrato dos atalhos operacionais.
2. Mapeia contagens reais (vencimentos, intakes, aulas) por área.
3. Gera fallback coerente por área quando a view não informa destinos específicos.

PONTOS CRITICOS:
- Esses atalhos são parte do core operacional do produto; links errados quebram a promessa principal de reduzir tempo de decisão.
"""

from django.conf import settings
from django.core.cache import cache

from access.roles import ROLE_DEV, ROLE_RECEPTION
from finance.overdue_metrics import count_overdue_students, get_overdue_payments_queryset
from onboarding.queries import count_pending_intakes


ADMIN_PATH_PREFIX = f"/{settings.ADMIN_URL_PATH}"


def resolve_shell_scope(*, current_path, role_slug=None):
    if current_path.startswith('/dashboard/'):
        return 'dashboard-reception' if role_slug == ROLE_RECEPTION else 'dashboard'
    if current_path.startswith('/entradas/'):
        return 'intake-center'
    if current_path.startswith('/alunos/'):
        return 'student-form' if ('/novo/' in current_path or '/editar/' in current_path) else 'students'
    if current_path.startswith('/financeiro/'):
        return 'finance-plan-form' if '/planos/' in current_path else 'finance'
    if current_path.startswith('/grade-aulas/'):
        return 'class-grid'
    if current_path.startswith('/operacao/recepcao/'):
        return 'operations-reception'
    if current_path.startswith('/operacao/manager/'):
        return 'operations-manager'
    if current_path.startswith('/operacao/coach/'):
        return 'operations-coach'
    if current_path.startswith('/operacao/dev/'):
        return 'operations-dev'
    if current_path.startswith('/operacao/'):
        return 'operations-owner'
    if current_path.startswith('/acessos/'):
        return 'access'
    if current_path.startswith('/mapa-sistema/'):
        return 'system-map'
    if current_path.startswith(ADMIN_PATH_PREFIX):
        return 'admin'
    return 'generic'


def _build_action(kind, default_label, default_target_label, source, *, scope='generic'):
    source = source or {}
    count = source.get('count')
    return {
        'kind': kind,
        'label': source.get('chip_label') or source.get('label') or default_label,
        'count': count if count and count > 0 else None,
        'target_label': (
            source.get('target_label')
            or source.get('href_label')
            or source.get('action_label')
            or default_target_label
        ),
        'href': source.get('href') or source.get('action_href') or '#page-body',
    }


def get_shell_counts(*, use_cache=True):
    """Retorna os counts globais para os pulse chips com cache curto para aliviar o shell."""
    from django.db.models import Count, Q
    from django.utils import timezone
    from finance.models import Enrollment, EnrollmentStatus, Payment
    from operations.models import ClassSession
    from students.models import Student, StudentStatus
    today = timezone.localdate()
    cache_key = f'octobox:shell-counts:{today}'

    if use_cache:
        cached_counts = cache.get(cache_key)
        if cached_counts is not None:
            return cached_counts

    overdue_payments = get_overdue_payments_queryset(Payment.objects.all(), today=today)

    # 🚀 Otimização de Performance (Epic 8)
    # Combinamos contagens da mesma tabela em uma única query para reduzir a 
    # rajada de acesso (Stampede) quando o cache expira.
    student_summary = Student.objects.aggregate(
        active=Count('id', filter=Q(status=StudentStatus.ACTIVE)),
        lead=Count('id', filter=Q(status=StudentStatus.LEAD))
    )

    counts = {
        'overdue_payments': overdue_payments.count(),
        'overdue_students': count_overdue_students(Payment.objects.all(), today=today),
        'pending_intakes': count_pending_intakes(),
        'sessions_today': ClassSession.objects.filter(scheduled_at__date=today).count(),
        'active_students': student_summary['active'],
        'lead_students': student_summary['lead'],
        'active_enrollments': Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE).count(),
    }

    if use_cache:
        # EPIC 9: Cache estendido para `SHELL_COUNTS_CACHE_TTL_SECONDS` (configuravel em settings)
        ttl = getattr(settings, 'SHELL_COUNTS_CACHE_TTL_SECONDS', 60)
        cache.set(cache_key, counts, timeout=ttl)

    return counts


def build_shell_action_buttons(*, priority=None, pending=None, next_action=None, counts=None, scope='generic'):
    """
    counts: dict opcional com chaves 'overdue_payments', 'pending_intakes', 'sessions_today'.
    Quando fornecido, injeta automaticamente o count no chip correspondente.
    Se não fornecido, preserva apenas os counts explicitamente passados por cada página.
    """
    c = counts or {}
    op = c.get('overdue_payments', 0)
    pi = c.get('pending_intakes', 0)
    st = c.get('sessions_today', 0)

    priority = dict(priority or {})
    pending = dict(pending or {})
    next_action = dict(next_action or {})

    if counts is not None:
        priority.setdefault('count', op)
        pending.setdefault('count', pi)
        next_action.setdefault('count', st)

    return [
        _build_action('priority', 'Prioridade', 'Abrir agora', priority, scope=scope),
        _build_action('pending', 'Pendente', 'Ver pendencia', pending, scope=scope),
        _build_action('next-action', 'Proximo', 'Abrir proximo passo', next_action, scope=scope),
    ]


def build_shell_action_buttons_from_focus(*, focus=None, priority=None, pending=None, next_action=None, counts=None, scope='generic'):
    focus = list(focus or [])

    def merge_focus_item(index, override):
        base = dict(focus[index] if len(focus) > index else {})
        base.update(override or {})
        return base or None

    return build_shell_action_buttons(
        priority=merge_focus_item(0, priority),
        pending=merge_focus_item(1, pending),
        next_action=merge_focus_item(2, next_action),
        counts=counts,
        scope=scope,
    )


def attach_shell_action_buttons(context, *, focus=None, priority=None, pending=None, next_action=None, counts=None, scope='generic'):
    """Anexa shell_action_buttons ao contexto, evitando repeticao nas views."""
    context['shell_action_buttons'] = build_shell_action_buttons_from_focus(
        focus=focus,
        priority=priority,
        pending=pending,
        next_action=next_action,
        counts=counts,
        scope=scope,
    )
    return context


def build_default_shell_action_buttons(*, current_path, role_slug, overdue_payments=0, pending_intakes=0, sessions_today=0):
    if role_slug == ROLE_DEV:
        return []

    op = overdue_payments
    pi = pending_intakes
    st = sessions_today
    scope = resolve_shell_scope(current_path=current_path, role_slug=role_slug)

    if current_path.startswith('/dashboard/'):
        if role_slug == ROLE_RECEPTION:
            return build_shell_action_buttons(
                priority={'label': 'Cobranças', 'href': '/operacao/recepcao/#reception-payment-board', 'target_label': 'Abrir cobranca curta', 'count': op},
                pending={'label': 'Entradas', 'href': '/operacao/recepcao/#reception-intake-board', 'target_label': 'Ver entradas', 'count': pi},
                next_action={'label': 'Aulas', 'href': '/grade-aulas/#today-board', 'target_label': 'Abrir agenda do turno', 'count': st},
                scope=scope,
            )
        return build_shell_action_buttons(
            priority={'label': 'Atrasos', 'href': '/financeiro/#finance-priority-board', 'target_label': 'Abrir financeiro', 'count': op},
            pending={'label': 'Entradas', 'href': '/entradas/#intake-queue-board', 'target_label': 'Ver entradas', 'count': pi},
            next_action={'label': 'Aulas', 'href': '/grade-aulas/#today-board', 'target_label': 'Abrir agenda do dia', 'count': st},
            scope=scope,
        )

    if current_path.startswith('/entradas/'):
        return build_shell_action_buttons(
            priority={'label': 'Fila', 'href': '#intake-queue-board', 'target_label': 'Abrir fila principal', 'count': pi},
            pending={'label': 'Origens', 'href': '#intake-source-board', 'target_label': 'Ver origens'},
            next_action={'label': 'Conversão', 'href': '#intake-conversion-board', 'target_label': 'Ver conversao'},
            scope=scope,
        )

    if current_path.startswith('/alunos/'):
        if '/novo/' in current_path or '/editar/' in current_path:
            return build_shell_action_buttons(
                priority={'label': 'Cadastro', 'href': '#student-form-essential', 'target_label': 'Abrir nucleo do cadastro'},
                pending={'label': 'Perfil', 'href': '#student-form-profile', 'target_label': 'Ver vinculo e perfil'},
                next_action={'label': 'Plano', 'href': '#student-form-plan', 'target_label': 'Ver plano e cobranca'},
                scope=scope,
            )
        return build_shell_action_buttons(
            priority={'label': 'Prioridades', 'href': '#student-priority-board', 'target_label': 'Abrir prioridades'},
            pending={'label': 'Entradas', 'href': '/entradas/#intake-queue-board', 'target_label': 'Abrir central de intake', 'count': pi},
            next_action={'label': 'Base', 'href': '#student-directory-board', 'target_label': 'Abrir base principal'},
            scope=scope,
        )

    if current_path.startswith('/financeiro/'):
        if '/planos/' in current_path:
            return build_shell_action_buttons(
                priority={'label': 'Plano', 'href': '#plan-form-core', 'target_label': 'Abrir nucleo do plano'},
                pending={'label': 'Comercial', 'href': '#plan-form-delivery', 'target_label': 'Ver clareza comercial'},
                next_action={'label': 'Carteira', 'href': '#plan-form-summary', 'target_label': 'Ver impacto na carteira'},
                scope=scope,
            )
        return build_shell_action_buttons(
            priority={'label': 'Cobranças', 'href': '#finance-priority-board', 'target_label': 'Abrir pressao de cobranca', 'count': op},
            pending={'label': 'Fila', 'href': '#finance-queue-board', 'target_label': 'Ver fila de atrasados', 'count': op},
            next_action={'label': 'Carteira', 'href': '#finance-portfolio-board', 'target_label': 'Abrir carteira ativa'},
            scope=scope,
        )

    if current_path.startswith('/grade-aulas/'):
        return build_shell_action_buttons(
            priority={'label': 'Hoje', 'href': '#today-board', 'target_label': 'Abrir aulas de hoje', 'count': st},
            pending={'label': 'Semana', 'href': '#weekly-board', 'target_label': 'Ver pico da semana'},
            next_action={'label': 'Planejar', 'href': '#planner-board', 'target_label': 'Ajustar grade'},
            scope=scope,
        )

    if current_path.startswith('/operacao/recepcao/'):
        return build_shell_action_buttons(
            priority={'label': 'Chegada', 'href': '#reception-intake-board', 'target_label': 'Ver chegada quente', 'count': pi},
            pending={'label': 'Cobranças', 'href': '#reception-payment-board', 'target_label': 'Abrir fila curta', 'count': op},
            next_action={'label': 'Aulas', 'href': '#reception-class-grid-board', 'target_label': 'Ver proxima aula', 'count': st},
            scope=scope,
        )

    if current_path.startswith('/operacao/manager/'):
        return build_shell_action_buttons(
            priority={'label': 'Triagem', 'href': '#manager-intake-board', 'target_label': 'Ver triagem aberta', 'count': pi},
            pending={'label': 'Vínculos', 'href': '#manager-link-board', 'target_label': 'Ver vinculos pendentes'},
            next_action={'label': 'Cobranças', 'href': '#manager-finance-board', 'target_label': 'Abrir cobranca urgente', 'count': op},
            scope=scope,
        )

    if current_path.startswith('/operacao/coach/'):
        return build_shell_action_buttons(
            priority={'label': 'Turmas', 'href': '#coach-sessions-board', 'target_label': 'Abrir turmas do turno', 'count': st},
            pending={'label': 'Presença', 'href': '#coach-sessions-board', 'target_label': 'Abrir presenca'},
            next_action={'label': 'Ocorrências', 'href': '#coach-boundary-board', 'target_label': 'Ver decisao tecnica'},
            scope=scope,
        )

    if current_path.startswith('/operacao/dev/'):
        return build_shell_action_buttons(
            priority={'label': 'Auditoria', 'href': '#dev-audit-board', 'target_label': 'Abrir rastros recentes'},
            pending={'label': 'Mapa', 'href': '/mapa-sistema/#system-reading-board', 'target_label': 'Ver mapa do sistema'},
            next_action={'label': 'Fronteiras', 'href': '/acessos/#access-role-map', 'target_label': 'Ver fronteiras de acesso'},
            scope=scope,
        )

    if current_path.startswith('/operacao/'):
        return build_shell_action_buttons(
            priority={'label': 'Cobranças', 'href': '/financeiro/', 'target_label': 'Abrir cobranças', 'count': op},
            pending={'label': 'Entradas', 'href': '/entradas/', 'target_label': 'Ver entradas', 'count': pi},
            next_action={'label': 'Estrutura', 'href': '/alunos/', 'target_label': 'Abrir estrutura do box'},
            scope=scope,
        )

    if current_path.startswith('/acessos/'):
        return build_shell_action_buttons(
            priority={'label': 'Papel', 'href': '#access-current-role', 'target_label': 'Ver escopo do papel'},
            pending={'label': 'Fronteiras', 'href': '#access-role-map', 'target_label': 'Ver mapa de fronteiras'},
            next_action={'label': 'Governança', 'href': '#access-governance-board', 'target_label': 'Ver governanca pratica'},
            scope=scope,
        )

    if current_path.startswith('/mapa-sistema/'):
        return build_shell_action_buttons(
            priority={'label': 'Fluxo', 'href': '#system-flow-board', 'target_label': 'Abrir fluxo macro'},
            pending={'label': 'Estudo', 'href': '#system-reading-board', 'target_label': 'Ver ordem de estudo'},
            next_action={'label': 'Bugs', 'href': '#system-bug-board', 'target_label': 'Ver triagem de bugs'},
            scope=scope,
        )

    return build_shell_action_buttons(
        priority={'href': '/dashboard/', 'target_label': 'Abrir panorama do dia'},
        pending={'href': '/entradas/#intake-queue-board', 'target_label': 'Abrir fila pendente', 'count': pi},
        next_action={'href': '/grade-aulas/#today-board', 'target_label': 'Abrir proxima acao', 'count': st},
        scope=scope,
    )


__all__ = ['attach_shell_action_buttons', 'build_default_shell_action_buttons', 'build_shell_action_buttons', 'build_shell_action_buttons_from_focus', 'get_shell_counts', 'resolve_shell_scope']