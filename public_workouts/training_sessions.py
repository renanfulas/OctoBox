"""Casos de uso de uma sessão Curva, isolados do contrato HTTP e do PWA."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from .guided_workout import build_guided_series
from .models import (
    PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutProgram, PublicWorkoutPushSubscription,
    PublicWorkoutTrainingSession, PublicWorkoutTrainingSet,
)


class TrainingSessionInvalid(ValueError):
    """Prescrição ou comando que não pertence ao programa publicado."""


class TrainingSessionConflict(Exception):
    """A sessão mudou de estado ou a série já foi registrada diferente."""


def day_plan(program: PublicWorkoutProgram, day_id: str) -> list[dict]:
    """Índices coincidem com a lista de movimentos guiáveis renderizada."""
    day = next((item for item in program.payload.get('days', ()) if item.get('day_id') == day_id), None)
    if day is None:
        raise TrainingSessionInvalid('dia não pertence ao programa publicado')
    movements = []
    for block in day.get('blocks', ()):
        for movement in block.get('movements', ()):
            series = build_guided_series(movement)
            if series:
                movements.append({
                    'slug': movement['movement_slug'],
                    'series': series,
                    'freeform': series[0]['role'] == 'legacy_unknown',
                    'allow_load_registration': movement.get('allow_load_registration') is not False,
                })
    if not movements:
        raise TrainingSessionInvalid('este dia ainda não tem exercícios')
    return movements


def active_session(*, account_id, plan_slug):
    cutoff = timezone.now() - timedelta(hours=36)
    return PublicWorkoutTrainingSession.objects.select_related('program').filter(
        account_id=account_id, plan_slug=plan_slug,
        ended_at__isnull=True, completed_at__isnull=True, started_at__gte=cutoff,
    ).order_by('-started_at').first()


@transaction.atomic
def start_session(*, account_id, plan_slug, day_id, start_key=None, expected_program_version=None):
    # A trava na conta serializa duas abas criando a primeira sessão.
    PublicWorkoutAccount.objects.select_for_update().get(pk=account_id)
    if start_key:
        previous = PublicWorkoutTrainingSession.objects.select_related('program').filter(start_key=start_key).first()
        if previous is not None:
            if previous.account_id != account_id or previous.plan_slug != plan_slug or previous.day_id != day_id:
                raise TrainingSessionConflict('chave de início já usada em outro treino')
            return previous
    program = PublicWorkoutProgram.objects.filter(slug=plan_slug, is_active=True).first()
    if program is None:
        raise TrainingSessionInvalid('programa ativo não encontrado')
    if expected_program_version is not None and program.version != expected_program_version:
        raise TrainingSessionConflict('a ficha mudou durante o treino offline; exporte o rascunho ou comece na nova versão')
    day_plan(program, day_id)
    previous = PublicWorkoutTrainingSession.objects.filter(
        account_id=account_id, plan_slug=plan_slug, day_id=day_id,
        program=program, completed_at__isnull=True, ended_at__isnull=True,
        started_at__gte=timezone.now() - timedelta(hours=36),
    ).order_by('-started_at').first()
    if previous is not None:
        return previous
    return PublicWorkoutTrainingSession.objects.create(
        account_id=account_id, plan_slug=plan_slug, day_id=day_id,
        program=program, start_key=start_key,
    )


@transaction.atomic
def record_set(*, account_id, plan_slug, session_id, movement_index, set_number,
               movement_slug, role, weight, reps, rir):
    session = PublicWorkoutTrainingSession.objects.select_for_update().filter(
        pk=session_id, account_id=account_id, plan_slug=plan_slug,
    ).first()
    if session is None:
        raise TrainingSessionInvalid('sessão inexistente')
    if session.ended_at is not None or session.completed_at is not None:
        raise TrainingSessionConflict('sessão já encerrada')
    if session.program is None:
        raise TrainingSessionConflict('sessão antiga sem versão de programa; inicie outra sessão')
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
    if prescription['reps'] is not None and reps is None:
        raise TrainingSessionInvalid('informe as repetições realizadas nesta série')
    if weight is None and reps is None and (movement['allow_load_registration'] or prescription['reps'] is not None):
        raise TrainingSessionInvalid('informe a carga ou as repetições realizadas')
    existing = PublicWorkoutTrainingSet.objects.filter(
        session=session, movement_index=movement_index, set_number=set_number,
    ).first()
    if existing is not None:
        if (existing.status, existing.movement_slug, existing.set_role, existing.weight_kg, existing.reps, existing.rir) != (
            'performed',
            movement_slug, role, weight, reps, rir,
        ):
            raise TrainingSessionConflict('série já registrada com outros valores')
        return existing, False

    # Cada Top efetivamente registrada pode ser a última quando a faixa é opcional.
    load_log = None
    if movement['allow_load_registration'] and role == 'top_set':
        from .services import record_load

        load_result = record_load(
            account_id=account_id, movement_slug=movement_slug,
            weight_kg=weight, reps=reps, rir=rir,
            performed_on=timezone.localtime(session.started_at).date(),
            program_id=session.program.program_id, set_role=role,
            idempotency_key=f'guided:{session.pk}:{movement_index}:{set_number}',
        )
        load_log = PublicWorkoutLoadLog.objects.get(idempotency_key=load_result['idempotency_key'])
    record = PublicWorkoutTrainingSet.objects.create(
        session=session, movement_index=movement_index, set_number=set_number,
        movement_slug=movement_slug, set_role=role, weight_kg=weight,
        reps=reps, rir=rir, load_log=load_log,
        stage_id=prescription.get('stage_id', ''),
        stage_ordinal=prescription.get('stage_ordinal'),
    )
    return record, True


@transaction.atomic
def finish_session(*, account_id, plan_slug, session_id, partial=False):
    session = PublicWorkoutTrainingSession.objects.select_for_update().filter(
        pk=session_id, account_id=account_id, plan_slug=plan_slug,
    ).first()
    if session is None:
        raise TrainingSessionInvalid('sessão inexistente')
    if session.ended_at is not None or session.completed_at is not None:
        if session.outcome != ('partial' if partial else 'completed'):
            raise TrainingSessionConflict('sessão já encerrada com outro resultado')
        return session, False
    if session.program is None:
        raise TrainingSessionConflict('sessão antiga sem versão de programa; inicie outra sessão')
    movements = day_plan(session.program, session.day_id)
    performed = session.sets.filter(status='performed')
    summary = performed.aggregate(sets=Count('id'), movements=Count('movement_index', distinct=True))
    recorded = set(performed.values_list('movement_index', 'set_number'))
    required = {
        (index, series['set_number'])
        for index, movement in enumerate(movements)
        for series in movement['series'] if series['required']
    }
    freeform_missing = any(
        movement['freeform'] and not any(index == item[0] for item in recorded)
        for index, movement in enumerate(movements)
    )
    if not partial and (not summary['sets'] or not required.issubset(recorded) or freeform_missing):
        raise TrainingSessionConflict('registre as séries mínimas de cada exercício ou encerre como treino parcial')
    session.ended_at = timezone.now()
    session.outcome = 'partial' if partial else 'completed'
    if not partial:
        session.completed_at = session.ended_at
    session.movement_count = summary['movements']
    session.completed_set_count = summary['sets']
    session.save(update_fields=['ended_at', 'outcome', 'completed_at', 'movement_count', 'completed_set_count', 'updated_at'])

    # A outbox existente faz a entrega após commit, com lease e retry.
    from .push import configured
    if not partial and configured() and PublicWorkoutPushSubscription.objects.filter(
        account_id=account_id, revoked_at__isnull=True,
    ).exists():
        from .outbox import TOPIC_TRAINING_COMPLETED, enqueue_outbox

        enqueue_outbox(
            topic=TOPIC_TRAINING_COMPLETED, aggregate_type='training_session',
            aggregate_id=session.pk, version=1,
        )
    return session, True
