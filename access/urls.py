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

from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import AccessOverviewView, HomeRedirectView, ThrottledLoginView

urlpatterns = [
    path('', HomeRedirectView.as_view(), name='home'),
    path('acessos/', AccessOverviewView.as_view(), name='access-overview'),
    path('login/', ThrottledLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
