"""Parsing HTTP dos comandos de saída/correção do treino guiado Curva."""

import uuid
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse

from public_workouts.services import LoadCorrectionConflictError, LoadCorrectionNotFoundError, LoadValueError
from public_workouts.training_sessions import TrainingSessionConflict, TrainingSessionInvalid
from public_workouts.training_set_decisions import cancel_session, correct_set, skip_set, unskip_set


def _address(data):
    if any(isinstance(data.get(field), bool) for field in ('movement_index', 'set_number')):
        raise ValueError('endereço de série inválido')
    session_id = uuid.UUID(str(data.get('session_id')))
    movement_index = int(data.get('movement_index'))
    set_number = int(data.get('set_number'))
    if not 0 <= movement_index <= 100 or not 1 <= set_number <= 100:
        raise ValueError('endereço de série inválido')
    return session_id, movement_index, set_number


def _values(data):
    if any(isinstance(data.get(field), bool) for field in ('weight_kg', 'reps', 'rir')):
        raise ValueError('valor de série inválido')
    weight = Decimal(str(data['weight_kg'])) if data.get('weight_kg') not in (None, '') else None
    reps = int(data['reps']) if data.get('reps') not in (None, '') else None
    rir = Decimal(str(data['rir'])) if data.get('rir') not in (None, '') else None
    if (
        (weight is not None and (not weight.is_finite() or weight < 0 or weight > Decimal('9999.99')
                                 or weight != weight.quantize(Decimal('0.01'))))
        or (reps is not None and not 1 <= reps <= 999)
        or (rir is not None and (not rir.is_finite() or rir < 0 or rir > 10
                                 or rir != rir.quantize(Decimal('0.1'))))
    ):
        raise ValueError('valor de série inválido')
    return weight, reps, rir


def handle_session_decision(*, data, account_id, plan_slug):
    action = data.get('action')
    try:
        if action == 'cancel':
            session_id = uuid.UUID(str(data.get('session_id')))
            session, created = cancel_session(
                account_id=account_id, plan_slug=plan_slug, session_id=session_id,
            )
            return JsonResponse({'ok': True, 'created': created, 'outcome': session.outcome})
        session_id, movement_index, set_number = _address(data)
        common = dict(account_id=account_id, plan_slug=plan_slug, session_id=session_id,
                      movement_index=movement_index, set_number=set_number)
        if action == 'skip':
            movement_slug = str(data.get('movement_slug') or '')
            role = str(data.get('set_role') or '')
            if not movement_slug or len(movement_slug) > 80 or not movement_slug.replace('-', '').isalnum():
                raise ValueError('movimento inválido')
            row, created = skip_set(**common, movement_slug=movement_slug, role=role)
            return JsonResponse({'ok': True, 'created': created, 'set_id': row.pk})
        if action == 'unskip':
            removed = unskip_set(**common)
            return JsonResponse({'ok': True, 'removed': removed})
        if action == 'correct':
            command_key = uuid.UUID(str(data.get('command_key')))
            weight, reps, rir = _values(data)
            row, changed = correct_set(
                **common, command_key=command_key, weight=weight, reps=reps, rir=rir,
            )
            return JsonResponse({'ok': True, 'changed': changed, 'set_id': row.pk})
    except (ValueError, TypeError, InvalidOperation, TrainingSessionInvalid, LoadValueError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except (TrainingSessionConflict, LoadCorrectionConflictError) as exc:
        return JsonResponse({'error': str(exc)}, status=409)
    except LoadCorrectionNotFoundError as exc:
        return JsonResponse({'error': str(exc)}, status=404)
    return JsonResponse({'error': 'action inválida'}, status=400)
