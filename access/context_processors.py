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

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from access.roles import ROLE_DEV
from communications.queries import count_pending_intakes
from finance.models import Payment, PaymentStatus


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
    asset_paths = list((settings.BASE_DIR / 'static' / 'css').rglob('*.css'))
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


def _build_navigation(role_slug, current_path=''):
    base_links = [
        {'label': 'Dashboard', 'href': '/dashboard/'},
        {'label': 'Alunos', 'href': '/alunos/'},
        {'label': 'Financeiro', 'href': '/financeiro/'},
        {'label': 'Grade de aulas', 'href': '/grade-aulas/'},
        {'label': 'Minha operação', 'href': '/operacao/'},
        {'label': 'Papéis e acessos', 'href': '/acessos/'},
        {'label': 'Mapa do sistema', 'href': '/mapa-sistema/'},
    ]

    role_links = {
        ROLE_OWNER: [
            {'label': 'Admin Django', 'href': '/admin/'},
            {'label': 'Auditoria', 'href': _admin_changelist_url('boxcore', 'auditevent')},
        ],
        ROLE_DEV: [
            {'label': 'Auditoria', 'href': _admin_changelist_url('boxcore', 'auditevent')},
            {'label': 'Admin Django', 'href': '/admin/'},
        ],
        ROLE_MANAGER: [
            {'label': 'Alunos', 'href': _admin_changelist_url('boxcore', 'student')},
            {'label': 'Central de entrada', 'href': _admin_changelist_url('boxcore', 'studentintake')},
            {'label': 'Pagamentos', 'href': _admin_changelist_url('boxcore', 'payment')},
            {'label': 'WhatsApp', 'href': _admin_changelist_url('boxcore', 'whatsappcontact')},
        ],
        ROLE_COACH: [
            {'label': 'Aulas', 'href': _admin_changelist_url('boxcore', 'classsession')},
            {'label': 'Ocorrências', 'href': _admin_changelist_url('boxcore', 'behaviornote')},
        ],
    }

    links = [*base_links, *role_links.get(role_slug, [])]
    active_href = _pick_active_href(current_path, links)

    return [
        {
            **item,
            'is_active': item['href'] == active_href,
        }
        for item in links
    ]


def role_navigation(request):
    role = get_user_role(request.user)
    role_slug = getattr(role, 'slug', '')
    overdue_payments = 0
    pending_intakes = 0

    if request.user.is_authenticated:
        overdue_payments = Payment.objects.filter(status=PaymentStatus.OVERDUE).count()
        pending_intakes = count_pending_intakes()

    return {
        'current_role': role,
        'sidebar_navigation': _build_navigation(role_slug, request.path) if request.user.is_authenticated else [],
        'global_search_action': '/alunos/',
        'static_asset_version': _build_static_asset_version(),
        'topbar_alerts': {
            'overdue_payments': overdue_payments,
            'pending_intakes': pending_intakes,
        },
    }
