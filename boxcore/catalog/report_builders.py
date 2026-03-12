"""
ARQUIVO: fachada legada dos builders de exportacao do catalogo.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a montagem real dos payloads vive em reporting.application.catalog_reports.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta os builders puros de relatorio do catalogo.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar montagem real de exportacao.
"""

from reporting.application.catalog_reports import build_finance_report, build_student_directory_report

__all__ = ['build_finance_report', 'build_student_directory_report']