"""Snapshots internos para desfazer somente o que a aplicação diária alterou."""

from django.db import connection

from student_app.models import SessionWorkoutBlock, SessionWorkoutMovement


def undo_cache_key(actor, token):
    return f'wod_day_apply_undo:{connection.schema_name}:{actor.pk}:{token}'


def model_state(instance):
    return {field.attname: getattr(instance, field.attname) for field in instance._meta.concrete_fields}


def workout_state(workout):
    if workout is None:
        return None
    blocks = []
    for block in workout.blocks.order_by('sort_order', 'id'):
        blocks.append({
            'fields': model_state(block),
            'movements': [model_state(movement) for movement in block.movements.order_by('sort_order', 'id')],
        })
    return {'fields': model_state(workout), 'blocks': blocks}


def restore_workout(workout, state):
    # A versão cresce mesmo ao restaurar conteúdo anterior, para invalidar snapshots.
    next_version = workout.version + 1
    workout.blocks.all().delete()
    for name, value in state['fields'].items():
        if name not in {'id', 'session_id', 'created_at', 'updated_at', 'version'}:
            setattr(workout, name, value)
    workout.version = next_version
    workout.save()
    for saved_block in state['blocks']:
        SessionWorkoutBlock.objects.create(**saved_block['fields'])
        SessionWorkoutMovement.objects.bulk_create([
            SessionWorkoutMovement(**fields) for fields in saved_block['movements']
        ])
