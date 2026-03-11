"""
ARQUIVO: services de intake do catálogo.

POR QUE ELE EXISTE:
- Separa da view a conversão de entrada provisória em aluno definitivo.

O QUE ESTE ARQUIVO FAZ:
1. Vincula um intake explícito ou encontrado por fallback de WhatsApp.
2. Atualiza o status comercial do intake para aprovado.
3. Registra a observação padrão de conversão na trilha do lead.

PONTOS CRITICOS:
- O fallback por telefone evita perder leads já capturados antes da conversão formal.
"""

from boxcore.models import IntakeStatus, StudentIntake


def sync_student_intake(*, student, intake=None):
    linked_intake = intake
    if linked_intake is None:
        linked_intake = StudentIntake.objects.filter(
            phone=student.phone,
            linked_student__isnull=True,
        ).order_by('-created_at').first()
    if linked_intake is None:
        return None

    linked_intake.linked_student = student
    linked_intake.status = IntakeStatus.APPROVED
    linked_intake.notes = '\n'.join(
        filter(None, [linked_intake.notes.strip(), 'Convertido em aluno definitivo pela tela leve.'])
    )
    linked_intake.save(update_fields=['linked_student', 'status', 'notes', 'updated_at'])
    return linked_intake