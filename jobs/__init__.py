"""
ARQUIVO: app Django real de jobs assincronos.

POR QUE ELE EXISTE:
- Separa a fronteira de jobs do namespace institucional boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace do app jobs.
2. Mantem automacoes futuras em fronteira propria.

PONTOS CRITICOS:
- Jobs devem continuar desacoplados do fluxo HTTP.
"""
