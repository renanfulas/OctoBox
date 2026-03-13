"""
ARQUIVO: fachada legada do admin de alunos dentro de boxcore.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a configuracao real vive em students.admin.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a classe real do admin de alunos.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar comportamento novo.
"""

from students.admin import StudentAdmin


__all__ = ['StudentAdmin']