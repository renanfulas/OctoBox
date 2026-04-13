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
from access.navigation_contracts import get_navigation_contract
from access.roles import ROLE_COACH, ROLE_DEV, ROLE_MANAGER, ROLE_OWNER, ROLE_RECEPTION, get_user_role
from access.shell_actions import get_shell_counts, resolve_shell_scope
from shared_support.shell_payloads import (
    build_shell_alert_item,
    build_shell_alert_link,
    build_shell_chrome_payload,
    build_shell_page_payload,
    build_shell_profile_payload,
    build_shell_quick_link,
    build_shell_search_payload,
    build_shell_sidebar_item,
    build_shell_sidebar_payload,
    build_shell_theme_toggle_payload,
)
from shared_support.static_assets import resolve_runtime_css_paths


_ASSET_VERSION_CACHE = {
    'checked_at': 0.0,
    'value': '1',
    'boot_calculated': False,
}


_SIDEBAR_ICON_PATHS = {
    'DB': '<path d="M3.5 9.5 12 3l8.5 6.5v9a1 1 0 0 1-1 1H15v-6h-6v6H4.5a1 1 0 0 1-1-1z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
    'OP': '<path d="M12 3.5v4m0 9v4m8.5-8.5h-4m-9 0h-4m11.7-5.7-2.8 2.8m-4.8 4.8-2.8 2.8m0-10.4 2.8 2.8m4.8 4.8 2.8 2.8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
    'AL': '<path d="M12 4 3.5 8.2 12 12.5l8.5-4.3L12 4Zm-5.5 7.2v4.3L12 19l5.5-3.5v-4.3" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
    'FI': '<path d="M12 3.5v17m4-13.5h-6.2a2.8 2.8 0 1 0 0 5.6h4.4a2.8 2.8 0 1 1 0 5.6H7.5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
    'EN': '<path d="M4.5 12h8m0 0-3-3m3 3-3 3m4.5-8.5h4a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
    'AU': '<rect x="4" y="5" width="16" height="15" rx="3" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M8 3.75v3.5M16 3.75v3.5M4 9h16" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
    'WA': '<path d="M12 3.5a8.5 8.5 0 0 0-7.4 12.7L3.75 20.5l4.5-.8A8.5 8.5 0 1 0 12 3.5Zm4.05 11.05c-.18.5-1.05.95-1.46 1.01-.38.06-.86.09-1.39-.08-.32-.1-.73-.23-1.26-.46-2.2-.95-3.64-3.17-3.75-3.32-.11-.15-.9-1.2-.9-2.3s.58-1.64.79-1.86c.2-.22.44-.27.59-.27h.43c.14 0 .33-.05.52.4.19.46.64 1.57.7 1.68.06.11.1.25.02.4-.08.15-.12.25-.24.38-.12.14-.25.31-.36.42-.12.12-.24.24-.1.47.13.23.61 1 1.32 1.63.91.81 1.67 1.06 1.9 1.18.23.11.36.09.49-.06.14-.15.58-.68.73-.92.15-.24.31-.2.52-.12.22.08 1.37.65 1.61.76.24.12.4.18.46.28.06.1.06.59-.12 1.1Z" fill="currentColor"/>',
    'OC': '<path d="M12 4.5 20 18H4l8-13.5Zm0 4.5v4m0 3.2h.01" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"/>',
}


def _render_sidebar_icon(icon_code):
    paths = _SIDEBAR_ICON_PATHS.get(icon_code)
    if not paths:
        return icon_code or ''
    return (
        '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'
        f'{paths}'
        '</svg>'
    )


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
            stat_result = asset_path.stat()
            mtimes.append(getattr(stat_result, 'st_mtime_ns', int(stat_result.st_mtime * 1_000_000_000)))

    return str(max(mtimes, default=1))


def _build_static_asset_version():
    if not settings.DEBUG:
        # PERFORMANCE AAA: Boot-time Asset Cache
        # Em producao, o CSS/JS nao muda sozinho.
        # Varremos os arquivos do HD exatas UMA vez no ciclo de vida da worker.
        if not _ASSET_VERSION_CACHE['boot_calculated']:
            _ASSET_VERSION_CACHE['value'] = getattr(settings, 'STATIC_ASSET_VERSION', _calculate_static_asset_version())
            _ASSET_VERSION_CACHE['boot_calculated'] = True
        return _ASSET_VERSION_CACHE['value']

    # Em modo de desenvolvimento (DEBUG=True), verificamos a cada 1 segundo
    # para permitir live reload fluido sem reiniciar o servidor.
    now = time.monotonic()
    if now - _ASSET_VERSION_CACHE['checked_at'] < 1:
        return _ASSET_VERSION_CACHE['value']

    _ASSET_VERSION_CACHE['value'] = _calculate_static_asset_version()
    _ASSET_VERSION_CACHE['checked_at'] = now
    return _ASSET_VERSION_CACHE['value']


