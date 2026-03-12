"""
ARQUIVO: app Django real de integracoes externas.

POR QUE ELE EXISTE:
- Define uma fronteira propria para adaptadores de terceiros, webhooks e payloads externos.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace das integracoes.
2. Evita misturar servicos externos com o core transacional do produto.

PONTOS CRITICOS:
- Tudo aqui deve ter idempotencia, rastreabilidade e cuidado com payload bruto.
"""
