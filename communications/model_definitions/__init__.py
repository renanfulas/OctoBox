"""
ARQUIVO: namespace das definicoes reais de models do app communications.

POR QUE ELE EXISTE:
- Permite mover a implementacao real dos models para fora de boxcore sem trocar ainda o estado historico do Django.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o pacote de definicoes de models do dominio.
2. Prepara a separacao entre ownership de codigo e app label historico.

PONTOS CRITICOS:
- Nesta fase os models ainda pertencem logicamente ao app label boxcore.
"""
