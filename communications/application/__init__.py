"""
ARQUIVO: camada de aplicacao do dominio de communications.

POR QUE ELE EXISTE:
- Separa os fluxos de WhatsApp e toque operacional da infraestrutura Django concreta.

O QUE ESTE ARQUIVO FAZ:
1. Marca a fronteira de commands, results, ports e use cases.
2. Permite reaproveitar os mesmos fluxos por web, API e jobs futuros.

PONTOS CRITICOS:
- Nada aqui deve depender diretamente de django.*.
"""
