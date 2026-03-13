"""
ARQUIVO: superficie estavel de modelos de auditoria.

POR QUE ELE EXISTE:
- reduz imports diretos de boxcore.models nas camadas que consomem auditoria.

O QUE ESTE ARQUIVO FAZ:
1. reexporta o modelo AuditEvent.

PONTOS CRITICOS:
- o ownership de codigo do model ja saiu de boxcore, mas o estado historico do app ainda permanece nesta fase.
"""

from auditing.model_definitions import AuditEvent

__all__ = ['AuditEvent']