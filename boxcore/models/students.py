"""
ARQUIVO: fachada legada dos models de students dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem o estado historico do Django em boxcore enquanto a implementacao real do cadastro de alunos vive em students.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta enums e model reais de students.
2. Preserva imports antigos durante a transicao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real dos models.
- O app label continua sendo boxcore nesta etapa para evitar mudanca de schema e de migrations.
"""

from students.model_definitions import (
    HealthIssueStatus,
    SourceConfidence,
    SourceResolutionMethod,
    Student,
    StudentSourceDeclaration,
    StudentGender,
    StudentStatus,
)


__all__ = [
    'HealthIssueStatus',
    'SourceConfidence',
    'SourceResolutionMethod',
    'Student',
    'StudentSourceDeclaration',
    'StudentGender',
    'StudentStatus',
]
