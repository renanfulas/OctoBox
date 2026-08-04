"""
ARQUIVO: rotas do modulo de acesso.

POR QUE ELE EXISTE:
- Separa autenticacao e visao de papeis do restante do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Define a entrada do sistema.
2. Expoe login e logout.
3. Expoe a recuperacao de senha do funcionario.
4. Expoe a tela de papeis e acessos.

PONTOS CRITICOS:
- Mudancas erradas nos nomes das rotas quebram redirecionamentos e links do projeto.
- As rotas de recuperacao de senha ficam sob `login/` de proposito: o prefixo
  `/login/` esta em PUBLIC_SCHEMA_PATHS (control/middleware.py), o que garante
  schema public (onde vive auth_user) e o rate limit de scope 'login'. Tirar
  essas rotas de baixo de `login/` quebra o fluxo — ver access/password_reset.py.
"""

from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import path

from .password_reset import (
    StaffPasswordResetCompleteView,
    StaffPasswordResetConfirmView,
    StaffPasswordResetSentView,
    StaffPasswordResetView,
)
from .views import (
    AccessEntryHubView,
    AccessOverviewView,
    AppHostThrottledLoginView,
    BoxSwitchView,
    HomeRedirectView,
    LandingPreviewView,
    ProductPageView,
)

urlpatterns = [
    path('', HomeRedirectView.as_view(), name='home'),
    path('produto/', ProductPageView.as_view(), name='product'),
    path('acessos/', AccessOverviewView.as_view(), name='access-overview'),
    path('box/', BoxSwitchView.as_view(), name='box-switch'),
    path('login/', AccessEntryHubView.as_view(), name='login'),
    path('login/funcionario/', AppHostThrottledLoginView.as_view(), name='login-staff'),
    path('login/senha/', StaffPasswordResetView.as_view(), name='password-reset'),
    path('login/senha/enviado/', StaffPasswordResetSentView.as_view(), name='password-reset-sent'),
    path(
        'login/senha/redefinir/<uidb64>/<token>/',
        StaffPasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),
    path('login/senha/pronto/', StaffPasswordResetCompleteView.as_view(), name='password-reset-complete'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# Rota de preview da landing sem o redirect de app host. Util para inspecao
# visual em ambiente local. Registra apenas em DEBUG para nao expor em producao.
if settings.DEBUG:
    urlpatterns.append(
        path('_preview/landing/', LandingPreviewView.as_view(), name='landing-preview'),
    )
