"""
ARQUIVO: rotas das áreas operacionais por papel.

POR QUE ELE EXISTE:
- Mantém a navegação de Owner, DEV, Manager e Coach em um módulo próprio.

O QUE ESTE ARQUIVO FAZ:
1. Redireciona o usuário para sua área principal.
2. Publica telas operacionais específicas por papel.
3. Expõe ações exclusivas de manager e coach.
4. Mantém uma rota técnica separada para DEV.

PONTOS CRITICOS:
- Mudanças aqui afetam o fluxo operacional por papel.
- As rotas precisam continuar alinhadas com as restrições declaradas nas views.
"""

from django.urls import path

from .action_views import AttendanceActionView, PaymentEnrollmentLinkView, TechnicalBehaviorNoteCreateView
from .base_views import RoleOperationRedirectView
from .workspace_views import CoachWorkspaceView, DevWorkspaceView, ManagerWorkspaceView, OwnerWorkspaceView

urlpatterns = [
    path('operacao/', RoleOperationRedirectView.as_view(), name='role-operations'),
    path('operacao/owner/', OwnerWorkspaceView.as_view(), name='owner-workspace'),
    path('operacao/dev/', DevWorkspaceView.as_view(), name='dev-workspace'),
    path('operacao/manager/', ManagerWorkspaceView.as_view(), name='manager-workspace'),
    path('operacao/coach/', CoachWorkspaceView.as_view(), name='coach-workspace'),
    path('operacao/pagamento/<int:payment_id>/vincular-matricula/', PaymentEnrollmentLinkView.as_view(), name='payment-enrollment-link'),
    path('operacao/aluno/<int:student_id>/ocorrencia-tecnica/', TechnicalBehaviorNoteCreateView.as_view(), name='technical-behavior-note-create'),
    path('operacao/presenca/<int:attendance_id>/<str:action>/', AttendanceActionView.as_view(), name='attendance-action'),
]