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
from django.urls import reverse

from access.admin import admin_changelist_url, admin_index_url, user_can_access_admin
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from access.shell_actions import build_default_shell_action_buttons, get_shell_counts, resolve_shell_scope


_ASSET_VERSION_CACHE = {
    'checked_at': 0.0,
    'value': '1',
}


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
    if not settings.DEBUG:
        return getattr(settings, 'STATIC_ASSET_VERSION', '1')

    now = time.monotonic()
    ttl_seconds = getattr(settings, 'STATIC_ASSET_SCAN_TTL_SECONDS', 30)
    if now - _ASSET_VERSION_CACHE['checked_at'] < ttl_seconds:
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
        {'prefix': '/dashboard/', 'eyebrow': 'Painel', 'title': 'Dashboard', 'scope': 'dashboard'},
        {'prefix': '/entradas/', 'eyebrow': 'Entradas', 'title': 'Central de Intake', 'scope': 'intake-center'},
        {'prefix': '/alunos/', 'eyebrow': 'Alunos', 'title': 'Alunos', 'scope': 'students'},
        {'prefix': '/financeiro/', 'eyebrow': 'Financeiro', 'title': 'Financeiro', 'scope': 'finance'},
        {'prefix': '/grade-aulas/', 'eyebrow': 'Aulas', 'title': 'Grade de aulas', 'scope': 'class-grid'},
        {'prefix': '/operacao/', 'eyebrow': 'Operacao', 'title': active_label, 'scope': 'operations-owner'},
        {'prefix': '/acessos/', 'eyebrow': 'Acessos', 'title': 'Papeis e acessos', 'scope': 'access'},
        {'prefix': '/mapa-sistema/', 'eyebrow': 'Sistema', 'title': 'Mapa do sistema', 'scope': 'system-map'},
        {'prefix': '/configuracoes-operacionais/', 'eyebrow': 'Config', 'title': 'Configuracoes operacionais', 'scope': 'operational-settings'},
        {'prefix': f"/{settings.ADMIN_URL_PATH}", 'eyebrow': 'Admin', 'title': active_label, 'scope': 'admin'},
    ]
    section = next((item for item in section_map if current_path.startswith(item['prefix'])), None)
    if section is None:
        section = {'eyebrow': 'OctoBox', 'title': active_label, 'scope': 'generic'}

    if current_path.startswith('/dashboard/') and role_slug == ROLE_RECEPTION:
        section = {**section, 'eyebrow': 'Recepcao'}

    return {
        **section,
        'scope': scope,
        'active_label': active_label,
        'role_label': role_label,
    }


def _build_navigation(role_slug, current_path=''):
    admin_home = admin_index_url()
    base_links = [
        {'label': 'Dashboard', 'href': '/dashboard/', 'icon': 'DB'},
        {'label': 'Minha operacao', 'href': '/operacao/', 'icon': 'OP'},
        {'label': 'Alunos', 'href': '/alunos/', 'icon': 'AL'},
        {'label': 'Financeiro', 'href': '/financeiro/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER), 'icon': 'FI'},
        {'label': 'Entradas', 'href': '/entradas/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION), 'icon': 'EN'},
        {'label': 'Grade de aulas', 'href': '/grade-aulas/', 'icon': 'AU'},
        {'label': 'Papeis e acessos', 'href': '/acessos/', 'icon': 'AC'},
        {'label': 'Mapa do sistema', 'href': '/mapa-sistema/', 'icon': 'MP'},
    ]

    role_links = {
        ROLE_OWNER: [
            {'label': 'Config. operacionais', 'href': '/configuracoes-operacionais/', 'icon': 'CF'},
            {'label': 'Admin Django', 'href': admin_home, 'icon': 'AD'},
            {'label': 'Auditoria', 'href': admin_changelist_url('boxcore', 'auditevent'), 'icon': 'AT'},
        ],
        ROLE_DEV: [
            {'label': 'Config. operacionais', 'href': '/configuracoes-operacionais/', 'icon': 'CF'},
            {'label': 'Auditoria', 'href': admin_changelist_url('boxcore', 'auditevent'), 'icon': 'AT'},
            {'label': 'Admin Django', 'href': admin_home, 'icon': 'AD'},
        ],
        ROLE_MANAGER: [
            {'label': 'WhatsApp', 'href': '/operacao/manager/#manager-link-board', 'icon': 'WA'},
        ],
        ROLE_COACH: [
            {'label': 'Ocorrencias', 'href': '/operacao/coach/#coach-boundary-board', 'icon': 'OC'},
        ],
        ROLE_RECEPTION: [],
    }

    filtered_base_links = [
        item for item in base_links
        if 'roles' not in item or role_slug in item['roles']
    ]
    links = []
    seen_hrefs = set()
    for item in [*filtered_base_links, *role_links.get(role_slug, [])]:
        href = item.get('href', '')
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        links.append({key: value for key, value in item.items() if key != 'roles'})

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
        ROLE_COACH: '/financeiro/',
    }

    return {
        'finance': finance_href_map.get(role_slug, '/financeiro/'),
        'intakes': '/entradas/',
    }


def role_navigation(request):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', '')
    sidebar_navigation = []
    shell_counts = {
        'overdue_payments': 0,
        'overdue_students': 0,
        'pending_intakes': 0,
        'sessions_today': 0,
        'active_students': 0,
        'lead_students': 0,
        'active_enrollments': 0,
    }

    if request.user.is_authenticated:
        shell_counts = get_shell_counts()
        sidebar_navigation = _build_navigation(role_slug, request.path)

    return {
        'can_access_admin': user_can_access_admin(request.user),
        'current_role': role,
        'sidebar_navigation': sidebar_navigation,
        'global_search_action': '/alunos/',
        'static_asset_version': _build_static_asset_version(),
        'topbar_alert_links': _build_topbar_alert_links(role_slug),
        'topbar_quick_links': [
            {'label': '+ Novo aluno', 'href': '/alunos/novo/#student-form-essential', 'kind': 'primary', 'action': 'open-topbar-student-quick-create'},
            {'label': '+ Entrada', 'href': '/entradas/', 'kind': 'secondary', 'action': 'open-topbar-intake-center'},
        ],
        'shell_page_context': _build_shell_page_context(request.path, role, sidebar_navigation, shell_counts),
        'shell_counts': shell_counts,
        'shell_action_buttons': build_default_shell_action_buttons(
            current_path=request.path,
            role_slug=role_slug,
            overdue_payments=shell_counts['overdue_payments'],
            pending_intakes=shell_counts['pending_intakes'],
            sessions_today=shell_counts['sessions_today'],
        ),
    }
