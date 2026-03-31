"""
ARQUIVO: presentation das telas do guide interno.

POR QUE ELE EXISTE:
- tira da view HTTP a montagem estrutural das telas internas do guide.
- organiza a leitura pedagogica e operacional em payloads explicitos.
"""

from access.shell_actions import build_shell_action_buttons_from_focus
from shared_support.page_payloads import build_page_assets, build_page_hero, build_page_payload
from shared_support.operational_settings import get_operational_whatsapp_repeat_block_hours


def build_system_map_page():
    system_map_focus = [
        {'href': '#system-flow-board', 'summary': 'Abrir o fluxo macro do sistema para entender o ponto mais quente da arquitetura.'},
        {'href': '#system-reading-board', 'summary': 'Ir para a ordem de leitura e ver o que ainda esta pendente de entendimento.'},
        {'href': '#system-bug-board', 'summary': 'Descer para a triagem pratica do proximo lugar onde investigar.'},
    ]

    return build_page_payload(
        context={
            'page_key': 'system-map',
            'title': 'Mapa do Sistema',
            'subtitle': 'Modulos, fronteiras e onde investigar bugs.',
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(focus=system_map_focus, scope='system-map'),
        },
        data={
            'hero': build_page_hero(
                eyebrow='Leitura guiada',
                title='Mapa do Sistema',
                copy='Modulos, fronteiras e onde investigar bugs.',
                actions=[
                    {'label': 'Ver papeis', 'href': '/acessos/', 'kind': 'secondary'},
                ],
                aria_label='Panorama do mapa do sistema',
                classes=['system-map-hero'],
                data_panel='system-map-hero',
            ),
            'system_flow': [
                'Entrada do projeto pelo Django',
                'Configuracao global, ambientes e rotas principais',
                'Acesso, login e definicao de papel',
                'Contexto global de navegacao filtrando a sidebar por papel',
                'Leitura dos modelos do negocio',
                'Catalogo visual separado em views, queries e workflows',
                'Areas operacionais separadas em workspaces, snapshots e actions',
                'Montagem do dashboard por snapshot e renderizacao visual final',
                'Admin, auditoria, comandos e testes apoiando a operacao',
            ],
            'module_cards': [
                {
                    'title': 'Entrada e perfis',
                    'summary': 'Controla login, logout, papeis, permissoes e navegacao global por papel.',
                    'paths': [
                        'access/urls.py',
                        'access/views.py',
                        'access/roles/',
                        'access/context_processors.py',
                    ],
                },
                {
                    'title': 'Auditoria',
                    'summary': 'Registra acoes sensiveis e prepara integridade para manutencao tecnica e contingencia futura.',
                    'paths': [
                        'boxcore/models/audit.py',
                        'auditing/services.py',
                        'auditing/admin.py',
                    ],
                },
                {
                    'title': 'Jornada do aluno e financeiro',
                    'summary': 'Organiza a rotina de alunos, financeiro e grade por dominio, separando HTTP, leituras e regra de negocio.',
                    'paths': [
                        'catalog/views/student_views.py',
                        'catalog/views/finance_views.py',
                        'catalog/views/class_grid_views.py',
                        'catalog/student_queries.py',
                        'catalog/finance_queries.py',
                        'catalog/finance_snapshot/',
                        'catalog/services/',
                    ],
                },
                {
                    'title': 'Rotina operacional do box',
                    'summary': 'Separa workspaces, snapshots e acoes reais de Owner, DEV, Manager e Coach.',
                    'paths': [
                        'operations/urls.py',
                        'operations/base_views.py',
                        'operations/workspace_views.py',
                        'operations/action_views.py',
                        'operations/actions.py',
                        'operations/facade/workspace.py',
                        'templates/operations/',
                    ],
                },
                {
                    'title': 'Dashboard',
                    'summary': 'Resume a operacao do box com view HTTP enxuta e snapshot consolidado de leitura.',
                    'paths': [
                        'dashboard/dashboard_views.py',
                        'dashboard/dashboard_snapshot_queries.py',
                        'templates/dashboard/index.html',
                    ],
                },
                {
                    'title': 'Base do negocio',
                    'summary': 'Guarda a estrutura real dos dados de aluno, financeiro, operacao, entrada provisoria e WhatsApp.',
                    'paths': [
                        'boxcore/models/students.py',
                        'boxcore/models/finance.py',
                        'boxcore/models/operations.py',
                        'boxcore/models/onboarding.py',
                        'boxcore/models/communications.py',
                        'communications/models.py',
                    ],
                },
                {
                    'title': 'Backoffice administrativo',
                    'summary': 'Organiza o backoffice do Django por assunto.',
                    'paths': [
                        'students/admin.py',
                        'finance/admin.py',
                        'operations/admin.py',
                        'communications/admin.py',
                        'boxcore/admin/onboarding.py',
                    ],
                },
                {
                    'title': 'Automacao interna',
                    'summary': 'Executa automacoes internas como bootstrap de papeis e importacao de alunos.',
                    'paths': [
                        'boxcore/management/commands/bootstrap_roles.py',
                        'boxcore/management/commands/import_students_csv.py',
                    ],
                },
                {
                    'title': 'Cobertura critica',
                    'summary': 'Valida acesso, catalogo, dashboard, importacao e operacao, incluindo services das camadas novas.',
                    'paths': [
                        'boxcore/tests/test_access.py',
                        'boxcore/tests/test_catalog.py',
                        'boxcore/tests/test_catalog_services.py',
                        'boxcore/tests/test_dashboard.py',
                        'boxcore/tests/test_guide.py',
                        'boxcore/tests/test_import_students.py',
                        'boxcore/tests/test_operations.py',
                        'boxcore/tests/test_operations_services.py',
                    ],
                },
            ],
            'bug_lookup': [
                ('Entrada, login ou papel', 'access/'),
                ('Sidebar ou atalhos errados para o papel', 'access/context_processors.py e templates/layouts/base.html'),
                ('Diretorio de alunos, ficha ou cadastro leve', 'catalog/views/student_views.py e catalog/student_queries.py'),
                ('Financeiro visual, fila de cobranca ou comunicacao', 'catalog/views/finance_views.py, catalog/finance_queries.py, catalog/finance_snapshot/ e catalog/services/operational_queue.py'),
                ('Workspace do dev, manager ou coach', 'operations/workspace_views.py, operations/action_views.py e templates/operations/'),
                ('Auditoria e rastreabilidade', 'boxcore/models/audit.py, auditing/services.py e auditing/admin.py'),
                ('Painel, cards ou alertas do dashboard', 'dashboard/dashboard_views.py e dashboard/dashboard_snapshot_queries.py'),
                ('Cadastro principal do aluno', 'boxcore/models/students.py ou students/admin.py'),
                ('Lead ou entrada provisoria', 'communications/models.py ou communications/admin.py'),
                ('WhatsApp e vinculo de contato', 'communications/models.py ou communications/admin.py'),
                ('Pagamento, plano ou matricula', 'boxcore/models/finance.py ou finance/admin.py'),
                ('Aula, presenca, check-in ou falta', 'boxcore/models/operations.py ou operations/admin.py'),
                ('Importacao', 'boxcore/management/commands/import_students_csv.py'),
                ('Visual da interface', 'templates/'),
                ('Rotas', 'config/urls.py, boxcore/urls.py e modulos de urls'),
            ],
            'reading_order': [
                'Subida do sistema e configuracao do ambiente',
                'Entrada, login, perfis e navegacao por papel',
                'Base de dados do negocio do box',
                'Jornada visual de alunos, financeiro e grade',
                'Rotina operacional por papel dentro do box',
                'Painel principal com leitura consolidada da operacao',
                'Auditoria e rastreabilidade',
                'Automacao interna e importacao',
                'Backoffice administrativo',
                'Testes por fluxo critico',
            ],
            'key_files': [
                'manage.py',
                'config/settings/base.py',
                'config/settings/development.py',
                'config/settings/production.py',
                'config/urls.py',
                'boxcore/urls.py',
                'access/views.py',
                'access/context_processors.py',
                'catalog/views/student_views.py',
                'catalog/finance_queries.py',
                'catalog/finance_snapshot/snapshot.py',
                'operations/workspace_views.py',
                'operations/action_views.py',
                'operations/actions.py',
                'operations/session_snapshots.py',
                'boxcore/models/audit.py',
                'auditing/services.py',
                'boxcore/models/students.py',
                'boxcore/models/finance.py',
                'boxcore/models/operations.py',
                'boxcore/models/onboarding.py',
                'boxcore/models/communications.py',
                'communications/models.py',
                'communications/admin.py',
                'dashboard/dashboard_views.py',
                'dashboard/dashboard_snapshot_queries.py',
                'guide/views.py',
                'templates/layouts/base.html',
                'templates/includes/ui/',
                'static/css/design-system.css',
                'static/css/catalog/shared.css',
                'static/css/catalog/students.css',
                'static/css/catalog/finance/',
                'static/css/catalog/class-grid.css',
            ],
            'reading_principles': [
                'Entenda por onde a requisicao entra e como rotas sao distribuidas.',
                'Identifique se o dominio separa view HTTP, query de leitura e action/workflow.',
                'Veja como o papel do usuario afeta sidebar, area principal e acoes.',
                'Desca para modelos, depois templates, admin e testes.',
            ],
            'product_split': [
                'Views: permissao, contexto, formularios e renderizacao.',
                'Queries/snapshots: leitura, agregacao e montagem de contexto pesado.',
                'Actions/workflows: mutacoes reais e regras sensiveis do dominio.',
            ],
            'usage_notes': [
                'Quando quiser estudar o projeto, siga a ordem recomendada de estudo.',
                'Quando encontrar um bug, use a tabela de sintomas para saber onde comecar.',
                'Quando quiser criar algo novo, descubra primeiro se ele e uma view, uma leitura de snapshot ou uma action de negocio antes de escolher a pasta.',
                'Quando o projeto crescer, esta pagina deve crescer junto para continuar servindo como mapa.',
            ],
        },
        actions={
            'primary': {
                'roles': '/acessos/',
            },
        },
        assets=build_page_assets(css=['css/guide/system-map.css']),
    )


