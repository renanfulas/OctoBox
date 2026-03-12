"""
ARQUIVO: app Django real de acesso.

POR QUE ELE EXISTE:
- Separa login, papeis, permissoes e navegacao global do app institucional boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace do app access.
2. Define a fronteira real de autenticacao e papeis.

PONTOS CRITICOS:
- Regras de papel daqui afetam navegacao, permissoes e bootstrap de grupos.
"""
