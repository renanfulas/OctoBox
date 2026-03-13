"""
ARQUIVO: views do guia interno do sistema.

POR QUE ELE EXISTE:
- traduz a arquitetura do projeto para uma visao visual e pedagogica dentro do app real guide.

O QUE ESTE ARQUIVO FAZ:
1. expoe a pagina Mapa do Sistema.
2. organiza modulos, fluxo, pontos de bug e ordem de leitura.
3. entrega uma visao navegavel para manutencao e estudo.

PONTOS CRITICOS:
- a navegacao por papel vem de context processor global e precisa continuar coerente aqui.
- a estrutura exibida aqui deve acompanhar a organizacao real do projeto.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class SystemMapView(LoginRequiredMixin, TemplateView):
    template_name = 'guide/system-map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['system_flow'] = [
            'Entrada do projeto pelo Django',
            'Configuracao global, ambientes e rotas principais',
            'Acesso, login e definicao de papel',
            'Contexto global de navegacao filtrando a sidebar por papel',
            'Leitura dos modelos do negocio',
            'Catalogo visual separado em views, queries e workflows',
            'Areas operacionais separadas em workspaces, snapshots e actions',
            'Montagem do dashboard por snapshot e renderizacao visual final',
            'Admin, auditoria, comandos e testes apoiando a operacao',
        ]
        context['module_cards'] = [
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
        ]
        context['bug_lookup'] = [
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
        ]
        context['reading_order'] = [
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
        ]
        context['key_files'] = [
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
            'static/css/catalog-system.css',
        ]
        return context