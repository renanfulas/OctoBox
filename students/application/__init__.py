"""
ARQUIVO: camada de aplicacao do dominio de alunos.

POR QUE ELE EXISTE:
- Concentra commands, results, ports e use cases sem depender de HTTP, template ou ORM concreto.

O QUE ESTE ARQUIVO FAZ:
1. Marca a fronteira de aplicacao do dominio.
2. Separa casos de uso da infraestrutura Django.

PONTOS CRITICOS:
- Nada aqui deve importar django.* diretamente.
"""
