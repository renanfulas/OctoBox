"""
ARQUIVO: fachada legada dos contratos de jobs dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto os contratos reais vivem em jobs.base.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os contratos reais de jobs.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from jobs.base import BaseJob, JobResult

__all__ = ['BaseJob', 'JobResult']