"""
ARQUIVO: utilitarios neutros compartilhados fora de namespaces historicos.

POR QUE ELE EXISTE:
- Hospeda helpers reutilizaveis que nao precisam permanecer presos a boxcore.

O QUE ESTE ARQUIVO FAZ:
1. Reserva um namespace neutro para suporte compartilhado.

PONTOS CRITICOS:
- So devem entrar aqui utilitarios sem impacto de schema, app label ou estado do Django.
"""
