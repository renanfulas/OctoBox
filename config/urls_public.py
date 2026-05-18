"""
ARQUIVO: URLs do schema public (PUBLIC_SCHEMA_URLCONF).

POR QUE ELE EXISTE:
- django-tenants roteie requisições para este URLCONF quando o schema é public.
- Paths aqui funcionam sem tenant ativo: login, signup, webhook, healthcheck, admin.

O QUE ESTE ARQUIVO FAZ:
- Serve as rotas que existem ANTES de qualquer Box ser provisionado.
- Não inclui rotas de domínio (dashboard, finanças, alunos) — essas ficam em config/urls.py.

PONTOS CRITICOS:
- Qualquer rota que precisa funcionar sem tenant (ex.: Stripe webhook, magic link) vem aqui.
- Rotas do aluno (/aluno/auth/) vêm aqui porque StudentAuthMiddleware resolve tenant depois.
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
