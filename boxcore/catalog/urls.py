"""
ARQUIVO: rotas das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- Organiza as entradas das telas leves de alunos, financeiro e grade fora do admin.

O QUE ESTE ARQUIVO FAZ:
1. Publica a pagina de alunos e o fluxo leve de cadastro/edicao.
2. Publica as acoes diretas de pagamento e matricula por aluno.
3. Publica a central visual de financeiro e a edicao leve de planos.
4. Publica a grade visual de aulas.

PONTOS CRITICOS:
- Estas rotas sustentam a navegacao principal de operacao diaria e precisam continuar estaveis.
"""

from django.urls import path

from .views import (
    ClassGridView,
    FinanceCenterView,
    MembershipPlanQuickUpdateView,
    StudentEnrollmentActionView,
    StudentDirectoryView,
    StudentPaymentActionView,
    StudentQuickCreateView,
    StudentQuickUpdateView,
)

urlpatterns = [
    path('alunos/', StudentDirectoryView.as_view(), name='student-directory'),
    path('alunos/novo/', StudentQuickCreateView.as_view(), name='student-quick-create'),
    path('alunos/<int:student_id>/editar/', StudentQuickUpdateView.as_view(), name='student-quick-update'),
    path('alunos/<int:student_id>/financeiro/acao/', StudentPaymentActionView.as_view(), name='student-payment-action'),
    path('alunos/<int:student_id>/matricula/acao/', StudentEnrollmentActionView.as_view(), name='student-enrollment-action'),
    path('financeiro/', FinanceCenterView.as_view(), name='finance-center'),
    path('financeiro/planos/<int:plan_id>/editar/', MembershipPlanQuickUpdateView.as_view(), name='membership-plan-quick-update'),
    path('grade-aulas/', ClassGridView.as_view(), name='class-grid'),
]