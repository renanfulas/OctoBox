"""
ARQUIVO: actions do atalho rapido de RM.

POR QUE ELE EXISTE:
- separa a mutacao curta de salvar RM e fechar gap da view da board.

O QUE ESTE ARQUIVO FAZ:
1. salva o RM do aluno no movimento alvo.
2. marca o gap operacional como coletado.
3. devolve a mensagem e redirect do fluxo.

PONTOS CRITICOS:
- manter side effects e feedback visual identicos ao fluxo anterior.
- nao crescer para um modulo generico; este corredor e propositalmente curto.
"""

from django.contrib import messages
from django.shortcuts import redirect

from student_app.models import SessionWorkoutRmGapAction, WorkoutRmGapActionStatus


def save_workout_student_rm_quick_edit(view, form):
    rm_record = form.save(commit=False)
    rm_record.student = view.student
    rm_record.exercise_slug = view.exercise_slug
    rm_record.save()
    SessionWorkoutRmGapAction.objects.update_or_create(
        workout=view.workout,
        student=view.student,
        exercise_slug=view.exercise_slug,
        defaults={
            'exercise_label': rm_record.exercise_label,
            'status': WorkoutRmGapActionStatus.COLLECTED,
            'note': 'RM registrado pelo atalho operacional da board.',
            'updated_by': view.request.user,
        },
    )
    messages.success(view.request, f'RM de {rm_record.exercise_label} salvo para {view.student.full_name}.')
    return redirect('workout-approval-board')


__all__ = ['save_workout_student_rm_quick_edit']
