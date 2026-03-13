"""
ARQUIVO: fachada publica das leituras da grade do catalogo.

POR QUE ELE EXISTE:
- Reexporta a leitura da grade pelo app real catalog durante a transicao.
"""

from boxcore.catalog.class_grid_queries import build_class_grid_snapshot

__all__ = ['build_class_grid_snapshot']