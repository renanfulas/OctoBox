"""Saídas e correções de uma sessão Curva; nenhuma regra de HTTP aqui."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from .models import PublicWorkoutLoadLog, PublicWorkoutTrainingSession, PublicWorkoutTrainingSet, PublicWorkoutTrainingSetRevision
from .training_sessions import TrainingSessionConflict, TrainingSessionInvalid, day_plan


def _locked_session(*, account_id, plan_slug, session_id):
    session = PublicWorkoutTrainingSession.objects.select_for_update().filter(
        pk=session_id, account_id=account_id, plan_slug=plan_slug,
    ).first()
    if session is None:
        raise TrainingSessionInvalid('sessão inexistente')
    if session.program is None:
        raise TrainingSessionConflict('sessão antiga sem versão de programa')
    return session


def _prescribed(*, session, movement_index, set_number, movement_slug, role):
    movements = day_plan(session.program, session.day_id)
    if not 0 <= movement_index < len(movements):
        raise TrainingSessionInvalid('movimento não pertence a este dia')
    movement = movements[movement_index]
    maximum = 30 if movement['freeform'] else len(movement['series'])
    if movement_slug != movement['slug'] or not 1 <= set_number <= maximum:
        raise TrainingSessionInvalid('série não pertence ao movimento')
    prescription = movement['series'][0] if movement['freeform'] else movement['series'][set_number - 1]
    if role != prescription['role']:
        raise TrainingSessionInvalid('papel da série diverge da prescrição')
    return movement, prescription


@transaction.atomic
def skip_set(*, account_id, plan_slug, session_id, movement_index, set_number, movement_slug, role):
    session = _locked_session(account_id=account_id, plan_slug=plan_slug, session_id=session_id)
    if session.ended_at is not None:
        raise TrainingSessionConflict('sessão já encerrada')
    _, prescription = _prescribed(
        session=session, movement_index=movement_index, set_number=set_number,
        movement_slug=movement_slug, role=role,
    )
    row = PublicWorkoutTrainingSet.objects.filter(
        session=session, movement_index=movement_index, set_number=set_number,
    ).first()
    if row is not None:
        if row.status != 'skipped':
            raise TrainingSessionConflict('série já realizada; use correção')
        return row, False
    row = PublicWorkoutTrainingSet.objects.create(
        session=session, movement_index=movement_index, set_number=set_number,
        movement_slug=movement_slug, set_role=role, status='skipped',
        stage_id=prescription.get('stage_id', ''),
        stage_ordinal=prescription.get('stage_ordinal'),
    )
    return row, True


@transaction.atomic
def unskip_set(*, account_id, plan_slug, session_id, movement_index, set_number):
    session = _locked_session(account_id=account_id, plan_slug=plan_slug, session_id=session_id)
    if session.ended_at is not None:
        raise TrainingSessionConflict('sessão já encerrada')
    row = PublicWorkoutTrainingSet.objects.filter(
        session=session, movement_index=movement_index, set_number=set_number,
    ).first()
    if row is None:
        return False
    if row.status != 'skipped':
        raise TrainingSessionConflict('série realizada não pode ser desfeita')
    row.delete()
    return True


def _fact(row):
    return {'weight_kg': str(row.weight_kg) if row.weight_kg is not None else None,
            'reps': row.reps, 'rir': str(row.rir) if row.rir is not None else None,
            'load_log_id': row.load_log_id}


@transaction.atomic
def correct_set(*, account_id, plan_slug, session_id, movement_index, set_number,
                command_key, weight, reps, rir):
    session = _locked_session(account_id=account_id, plan_slug=plan_slug, session_id=session_id)
    existing_revision = PublicWorkoutTrainingSetRevision.objects.select_related('training_set').filter(command_key=command_key).first()
    if existing_revision is not None:
        row = existing_revision.training_set
        if row.session_id != session.pk or row.movement_index != movement_index or row.set_number != set_number:
            raise TrainingSessionConflict('chave de correção já usada em outra série')
        return row, False
    row = PublicWorkoutTrainingSet.objects.select_for_update().filter(
        session=session, movement_index=movement_index, set_number=set_number,
        status='performed',
    ).first()
    if row is None:
        raise TrainingSessionInvalid('série realizada não encontrada')
    movement, prescription = _prescribed(
        session=session, movement_index=movement_index, set_number=set_number,
        movement_slug=row.movement_slug, role=row.set_role,
    )
    if prescription.get('hold_seconds') is not None:
        # Série por tempo não tem carga/repetições para corrigir (nem registro de carga).
        raise TrainingSessionInvalid('série por tempo não tem carga para corrigir')
    if prescription['reps'] is not None and reps is None:
        raise TrainingSessionInvalid('informe as repetições realizadas')
    if weight is None and reps is None and (movement['allow_load_registration'] or prescription['reps'] is not None):
        raise TrainingSessionInvalid('informe a carga ou as repetições realizadas')
    before = _fact(row)
    if (row.weight_kg, row.reps, row.rir) == (weight, reps, rir):
        PublicWorkoutTrainingSetRevision.objects.create(
            training_set=row, command_key=command_key, before=before, after=before,
        )
        return row, False
    if row.set_role == 'top_set' and movement['allow_load_registration']:
        from .services import correct_load

        original_key = row.load_log.idempotency_key if row.load_log_id else f'guided:{session.pk}:{movement_index}:{set_number}'
        result = correct_load(
            account_id=account_id, supersedes_idempotency_key=original_key,
            idempotency_key=f'guided-correction:{command_key}',
            weight_kg=weight, reps=reps, rir=rir,
        )
        row.load_log = PublicWorkoutLoadLog.objects.get(idempotency_key=result['idempotency_key'])
    row.weight_kg, row.reps, row.rir = weight, reps, rir
    row.save(update_fields=['weight_kg', 'reps', 'rir', 'load_log', 'updated_at'])
    PublicWorkoutTrainingSetRevision.objects.create(
        training_set=row, command_key=command_key, before=before, after=_fact(row),
    )
    return row, True


@transaction.atomic
def cancel_session(*, account_id, plan_slug, session_id):
    session = _locked_session(account_id=account_id, plan_slug=plan_slug, session_id=session_id)
    if session.ended_at is not None:
        if session.outcome != 'cancelled':
            raise TrainingSessionConflict('sessão já encerrada com outro resultado')
        return session, False
    summary = session.sets.filter(status='performed').aggregate(
        sets=Count('id'), movements=Count('movement_index', distinct=True),
    )
    session.ended_at = timezone.now()
    session.outcome = 'cancelled'
    session.completed_set_count = summary['sets'] or 0
    session.movement_count = summary['movements'] or 0
    session.save(update_fields=['ended_at', 'outcome', 'completed_set_count', 'movement_count', 'updated_at'])
    return session, True
