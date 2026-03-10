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
from .test_catalog import CatalogViewTests
from .test_dashboard import DashboardViewTests
from .test_finance import FinanceCenterTests
from .test_guide import GuideViewTests
from .test_import_students import ImportStudentsCsvCommandTests
from .test_operations import OperationWorkspaceTests

__all__ = [
    'AuditTrailTests',
    'AccessViewTests',
    'BootstrapRolesCommandTests',
    'CatalogViewTests',
    'DashboardViewTests',
    'FinanceCenterTests',
    'GuideViewTests',
    'ImportStudentsCsvCommandTests',
    'OperationWorkspaceTests',
]