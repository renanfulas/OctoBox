"""
ARQUIVO: fachada publica das leituras financeiras do catalogo.

POR QUE ELE EXISTE:
- concentra a entrada canonica do snapshot financeiro no app real catalog.
"""

from .finance_snapshot import build_finance_snapshot

__all__ = ['build_finance_snapshot']