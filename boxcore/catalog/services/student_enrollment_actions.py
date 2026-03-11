"""
ARQUIVO: handlers de acoes de matricula do aluno no catalogo.

POR QUE ELE EXISTE:
- Explicita pelo nome do arquivo que esta camada resolve a acao publica handle_student_enrollment_action.

O QUE ESTE ARQUIVO FAZ:
1. Cancela matricula com data e motivo.
2. Reativa matricula preservando historico.
3. Registra auditoria dos movimentos comerciais ligados a matricula.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta status comercial, historico e cobranca futura do aluno.
"""

from boxcore.auditing import log_audit_event

from .enrollments import cancel_enrollment, reactivate_enrollment


def handle_student_enrollment_action(*, actor, student, enrollment, action, action_date, reason=''):
    if action == 'cancel-enrollment':
        cancel_enrollment(enrollment=enrollment, action_date=action_date, reason=reason)
        log_audit_event(
            actor=actor,
            action='student_enrollment_canceled',
            target=enrollment,
            description='Matricula cancelada pela tela do aluno.',
            metadata={'reason': reason},
        )
        return enrollment

    if action == 'reactivate-enrollment':
        new_enrollment = reactivate_enrollment(student=student, enrollment=enrollment, action_date=action_date, reason=reason)
        log_audit_event(
            actor=actor,
            action='student_enrollment_reactivated',
            target=new_enrollment,
            description='Matricula reativada pela tela do aluno.',
            metadata={'reason': reason},
        )
        return new_enrollment

    return None