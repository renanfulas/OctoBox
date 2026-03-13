"""
ARQUIVO: base das views operacionais por papel.

POR QUE ELE EXISTE:
- Centraliza redirecionamento por papel e contexto base compartilhado das areas operacionais.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona o usuario para sua area principal de operacao.
2. Entrega contexto base compartilhado entre Owner, DEV, Manager e Coach.

PONTOS CRITICOS:
- Mudancas aqui afetam todas as rotas operacionais por papel.
"""

from operations.base_views import *