def _pick_active_nav_key(current_view_name):
    contract = get_navigation_contract(current_view_name)
    return contract.get('nav_key', '')


def _build_shell_page_context(current_view_name, current_path, role, navigation, alerts):
    contract = get_navigation_contract(current_view_name)
    nav_key = contract.get('nav_key')

    active_item = next((item for item in navigation if item.get('nav_key') == nav_key), None)
    active_label = active_item['label'] if active_item else 'OctoBox Control'
    role_label = getattr(role, 'label', 'Sem papel definido')
    role_slug = getattr(role, 'slug', '')

    scope = resolve_shell_scope(view_name=current_view_name, role_slug=role_slug, fallback_path=current_path)

    section_map = {
        'dashboard': {'eyebrow': 'Painel', 'title': 'Dashboard'},
        'intake-center': {'eyebrow': 'Triagem', 'title': 'Fila de Entradas'},
        'students': {'eyebrow': 'Gestao', 'title': 'Diretorio de Alunos'},
        'finance': {'eyebrow': 'Gestao', 'title': 'Centro Financeiro'},
        'class-grid': {'eyebrow': 'Grade', 'title': 'Agenda de Aulas'},
        'reports-hub': {'eyebrow': 'Relatorios', 'title': 'Camada gerencial'},
        'operations-owner': {'eyebrow': 'Operacao', 'title': 'Painel Operacional'},
        'access': {'eyebrow': 'Acessos', 'title': 'Papeis e acessos'},
        'system-map': {'eyebrow': 'Sistema', 'title': 'Mapa do sistema'},
        'operational-settings': {'eyebrow': 'Config', 'title': 'Configuracoes operacionais'},
        'admin': {'eyebrow': 'Admin', 'title': active_label},
    }

    section = section_map.get(scope)
    if not section:
        section = {'eyebrow': 'OctoBox', 'title': active_label}

    if scope == 'dashboard' and role_slug == ROLE_RECEPTION:
        section = {**section, 'eyebrow': 'Recepcao'}

    return build_shell_page_payload(
        eyebrow=section['eyebrow'],
        title=section['title'],
        scope=scope,
        active_label=active_label,
        role_label=role_label,
        role_slug=role_slug,
    )


