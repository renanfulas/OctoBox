"""
ARQUIVO: policy operacional da grade de aulas.

POR QUE ELE EXISTE:
- concentra as regras de editabilidade e exclusao de aulas para evitar logica espalhada entre form, view e service.

O QUE ESTE ARQUIVO FAZ:
1. monta a policy aplicavel a uma aula.
2. define quais status a edicao rapida pode usar.
3. valida cenarios de reabertura e exclusao com historico vinculado.

PONTOS CRITICOS:
- essa policy governa mutacoes da agenda real e precisa refletir a regra operacional correta.
"""

from operations.application.class_grid_policy import *