"""
ARQUIVO: fachada legada das bases abstratas de models dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto as bases compartilhadas passam a viver em um modulo neutro.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a base abstrata de timestamps.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real de bases compartilhadas.
"""

from model_support.base import TimeStampedModel


__all__ = ['TimeStampedModel']