"""
ARQUIVO: indice da camada hibrida do snapshot financeiro.

POR QUE ELE EXISTE:
- agrupa pontes de apresentacao entre leitura tradicional e assistida.
"""

from .flow_bridge import build_finance_flow_bridge

__all__ = ['build_finance_flow_bridge']
