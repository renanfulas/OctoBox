"""
ARQUIVO: fachada do motor de intake do catálogo.

POR QUE ELE EXISTE:
- Mantém o contrato histórico de conversão de intake enquanto a superfície canônica vive em catalog.services.intakes.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta o helper público atual de intake.

PONTOS CRITICOS:
- Este arquivo não deve voltar a concentrar fallback, lock ou atualização comercial.
"""

from catalog.services.intakes import sync_student_intake


__all__ = ['sync_student_intake']
