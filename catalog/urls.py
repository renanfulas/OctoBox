"""
ARQUIVO: rotas das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- publica a casca HTTP do catalogo a partir do app catalog real.
"""

from django.urls import path

from .views.class_grid_views import ClassGridView
from .views.finance_views import FinanceCommunicationActionView, FinanceCenterView, FinanceReportExportView, MembershipPlanQuickUpdateView
from .views.student_views import (
    StudentDirectoryExportView,
    StudentDirectoryView,
    StudentEnrollmentActionView,
    StudentPaymentActionView,
    StudentQuickCreateView,
    StudentQuickUpdateView,
)

urlpatterns = [
    path('alunos/', StudentDirectoryView.as_view(), name='student-directory'),
    path('alunos/exportar/<str:report_format>/', StudentDirectoryExportView.as_view(), name='student-directory-export'),
    path('alunos/novo/', StudentQuickCreateView.as_view(), name='student-quick-create'),
    path('alunos/<int:student_id>/editar/', StudentQuickUpdateView.as_view(), name='student-quick-update'),
    path('alunos/<int:student_id>/financeiro/acao/', StudentPaymentActionView.as_view(), name='student-payment-action'),
    path('alunos/<int:student_id>/matricula/acao/', StudentEnrollmentActionView.as_view(), name='student-enrollment-action'),
    path('financeiro/', FinanceCenterView.as_view(), name='finance-center'),
    path('financeiro/exportar/<str:report_format>/', FinanceReportExportView.as_view(), name='finance-report-export'),
    path('financeiro/comunicacao/acao/', FinanceCommunicationActionView.as_view(), name='finance-communication-action'),
    path('financeiro/planos/<int:plan_id>/editar/', MembershipPlanQuickUpdateView.as_view(), name='membership-plan-quick-update'),
    path('grade-aulas/', ClassGridView.as_view(), name='class-grid'),
]
