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
            'Configuração global e rotas principais',
            'Acesso, login e definição de papel',
            'Contexto global de navegação filtrando a sidebar por papel',
            'Leitura dos modelos do negócio',
            'Áreas operacionais e ações exclusivas por papel',
            'Montagem do dashboard e contexto da tela',
            'Renderização visual no front-end e admin apoiando a operação',
        ]
        context['module_cards'] = [
            {
                'title': 'Acesso',
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
                'title': 'Operação por papel',
                'summary': 'Separa as áreas e ações reais de Owner, DEV, Manager e Coach.',
                'paths': [
                    'boxcore/operations/views.py',
                    'boxcore/operations/urls.py',
                    'templates/operations/',
                ],
            },
            {
                'title': 'Dashboard',
                'summary': 'Resume a operação do box com métricas, alertas e leitura rápida.',
                'paths': [
                    'boxcore/dashboard/views.py',
                    'templates/dashboard/index.html',
                ],
            },
            {
                'title': 'Modelos',
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
                'title': 'Admin',
                'summary': 'Organiza o backoffice do Django por assunto.',
                'paths': [
                    'boxcore/admin/students.py',
                    'boxcore/admin/finance.py',
                    'boxcore/admin/operations.py',
                    'boxcore/admin/onboarding.py',
                ],
            },
            {
                'title': 'Comandos',
                'summary': 'Executa automações internas como bootstrap de papéis e importação de alunos.',
                'paths': [
                    'boxcore/management/commands/bootstrap_roles.py',
                    'boxcore/management/commands/import_students_csv.py',
                ],
            },
            {
                'title': 'Testes',
                'summary': 'Valida acesso, guia, dashboard, importação e operação por papel.',
                'paths': [
                    'boxcore/tests/test_access.py',
                    'boxcore/tests/test_dashboard.py',
                    'boxcore/tests/test_guide.py',
                    'boxcore/tests/test_import_students.py',
                    'boxcore/tests/test_operations.py',
                ],
            },
        ]
        context['bug_lookup'] = [
            ('Login ou papel', 'boxcore/access/'),
            ('Sidebar errada para o papel', 'boxcore/access/context_processors.py e templates/layouts/base.html'),
            ('Operacao do dev, manager ou coach', 'boxcore/operations/views.py e templates/operations/'),
            ('Auditoria e rastreabilidade', 'boxcore/models/audit.py, boxcore/auditing/services.py e boxcore/admin/audit.py'),
            ('Métricas do painel', 'boxcore/dashboard/views.py'),
            ('Aluno', 'boxcore/models/students.py ou boxcore/admin/students.py'),
            ('Entrada provisoria ou lead', 'boxcore/models/onboarding.py ou boxcore/admin/onboarding.py'),
            ('WhatsApp e vinculo de contato', 'boxcore/models/communications.py ou boxcore/admin/onboarding.py'),
            ('Pagamento', 'boxcore/models/finance.py ou boxcore/admin/finance.py'),
            ('Aula, presença ou falta', 'boxcore/models/operations.py ou boxcore/admin/operations.py'),
            ('Importação', 'boxcore/management/commands/import_students_csv.py'),
            ('Visual da interface', 'templates/'),
            ('Rotas', 'config/urls.py, boxcore/urls.py e módulos de urls'),
        ]
        context['reading_order'] = [
            'Entrada do sistema e configuração global',
            'Acesso, login, papéis e navegação por papel',
            'Modelos de dados do negócio',
            'Operação por papel e ações exclusivas',
            'Auditoria e rastreabilidade',
            'Dashboard e templates principais',
            'Comandos internos e importação',
            'Admin do Django',
            'Testes por assunto',
        ]
        context['key_files'] = [
            'manage.py',
            'config/settings.py',
            'config/urls.py',
            'boxcore/urls.py',
            'boxcore/access/views.py',
            'boxcore/access/context_processors.py',
            'boxcore/operations/views.py',
            'boxcore/models/audit.py',
            'boxcore/auditing/services.py',
            'boxcore/models/students.py',
            'boxcore/models/finance.py',
            'boxcore/models/operations.py',
            'boxcore/models/onboarding.py',
            'boxcore/models/communications.py',
            'boxcore/dashboard/views.py',
            'templates/layouts/base.html',
        ]
        return context