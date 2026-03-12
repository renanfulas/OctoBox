"""
ARQUIVO: fachada legada do namespace de auditoria dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem compatibilidade temporaria enquanto o app real vive em auditing.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a funcao principal de auditoria.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from auditing import log_audit_event

__all__ = ['log_audit_event']