"""
ARQUIVO: fachada publica das leituras de alunos do catalogo.

POR QUE ELE EXISTE:
- Mantem a casca HTTP do app catalog importando leituras pelo proprio dominio em vez de entrar por boxcore.catalog.
"""

from boxcore.catalog.student_queries import build_student_directory_snapshot, build_student_financial_snapshot

__all__ = ['build_student_directory_snapshot', 'build_student_financial_snapshot']