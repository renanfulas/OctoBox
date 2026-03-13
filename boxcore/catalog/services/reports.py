"""
ARQUIVO: fachada legada da exportacao HTTP do catalogo.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a superficie canonica vive em catalog.services.reports.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a entrada publica atual de exportacao.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real de exportacao.
"""

from catalog.services.reports import build_csv_response, build_pdf_response, build_report_response

__all__ = ['build_csv_response', 'build_pdf_response', 'build_report_response']