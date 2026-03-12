"""
ARQUIVO: fachada legada da API dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem compatibilidade temporaria enquanto o app real de API passa a viver no namespace api.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace legado durante a transicao.
2. Indica que o modulo real agora mora fora de boxcore.

PONTOS CRITICOS:
- Nao adicionar codigo novo aqui; a fonte real agora e o app api.
"""