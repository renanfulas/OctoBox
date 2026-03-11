"""
ARQUIVO: views do guia interno do sistema.

POR QUE ELE EXISTE:
- Traduz a arquitetura do projeto para uma visão visual e pedagógica dentro do próprio app.

O QUE ESTE ARQUIVO FAZ:
1. Expõe a página Mapa do Sistema.
2. Organiza módulos, fluxo, pontos de bug e ordem de leitura.
3. Entrega uma visão navegável para manutenção e estudo.

PONTOS CRITICOS:
- A navegação por papel vem de context processor global e precisa continuar coerente aqui.
- A estrutura exibida aqui deve acompanhar a organização real do projeto.
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
            'Acesso, login e definição de papel',
            'Contexto global de navegação filtrando a sidebar por papel',
            'Leitura dos modelos do negócio',
            'Catalogo visual separado em views, queries e workflows',
            'Areas operacionais separadas em workspaces, snapshots e actions',
            'Montagem do dashboard por snapshot e renderizacao visual final',
            'Admin, auditoria, comandos e testes apoiando a operacao',
        ]
        context['module_cards'] = [
            {
                'title': 'Entrada e perfis',
                'summary': 'Controla login, logout, papéis, permissões e navegação global por papel.',
                'paths': [
                    'boxcore/access/urls.py',
                    'boxcore/access/views.py',
                    'boxcore/access/roles/',
                    'boxcore/access/context_processors.py',
                ],
            },
            {
                'title': 'Auditoria',
                'summary': 'Registra ações sensíveis e prepara integridade para manutenção técnica e contingência futura.',
                'paths': [
                    'boxcore/models/audit.py',
                    'boxcore/auditing/services.py',
                    'boxcore/admin/audit.py',
                ],
            },
            {
                'title': 'Jornada do aluno e financeiro',
                'summary': 'Organiza a rotina de alunos, financeiro e grade por dominio, separando HTTP, leituras e regra de negocio.',
                'paths': [
                    'boxcore/catalog/views/student_views.py',
                    'boxcore/catalog/views/finance_views.py',
                    'boxcore/catalog/views/class_grid_views.py',
                    'boxcore/catalog/student_queries.py',
                    'boxcore/catalog/finance_queries.py',
                    'boxcore/catalog/services/',
                ],
            },
            {
                'title': 'Rotina operacional do box',
                'summary': 'Separa workspaces, snapshots e acoes reais de Owner, DEV, Manager e Coach.',
                'paths': [
                    'boxcore/operations/urls.py',
                    'boxcore/operations/base_views.py',
                    'boxcore/operations/workspace_views.py',
                    'boxcore/operations/workspace_snapshot_queries.py',
                    'boxcore/operations/action_views.py',
                    'boxcore/operations/actions.py',
                    'templates/operations/',
                ],
            },
            {
                'title': 'Dashboard',
                'summary': 'Resume a operacao do box com view HTTP enxuta e snapshot consolidado de leitura.',
                'paths': [
                    'boxcore/dashboard/dashboard_views.py',
                    'boxcore/dashboard/dashboard_snapshot_queries.py',
                    'templates/dashboard/index.html',
                ],
            },
            {
                'title': 'Base do negocio',
                'summary': 'Guarda a estrutura real dos dados de aluno, financeiro, operação, entrada provisória e WhatsApp.',
                'paths': [
                    'boxcore/models/students.py',
                    'boxcore/models/finance.py',
                    'boxcore/models/operations.py',
                    'boxcore/models/onboarding.py',
                    'boxcore/models/communications.py',
                ],
            },
            {
                'title': 'Backoffice administrativo',
                'summary': 'Organiza o backoffice do Django por assunto.',
                'paths': [
                    'boxcore/admin/students.py',
                    'boxcore/admin/finance.py',
                    'boxcore/admin/operations.py',
                    'boxcore/admin/onboarding.py',
                ],
            },
            {
                'title': 'Automacao interna',
                'summary': 'Executa automações internas como bootstrap de papéis e importação de alunos.',
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
            ('Entrada, login ou papel', 'boxcore/access/'),
            ('Sidebar ou atalhos errados para o papel', 'boxcore/access/context_processors.py e templates/layouts/base.html'),
            ('Diretorio de alunos, ficha ou cadastro leve', 'boxcore/catalog/views/student_views.py e boxcore/catalog/student_queries.py'),
            ('Financeiro visual, fila de cobranca ou comunicacao', 'boxcore/catalog/views/finance_views.py, boxcore/catalog/finance_queries.py e boxcore/catalog/services/operational_queue.py'),
            ('Workspace do dev, manager ou coach', 'boxcore/operations/workspace_views.py, boxcore/operations/action_views.py e templates/operations/'),
            ('Auditoria e rastreabilidade', 'boxcore/models/audit.py, boxcore/auditing/services.py e boxcore/admin/audit.py'),
            ('Painel, cards ou alertas do dashboard', 'boxcore/dashboard/dashboard_views.py e boxcore/dashboard/dashboard_snapshot_queries.py'),
            ('Cadastro principal do aluno', 'boxcore/models/students.py ou boxcore/admin/students.py'),
            ('Lead ou entrada provisoria', 'boxcore/models/onboarding.py ou boxcore/admin/onboarding.py'),
            ('WhatsApp e vinculo de contato', 'boxcore/models/communications.py ou boxcore/admin/onboarding.py'),
            ('Pagamento, plano ou matricula', 'boxcore/models/finance.py ou boxcore/admin/finance.py'),
            ('Aula, presenca, check-in ou falta', 'boxcore/models/operations.py ou boxcore/admin/operations.py'),
            ('Importação', 'boxcore/management/commands/import_students_csv.py'),
            ('Visual da interface', 'templates/'),
            ('Rotas', 'config/urls.py, boxcore/urls.py e módulos de urls'),
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
            'boxcore/access/views.py',
            'boxcore/access/context_processors.py',
            'boxcore/catalog/views/student_views.py',
            'boxcore/catalog/finance_queries.py',
            'boxcore/operations/workspace_views.py',
            'boxcore/operations/actions.py',
            'boxcore/models/audit.py',
            'boxcore/auditing/services.py',
            'boxcore/models/students.py',
            'boxcore/models/finance.py',
            'boxcore/models/operations.py',
            'boxcore/models/onboarding.py',
            'boxcore/models/communications.py',
            'boxcore/dashboard/dashboard_views.py',
            'boxcore/dashboard/dashboard_snapshot_queries.py',
            'templates/layouts/base.html',
        ]
        return context