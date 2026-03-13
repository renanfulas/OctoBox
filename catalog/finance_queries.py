"""
ARQUIVO: fachada publica das leituras financeiras do catalogo.

POR QUE ELE EXISTE:
- Evita que as views do app catalog dependam diretamente do namespace historico boxcore.catalog.
"""

from boxcore.catalog.finance_queries import build_finance_snapshot

__all__ = ['build_finance_snapshot']