"""
ARQUIVO: queries dos snapshots de workspace operacional por papel.

POR QUE ELE EXISTE:
- Centraliza leituras e snapshots usados pelas areas de Owner, DEV, Manager e Coach.

O QUE ESTE ARQUIVO FAZ:
1. Monta snapshots executivos, tecnicos, gerenciais e de aula.
2. Reaproveita consultas pesadas fora da camada HTTP.
3. Mantem as views operacionais focadas em permissao, request e resposta.

PONTOS CRITICOS:
- Mudancas aqui afetam a leitura operacional por papel e podem degradar performance se mal feitas.
"""

from operations.queries import *