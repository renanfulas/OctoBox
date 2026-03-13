"""
ARQUIVO: queries de alunos do catalogo.

POR QUE ELE EXISTE:
- Mantem imports historicos funcionando enquanto a superficie canonica vive em catalog.student_queries.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta as leituras publicas atuais da area de alunos.

PONTOS CRITICOS:
- Mudancas aqui devem permanecer apenas de compatibilidade.
"""

from catalog.student_queries import build_student_directory_snapshot, build_student_financial_snapshot


__all__ = ['build_student_directory_snapshot', 'build_student_financial_snapshot']