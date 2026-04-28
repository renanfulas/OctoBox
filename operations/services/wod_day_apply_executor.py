"""
ARQUIVO: executor de aplicação de template em todas as sessões de um dia.

POR QUE ELE EXISTE:
- orquestra a aplicação em lote reutilizando apply_persisted_workout_template,
  que já lida com criação/atualização de SessionWorkout e revisão de auditoria.

O QUE ESTE ARQUIVO FAZ:
1. carrega sessões do dia alvo filtradas por box e class_type permitidos.
2. aplica as regras de elegibilidade (replace_empty | overwrite).
3. chama apply_persisted_workout_template por sessão elegível.
4. retorna payload para undo e resumo de impacto.

PONTOS CRÍTICOS:
- instância única por box (single-tenant); sem filtro box_id em ClassSession.
- nunca propaga exceção de sessão individual — registra skip com motivo.
- retorna undo_token com os workout_ids criados/afetados (usado por wod_day_apply_undo).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from operations.domain.wod_day_apply_rules import ApplyMode, filter_eligible_sessions
from operations.models import ClassSession, WorkoutTemplate
from operations.workout_templates import apply_persisted_workout_template


_UNDO_TTL = 60  # segundos


@dataclass
class DayApplyResult:
    applied_count: int
    skipped_count: int
    undo_token: str
    applied_session_ids: list[int] = field(default_factory=list)
    skipped_reasons: list[dict] = field(default_factory=list)


def _day_range(target_date: date):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(target_date, time.min), tz)
    end = timezone.make_aware(datetime.combine(target_date, time.max), tz)
    return start, end


def execute_day_apply(
    *,
    actor,
    target_date: date,
    template_id: int,
    mode: ApplyMode,
) -> DayApplyResult:
    template = WorkoutTemplate.objects.filter(
        id=template_id,
        is_active=True,
        archived_at__isnull=True,
    ).first()
    if template is None:
        return DayApplyResult(
            applied_count=0,
            skipped_count=0,
            undo_token='',
            skipped_reasons=[{'reason': 'Template não encontrado ou arquivado.'}],
        )

    range_start, range_end = _day_range(target_date)
    sessions = list(
        ClassSession.objects.select_related('workout')
        .filter(scheduled_at__gte=range_start, scheduled_at__lte=range_end)
        .order_by('scheduled_at', 'id')
    )

    session_payloads = [
        {
            'session_id': s.id,
            'session': s,
            'has_existing_workout': hasattr(s, 'workout'),
        }
        for s in sessions
    ]

    eligible, skipped = filter_eligible_sessions(session_payloads=session_payloads, mode=mode)

    applied_session_ids = []
    skipped_reasons = [{'session_id': s.session_id, 'reason': s.skip_reason} for s in skipped]

    with transaction.atomic():
        for payload in eligible:
            session = payload['session']
            if mode == 'overwrite' and hasattr(session, 'workout'):
                session.workout.blocks.all().delete()

            result = apply_persisted_workout_template(
                actor=actor,
                template=template,
                target_session=session,
            )
            if result.get('ok', True) is not False:
                applied_session_ids.append(session.id)
            else:
                skipped_reasons.append({
                    'session_id': session.id,
                    'reason': result.get('reason', 'erro desconhecido'),
                })

        WorkoutTemplate.objects.filter(pk=template.pk).update(
            usage_count=template.usage_count + len(applied_session_ids),
            last_used_at=timezone.now(),
        )

    undo_token = str(uuid.uuid4())
    cache.set(
        f'wod_day_apply_undo:{undo_token}',
        {
            'template_id': template_id,
            'session_ids': applied_session_ids,
            'mode': mode,
        },
        timeout=_UNDO_TTL,
    )

    return DayApplyResult(
        applied_count=len(applied_session_ids),
        skipped_count=len(skipped_reasons),
        undo_token=undo_token,
        applied_session_ids=applied_session_ids,
        skipped_reasons=skipped_reasons,
    )


__all__ = ['DayApplyResult', 'execute_day_apply']
