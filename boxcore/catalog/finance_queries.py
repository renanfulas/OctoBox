"""
ARQUIVO: fachada compatível das queries financeiras.

POR QUE ELE EXISTE:
- Mantem o ponto de import estavel enquanto o snapshot financeiro fica modularizado internamente.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o construtor principal do snapshot financeiro.

PONTOS CRITICOS:
- Views, relatorios e testes ainda dependem desta API publica.
"""

from .finance_snapshot import build_finance_snapshot


__all__ = ['build_finance_snapshot']