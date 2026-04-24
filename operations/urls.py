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
from .workout_action_views import (
    WorkoutApprovalActionView,
    WorkoutApprovalBatchActionView,
    WorkoutFollowUpActionView,
    WorkoutRmGapActionView,
    WorkoutOperationalMemoryCreateView,
    WorkoutWeeklyCheckpointUpdateView,
)
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
from .workout_editor_views import (
    CoachSessionWorkoutEditorView,
    WorkoutEditorHomeView,
    WorkoutPrescriptionPreviewView,
)
from .workout_board_views import (
    OperationsExecutiveSummaryView,
    WorkoutApprovalBoardView,
    WorkoutPublicationHistoryView,
    WorkoutSmartPasteView,
    WorkoutStudentRmQuickEditView,
)
from .workout_planner_views import (
    WorkoutPlannerApplyTrustedTemplateView,
    WorkoutPlannerDuplicatePreviousSlotView,
    WorkoutPlannerTemplatePickerTelemetryView,
    WorkoutPlannerView,
)
from .workout_template_views import (
    WorkoutApprovalPolicyUpdateView,
    WorkoutTemplateCreateBlockView,
    WorkoutTemplateCreateMovementView,
    WorkoutTemplateDeleteBlockView,
    WorkoutTemplateDeleteMovementView,
    WorkoutTemplateDeleteView,
    WorkoutTemplateDuplicateView,
    WorkoutTemplateManagementView,
    WorkoutTemplateMoveBlockView,
    WorkoutTemplateMoveMovementView,
    WorkoutTemplateToggleActiveView,
    WorkoutTemplateToggleFeaturedView,
    WorkoutTemplateUpdateBlockView,
    WorkoutTemplateUpdateMetadataView,
    WorkoutTemplateUpdateMovementView,
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
    path('operacao/wod/editor/', WorkoutEditorHomeView.as_view(), name='workout-editor-home'),
    path('operacao/wod/paste/', WorkoutSmartPasteView.as_view(), name='workout-smart-paste'),
    path('operacao/wod/planner/', WorkoutPlannerView.as_view(), name='workout-planner'),
    path('operacao/wod/planner/template-picker/telemetry/', WorkoutPlannerTemplatePickerTelemetryView.as_view(), name='workout-planner-template-picker-telemetry'),
    path(
        'operacao/wod/planner/celula/<int:session_id>/duplicar-slot-anterior/',
        WorkoutPlannerDuplicatePreviousSlotView.as_view(),
        name='workout-planner-duplicate-previous-slot',
    ),
    path(
        'operacao/wod/planner/celula/<int:session_id>/template-confiavel/<int:template_id>/',
        WorkoutPlannerApplyTrustedTemplateView.as_view(),
        name='workout-planner-apply-trusted-template',
    ),
    path('operacao/coach/aula/<int:session_id>/wod/', CoachSessionWorkoutEditorView.as_view(), name='coach-session-workout-editor'),
    path(
        'operacao/coach/aula/<int:session_id>/wod/prescription-preview/',
        WorkoutPrescriptionPreviewView.as_view(),
        name='workout-prescription-preview',
    ),
    path('operacao/wod/templates/', WorkoutTemplateManagementView.as_view(), name='workout-template-management'),
    path('operacao/wod/templates/policy/', WorkoutApprovalPolicyUpdateView.as_view(), name='workout-approval-policy-update'),
    path('operacao/wod/templates/<int:template_id>/duplicate/', WorkoutTemplateDuplicateView.as_view(), name='workout-template-duplicate'),
    path('operacao/wod/templates/<int:template_id>/delete/', WorkoutTemplateDeleteView.as_view(), name='workout-template-delete'),
    path('operacao/wod/templates/<int:template_id>/toggle/', WorkoutTemplateToggleActiveView.as_view(), name='workout-template-toggle-active'),
    path('operacao/wod/templates/<int:template_id>/featured/', WorkoutTemplateToggleFeaturedView.as_view(), name='workout-template-toggle-featured'),
    path('operacao/wod/templates/<int:template_id>/update/', WorkoutTemplateUpdateMetadataView.as_view(), name='workout-template-update-metadata'),
    path('operacao/wod/templates/<int:template_id>/blocks/create/', WorkoutTemplateCreateBlockView.as_view(), name='workout-template-create-block'),
    path('operacao/wod/templates/blocos/<int:block_id>/update/', WorkoutTemplateUpdateBlockView.as_view(), name='workout-template-update-block'),
    path('operacao/wod/templates/blocos/<int:block_id>/delete/', WorkoutTemplateDeleteBlockView.as_view(), name='workout-template-delete-block'),
    path('operacao/wod/templates/blocos/<int:block_id>/movements/create/', WorkoutTemplateCreateMovementView.as_view(), name='workout-template-create-movement'),
    path('operacao/wod/templates/movimentos/<int:movement_id>/update/', WorkoutTemplateUpdateMovementView.as_view(), name='workout-template-update-movement'),
    path('operacao/wod/templates/movimentos/<int:movement_id>/delete/', WorkoutTemplateDeleteMovementView.as_view(), name='workout-template-delete-movement'),
    path('operacao/wod/templates/blocos/<int:block_id>/<str:direction>/', WorkoutTemplateMoveBlockView.as_view(), name='workout-template-move-block'),
    path('operacao/wod/templates/movimentos/<int:movement_id>/<str:direction>/', WorkoutTemplateMoveMovementView.as_view(), name='workout-template-move-movement'),
    path('operacao/wod/aprovacoes/', WorkoutApprovalBoardView.as_view(), name='workout-approval-board'),
    path('operacao/wod/aprovacoes/lote/', WorkoutApprovalBatchActionView.as_view(), name='workout-approval-batch-action'),
    path('operacao/wod/historico/', WorkoutPublicationHistoryView.as_view(), name='workout-publication-history'),
    path('operacao/resumo-executivo/', OperationsExecutiveSummaryView.as_view(), name='operations-executive-summary'),
    path(
        'operacao/wod/<int:workout_id>/aluno/<int:student_id>/rm/<slug:exercise_slug>/',
        WorkoutStudentRmQuickEditView.as_view(),
        name='workout-student-rm-quick-edit',
    ),
    path('operacao/wod/aprovacoes/checkpoint-semanal/', WorkoutWeeklyCheckpointUpdateView.as_view(), name='workout-weekly-checkpoint-update'),
    path('operacao/wod/<int:workout_id>/follow-up/', WorkoutFollowUpActionView.as_view(), name='workout-follow-up-action'),
    path('operacao/wod/<int:workout_id>/rm-gap/', WorkoutRmGapActionView.as_view(), name='workout-rm-gap-action'),
    path('operacao/wod/<int:workout_id>/memory/', WorkoutOperationalMemoryCreateView.as_view(), name='workout-operational-memory-create'),
    path('operacao/wod/<int:workout_id>/<str:action>/', WorkoutApprovalActionView.as_view(), name='workout-approval-action'),
    path('operacao/whatsapp/', WhatsAppWorkspaceView.as_view(), name='whatsapp-workspace'),
    path('operacao/recepcao/pagamento/<int:payment_id>/acao/', ReceptionPaymentActionView.as_view(), name='reception-payment-action'),
    path('operacao/pagamento/<int:payment_id>/vincular-matricula/', PaymentEnrollmentLinkView.as_view(), name='payment-enrollment-link'),
    path('operacao/manager/intake/<int:intake_id>/abrir-contato/', ManagerIntakeContactView.as_view(), name='manager-intake-contact'),
    path('operacao/aluno/<int:student_id>/ocorrencia-tecnica/', TechnicalBehaviorNoteCreateView.as_view(), name='technical-behavior-note-create'),
    path('operacao/presenca/<int:attendance_id>/<str:action>/', AttendanceActionView.as_view(), name='attendance-action'),
]
