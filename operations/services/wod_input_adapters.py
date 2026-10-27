"""Preview de leitura do aplicador diário legado, sem mutação de WOD."""

from datetime import datetime, time, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from access.roles import ROLE_COACH, ROLE_MANAGER, ROLE_OWNER, get_user_role
from operations.models import ClassSession, ClassType, SessionStatus, WorkoutTemplate
from student_app.models import SessionWorkoutStatus


def build_day_apply_preview(*, actor, target_date, template_id, class_type, mode):
    role = get_user_role(actor)
    if role is None or role.slug not in {ROLE_COACH, ROLE_MANAGER, ROLE_OWNER}:
        raise PermissionDenied('Sem permissão para conferir WODs.')
    if class_type not in ClassType.values or mode not in {'replace_empty', 'overwrite'}:
        raise ValidationError('Escolha a modalidade e o modo de aplicação.')
    template = WorkoutTemplate.objects.filter(
        pk=template_id, is_active=True, archived_at__isnull=True,
    ).first()
    if template is None:
        raise ValidationError('Template não encontrado ou arquivado.')
    if role.slug == ROLE_COACH and template.created_by_id != actor.pk:
        raise PermissionDenied('Use um template criado por você.')

    start = timezone.make_aware(datetime.combine(target_date, time.min))
    sessions = ClassSession.objects.select_related('coach', 'workout_program', 'workout').filter(
        scheduled_at__gte=start,
        scheduled_at__lt=start + timedelta(days=1),
        class_type=class_type,
        status__in=(SessionStatus.SCHEDULED, SessionStatus.OPEN, SessionStatus.COMPLETED),
    ).order_by('scheduled_at', 'id')
    if role.slug == ROLE_COACH:
        sessions = sessions.filter(coach=actor)

    entries = []
    program_names = set()
    for session in sessions:
        workout = getattr(session, 'workout', None)
        program = session.workout_program
        program_name = program.name if program else 'Sem programa associado'
        program_names.add((session.workout_program_id, program_name))
        if workout is not None and (mode == 'replace_empty' or workout.status != SessionWorkoutStatus.DRAFT):
            status, reason = 'preserved', 'WOD existente preservado.'
        else:
            status, reason = 'ready', 'Receberá o template como rascunho.'
        if session.status == SessionStatus.COMPLETED:
            reason += ' Aula concluída: este aplicador legado ainda a inclui.'
        entries.append({
            'session_id': session.pk,
            'title': session.title,
            'scheduled_at': timezone.localtime(session.scheduled_at).strftime('%H:%M'),
            'program': program_name,
            'status': status,
            'reason': reason,
            'completed': session.status == SessionStatus.COMPLETED,
        })
    return {
        'ok': True,
        'scope': 'class_type_legacy',
        'template': template.name,
        'date': target_date.isoformat(),
        'entries': entries,
        'ready_count': sum(entry['status'] == 'ready' for entry in entries),
        'preserved_count': sum(entry['status'] == 'preserved' for entry in entries),
        'programs': [name for _id, name in sorted(program_names, key=lambda row: (row[1], row[0] or 0))],
        'mixed_programs': len(program_names) > 1,
        'completed_count': sum(entry['completed'] for entry in entries),
    }


__all__ = ['build_day_apply_preview']
