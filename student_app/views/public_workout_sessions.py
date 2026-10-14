"""Endpoint autenticado da sessão guiada do aluno Curva."""

import uuid
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse, JsonResponse
from django.views import View

from student_identity.public_workout_session import get_public_workout_account_id_from_request
from student_app.views.public_workout_access import (
    _confirm_login_session_owns_slug_or_404,
    _get_public_workout_entry,
)
from student_app.views.public_workout_session_commands import handle_session_decision
from student_app.views.public_workout_request import json_payload

from public_workouts.services import LoadValueError
from public_workouts.training_sessions import (
    TrainingSessionConflict, TrainingSessionInvalid, active_session,
    finish_session, record_set, start_session,
)


def _session_body(session):
    rows = list(session.sets.all())
    return {
        'session_id': str(session.pk), 'day_id': session.day_id,
        'started_at': session.started_at.isoformat(),
        'completed_at': session.completed_at.isoformat() if session.completed_at else None,
        'ended_at': session.ended_at.isoformat() if session.ended_at else None,
        'outcome': session.outcome or None,
        'program_version': session.program.version if session.program else None,
        'recorded': [
            {
                'movement_index': row.movement_index, 'set_number': row.set_number,
                'weight_kg': str(row.weight_kg) if row.weight_kg is not None else None,
                'reps': row.reps, 'rir': str(row.rir) if row.rir is not None else None,
            }
            for row in rows if row.status == 'performed'
        ],
        'skipped': [
            f'{row.movement_index}:{row.set_number}'
            for row in rows if row.status == 'skipped'
        ],
    }


class PublicWorkoutSessionView(View):
    http_method_names = ['get', 'post']

    def get(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)
        _confirm_login_session_owns_slug_or_404(request, plan.slug)
        session = active_session(account_id=account_id, plan_slug=plan.slug)
        response = JsonResponse({'ok': True, 'session': _session_body(session) if session else None})
        response['Cache-Control'] = 'no-store'
        return response

    def post(self, request, plan_slug, *args, **kwargs):
        plan = _get_public_workout_entry(plan_slug)
        account_id = get_public_workout_account_id_from_request(request)
        if account_id is None:
            return JsonResponse({'error': 'login necessario'}, status=401)
        _confirm_login_session_owns_slug_or_404(request, plan.slug)
        data = json_payload(request)
        if data is None:
            return HttpResponse(status=400)
        if data.get('account_scope') not in (None, '', str(account_id)):
            return JsonResponse({'error': 'Entre novamente na mesma conta para enviar este treino.'}, status=401)
        action = data.get('action')
        if action in {'skip', 'unskip', 'correct', 'cancel'}:
            return handle_session_decision(data=data, account_id=account_id, plan_slug=plan.slug)
        if action == 'start':
            day_id = str(data.get('day_id') or '').strip()
            if not day_id or len(day_id) > 32:
                return JsonResponse({'error': 'day_id obrigatorio'}, status=400)
            try:
                start_key = str(uuid.UUID(str(data['start_key']))) if data.get('start_key') else None
                expected_version = int(data['program_version']) if data.get('program_version') not in (None, '') else None
                if isinstance(data.get('program_version'), bool) or (expected_version is not None and expected_version < 1):
                    raise ValueError('versão inválida')
            except (ValueError, TypeError, AttributeError):
                return JsonResponse({'error': 'chave de início ou versão inválida'}, status=400)
            try:
                session = start_session(
                    account_id=account_id, plan_slug=plan.slug, day_id=day_id, start_key=start_key,
                    expected_program_version=expected_version,
                )
            except TrainingSessionInvalid as exc:
                return JsonResponse({'error': str(exc)}, status=400)
            except TrainingSessionConflict as exc:
                return JsonResponse({'error': str(exc)}, status=409)
            return JsonResponse({'ok': True, **_session_body(session)})
        if action in {'complete', 'partial'}:
            try:
                session_id = uuid.UUID(str(data.get('session_id')))
            except (ValueError, TypeError, AttributeError):
                return JsonResponse({'error': 'session_id invalido'}, status=400)
            try:
                session, created = finish_session(
                    account_id=account_id, plan_slug=plan.slug, session_id=session_id,
                    partial=action == 'partial',
                )
            except TrainingSessionInvalid as exc:
                return JsonResponse({'error': str(exc)}, status=404)
            except TrainingSessionConflict as exc:
                return JsonResponse({'error': str(exc)}, status=409)
            return JsonResponse({'ok': True, 'created': created, **_session_body(session)})
        if action == 'set':
            try:
                if any(isinstance(data.get(field), bool) for field in ('movement_index', 'set_number', 'reps', 'weight_kg', 'rir')):
                    raise ValueError('boolean não é número de série')
                session_id = uuid.UUID(str(data.get('session_id')))
                movement_index = int(data.get('movement_index'))
                set_number = int(data.get('set_number'))
                reps = int(data.get('reps')) if data.get('reps') not in (None, '') else None
                weight = Decimal(str(data.get('weight_kg'))) if data.get('weight_kg') not in (None, '') else None
                rir = Decimal(str(data.get('rir'))) if data.get('rir') not in (None, '') else None
                movement_slug = str(data.get('movement_slug') or '')
                role = str(data.get('set_role') or '')
            except (ValueError, TypeError, InvalidOperation):
                return JsonResponse({'error': 'serie invalida'}, status=400)
            valid_roles = {'warmup', 'feeder', 'top_set', 'max_set', 'legacy_unknown'}
            if (
                not movement_slug or len(movement_slug) > 80 or not movement_slug.replace('-', '').isalnum()
                or not 0 <= movement_index <= 100
                or not 1 <= set_number <= 100 or role not in valid_roles
                or (reps is not None and not 1 <= reps <= 999)
                or (weight is not None and (not weight.is_finite() or weight < 0 or weight > Decimal('9999.99')))
                or (rir is not None and (not rir.is_finite() or rir < 0 or rir > 10))
            ):
                return JsonResponse({'error': 'serie invalida'}, status=400)
            if weight is not None:
                if weight != weight.quantize(Decimal('0.01')):
                    return JsonResponse({'error': 'carga aceita no máximo duas casas decimais'}, status=400)
                weight = weight.quantize(Decimal('0.01'))
            if rir is not None:
                if rir != rir.quantize(Decimal('0.1')):
                    return JsonResponse({'error': 'RIR aceita no máximo uma casa decimal'}, status=400)
                rir = rir.quantize(Decimal('0.1'))
            try:
                record, created = record_set(
                    account_id=account_id, plan_slug=plan.slug, session_id=session_id,
                    movement_index=movement_index, set_number=set_number,
                    movement_slug=movement_slug, role=role, weight=weight, reps=reps, rir=rir,
                )
            except (TrainingSessionInvalid, LoadValueError, ValueError) as exc:
                return JsonResponse({'error': str(exc)}, status=400)
            except TrainingSessionConflict as exc:
                return JsonResponse({'error': str(exc)}, status=409)
            return JsonResponse({'ok': True, 'created': created, 'set_id': record.pk})
        return JsonResponse({'error': 'action invalida'}, status=400)


