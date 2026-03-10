"""
ARQUIVO: rotas do módulo de acesso.

POR QUE ELE EXISTE:
- Separa autenticação e visão de papéis do restante do sistema.

O QUE ESTE ARQUIVO FAZ:
1. Define a entrada do sistema.
2. Expõe login e logout.
3. Expõe a tela de papéis e acessos.

PONTOS CRITICOS:
- Mudanças erradas nos nomes das rotas quebram redirecionamentos e links do projeto.
"""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .views import AccessOverviewView, HomeRedirectView

urlpatterns = [
    path('', HomeRedirectView.as_view(), name='home'),
    path('acessos/', AccessOverviewView.as_view(), name='access-overview'),
    path('login/', LoginView.as_view(template_name='access/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]