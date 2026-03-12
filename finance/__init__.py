"""
ARQUIVO: namespace tecnico do dominio financeiro fora do boxcore.

POR QUE ELE EXISTE:
- Marca a extracao progressiva dos workflows comerciais leves para fora da camada historica do catalogo.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace para application e infrastructure.
2. Permite evoluir o lado comercial sem depender do agregador legado.

PONTOS CRITICOS:
- Nesta fase este pacote ainda nao e um app Django; ele e uma fronteira tecnica.
"""