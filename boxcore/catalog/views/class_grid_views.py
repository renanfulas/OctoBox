"""
ARQUIVO: views da grade de aulas do catalogo.

POR QUE ELE EXISTE:
- Isola a camada HTTP da leitura visual de agenda e ocupacao de aulas.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza a grade visual de aulas.
2. Consome o snapshot de agenda vindo da camada de queries.

PONTOS CRITICOS:
- Esta tela depende do snapshot de agenda e da coerencia de datas no contexto base.
"""

from catalog.views.class_grid_views import *