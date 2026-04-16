"""
ARQUIVO: facade publica das exportacoes HTTP do namespace reporting.

POR QUE ELE EXISTE:
- oferece uma porta oficial pequena para cascas HTTP que precisam transformar payloads de relatorio em resposta baixavel.
- evita que views consumam `reporting.infrastructure` diretamente.

O QUE ESTE ARQUIVO FAZ:
1. expoe a construcao de resposta final de relatorio.
2. preserva a implementacao concreta em infrastructure.
"""

from django.http import HttpResponse

from reporting.infrastructure.http_exports import (
    build_csv_response,
    build_pdf_response,
    build_report_response,
)


def run_report_response_build(report_payload: dict) -> HttpResponse:
    return build_report_response(report_payload)


__all__ = [
    'build_csv_response',
    'build_pdf_response',
    'run_report_response_build',
]
