"""
ARQUIVO: adapter Django do motor de intake do aluno.

POR QUE ELE EXISTE:
- Remove do catálogo legado a implementação concreta de conversão e vínculo do intake.

O QUE ESTE ARQUIVO FAZ:
1. Resolve intake explícito ou fallback por telefone.
2. Atualiza status e observação comercial de conversão.
3. Mantém o quick flow dependente só do adapter novo.

PONTOS CRITICOS:
- Este arquivo concentra ORM e lock do fluxo de conversão de lead.
"""

from django.db import transaction

from boxcore.models import Student
from boxcore.shared.phone_numbers import build_phone_match_candidates, normalize_phone_number
from communications.models import IntakeStatus, StudentIntake
from students.application.commands import StudentIntakeSyncCommand
from students.application.intake_terms import DEFAULT_INTAKE_CONVERSION_NOTE
from students.application.ports import StudentIntakeWorkflowPort
from students.application.use_cases import execute_student_intake_sync_use_case


class DjangoStudentIntakeWorkflowPort(StudentIntakeWorkflowPort):
    @transaction.atomic
    def sync(self, command: StudentIntakeSyncCommand) -> int | None:
        student = Student.objects.get(pk=command.student_id)
        linked_intake = StudentIntake.objects.filter(pk=command.intake_record_id).first() if command.intake_record_id else None
        normalized_phone = normalize_phone_number(student.phone)
        if linked_intake is None:
            linked_intake = StudentIntake.objects.filter(
                phone__in=build_phone_match_candidates(student.phone),
                linked_student__isnull=True,
            ).order_by('-pk').first()
        if linked_intake is None:
            return None

        linked_intake = StudentIntake.objects.select_for_update().get(pk=linked_intake.pk)
        if normalized_phone and linked_intake.phone != normalized_phone:
            linked_intake.phone = normalized_phone

        linked_intake.linked_student = student
        linked_intake.status = IntakeStatus.APPROVED
        linked_intake.notes = '\n'.join(
            filter(None, [linked_intake.notes.strip(), DEFAULT_INTAKE_CONVERSION_NOTE])
        )
        linked_intake.save(update_fields=['phone', 'linked_student', 'status', 'notes', 'updated_at'])
        return linked_intake.id


def execute_student_intake_sync_command(command: StudentIntakeSyncCommand):
    return execute_student_intake_sync_use_case(
        command,
        intake_workflow_port=DjangoStudentIntakeWorkflowPort(),
    )


__all__ = ['execute_student_intake_sync_command']