def build_operational_settings_page():
    operational_focus = [
        {'href': '#operational-settings-window', 'summary': 'Ajustar a janela de bloqueio do WhatsApp sem editar variavel de ambiente.'},
        {'href': '#operational-settings-access', 'summary': 'Criar perfis de acesso sem depender do admin do Django.'},
        {'href': '/acessos/#access-profile-create', 'summary': 'Abrir a area de acessos para seguir a configuracao da equipe.'},
    ]
    repeat_block_hours = get_operational_whatsapp_repeat_block_hours()

    return build_page_payload(
        context={
            'page_key': 'operational-settings',
            'title': 'Configuracoes operacionais',
            'subtitle': 'Ajuste rapido da janela do WhatsApp e dos perfis de acesso.',
        },
        shell={
            'shell_action_buttons': build_shell_action_buttons_from_focus(
                focus=operational_focus,
                scope='operational-settings',
            ),
        },
        data={
            'hero': build_page_hero(
                eyebrow='Configuracao operacional',
                title='Configuracoes operacionais',
                copy='Ajuste rapido da janela do WhatsApp e dos perfis de acesso.',
                actions=[
                    {'label': 'Abrir acessos', 'href': '/acessos/#access-profile-create', 'kind': 'secondary'},
                ],
                aria_label='Janela operacional do WhatsApp',
                classes=['system-map-hero'],
                data_panel='operational-settings-hero',
            ),
            'repeat_block_hours': repeat_block_hours,
            'repeat_block_mode_label': (
                'Repeticao imediata liberada'
                if repeat_block_hours == 0 else
                f'Bloqueio de repeticao por {repeat_block_hours}h'
            ),
            'guardrails': [
                'A mesma mensagem para o mesmo contato nao dispara de novo dentro da janela configurada.',
                'Quando bloqueado, o ultimo log valido e reaproveitado para manter rastreabilidade.',
                'Papeis somente leitura nao recebem CTA de disparo no Dashboard.',
            ],
            'repeat_block_options': [
                {'value': 24, 'label': '24h', 'summary': 'Trava diaria padrao para evitar repeticao no mesmo dia.'},
                {'value': 12, 'label': '12h', 'summary': 'Janela intermediaria para uma retomada mais curta.'},
                {'value': 0, 'label': '0h', 'summary': 'Libera repeticao imediata quando a operacao precisar.'},
            ],
            'access_overview_href': '/acessos/#access-profile-create',
        },
        assets=build_page_assets(css=['css/guide/system-map.css']),
    )
