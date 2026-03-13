"""
ARQUIVO: pacote de suporte transversal para models.

POR QUE ELE EXISTE:
- Hospeda bases abstratas e utilitarios neutros que podem ser reutilizados por dominios reais sem depender diretamente do namespace historico boxcore.models.

O QUE ESTE ARQUIVO FAZ:
1. Marca um ponto neutro para compartilhamento de estrutura de models.

PONTOS CRITICOS:
- Este pacote nao deve virar agregador generico de models concretos.
"""
