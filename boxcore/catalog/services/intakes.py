"""
ARQUIVO: fachada do motor de intake do catálogo.

POR QUE ELE EXISTE:
- Mantém o contrato histórico de conversão de intake enquanto a implementação real saiu para students.

O QUE ESTE ARQUIVO FAZ:
1. Traduz a chamada legada para um command explícito.
2. Encaminha o vínculo para o adapter real.
3. Devolve o modelo esperado pelos chamadores históricos.

PONTOS CRITICOS:
- Este arquivo não deve voltar a concentrar fallback, lock ou atualização comercial.
"""

from communications.models import StudentIntake
from students.application.commands import StudentIntakeSyncCommand
from students.infrastructure.django_intakes import execute_student_intake_sync_command


def sync_student_intake(*, student, intake=None):
    intake_id = execute_student_intake_sync_command(
        StudentIntakeSyncCommand(
            student_id=student.id,
            intake_record_id=getattr(intake, 'id', None),
        )
    )
    if intake_id is None:
        return None
    return StudentIntake.objects.get(pk=intake_id)
