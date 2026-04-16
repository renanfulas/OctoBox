"""
ARQUIVO: rotas do guia interno do sistema.

POR QUE ELE EXISTE:
- separa as paginas pedagogicas e de apoio tecnico do restante da aplicacao no app real guide.

O QUE ESTE ARQUIVO FAZ:
1. publica a pagina Mapa do Sistema.

PONTOS CRITICOS:
- mudanca no nome da rota impacta links do menu e testes.
"""

from django.urls import path

from student_identity.staff_views import StudentInvitationOperationsView
from .views import OperationalSettingsView, SystemMapView, OperationalSettingsAutoImportApiView

urlpatterns = [
    path('mapa-sistema/', SystemMapView.as_view(), name='system-map'),
    path('configuracoes-operacionais/', OperationalSettingsView.as_view(), name='operational-settings'),
    path(
        'configuracoes-operacionais/aluno/convites/',
        StudentInvitationOperationsView.as_view(),
        name='student-invitation-operations',
    ),
    path('configuracoes-operacionais/api/importar/', OperationalSettingsAutoImportApiView.as_view(), name='operational-settings-api-import'),
]
