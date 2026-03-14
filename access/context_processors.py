"""
ARQUIVO: contexto global de navegacao por papel.

POR QUE ELE EXISTE:
- Evita repetir logica de sidebar, topbar e alertas em cada view autenticada.
- Mantem o menu coerente com o papel efetivo do usuario e com a rota ativa.

O QUE ESTE ARQUIVO FAZ:
1. Descobre o papel atual do usuario logado.
2. Monta os links permitidos para a sidebar.
3. Marca automaticamente o item ativo da navegacao.
4. Expoe alertas globais de financeiro e intake para os templates.
5. Gera uma versao de assets para evitar cache antigo de CSS no navegador.

PONTOS CRITICOS:
- Mudancas aqui impactam a navegacao do sistema inteiro.
- Os links devem refletir a fronteira operacional e tecnica real de cada papel.
"""

import time
from pathlib import Path

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from access.shell_actions import build_default_shell_action_buttons, resolve_shell_scope
from communications.queries import count_pending_intakes
from finance.models import Payment, PaymentStatus
from operations.models import ClassSession


_ASSET_VERSION_CACHE = {
    'checked_at': 0.0,
    'value': '1',
}
_ASSET_VERSION_TTL_SECONDS = 5.0


def _admin_changelist_url(app_label, model_name, fallback='/admin/'):
    try:
        return reverse(f'admin:{app_label}_{model_name}_changelist')
    except NoReverseMatch:
        return fallback


def _calculate_static_asset_version():
    static_root = settings.BASE_DIR / 'static'
    asset_paths = [
        *list((static_root / 'css').rglob('*.css')),
        *list((static_root / 'js').rglob('*.js')),
    ]
    mtimes = []

    for asset_path in asset_paths:
        if isinstance(asset_path, Path) and asset_path.exists():
            mtimes.append(int(asset_path.stat().st_mtime))

    return str(max(mtimes, default=1))


def _build_static_asset_version():
    now = time.monotonic()
    if now - _ASSET_VERSION_CACHE['checked_at'] < _ASSET_VERSION_TTL_SECONDS:
        return _ASSET_VERSION_CACHE['value']

    _ASSET_VERSION_CACHE['value'] = _calculate_static_asset_version()
    _ASSET_VERSION_CACHE['checked_at'] = now
    return _ASSET_VERSION_CACHE['value']


def _pick_active_href(current_path, links):
    current_path = current_path or '/'
    matches = []

    for item in links:
        href = item['href']
        if current_path == href or current_path.startswith(href):
            matches.append(href)

    return max(matches, key=len, default='')


def _build_shell_page_context(current_path, role, navigation, alerts):
    active_item = next((item for item in navigation if item['is_active']), None)
    active_label = active_item['label'] if active_item else 'OctoBox Control'
    role_label = getattr(role, 'label', 'Sem papel definido')
    role_slug = getattr(role, 'slug', '')
    scope = resolve_shell_scope(current_path=current_path, role_slug=role_slug)
    section_map = [
        {
            'prefix': '/dashboard/',
            'eyebrow': 'Pulso geral do box',
            'title': 'Dashboard',
            'subtitle': 'Panorama do dia, filas e proxima acao.',
            'scope': 'dashboard',
        },
        {
            'prefix': '/alunos/',
            'eyebrow': 'Centro da jornada do aluno',
            'title': 'Alunos',
            'subtitle': 'Entrada, base ativa e vinculos pendentes.',
            'scope': 'students',
        },
        {
            'prefix': '/financeiro/',
            'eyebrow': 'Leitura comercial do box',
            'title': 'Financeiro',
            'subtitle': 'Caixa, cobranca e carteira num so lugar.',
            'scope': 'finance',
        },
        {
            'prefix': '/grade-aulas/',
            'eyebrow': 'Ritmo da operacao de treino',
            'title': 'Grade de aulas',
            'subtitle': 'Horario, capacidade e ajustes rapidos.',
            'scope': 'class-grid',
        },
        {
            'prefix': '/operacao/',
            'eyebrow': 'Workspace principal do papel',
            'title': active_label,
            'subtitle': f'Decisao certa para o papel {role_label.lower()}.',
            'scope': 'operations-owner',
        },
        {
            'prefix': '/acessos/',
            'eyebrow': 'Fronteiras do sistema',
            'title': 'Papeis e acessos',
            'subtitle': 'Quem pode agir e onde.',
            'scope': 'access',
        },
        {
            'prefix': '/mapa-sistema/',
            'eyebrow': 'Mapa estrutural visivel',
            'title': 'Mapa do sistema',
            'subtitle': 'Arquitetura, modulos e onde investigar.',
            'scope': 'system-map',
        },
        {
            'prefix': '/admin/',
            'eyebrow': 'Camada administrativa',
            'title': active_label,
            'subtitle': 'Apoio tecnico e administrativo.',
            'scope': 'admin',
        },
    ]
    section = next((item for item in section_map if current_path.startswith(item['prefix'])), None)
    if section is None:
        section = {
            'eyebrow': 'Centro operacional atual',
            'title': active_label,
            'subtitle': 'Onde voce esta e o que importa agora.',
            'scope': 'generic',
        }

    if current_path.startswith('/dashboard/') and role_slug == ROLE_RECEPTION:
        section = {
            **section,
            'eyebrow': 'Pulso da recepcao no dia',
            'subtitle': 'Chegada, agenda e caixa curto do turno.',
        }

    return {
        **section,
        'scope': scope,
        'active_label': active_label,
        'role_label': role_label,
        'stats': [
            {'label': 'Papel ativo', 'value': role_label},
            {'label': 'Intakes abertos', 'value': alerts['pending_intakes']},
            {'label': 'Vencimentos', 'value': alerts['overdue_payments']},
        ],
    }


