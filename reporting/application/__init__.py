"""
ARQUIVO: camada pura de montagem de payloads de relatorio.

POR QUE ELE EXISTE:
- Mantem a formatacao dos relatorios fora das views e da serializacao HTTP concreta.

O QUE ESTE ARQUIVO FAZ:
1. Marca a fronteira de builders puros de relatorio.
2. Prepara reaproveitamento por web, jobs e futuras integrações.

PONTOS CRITICOS:
- Nada aqui deve depender de HttpResponse ou reportlab diretamente.
"""