"""
ARQUIVO: fachada compatível das queries financeiras.

POR QUE ELE EXISTE:
- Mantem o ponto de import estavel enquanto a superficie canonica vive em catalog.finance_queries.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o construtor publico atual do snapshot financeiro.

PONTOS CRITICOS:
- Views, relatorios e testes ainda dependem desta API publica.
"""

from catalog.finance_queries import build_finance_snapshot


__all__ = ['build_finance_snapshot']