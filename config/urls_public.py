"""
ARQUIVO: URLs do schema public — MORTO, nao usado pelo runtime atual.

⚠️ AVISO (achado em 2026-09-16, ver CLAUDE.md > Gotchas de runtime):
Este arquivo e a setting PUBLIC_SCHEMA_URLCONF (config/settings/base.py) NAO
sao consultados por nenhum request real. django_tenants.middleware.TenantMainMiddleware
(o middleware que leria PUBLIC_SCHEMA_URLCONF e trocaria request.urlconf) NUNCA foi
adicionado a MIDDLEWARE — so django_tenants como app (pra ORM/migrations) e o
DATABASE_ROUTERS estao ativos. ROOT_URLCONF = 'config.urls' e o UNICO urlconf usado,
sempre, pra qualquer request, tenant ou nao. A doc anterior deste docstring
("django-tenants roteie requisicoes para este URLCONF quando o schema e public")
e FALSA na configuracao atual — nao apague este aviso sem reler
docs/plans/urls-public-dead-code-mitigation-corda.md primeiro.

A isolacao real de "essa rota funciona sem tenant" e feita por
control.middleware.TenantBySessionMiddleware.PUBLIC_SCHEMA_PATHS (whitelist de
prefixo de path, independente de dominio/porta/urlconf) — nao por troca de
urlconf. Toda rota abaixo ja existe (e, em geral, com implementacao mais
completa) em config/urls.py: login/logout via access.urls, signup.urls,
integrations.urls, api.urls, student_app.urls, metrics_view, admin.site.urls.

POR QUE ISSO IMPORTA:
- Se um dia alguem reler o docstring antigo e assumir que mexer aqui muda o
  roteamento real, vai editar um arquivo morto e nao entender por que nada
  mudou em producao.
- O plano de mitigacao (ver link acima) avalia 3 saidas: reativar de verdade
  (instalar TenantMainMiddleware), reaproveitar como contrato/teste de
  regressao, ou excluir. Nenhuma foi executada ainda — este arquivo continua
  do jeito que estava, so com o registro corrigido.
"""

from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.contrib.auth import views as auth_views

from access.admin import install_admin_site_gate
from monitoring.prometheus_middleware import metrics_view

install_admin_site_gate()

urlpatterns = [
    # Auth de staff
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Signup e onboarding do Early Adopters
    path('', include('signup.urls')),

    # Webhook Stripe (chega antes de saber qual Box)
    path('', include('integrations.urls')),

    # API de saúde (sem tenant)
    path('api/', include('api.urls')),

    # Auth do aluno (StudentAuthMiddleware resolve tenant depois)
    path('aluno/', include('student_app.urls')),

    # Admin da plataforma (Renan)
    path('metrics/', metrics_view),
    path(settings.ADMIN_URL_PATH, admin.site.urls),
]
