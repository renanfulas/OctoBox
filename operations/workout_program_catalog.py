"""Tenant-local default modalities for weekly programming and class rows."""

from operations.model_definitions import ClassType, WorkoutProgram


DEFAULT_WORKOUT_PROGRAMS = (
    ('crossfit', 'CrossFit', [
        'warmup', 'strength', 'skill', 'metcon', 'cooldown', 'mobility', 'custom',
    ]),
    ('hyrox', 'HYROX', [
        'warmup', 'strength', 'skill', 'metcon', 'cooldown', 'mobility', 'custom',
    ]),
    ('mobility', 'Alongamento e mobilidade', ['warmup', 'cooldown', 'mobility', 'custom']),
    ('oly', 'Halterofilia', ['warmup', 'skill', 'cooldown', 'custom']),
    ('strength', 'Força', ['warmup', 'strength', 'skill', 'cooldown', 'custom']),
    ('open_gym', 'Open Gym', [
        'warmup', 'strength', 'skill', 'metcon', 'cooldown', 'mobility', 'custom',
    ]),
    ('other', 'Outros', [
        'warmup', 'strength', 'skill', 'metcon', 'cooldown', 'mobility', 'custom',
    ]),
)


def ensure_default_workout_programs():
    """Idempotently recover the canonical tenant catalog if provisioning missed it."""
    existing = WorkoutProgram.objects.filter(is_active=True)
    if existing.filter(slug='crossfit').exists():
        return existing
    for sort_order, (slug, name, allowed_block_kinds) in enumerate(DEFAULT_WORKOUT_PROGRAMS):
        WorkoutProgram.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'allowed_block_kinds': allowed_block_kinds,
                'sort_order': sort_order,
            },
        )
    return WorkoutProgram.objects.filter(is_active=True)


def program_slug_for_class_type(class_type):
    return {
        ClassType.CROSS: 'crossfit',
        ClassType.HYROX: 'hyrox',
        ClassType.MOBILITY: 'mobility',
        ClassType.OLY: 'oly',
        ClassType.STRENGTH: 'strength',
        ClassType.OPEN_GYM: 'open_gym',
        ClassType.OTHER: 'other',
    }.get(class_type, 'other')
