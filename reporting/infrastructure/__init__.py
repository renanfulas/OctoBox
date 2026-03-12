"""
ARQUIVO: infraestrutura concreta de exportacao HTTP.

POR QUE ELE EXISTE:
- Isola CSV, PDF e HttpResponse concretos fora das views e do catalogo historico.

O QUE ESTE ARQUIVO FAZ:
1. Expoe a renderizacao concreta de payloads de relatorio.

PONTOS CRITICOS:
- Esta camada pode depender de Django HttpResponse e reportlab.
"""

from .http_exports import build_csv_response, build_pdf_response, build_report_response

__all__ = ['build_csv_response', 'build_pdf_response', 'build_report_response']