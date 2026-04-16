"""
ARQUIVO: testes da facade publica de exportacao HTTP do namespace reporting.

POR QUE ELE EXISTE:
- protege a nova porta oficial de exportacao de relatorios.
- evita regressao para imports diretos de `reporting.infrastructure` nas cascas HTTP.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from reporting.facade import run_report_response_build


class ReportingFacadeTests(SimpleTestCase):
    @patch('reporting.facade.http_exports.build_report_response')
    def test_run_report_response_build_delegates_to_infrastructure(self, build_report_response_mock):
        payload = {'format': 'csv', 'filename': 'relatorio.csv', 'headers': [], 'rows': []}
        sentinel_response = object()
        build_report_response_mock.return_value = sentinel_response

        result = run_report_response_build(payload)

        self.assertIs(result, sentinel_response)
        build_report_response_mock.assert_called_once_with(payload)
