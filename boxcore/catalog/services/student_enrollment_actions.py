"""
ARQUIVO: fachada das actions de matricula do aluno.

POR QUE ELE EXISTE:
- Mantem a interface publica atual enquanto o fluxo real de matricula sai para command, use case e adapter Django.

O QUE ESTE ARQUIVO FAZ:
1. Traduz parametros legados para um command explicito.
2. Chama o use case concreto do dominio.
3. Devolve o model historico esperado pelas views e testes.

PONTOS CRITICOS:
- Este arquivo nao deve voltar a concentrar auditoria, ORM ou transacao.
"""

from students.application.commands import StudentEnrollmentActionCommand
from students.infrastructure import execute_student_enrollment_action_command

from boxcore.models import Enrollment


def handle_student_enrollment_action(*, actor, student, enrollment, action, action_date, reason=''):
    command = StudentEnrollmentActionCommand(
        actor_id=getattr(actor, 'id', None),
        student_id=student.id,
        enrollment_id=enrollment.id,
        action=action,
        action_date=action_date,
        reason=reason,
    )
    result = execute_student_enrollment_action_command(command)
    if result.enrollment_id is None:
        return None
    return Enrollment.objects.get(pk=result.enrollment_id)