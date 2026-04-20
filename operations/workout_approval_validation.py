"""
ARQUIVO: validacoes do corredor de aprovacao do WOD.

POR QUE ELE EXISTE:
- separa as guardas de decisao da action view de aprovacao.

O QUE ESTE ARQUIVO FAZ:
1. verifica se o workout ainda aguarda aprovacao.
2. valida confirmacao de mudancas sensiveis.
3. valida formulario de rejeicao.

PONTOS CRITICOS:
- manter mensagens e criterios identicos ao fluxo anterior.
"""

from student_app.models import SessionWorkoutStatus


def is_workout_pending_approval(*, workout):
    return workout.status == SessionWorkoutStatus.PENDING_APPROVAL


def requires_sensitive_confirmation(*, review_snapshot, request):
    return review_snapshot['requires_confirmation'] and request.POST.get('confirm_sensitive_changes') != '1'


def validate_rejection_form(*, form):
    return form.is_valid()


__all__ = [
    'is_workout_pending_approval',
    'requires_sensitive_confirmation',
    'validate_rejection_form',
]
