"""
ARQUIVO: adapter Django de persistencia da grade de aulas.

POR QUE ELE EXISTE:
- separa do writer principal as operacoes ORM concretas de aula para reduzir acoplamento local.

O QUE ESTE ARQUIVO FAZ:
1. busca duplicidades do lote por titulo e horario.
2. cria aulas planejadas pela camada operacional.
3. reidrata aulas com lock para edicao e exclusao.
4. aplica update_fields e exclusao concreta das aulas.

PONTOS CRITICOS:
- esta camada mantem ORM e locking; as decisoes de fluxo ficam acima dela.
"""

from operations.models import ClassSession


class DjangoClassGridSessionStore:
    def find_existing_scheduled_ats(self, *, title: str, scheduled_ats: list) -> frozenset:
        return frozenset(
            ClassSession.objects.filter(
                title=title,
                scheduled_at__in=scheduled_ats,
            ).values_list('scheduled_at', flat=True)
        )

    def create_session(
        self,
        *,
        title: str,
        coach,
        scheduled_at,
        duration_minutes: int,
        capacity: int,
        status: str,
        notes: str,
    ) -> int:
        session = ClassSession.objects.create(
            title=title,
            coach=coach,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            capacity=capacity,
            status=status,
            notes=notes,
        )
        return session.id

    def get_session_for_update(self, *, session_id: int):
        return ClassSession.objects.select_for_update().get(pk=session_id)

    def list_sessions_for_reset(self):
        return list(ClassSession.objects.select_for_update().order_by('scheduled_at', 'id'))

    def has_attendance(self, *, session) -> bool:
        return session.attendances.exists()

    def collect_current_values(self, *, session, field_names: tuple[str, ...]) -> dict[str, object]:
        return {
            field_name: getattr(session, field_name)
            for field_name in field_names
        }

    def save_session_updates(self, *, session, target_values: dict[str, object], changed_fields: tuple[str, ...]) -> None:
        if not changed_fields:
            return

        for field_name in changed_fields:
            setattr(session, field_name, target_values[field_name])

        session.save(update_fields=[*changed_fields, 'updated_at'])

    def delete_session(self, *, session) -> None:
        session.delete()


__all__ = ['DjangoClassGridSessionStore']
