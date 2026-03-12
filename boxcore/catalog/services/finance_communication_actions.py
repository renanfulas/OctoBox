"""
ARQUIVO: fachada da ação de comunicação financeira do catálogo.

POR QUE ELE EXISTE:
- Mantém a entrada histórica da UI enquanto a orquestração real foi movida para communications.

O QUE ESTE ARQUIVO FAZ:
1. Traduz o payload da UI para um command explícito.
2. Encaminha o fluxo para a infraestrutura de communications.
3. Devolve o mesmo shape esperado pela camada HTTP.

PONTOS CRITICOS:
- Este arquivo não deve voltar a resolver ORM nem registrar mensagem diretamente.
"""

from boxcore.models import Student
from communications.application.commands import FinanceCommunicationActionCommand
from communications.infrastructure import execute_finance_communication_action_command, get_message_log


def handle_finance_communication_action(*, actor, payload):
    result = execute_finance_communication_action_command(
        FinanceCommunicationActionCommand(
            actor_id=getattr(actor, 'id', None),
            action_kind=payload.get('action_kind') or '',
            student_id=int(payload.get('student_id')),
            payment_id=int(payload.get('payment_id')) if payload.get('payment_id') else None,
            enrollment_id=int(payload.get('enrollment_id')) if payload.get('enrollment_id') else None,
        )
    )
    return {
        'student': Student.objects.get(pk=result.student_id),
        'message': get_message_log(result.message_log_id),
    }