def _build_navigation(role_slug, current_view_name):
    operation_roles = (ROLE_OWNER, ROLE_DEV, ROLE_RECEPTION, ROLE_COACH)
    if getattr(settings, 'OPERATIONS_MANAGER_WORKSPACE_ENABLED', False):
        operation_roles = (*operation_roles, ROLE_MANAGER)

    base_links = [
        {
            'nav_key': 'dashboard',
            'label': 'Dashboard',
            'href': reverse('dashboard'),
            'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_COACH),
            'icon': 'DB',
        },
        {
            'nav_key': 'operacao',
            'label': 'Minha operacao',
            'href': reverse('role-operations'),
            'roles': operation_roles,
            'icon': 'OP',
        },
        {'nav_key': 'alunos', 'label': 'Alunos', 'href': reverse('student-directory'), 'icon': 'AL'},
        {
            'nav_key': 'financeiro',
            'label': 'Financeiro',
            'href': reverse('finance-center'),
            'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER),
            'icon': 'FI',
        },
        {
            'nav_key': 'entradas',
            'label': 'Entradas',
            'href': reverse('intake-center'),
            'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER, ROLE_RECEPTION),
            'icon': 'EN',
        },
        {'nav_key': 'grade-aulas', 'label': 'Grade de aulas', 'href': reverse('class-grid'), 'icon': 'AU'},
    ]

    role_links = {
        ROLE_OWNER: [
            {'nav_key': 'whatsapp', 'label': 'WhatsApp', 'href': reverse('whatsapp-workspace'), 'icon': 'WA'},
        ],
        ROLE_DEV: [],
        ROLE_MANAGER: [
            {'nav_key': 'whatsapp', 'label': 'WhatsApp', 'href': reverse('whatsapp-workspace'), 'icon': 'WA'},
        ],
        ROLE_COACH: [
            {'nav_key': 'operacao', 'label': 'Ocorrencias', 'href': reverse('role-operations') + '#coach-boundary-board', 'icon': 'OC'},
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

    for item in links:
        code = item.get('icon', '')
        item['icon'] = _render_sidebar_icon(code)

    active_nav_key = _pick_active_nav_key(current_view_name)

    return [
        build_shell_sidebar_item(
            nav_key=item.get('nav_key', ''),
            label=item.get('label', ''),
            href=item.get('href', ''),
            icon=item.get('icon', ''),
            is_active=item.get('nav_key') == active_nav_key,
        )
        for item in links
    ]


def _build_topbar_alert_links(role_slug):
    finance_href_map = {
        ROLE_OWNER: reverse('finance-center'),
        ROLE_DEV: reverse('finance-center'),
        ROLE_MANAGER: reverse('finance-center'),
        ROLE_RECEPTION: reverse('reception-workspace') + '#reception-payment-board',
        ROLE_COACH: reverse('finance-center'),
    }

    return {
        'finance': finance_href_map.get(role_slug, reverse('finance-center')),
        'intakes': reverse('intake-center'),
    }


def role_navigation(request):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', '')
    user_display_name = ''
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

    view_name = getattr(request.resolver_match, 'view_name', '') if hasattr(request, 'resolver_match') else ''

    if request.user.is_authenticated:
        user_display_name = request.user.get_full_name() or request.user.username
        shell_counts = get_shell_counts()
        sidebar_navigation = _build_navigation(role_slug, current_view_name=view_name)

        if role_slug in (ROLE_OWNER, ROLE_DEV):
            profile_navigation = [
                {'label': 'Papeis e acessos', 'href': reverse('access-overview')},
                {'label': 'Config. operacionais', 'href': reverse('operational-settings')},
                {'label': 'Auditoria', 'href': admin_changelist_url('boxcore', 'auditevent')},
            ]

    shell_page_context = _build_shell_page_context(view_name, request.path, role, sidebar_navigation, shell_counts)
    topbar_alert_links = _build_topbar_alert_links(role_slug)
    global_search_action = reverse('student-directory')
    topbar_quick_links = [
        build_shell_quick_link(
            label='+ Aluno',
            href=reverse('student-quick-create') + '#student-form-essential',
            kind='secondary',
            action='open-topbar-student-quick-create',
        ),
        build_shell_quick_link(
            label='+ Entrada',
            href=reverse('intake-center'),
            kind='secondary',
            action='open-topbar-intake-center',
        ),
    ]
    shell_chrome = build_shell_chrome_payload(
        sidebar=build_shell_sidebar_payload(
            brand='OctoBox Control',
            tagline='Gestao viva do box com leitura comercial e rotina operacional clara.',
            user_name=user_display_name,
            navigation=sidebar_navigation,
        ),
        topbar={
            'search': build_shell_search_payload(
                action=global_search_action,
                placeholder='Buscar aluno, telefone ou CPF',
                autocomplete_url=reverse('api-v1-student-autocomplete'),
            ),
            'quick_links': topbar_quick_links,
            'alert_links': build_shell_alert_link(
                finance=topbar_alert_links['finance'],
                intakes=topbar_alert_links['intakes'],
            ),
            'alerts': [
                build_shell_alert_item(
                    key='overdue-payments',
                    href=topbar_alert_links['finance'],
                    count=shell_counts['overdue_payments'],
                    singular_label='vencimento',
                    plural_label='vencimentos',
                    action='open-finance-alerts',
                    tone='danger',
                ),
                build_shell_alert_item(
                    key='pending-intakes',
                    href=topbar_alert_links['intakes'],
                    count=shell_counts['pending_intakes'],
                    singular_label='entrada',
                    plural_label='entradas',
                    action='open-intake-alerts',
                ),
            ],
            'theme_toggle': build_shell_theme_toggle_payload(state='light'),
            'profile': build_shell_profile_payload(
                user_name=user_display_name,
                role_label=getattr(role, 'label', 'Sem papel definido'),
                navigation=profile_navigation,
            ),
        },
        page=shell_page_context,
        counts=shell_counts,
    )

    return {
        'can_access_admin': user_can_access_admin(request.user),
        'current_role': role,
        'shell_chrome': shell_chrome,
        'sidebar_navigation': sidebar_navigation,
        'profile_navigation': profile_navigation,
        'global_search_action': global_search_action,
        'shell_core_stylesheets': resolve_runtime_css_paths(['css/design-system.css']),
        'static_asset_version': _build_static_asset_version(),
        'topbar_alert_links': topbar_alert_links,
        'topbar_quick_links': topbar_quick_links,
        'shell_page_context': shell_page_context,
        'shell_counts': shell_counts,
    }
