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

from access.admin import admin_changelist_url, admin_index_url, user_can_access_admin
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from access.shell_actions import build_default_shell_action_buttons, get_shell_counts, resolve_shell_scope
from shared_support.static_assets import resolve_runtime_css_paths


_ASSET_VERSION_CACHE = {
    'checked_at': 0.0,
    'value': '1',
}


def _calculate_static_asset_version():
    static_root = settings.BASE_DIR / 'static'
    css_paths = [
        asset_path for asset_path in (static_root / 'css').rglob('*.css')
        if 'build' not in asset_path.parts
    ]
    asset_paths = [
        *css_paths,
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
    ttl_seconds = 1 if settings.DEBUG else 30
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
        {'prefix': '/entradas/', 'eyebrow': 'Triagem', 'title': 'Fila de Entradas', 'scope': 'intake-center'},
        {'prefix': '/alunos/', 'eyebrow': 'Gestão', 'title': 'Diretório de Alunos', 'scope': 'students'},
        {'prefix': '/financeiro/', 'eyebrow': 'Gestão', 'title': 'Centro Financeiro', 'scope': 'finance'},
        {'prefix': '/grade-aulas/', 'eyebrow': 'Grade', 'title': 'Agenda de Aulas', 'scope': 'class-grid'},
        {'prefix': '/operacao/', 'eyebrow': 'Operação', 'title': 'Painel Operacional', 'scope': 'operations-owner'},
        {'prefix': '/acessos/', 'eyebrow': 'Acessos', 'title': 'Papéis e acessos', 'scope': 'access'},
        {'prefix': '/mapa-sistema/', 'eyebrow': 'Sistema', 'title': 'Mapa do sistema', 'scope': 'system-map'},
        {'prefix': '/configuracoes-operacionais/', 'eyebrow': 'Config', 'title': 'Configurações operacionais', 'scope': 'operational-settings'},
        {'prefix': f"/{settings.ADMIN_URL_PATH}", 'eyebrow': 'Admin', 'title': active_label, 'scope': 'admin'},
    ]
    section = next((item for item in section_map if current_path.startswith(item['prefix'])), None)
    if section is None:
        section = {'eyebrow': 'OctoBox', 'title': active_label, 'scope': 'generic'}

    if current_path.startswith('/dashboard/') and role_slug == ROLE_RECEPTION:
        section = {**section, 'eyebrow': 'Recepção'}

    return {
        **section,
        'scope': scope,
        'active_label': active_label,
        'role_label': role_label,
    }


def _build_navigation(role_slug, current_path=''):
    admin_home = admin_index_url()
    base_links = [
        {'label': 'Dashboard', 'href': '/dashboard/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER), 'icon': 'DB'},
        {'label': 'Minha operação', 'href': '/operacao/', 'icon': 'OP'},
        {'label': 'Alunos', 'href': '/alunos/', 'icon': 'AL'},
        {'label': 'Financeiro', 'href': '/financeiro/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER), 'icon': 'FI'},
        {'label': 'Entradas', 'href': '/entradas/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION), 'icon': 'EN'},
        {'label': 'Grade de aulas', 'href': '/grade-aulas/', 'icon': 'AU'},
    ]

    role_links = {
        ROLE_OWNER: [
            {'label': 'WhatsApp', 'href': '/operacao/whatsapp/', 'icon': 'WA'},
        ],
        ROLE_DEV: [],
        ROLE_MANAGER: [
            {'label': 'WhatsApp', 'href': '/operacao/whatsapp/', 'icon': 'WA'},
        ],
        ROLE_COACH: [
            {'label': 'Ocorrências', 'href': '/operacao/coach/#coach-boundary-board', 'icon': 'OC'},
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
    # map short icon codes to sophisticated emoji choices
    emoji_map = {
        'DB': '🏠',
        'OP': '⚡',
        'AL': '🎓',
        'FI': '💰',
        'EN': '📥',
        'AU': '🗓️',
        'AC': '👥',
        'MP': '🗺️',
        'CF': '⚙️',
        'AD': '🧩',
        'AT': '🔍',
        'WA': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" width="20" height="20" style="fill: #25D366;"><path d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-5.5-2.8-23.2-8.5-44.2-27.1-16.4-14.6-27.4-32.7-30.6-38.2-3.2-5.6-.3-8.6 2.4-11.4 2.5-2.5 5.5-6.5 8.3-9.8 2.8-3.3 3.7-5.6 5.5-9.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 13.2 5.8 23.5 9.2 31.5 11.8 13.3 4.2 25.4 3.6 35 2.2 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.7z"/></svg>',
        'OC': '🚨',
    }

    for item in links:
        code = item.get('icon', '')
        # prefer mapped emoji, fall back to existing icon text
        item['icon'] = emoji_map.get(code, code)
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
    profile_navigation = []
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

        # Build Profile Navigation (Administrative/Legacy links)
        admin_home = admin_index_url()
        if role_slug in (ROLE_OWNER, ROLE_DEV):
            profile_navigation = [
                {'label': 'Papéis e acessos', 'href': '/acessos/'},
                {'label': 'Config. operacionais', 'href': '/configuracoes-operacionais/'},
                {'label': 'Auditoria', 'href': admin_changelist_url('boxcore', 'auditevent')},
                {'label': 'Admin Django', 'href': admin_home},
                {'label': 'Mapa do sistema', 'href': '/mapa-sistema/'},
            ]

    return {
        'can_access_admin': user_can_access_admin(request.user),
        'current_role': role,
        'sidebar_navigation': sidebar_navigation,
        'profile_navigation': profile_navigation,
        'global_search_action': '/alunos/',
        'shell_core_stylesheets': resolve_runtime_css_paths(['css/design-system.css']),
        'static_asset_version': _build_static_asset_version(),
        'topbar_alert_links': _build_topbar_alert_links(role_slug),
        'topbar_quick_links': [
            {'label': '+ Aluno', 'href': '/alunos/novo/#student-form-essential', 'kind': 'secondary', 'action': 'open-topbar-student-quick-create'},
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


