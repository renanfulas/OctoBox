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

from access.roles import ROLE_DEV, ROLE_RECEPTION


def resolve_shell_scope(*, current_path, role_slug=None):
    if current_path.startswith('/dashboard/'):
        return 'dashboard-reception' if role_slug == ROLE_RECEPTION else 'dashboard'
    if current_path.startswith('/alunos/'):
        return 'student-form' if ('/novo/' in current_path or '/editar/' in current_path) else 'students'
    if current_path.startswith('/financeiro/'):
        return 'finance-plan-form' if '/planos/' in current_path else 'finance'
    if current_path.startswith('/grade-aulas/'):
        return 'class-grid'
    if current_path.startswith('/operacao/recepcao-preview/'):
        return 'operations-reception-preview'
    if current_path.startswith('/operacao/recepcao/'):
        return 'operations-reception'
    if current_path.startswith('/operacao/manager/'):
        return 'operations-manager'
    if current_path.startswith('/operacao/coach/'):
        return 'operations-coach'
    if current_path.startswith('/operacao/'):
        return 'operations-owner'
    if current_path.startswith('/acessos/'):
        return 'access'
    if current_path.startswith('/mapa-sistema/'):
        return 'system-map'
    if current_path.startswith('/admin/'):
        return 'admin'
    return 'generic'


def _build_action(kind, default_label, default_summary, source, *, scope='generic'):
    source = source or {}
    count = source.get('count')
    summary = source.get('summary') or source.get('copy') or source.get('note') or default_summary
    return {
        'kind': kind,
        'label': default_label,
        'count': count if count and count > 0 else None,
        'summary': summary,
        'href': source.get('href') or source.get('action_href') or '#page-body',
    }


def get_shell_counts():
    """Retorna os counts globais para os pulse chips."""
    from django.utils import timezone
    from communications.queries import count_pending_intakes
    from finance.models import Payment, PaymentStatus
    from operations.models import ClassSession
    return {
        'overdue_payments': Payment.objects.filter(status=PaymentStatus.OVERDUE).count(),
        'pending_intakes': count_pending_intakes(),
        'sessions_today': ClassSession.objects.filter(scheduled_at__date=timezone.localdate()).count(),
    }


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
        _build_action('priority', 'Prioridade', 'Abrir agora o ponto mais quente da operação.', priority, scope=scope),
        _build_action('pending', 'Pendente', 'Ir direto para o bloco que ainda está em aberto.', pending, scope=scope),
        _build_action('next-action', 'Próxima ação', 'Abrir o próximo passo que destrava o dia.', next_action, scope=scope),
    ]


