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

from communications.models import IntakeStatus, StudentIntake
from students.application.commands import StudentIntakeSyncCommand
from students.application.ports import StudentIntakeWorkflowPort
from students.application.use_cases import execute_student_intake_sync_use_case
from students.domain import build_intake_conversion_decision, build_intake_lookup_decision
from students.models import Student


class DjangoStudentIntakeWorkflowPort(StudentIntakeWorkflowPort):
    @transaction.atomic
    def sync(self, command: StudentIntakeSyncCommand) -> int | None:
        student = Student.objects.get(pk=command.student_id)
        lookup_decision = build_intake_lookup_decision(
            intake_record_id=command.intake_record_id,
            student_phone=student.phone,
        )

        linked_intake = StudentIntake.objects.filter(pk=lookup_decision.explicit_intake_id).first() if lookup_decision.explicit_intake_id else None
        if linked_intake is None and lookup_decision.should_try_phone_fallback:
            linked_intake = StudentIntake.objects.filter(
                phone__in=lookup_decision.fallback_phone_candidates,
                linked_student__isnull=True,
            ).order_by('-pk').first()
        if linked_intake is None:
            return None

        linked_intake = StudentIntake.objects.select_for_update().get(pk=linked_intake.pk)
        conversion_decision = build_intake_conversion_decision(
            existing_phone=linked_intake.phone,
            existing_notes=linked_intake.notes,
            normalized_student_phone=lookup_decision.normalized_student_phone,
        )

        if conversion_decision.normalized_phone and linked_intake.phone != conversion_decision.normalized_phone:
            linked_intake.phone = conversion_decision.normalized_phone

        linked_intake.linked_student = student
        linked_intake.status = conversion_decision.status
        linked_intake.notes = conversion_decision.notes
        linked_intake.save(update_fields=['phone', 'linked_student', 'status', 'notes', 'updated_at'])
        return linked_intake.id


def execute_student_intake_sync_command(command: StudentIntakeSyncCommand):
    return execute_student_intake_sync_use_case(
        command,
        intake_workflow_port=DjangoStudentIntakeWorkflowPort(),
    )


__all__ = ['execute_student_intake_sync_command']
