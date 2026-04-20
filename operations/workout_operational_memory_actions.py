"""
ARQUIVO: actions da memoria operacional curta do WOD publicado.

POR QUE ELE EXISTE:
- separa da action view a criacao da memoria operacional e sua auditoria.

O QUE ESTE ARQUIVO FAZ:
1. cria memoria operacional curta.
2. registra auditoria correspondente.

PONTOS CRITICOS:
- manter metadata e feedback identicos ao fluxo anterior.
"""

from student_app.models import SessionWorkoutOperationalMemory

from .workout_support import record_workout_audit


def create_workout_operational_memory(*, actor, workout, payload):
    memory = SessionWorkoutOperationalMemory.objects.create(
        workout=workout,
        kind=payload['kind'],
        note=payload['note'],
        created_by=actor,
    )
    record_workout_audit(
        actor=actor,
        workout=workout,
        action='session_workout_operational_memory_created',
        description='Owner ou manager registrou um marco curto da memoria operacional do caso.',
        metadata={
            'session_id': workout.session_id,
            'version': workout.version,
            'memory_kind': memory.kind,
            'memory_kind_label': memory.get_kind_display(),
            'note': memory.note,
        },
    )
    return memory


__all__ = ['create_workout_operational_memory']
