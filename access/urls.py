"""
ARQUIVO: rotas do modulo de acesso.

POR QUE ELE EXISTE:
- Separa autenticacao e visao de papeis do restante do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Define a entrada do sistema.
2. Expoe login e logout.
3. Expoe a tela de papeis e acessos.

PONTOS CRITICOS:
- Mudancas erradas nos nomes das rotas quebram redirecionamentos e links do projeto.
"""

from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    AccessEntryHubView,
    AccessOverviewView,
    AppHostThrottledLoginView,
    HomeRedirectView,
    LandingPreviewView,
    ProductPageView,
)

urlpatterns = [
    path('', HomeRedirectView.as_view(), name='home'),
    path('produto/', ProductPageView.as_view(), name='product'),
    path('acessos/', AccessOverviewView.as_view(), name='access-overview'),
    path('login/', AccessEntryHubView.as_view(), name='login'),
    path('login/funcionario/', AppHostThrottledLoginView.as_view(), name='login-staff'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# Rota de preview da landing sem o redirect de app host. Util para inspecao
# visual em ambiente local. Registra apenas em DEBUG para nao expor em producao.
if settings.DEBUG:
    urlpatterns.append(
        path('_preview/landing/', LandingPreviewView.as_view(), name='landing-preview'),
    )
