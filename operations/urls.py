"""
ARQUIVO: rotas das areas operacionais por papel.

POR QUE ELE EXISTE:
- publica a casca HTTP operacional a partir do app operations real.

O QUE ESTE ARQUIVO FAZ:
1. redireciona o usuario para sua area principal.
2. publica telas operacionais por papel.
3. expõe acoes exclusivas de manager e coach.

PONTOS CRITICOS:
- mudancas aqui afetam o fluxo operacional por papel.
"""

from django.urls import path

from .action_views import (
    AttendanceActionView,
    ManagerIntakeContactView,
    PaymentEnrollmentLinkView,
    ReceptionPaymentActionView,
    TechnicalBehaviorNoteCreateView,
)
from .base_views import RoleOperationRedirectView
from .workspace_views import (
    CoachWorkspaceView,
    DevWorkspaceView,
    ManagerBoardsPartialView,
    ManagerEventStreamView,
    ManagerWorkspaceView,
    OperationEventStreamView,
    OwnerWorkspacePartialView,
    OwnerWorkspaceView,
    ReceptionPaymentBoardPartialView,
    ReceptionWorkspaceView,
    WhatsAppWorkspaceView,
)

from .reports_views import ReportHubView

urlpatterns = [
    path('operacao/', RoleOperationRedirectView.as_view(), name='role-operations'),
    path('operacao/relatorios/', ReportHubView.as_view(), name='reports-hub'),
    path('operacao/owner/', OwnerWorkspaceView.as_view(), name='owner-workspace'),
    path('operacao/owner/fragmentos/workspace/', OwnerWorkspacePartialView.as_view(), name='owner-workspace-fragment'),
    path('operacao/dev/', DevWorkspaceView.as_view(), name='dev-workspace'),
    path('operacao/manager/', ManagerWorkspaceView.as_view(), name='manager-workspace'),
    path('operacao/manager/fragmentos/boards/', ManagerBoardsPartialView.as_view(), name='manager-boards-fragment'),
    path('operacao/manager/events/stream/', ManagerEventStreamView.as_view(), name='manager-event-stream'),
    path('operacao/eventos/stream/', OperationEventStreamView.as_view(), name='operation-event-stream'),
    path('operacao/recepcao/', ReceptionWorkspaceView.as_view(), name='reception-workspace'),
    path('operacao/recepcao/fragmentos/pagamentos/', ReceptionPaymentBoardPartialView.as_view(), name='reception-payment-board-fragment'),
    path('operacao/coach/', CoachWorkspaceView.as_view(), name='coach-workspace'),
    path('operacao/whatsapp/', WhatsAppWorkspaceView.as_view(), name='whatsapp-workspace'),
    path('operacao/recepcao/pagamento/<int:payment_id>/acao/', ReceptionPaymentActionView.as_view(), name='reception-payment-action'),
    path('operacao/pagamento/<int:payment_id>/vincular-matricula/', PaymentEnrollmentLinkView.as_view(), name='payment-enrollment-link'),
    path('operacao/manager/intake/<int:intake_id>/abrir-contato/', ManagerIntakeContactView.as_view(), name='manager-intake-contact'),
    path('operacao/aluno/<int:student_id>/ocorrencia-tecnica/', TechnicalBehaviorNoteCreateView.as_view(), name='technical-behavior-note-create'),
    path('operacao/presenca/<int:attendance_id>/<str:action>/', AttendanceActionView.as_view(), name='attendance-action'),
]
