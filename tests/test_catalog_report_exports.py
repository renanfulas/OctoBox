"""
ARQUIVO: testes de blindagem das exportacoes do catalogo.

POR QUE ELE EXISTE:
- protege que as views de exportacao usem a facade publica de reporting.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from catalog.views.finance_views import FinanceReportExportView
from catalog.views.student_views import StudentDirectoryExportView


class CatalogReportExportsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(id=7)

    @patch('catalog.views.finance_views.run_report_response_build')
    @patch('catalog.views.finance_views.build_finance_report')
    @patch('catalog.views.finance_views.build_finance_snapshot')
    @patch('catalog.views.finance_views.check_export_quota')
    def test_finance_report_export_view_uses_reporting_facade(
        self,
        check_export_quota_mock,
        build_finance_snapshot_mock,
        build_finance_report_mock,
        run_report_response_build_mock,
    ):
        request = self.factory.get('/catalogo/financeiro/export/csv/')
        request.user = self.user
        check_export_quota_mock.return_value = (True, 0)
        build_finance_snapshot_mock.return_value = {'payments': [], 'plans': [], 'enrollments': []}
        build_finance_report_mock.return_value = {'format': 'csv', 'filename': 'finance.csv', 'headers': [], 'rows': []}
        response = HttpResponse('finance')
        run_report_response_build_mock.return_value = response

        result = FinanceReportExportView().get(request, report_format='csv')

        self.assertIs(result, response)
        run_report_response_build_mock.assert_called_once_with(build_finance_report_mock.return_value)

    @patch('catalog.views.student_views.run_report_response_build')
    @patch('catalog.views.student_views.build_student_directory_report')
    @patch('catalog.views.student_views.build_student_directory_snapshot')
    @patch('catalog.views.student_views.check_export_quota')
    def test_student_directory_export_view_uses_reporting_facade(
        self,
        check_export_quota_mock,
        build_student_directory_snapshot_mock,
        build_student_directory_report_mock,
        run_report_response_build_mock,
    ):
        request = self.factory.get('/catalogo/alunos/export/csv/')
        request.user = self.user
        check_export_quota_mock.return_value = (True, 0)
        build_student_directory_snapshot_mock.return_value = {'students': []}
        build_student_directory_report_mock.return_value = {'format': 'csv', 'filename': 'students.csv', 'headers': [], 'rows': []}
        response = HttpResponse('students')
        run_report_response_build_mock.return_value = response

        result = StudentDirectoryExportView().get(request, report_format='csv')

        self.assertIs(result, response)
        run_report_response_build_mock.assert_called_once_with(build_student_directory_report_mock.return_value)
