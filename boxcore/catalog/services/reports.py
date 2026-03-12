"""
ARQUIVO: fachada legada da exportacao HTTP do catalogo.

POR QUE ELE EXISTE:
- Mantem imports antigos funcionando enquanto a serializacao real vive em reporting.infrastructure.http_exports.

O QUE ESTE ARQUIVO FAZ:
1. Reexporta a renderizacao concreta de CSV/PDF.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar implementacao real de exportacao.
"""

from reporting.infrastructure import build_csv_response, build_pdf_response, build_report_response

__all__ = ['build_csv_response', 'build_pdf_response', 'build_report_response']