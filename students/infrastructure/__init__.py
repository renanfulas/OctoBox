"""
ARQUIVO: exportador lazy dos adapters Django do dominio de alunos.

POR QUE ELE EXISTE:
- Mantem ORM, transacao e auditoria concretos fora da camada de aplicacao sem introduzir ciclos de import.

O QUE ESTE ARQUIVO FAZ:
1. Exporta execucao concreta dos casos de uso com imports tardios.
2. Evita ciclos entre services historicos e adapters novos.

PONTOS CRITICOS:
- As funcoes abaixo devem permanecer finas; a implementacao real mora nos modulos especificos.
"""


def execute_create_student_quick_command(command):
    from .django_quick_flow import execute_create_student_quick_command as implementation

    return implementation(command)


def execute_update_student_quick_command(command):
    from .django_quick_flow import execute_update_student_quick_command as implementation

    return implementation(command)


def execute_student_enrollment_action_command(command):
    from .django_actions import execute_student_enrollment_action_command as implementation

    return implementation(command)


def execute_student_payment_action_command(command):
    from .django_actions import execute_student_payment_action_command as implementation

    return implementation(command)


def execute_student_payment_regeneration_command(command):
    from .django_payments import execute_student_payment_regeneration_command as implementation

    return implementation(command)


def execute_student_payment_schedule_command(command):
    from .django_payments import execute_student_payment_schedule_command as implementation

    return implementation(command)

__all__ = [
	'execute_create_student_quick_command',
	'execute_student_enrollment_action_command',
	'execute_student_payment_action_command',
	'execute_student_payment_regeneration_command',
	'execute_student_payment_schedule_command',
	'execute_update_student_quick_command',
]
