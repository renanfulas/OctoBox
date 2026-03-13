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


def _build_shell_page_context(current_path, role, navigation, alerts):
    active_item = next((item for item in navigation if item['is_active']), None)
    active_label = active_item['label'] if active_item else 'OctoBox Control'
    role_label = getattr(role, 'label', 'Sem papel definido')
    section_map = [
        {
            'prefix': '/dashboard/',
            'eyebrow': 'Pulso geral do box',
            'title': 'Dashboard',
            'subtitle': 'Comece pelo panorama vivo do dia antes de descer para filas, cobrancas ou ajustes de detalhe.',
        },
        {
            'prefix': '/alunos/',
            'eyebrow': 'Centro da jornada do aluno',
            'title': 'Alunos',
            'subtitle': 'Aqui a leitura precisa deixar claro quem entrou, quem esta ativo e onde a relacao ainda pede vinculo ou correcoes simples.',
        },
        {
            'prefix': '/financeiro/',
            'eyebrow': 'Leitura comercial do box',
            'title': 'Financeiro',
            'subtitle': 'Use este recorte para ver pressao de caixa, proposta comercial e sinais de retencao sem transformar a tela em extrato confuso.',
        },
        {
            'prefix': '/grade-aulas/',
            'eyebrow': 'Ritmo da operacao de treino',
            'title': 'Grade de aulas',
            'subtitle': 'A grade deve mostrar rapido horario, capacidade e proximas correcoes antes que a rotina dependa de memoria.',
        },
        {
            'prefix': '/operacao/',
            'eyebrow': 'Workspace principal do papel',
            'title': active_label,
            'subtitle': f'Este centro existe para o papel {role_label.lower()} enxergar primeiro a decisao certa, nao para navegar no escuro entre blocos longos.',
        },
        {
            'prefix': '/acessos/',
            'eyebrow': 'Fronteiras do sistema',
            'title': 'Papeis e acessos',
            'subtitle': 'Leia esta area como mapa de limite real: quem pode agir, onde pode agir e qual fronteira protege a rotina do box.',
        },
        {
            'prefix': '/mapa-sistema/',
            'eyebrow': 'Mapa estrutural visivel',
            'title': 'Mapa do sistema',
            'subtitle': 'A construcao pode aparecer, desde que continue bonita, legivel e capaz de orientar manutencao sem adivinhacao.',
        },
        {
            'prefix': '/admin/',
            'eyebrow': 'Camada administrativa',
            'title': active_label,
            'subtitle': 'Use esta area como apoio tecnico e administrativo, nunca como substituto da fachada principal do produto.',
        },
    ]
    section = next((item for item in section_map if current_path.startswith(item['prefix'])), None)
    if section is None:
        section = {
            'eyebrow': 'Centro operacional atual',
            'title': active_label,
            'subtitle': 'A tela atual deve dizer rapidamente onde voce esta, o que importa agora e qual proximo passo evita atrito inutil.',
        }

    if current_path.startswith('/dashboard/') and getattr(role, 'slug', '') == ROLE_RECEPTION:
        section = {
            **section,
            'eyebrow': 'Pulso da recepcao no dia',
            'subtitle': 'Comece por chegada, agenda proxima e caixa curto para a Recepcao entrar no turno com leitura util antes de abrir outras areas.',
        }

    return {
        **section,
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
        {'label': 'Dashboard', 'href': '/dashboard/'},
        {'label': 'Alunos', 'href': '/alunos/'},
        {'label': 'Financeiro', 'href': '/financeiro/', 'roles': (ROLE_OWNER, ROLE_DEV, ROLE_MANAGER)},
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

    if request.user.is_authenticated:
        overdue_payments = Payment.objects.filter(status=PaymentStatus.OVERDUE).count()
        pending_intakes = count_pending_intakes()
        sidebar_navigation = _build_navigation(role_slug, request.path)

    topbar_alerts = {
        'overdue_payments': overdue_payments,
        'pending_intakes': pending_intakes,
    }

    return {
        'current_role': role,
        'sidebar_navigation': sidebar_navigation,
        'global_search_action': '/alunos/',
        'static_asset_version': _build_static_asset_version(),
        'topbar_alerts': topbar_alerts,
        'topbar_alert_links': _build_topbar_alert_links(role_slug),
        'shell_page_context': _build_shell_page_context(request.path, role, sidebar_navigation, topbar_alerts),
    }
