"""
ARQUIVO: agregador de rotas da API.

POR QUE ELE EXISTE:
- Define um ponto unico de entrada para versoes de API sem acoplar a navegacao web interna.

O QUE ESTE ARQUIVO FAZ:
1. Publica o indice raiz da API.
2. Encaminha versoes como v1 e futuras expansoes.

PONTOS CRITICOS:
- Endpoints de API nao devem reutilizar templates nem depender da estrutura visual do site.
"""

from django.urls import include, path

from .views import ApiRootView


urlpatterns = [
    path('', ApiRootView.as_view(), name='api-root'),
    path('v1/', include('api.v1.urls')),
]
