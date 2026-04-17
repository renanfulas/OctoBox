"""
ARQUIVO: fachada legada dos models de operations dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem o estado historico do Django em boxcore enquanto a implementacao real da operacao diaria vive em operations.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta enums e models reais de operations.
2. Preserva imports antigos durante a transicao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real dos models.
- O app label continua sendo boxcore nesta etapa para evitar mudanca de schema e de migrations.
"""

from operations.model_definitions import (
    Attendance,
    AttendanceStatus,
    BehaviorCategory,
    BehaviorNote,
    ClassSession,
    LeadImportDeclaredRange,
    LeadImportJob,
    LeadImportJobStatus,
    LeadImportProcessingMode,
    LeadImportSourceType,
    SessionStatus,
)


__all__ = [
    'Attendance',
    'AttendanceStatus',
    'BehaviorCategory',
    'BehaviorNote',
    'ClassSession',
    'LeadImportDeclaredRange',
    'LeadImportJob',
    'LeadImportJobStatus',
    'LeadImportProcessingMode',
    'LeadImportSourceType',
    'SessionStatus',
]
