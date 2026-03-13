"""
ARQUIVO: namespace tecnico do dominio de alunos fora do boxcore.

POR QUE ELE EXISTE:
- Marca o inicio da extracao do fluxo principal de aluno para fora da camada diretamente acoplada ao Django.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace para application, infrastructure e superficie de models.
2. Permite evoluir o dominio de alunos sem depender do app label final ainda.

PONTOS CRITICOS:
- Nesta fase ele ja pode ser registrado como app leve, mas ainda nao carrega o estado historico dos models.
"""
