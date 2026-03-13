"""
ARQUIVO: queries da grade de aulas do catalogo.

POR QUE ELE EXISTE:
- Mantem imports historicos funcionando enquanto a superficie canonica vive em catalog.class_grid_queries.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a leitura publica atual da grade.

PONTOS CRITICOS:
- mudancas aqui devem permanecer apenas de compatibilidade.
"""

from django.utils import timezone

from catalog.class_grid_queries import build_class_grid_snapshot


__all__ = ['build_class_grid_snapshot']