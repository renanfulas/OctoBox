"""
ARQUIVO: agregador dos testes do boxcore.

POR QUE ELE EXISTE:
- Garante descoberta simples dos testes pelo Django.

O QUE ESTE ARQUIVO FAZ:
1. Reúne testes de acesso, auditoria, catálogo, dashboard, guia, importação e operação por papel.

PONTOS CRITICOS:
- Se faltar import aqui, parte dos testes pode deixar de rodar no comando padrão.
"""

from .test_audit import AuditTrailTests
from .test_access import AccessViewTests, BootstrapRolesCommandTests
from .test_api import ApiFoundationTests
from .test_catalog import CatalogViewTests
from .test_dashboard import DashboardViewTests
from .test_finance import FinanceCenterTests
from .test_guide import GuideViewTests
from .test_import_students import ImportStudentsCsvCommandTests
from .test_integrations import WhatsAppIntegrationFoundationTests
from .test_operations import OperationWorkspaceTests
from .test_page_payloads import PageHeroContractTests, PagePayloadBridgeContractTests
from .test_settings import SettingsHelperTests
from .test_shell_hints import ShellHintBuilderUnitTests, ShellHintIntegrationTests

__all__ = [
    'AuditTrailTests',
    'AccessViewTests',
    'ApiFoundationTests',
    'BootstrapRolesCommandTests',
    'CatalogViewTests',
    'DashboardViewTests',
    'FinanceCenterTests',
    'GuideViewTests',
    'ImportStudentsCsvCommandTests',
    'WhatsAppIntegrationFoundationTests',
    'OperationWorkspaceTests',
    'PageHeroContractTests',
    'PagePayloadBridgeContractTests',
    'SettingsHelperTests',
    'ShellHintBuilderUnitTests',
    'ShellHintIntegrationTests',
]