"""
ARQUIVO: app Django real de communications.

POR QUE ELE EXISTE:
- Separa a conversa operacional, identidade de canal e leituras de comunicacao do app institucional boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace do dominio communications.
2. Define a fronteira real para services e queries de contato e mensagem.

PONTOS CRITICOS:
- Nesta fase o app ainda usa modelos historicos de boxcore por compatibilidade.
"""
