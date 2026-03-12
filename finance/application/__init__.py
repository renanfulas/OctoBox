"""
ARQUIVO: camada de aplicacao do dominio financeiro leve.

POR QUE ELE EXISTE:
- Separa commands, ports e use cases dos workflows comerciais pequenos sem depender de FormView ou ORM concreto.

O QUE ESTE ARQUIVO FAZ:
1. Marca a fronteira de aplicacao financeira.
2. Prepara o dominio para reaproveitamento fora da view atual.

PONTOS CRITICOS:
- Nada aqui deve importar django.* diretamente.
"""