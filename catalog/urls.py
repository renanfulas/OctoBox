"""
ARQUIVO: rotas das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP do catalogo a partir do app catalog real.
"""

from django.urls import path

from .views.class_grid_views import ClassGridView
from .views.finance_views import FinanceCommunicationActionView, FinanceCenterView, FinanceReportExportView, MembershipPlanQuickUpdateView
from .views.student_views import (
    StudentBulkActionView,
    StudentDirectoryExportView,
    StudentImportView,
    StudentImportProgressView,
    StudentDirectoryView,
    StudentDrawerFragmentsView,
    StudentDrawerProfileSaveView,
    StudentEditSessionReleaseView,
    StudentEventStreamView,
    StudentReadSnapshotView,
    StudentEditSessionStartView,
    StudentEnrollmentActionView,
    StudentLockHeartbeatView,
    StudentLockStatusView,
    StudentPaymentActionView,
    StudentPaymentDrawerView,
    StudentQuickCreateView,
    StudentExpressCreateView,
    StudentQuickUpdateView,
    StudentSourceCaptureView,
)

from finance.views.stripe_checkout import StripeCheckoutRedirectView, StripeCheckoutSuccessView, StripeCheckoutCancelView
from finance.views.stripe_webhooks import stripe_webhook_receiver

urlpatterns = [
    path('alunos/', StudentDirectoryView.as_view(), name='student-directory'),
    path('alunos/lote/', StudentBulkActionView.as_view(), name='student-bulk-action'),
    path('alunos/importar/', StudentImportView.as_view(), name='student-import'),
    path('alunos/importar/progresso/<str:job_id>/', StudentImportProgressView.as_view(), name='student-import-progress'),
    path('alunos/exportar/<str:report_format>/', StudentDirectoryExportView.as_view(), name='student-directory-export'),
    path('alunos/novo/', StudentQuickCreateView.as_view(), name='student-quick-create'),
    path('alunos/balcao/', StudentExpressCreateView.as_view(), name='student-express-create'),
    path('alunos/origem/qualificar/', StudentSourceCaptureView.as_view(), name='student-source-capture'),
    path('alunos/<int:student_id>/editar/', StudentQuickUpdateView.as_view(), name='student-quick-update'),
    path('alunos/<int:student_id>/snapshot/', StudentReadSnapshotView.as_view(), name='student-read-snapshot'),
    path('alunos/<int:student_id>/events/stream/', StudentEventStreamView.as_view(), name='student-event-stream'),
    path('alunos/<int:student_id>/drawer/fragments/', StudentDrawerFragmentsView.as_view(), name='student-drawer-fragments'),
    path('alunos/<int:student_id>/drawer/profile/', StudentDrawerProfileSaveView.as_view(), name='student-drawer-profile-save'),
    path('alunos/<int:student_id>/editar/sessao/iniciar/', StudentEditSessionStartView.as_view(), name='student-edit-session-start'),
    path('alunos/<int:student_id>/editar/sessao/liberar/', StudentEditSessionReleaseView.as_view(), name='student-edit-session-release'),
    path('alunos/<int:student_id>/editar/lock/heartbeat/', StudentLockHeartbeatView.as_view(), name='student-lock-heartbeat'),
    path('alunos/<int:student_id>/editar/lock/status/', StudentLockStatusView.as_view(), name='student-lock-status'),
    path('alunos/<int:student_id>/financeiro/acao/', StudentPaymentActionView.as_view(), name='student-payment-action'),
    path('alunos/<int:student_id>/financeiro/cobranca/<int:payment_id>/drawer/', StudentPaymentDrawerView.as_view(), name='student-payment-drawer'),
    path('alunos/<int:student_id>/matricula/acao/', StudentEnrollmentActionView.as_view(), name='student-enrollment-action'),
    path('financeiro/', FinanceCenterView.as_view(), name='finance-center'),
    path('financeiro/exportar/<str:report_format>/', FinanceReportExportView.as_view(), name='finance-report-export'),
    path('financeiro/comunicacao/acao/', FinanceCommunicationActionView.as_view(), name='finance-communication-action'),
    path('financeiro/planos/<int:plan_id>/editar/', MembershipPlanQuickUpdateView.as_view(), name='membership-plan-quick-update'),
    path('financeiro/stripe/checkout/<int:payment_id>/', StripeCheckoutRedirectView.as_view(), name='finance-checkout-redirect'),
    path('financeiro/stripe/checkout/sucesso/<int:payment_id>/', StripeCheckoutSuccessView.as_view(), name='checkout_success'),
    path('financeiro/stripe/checkout/cancelado/<int:payment_id>/', StripeCheckoutCancelView.as_view(), name='checkout_cancel'),
    path('financeiro/stripe/webhook/', stripe_webhook_receiver, name='stripe-webhook'),
    path('grade-aulas/', ClassGridView.as_view(), name='class-grid'),
]
