"""
ARQUIVO: namespace tecnico do dominio de alunos fora do boxcore.

POR QUE ELE EXISTE:
- Marca o inicio da extracao do fluxo principal de aluno para fora da camada diretamente acoplada ao Django.

O QUE ESTE ARQUIVO FAZ:
1. Reserva o namespace para application e infrastructure.
2. Permite evoluir o dominio de alunos sem depender do app label final ainda.

PONTOS CRITICOS:
- Nesta fase este pacote nao e um app Django; ele e uma fronteira tecnica de dominio e aplicacao.
"""