def attach_shell_action_buttons(context, *, focus=None, priority=None, pending=None, next_action=None, counts=None, scope='generic'):
    """Anexa shell_action_buttons ao contexto, evitando repeticao nas views."""
    focus = focus or []
    context['shell_action_buttons'] = build_shell_action_buttons(
        priority=priority if priority is not None else (focus[0] if len(focus) > 0 else None),
        pending=pending if pending is not None else (focus[1] if len(focus) > 1 else None),
        next_action=next_action if next_action is not None else (focus[2] if len(focus) > 2 else None),
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
                priority={'href': '/operacao/recepcao/#reception-payment-board', 'summary': 'Caixa curto do balcao.', 'count': op},
                pending={'href': '/operacao/recepcao/#reception-intake-board', 'summary': 'Chegadas pendentes.', 'count': pi},
                next_action={'href': '/grade-aulas/#today-board', 'summary': 'Agenda do turno.', 'count': st},
                scope=scope,
            )
        return build_shell_action_buttons(
            priority={'href': '/financeiro/#finance-priority-board', 'summary': 'Regua financeira.', 'count': op},
            pending={'href': '/alunos/#student-intake-board', 'summary': 'Fila de entrada.', 'count': pi},
            next_action={'href': '/grade-aulas/#today-board', 'summary': 'Agenda de hoje.', 'count': st},
            scope=scope,
        )

    if current_path.startswith('/alunos/'):
        if '/novo/' in current_path or '/editar/' in current_path:
            return build_shell_action_buttons(
                priority={'href': '#student-form-essential', 'summary': 'Nucleo do cadastro.'},
                pending={'href': '#student-form-profile', 'summary': 'Vinculo e perfil.'},
                next_action={'href': '#student-form-plan', 'summary': 'Plano e cobranca.'},
                scope=scope,
            )
        return build_shell_action_buttons(
            priority={'href': '#student-priority-board', 'summary': 'Leads e acoes imediatas.'},
            pending={'href': '#student-intake-board', 'summary': 'Fila de entrada.', 'count': pi},
            next_action={'href': '#student-directory-board', 'summary': 'Base principal.'},
            scope=scope,
        )

    if current_path.startswith('/financeiro/'):
        if '/planos/' in current_path:
            return build_shell_action_buttons(
                priority={'href': '#plan-form-core', 'summary': 'Nucleo do plano.'},
                pending={'href': '#plan-form-delivery', 'summary': 'Clareza comercial.'},
                next_action={'href': '#plan-form-summary', 'summary': 'Impacto na carteira.'},
                scope=scope,
            )
        return build_shell_action_buttons(
            priority={'href': '#finance-priority-board', 'summary': 'Pressao de cobranca.', 'count': op},
            pending={'href': '#finance-queue-board', 'summary': 'Fila de atrasados.', 'count': op},
            next_action={'href': '#finance-portfolio-board', 'summary': 'Carteira ativa.'},
            scope=scope,
        )

    if current_path.startswith('/grade-aulas/'):
        return build_shell_action_buttons(
            priority={'href': '#today-board', 'summary': 'Aulas de hoje.', 'count': st},
            pending={'href': '#weekly-board', 'summary': 'Pico da semana.'},
            next_action={'href': '#planner-board', 'summary': 'Ajustar grade.'},
            scope=scope,
        )

    if current_path.startswith('/operacao/recepcao-preview/') or current_path.startswith('/operacao/recepcao/'):
        return build_shell_action_buttons(
            priority={'href': '#reception-intake-board', 'summary': 'Chegada quente.', 'count': pi},
            pending={'href': '#reception-payment-board', 'summary': 'Fila curta.', 'count': op},
            next_action={'href': '#reception-class-grid-board', 'summary': 'Proxima aula.', 'count': st},
            scope=scope,
        )

    if current_path.startswith('/operacao/manager/'):
        return build_shell_action_buttons(
            priority={'href': '#manager-intake-board', 'summary': 'Triagem aberta.', 'count': pi},
            pending={'href': '#manager-link-board', 'summary': 'Vinculos pendentes.'},
            next_action={'href': '#manager-finance-board', 'summary': 'Cobranca urgente.', 'count': op},
            scope=scope,
        )

    if current_path.startswith('/operacao/coach/'):
        return build_shell_action_buttons(
            priority={'href': '#coach-sessions-board', 'summary': 'Turmas do turno.', 'count': st},
            pending={'href': '#coach-sessions-board', 'summary': 'Presenca aberta.'},
            next_action={'href': '#coach-boundary-board', 'summary': 'Decisao tecnica.'},
            scope=scope,
        )

    if current_path.startswith('/operacao/'):
        return build_shell_action_buttons(
            priority={'href': '#owner-growth-board', 'summary': 'Crescimento e rotina.'},
            pending={'href': '#owner-risk-board', 'summary': 'Risco de caixa.', 'count': op},
            next_action={'href': '#owner-structure-board', 'summary': 'Estrutura do box.'},
            scope=scope,
        )

    if current_path.startswith('/acessos/'):
        return build_shell_action_buttons(
            priority={'href': '#access-current-role', 'summary': 'Escopo do papel.'},
            pending={'href': '#access-role-map', 'summary': 'Mapa de fronteiras.'},
            next_action={'href': '#access-governance-board', 'summary': 'Governanca pratica.'},
            scope=scope,
        )

    if current_path.startswith('/mapa-sistema/'):
        return build_shell_action_buttons(
            priority={'href': '#system-flow-board', 'summary': 'Fluxo macro.'},
            pending={'href': '#system-reading-board', 'summary': 'Ordem de estudo.'},
            next_action={'href': '#system-bug-board', 'summary': 'Triagem de bugs.'},
            scope=scope,
        )

    return build_shell_action_buttons(
        priority={'href': '/dashboard/', 'summary': 'Panorama do dia.'},
        pending={'href': '/alunos/#student-intake-board', 'summary': 'Fila pendente.', 'count': pi},
        next_action={'href': '/grade-aulas/#today-board', 'summary': 'Proxima acao.', 'count': st},
        scope=scope,
    )


__all__ = ['attach_shell_action_buttons', 'build_default_shell_action_buttons', 'build_shell_action_buttons', 'get_shell_counts', 'resolve_shell_scope']