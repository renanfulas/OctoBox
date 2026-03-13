"""
ARQUIVO: base das views do catalogo.

POR QUE ELE EXISTE:
- Centraliza comportamento comum das views leves do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. Define a view base com autenticacao e papeis permitidos.
2. Entrega contexto base compartilhado entre alunos, financeiro e grade.

PONTOS CRITICOS:
- Mudancas aqui afetam todas as views do catalogo.
"""

from catalog.views.catalog_base_views import *