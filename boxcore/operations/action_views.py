"""
ARQUIVO: views de acoes operacionais por papel.

POR QUE ELE EXISTE:
- Isola a camada HTTP das acoes que alteram estado real em operations.

O QUE ESTE ARQUIVO FAZ:
1. Orquestra vinculo financeiro do manager.
2. Orquestra ocorrencia tecnica e presenca do coach.
3. Mantem os redirects de retorno ao workspace de origem.

PONTOS CRITICOS:
- Essas rotas disparam mutacoes reais e precisam manter permissoes e side effects intactos.
"""

from operations.action_views import *