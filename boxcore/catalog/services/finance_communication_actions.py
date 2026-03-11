"""
ARQUIVO: handlers de acoes de comunicacao financeira do catalogo.

POR QUE ELE EXISTE:
- Explicita pelo nome do arquivo que esta camada resolve a acao publica handle_finance_communication_action.

O QUE ESTE ARQUIVO FAZ:
1. Resolve aluno, pagamento e matricula a partir da acao enviada pela UI.
2. Registra o toque operacional de WhatsApp com auditoria.
3. Devolve o aluno impactado para a camada HTTP responder com mensagem adequada.

PONTOS CRITICOS:
- Qualquer regressao aqui afeta a regua operacional e a trilha de comunicacao do produto.
"""

from django.shortcuts import get_object_or_404

from boxcore.models import Enrollment, Payment, Student

from .communications import register_operational_message


def handle_finance_communication_action(*, actor, payload):
    student = get_object_or_404(Student, pk=payload.get('student_id'))
    payment = None
    enrollment = None

    payment_id = payload.get('payment_id')
    enrollment_id = payload.get('enrollment_id')
    if payment_id:
        payment = get_object_or_404(Payment, pk=payment_id, student=student)
    if enrollment_id:
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id, student=student)

    message = register_operational_message(
        actor=actor,
        action_kind=payload.get('action_kind'),
        student=student,
        payment=payment,
        enrollment=enrollment,
    )
    return {
        'student': student,
        'message': message,
    }