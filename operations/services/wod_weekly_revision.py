"""Escritas monotônicas do plano semanal em edições concorrentes."""

from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone

from student_app.models import WeeklyWodPlan


def save_weekly_plan_revision(plan, *, fields=None):
    if plan.pk is None:
        plan.save()
        return plan
    expected = plan.revision
    names = fields or (
        'week_start', 'workout_program_id', 'label', 'source_text',
        'parsed_payload', 'status', 'created_by_id',
    )
    values = {name: getattr(plan, name) for name in names}
    now = timezone.now()
    changed = WeeklyWodPlan.objects.filter(pk=plan.pk, revision=expected).update(
        **values, revision=F('revision') + 1, updated_at=now,
    )
    if not changed:
        raise ValidationError('O rascunho mudou em outra aba. Confira a versão atual antes de continuar.')
    plan.revision += 1
    plan.updated_at = now
    return plan


__all__ = ['save_weekly_plan_revision']
