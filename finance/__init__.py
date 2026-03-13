"""
ARQUIVO: namespace tecnico do dominio financeiro fora do boxcore.

POR QUE ELE EXISTE:
- Marca a extracao progressiva dos workflows comerciais leves para fora da camada historica do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace para application, infrastructure e superficie de models.
2. Permite evoluir o lado comercial sem depender do agregador legado.

PONTOS CRITICOS:
- Nesta fase ele ja pode ser registrado como app leve, mas ainda nao carrega o estado historico dos models.
"""