"""
ARQUIVO: fachada da fila operacional do financeiro.

POR QUE ELE EXISTE:
- Mantém a interface histórica do catálogo enquanto a montagem real do snapshot foi movida para communications.

O QUE ESTE ARQUIVO FAZ:
1. Pede o snapshot operacional ao adapter de communications.
2. Reidrata modelos para a UI atual.
3. Mantém as métricas com o mesmo formato esperado pelas views.

PONTOS CRITICOS:
- Este arquivo não deve voltar a concentrar query e priorização operacional.
"""

from boxcore.models import Enrollment, Payment, Student
from communications.application.commands import BuildOperationalQueueSnapshotCommand
from communications.infrastructure import execute_build_operational_queue_snapshot_command


def build_operational_queue_snapshot(*, limit=9):
    result = execute_build_operational_queue_snapshot_command(BuildOperationalQueueSnapshotCommand(limit=limit))
    student_ids = {item.student_id for item in result.items}
    payment_ids = {item.payment_id for item in result.items if item.payment_id is not None}
    enrollment_ids = {item.enrollment_id for item in result.items if item.enrollment_id is not None}

    students_by_id = Student.objects.in_bulk(student_ids)
    payments_by_id = Payment.objects.select_related('enrollment__plan', 'student').in_bulk(payment_ids)
    enrollments_by_id = Enrollment.objects.select_related('student', 'plan').in_bulk(enrollment_ids)

    queue = []
    for item in result.items:
        queue.append(
            {
                'kind': item.kind,
                'title': item.title,
                'student': students_by_id.get(item.student_id),
                'payment': payments_by_id.get(item.payment_id),
                'enrollment': enrollments_by_id.get(item.enrollment_id),
                'pill': item.pill,
                'pill_class': item.pill_class,
                'summary': item.summary,
                'suggested_message': item.suggested_message,
            }
        )
    return queue


def build_operational_queue_metrics(queue):
    return {
        'Vencendo nos proximos dias': sum(1 for item in queue if item['kind'] == 'upcoming'),
        'Cobrancas em atraso': sum(1 for item in queue if item['kind'] == 'overdue'),
        'Chance de reativacao': sum(1 for item in queue if item['kind'] == 'reactivation'),
    }


build_operational_queue = build_operational_queue_snapshot
summarize_operational_queue = build_operational_queue_metrics