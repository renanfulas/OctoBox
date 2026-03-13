"""
ARQUIVO: store Django das acoes do workspace operacional.

POR QUE ELE EXISTE:
- tira do writer principal do workspace a responsabilidade de consultar e persistir entidades ORM diretamente.

O QUE ESTE ARQUIVO FAZ:
1. reidrata pagamentos e presencas com lock.
2. resolve a matricula ativa de um aluno.
3. persiste vinculo financeiro, ocorrencia tecnica e mutacao de presenca.

PONTOS CRITICOS:
- esta camada mantem ORM e locking; a decisao operacional continua acima dela.
"""

from finance.models import Enrollment, EnrollmentStatus, Payment
from operations.models import Attendance, BehaviorNote


class DjangoWorkspaceStore:
    def get_payment_for_update(self, *, payment_id: int):
        return Payment.objects.select_related('student').select_for_update().get(pk=payment_id)

    def get_active_enrollment_for_student(self, *, student) -> Enrollment | None:
        return Enrollment.objects.filter(
            student=student,
            status=EnrollmentStatus.ACTIVE,
        ).order_by('-start_date').first()

    def save_payment_enrollment_link(self, *, payment, enrollment, note: str) -> None:
        payment.enrollment = enrollment
        payment.notes = note
        payment.save(update_fields=['enrollment', 'notes', 'updated_at'])

    def create_behavior_note(self, *, student_id: int, author_id: int | None, category: str, description: str) -> int:
        note = BehaviorNote.objects.create(
            student_id=student_id,
            author_id=author_id,
            category=category,
            description=description,
        )
        return note.id

    def get_attendance_for_update(self, *, attendance_id: int):
        return Attendance.objects.select_for_update().get(pk=attendance_id)

    def save_attendance_action(
        self,
        *,
        attendance,
        status: str,
        check_in_at,
        check_out_at,
    ) -> None:
        attendance.status = status
        attendance.check_in_at = check_in_at
        attendance.check_out_at = check_out_at
        attendance.save(update_fields=['status', 'check_in_at', 'check_out_at', 'updated_at'])


__all__ = ['DjangoWorkspaceStore']