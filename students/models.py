"""
ARQUIVO: superficie estavel de modelos do dominio de alunos.

POR QUE ELE EXISTE:
- reduz imports diretos de boxcore.models ao expor o contrato de modelos do dominio students.

O QUE ESTE ARQUIVO FAZ:
1. reexporta o modelo principal de aluno.
2. reexporta enums e tipos diretamente ligados ao aluno.

PONTOS CRITICOS:
- o ownership de codigo do cadastro de alunos ja saiu de boxcore, mas o estado historico do app ainda permanece nesta fase.
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
