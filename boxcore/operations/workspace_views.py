"""
ARQUIVO: views de workspace operacional por papel.

POR QUE ELE EXISTE:
- Separa a camada HTTP das areas de Owner, DEV, Manager e Coach.

O QUE ESTE ARQUIVO FAZ:
1. Renderiza as areas operacionais por papel com snapshots prontos.
2. Mantem as views focadas em permissao, contexto e template.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta a experiencia operacional por papel.
"""

from operations.workspace_views import *