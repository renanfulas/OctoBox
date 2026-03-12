"""
ARQUIVO: fachada legada dos servicos de auditoria dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a implementacao real vive em auditing.services.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os servicos reais de auditoria.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from auditing.services import log_audit_event

__all__ = ['log_audit_event']