def _build_navigation(role_slug, current_path=''):
    base_links = [
        {'label': 'Dashboard', 'href': '/dashboard/', 'icon': '🏠'},
        {'label': 'Alunos', 'href': '/alunos/', 'icon': '🎓'},
        {'label': 'Financeiro', 'href': '/financeiro/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER), 'icon': '💰'},
        {'label': 'Grade de aulas', 'href': '/grade-aulas/', 'icon': '📅'},
        {'label': 'Minha operação', 'href': '/operacao/', 'icon': '⚡'},
        {'label': 'Papéis e acessos', 'href': '/acessos/', 'icon': '🔐'},
        {'label': 'Mapa do sistema', 'href': '/mapa-sistema/', 'icon': '🗺️'},
    ]

    role_links = {
        ROLE_OWNER: [
            {'label': 'Admin Django', 'href': '/admin/', 'icon': '⚙️'},
            {'label': 'Auditoria', 'href': _admin_changelist_url('boxcore', 'auditevent'), 'icon': '📋'},
        ],
        ROLE_DEV: [
            {'label': 'Auditoria', 'href': _admin_changelist_url('boxcore', 'auditevent'), 'icon': '📋'},
            {'label': 'Admin Django', 'href': '/admin/', 'icon': '⚙️'},
        ],
        ROLE_MANAGER: [
            {'label': 'Alunos', 'href': _admin_changelist_url('boxcore', 'student'), 'icon': '👥'},
            {'label': 'Central de entrada', 'href': _admin_changelist_url('boxcore', 'studentintake'), 'icon': '📥'},
            {'label': 'Pagamentos', 'href': _admin_changelist_url('boxcore', 'payment'), 'icon': '💳'},
            {'label': 'WhatsApp', 'href': _admin_changelist_url('boxcore', 'whatsappcontact'), 'icon': '💬'},
        ],
        ROLE_COACH: [
            {'label': 'Aulas', 'href': _admin_changelist_url('boxcore', 'classsession'), 'icon': '📅'},
            {'label': 'Ocorrências', 'href': _admin_changelist_url('boxcore', 'behaviornote'), 'icon': '📝'},
        ],
        ROLE_RECEPTION: [],
    }

    filtered_base_links = [
        item for item in base_links
        if 'roles' not in item or role_slug in item['roles']
    ]
    links = [
        {key: value for key, value in item.items() if key != 'roles'}
        for item in [*filtered_base_links, *role_links.get(role_slug, [])]
    ]
    for item in links:
        item.setdefault('icon', '')
    active_href = _pick_active_href(current_path, links)

    return [
        {
            **item,
            'is_active': item['href'] == active_href,
        }
        for item in links
    ]


def _build_topbar_alert_links(role_slug):
    finance_href_map = {
        ROLE_OWNER: '/financeiro/',
        ROLE_DEV: '/financeiro/',
        ROLE_MANAGER: '/financeiro/',
        ROLE_RECEPTION: '/operacao/recepcao/#reception-payment-board',
        ROLE_COACH: '/dashboard/#dashboard-finance-board',
    }

    return {
        'finance': finance_href_map.get(role_slug, '/dashboard/#dashboard-finance-board'),
        'intakes': '/alunos/',
    }


def role_navigation(request):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', '')
    overdue_payments = 0
    pending_intakes = 0
    sidebar_navigation = []

    sessions_today = 0

    if request.user.is_authenticated:
        from django.utils import timezone
        overdue_payments = Payment.objects.filter(status=PaymentStatus.OVERDUE).count()
        pending_intakes = count_pending_intakes()
        sessions_today = ClassSession.objects.filter(scheduled_at__date=timezone.localdate()).count()
        sidebar_navigation = _build_navigation(role_slug, request.path)

    shell_counts = {
        'overdue_payments': overdue_payments,
        'pending_intakes': pending_intakes,
        'sessions_today': sessions_today,
    }

    return {
        'current_role': role,
        'sidebar_navigation': sidebar_navigation,
        'global_search_action': '/alunos/',
        'static_asset_version': _build_static_asset_version(),
        'topbar_alert_links': _build_topbar_alert_links(role_slug),
        'shell_page_context': _build_shell_page_context(request.path, role, sidebar_navigation, shell_counts),
        'shell_counts': shell_counts,
        'shell_action_buttons': build_default_shell_action_buttons(
            current_path=request.path,
            role_slug=role_slug,
            overdue_payments=overdue_payments,
            pending_intakes=pending_intakes,
            sessions_today=sessions_today,
        ),
    }
