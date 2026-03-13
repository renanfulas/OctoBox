"""
ARQUIVO: fachada legada do model de auditoria dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem o estado historico do Django em boxcore enquanto a implementacao real de auditoria vive em auditing.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o model real de auditoria.
2. Preserva imports antigos durante a transicao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real do model.
- O app label continua sendo boxcore nesta etapa para evitar mudanca de schema e de migrations.
"""

from auditing.model_definitions import AuditEvent


__all__ = ['AuditEvent']