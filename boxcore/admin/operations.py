"""
ARQUIVO: fachada legada do admin operacional dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a configuracao real vive em operations.admin.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as classes reais do admin operacional.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar registros novos do admin.
"""

from operations.admin import AttendanceAdmin, BehaviorNoteAdmin, ClassSessionAdmin, LeadImportJobAdmin


__all__ = ['AttendanceAdmin', 'BehaviorNoteAdmin', 'ClassSessionAdmin', 'LeadImportJobAdmin']
