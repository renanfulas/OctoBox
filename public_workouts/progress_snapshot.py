"""
ARQUIVO: única leitura de ORM pra decidir "o que é verdade sobre
progresso" (plano docs/plans/curva-grafico-hierarquia-e-set-role.md,
Revisão 8, §7.5).

POR QUE ELE EXISTE:
- Curva de evolução, badge de 1RM, tendência semanal e sugestão de carga
  hoje escaneavam `PublicWorkoutLoadLog`/`load_history` bruto cada um por
  conta própria, sem filtro de `set_role` -- contaminação real (aquecimento
  misturado com série principal) já em produção antes deste módulo
  existir. Este é o ÚNICO lugar que consulta o model bruto pra fins de
  progresso; todo consumidor lê daqui.
- Assinatura EM LOTE (`build_progress_snapshots`), nao por movimento: uma
  tela com N movimentos nunca gera N queries -- duas queries pra CONTA
  INTEIRA, agrupadas por `movement_slug` em memória.

PONTOS CRITICOS:
- Dataclasses PRÓPRIOS (`ProgressPoint`/`ProgressSnapshot`), nunca
  `services.py::_serialize_load_log`: `services.py` PASSA A IMPORTAR este
  módulo (build_student_package/personal_record/movement_load_display) --
  se este módulo importasse de volta `services.py`, seria import
  circular. Zero dependência de `services.py` aqui, de propósito.
- `legacy_points`/`curve_points` respeitam a janela de 90 dias do eixo;
  `has_legacy_history` NUNCA filtra por janela -- o aluno vê "seu
  histórico está salvo" mesmo que nada caiba visualmente na janela atual.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from django.db.models import Q
from django.utils import timezone

from .models import PublicWorkoutLoadLog
from .models import PublicWorkoutLoadLogSetRole as SetRole
from .one_rep_max import detect_one_rep_max_trend_from_logs, estimate_one_rep_max
from .progress_eligibility import _CURVE_AND_TREND_ROLES, effective_top_sets_by_day

_WINDOW_DAYS = 90
_PLATE_INCREMENT_KG = Decimal('2.5')


@dataclass(frozen=True)
class ProgressPoint:
    """Representação neutra de um ponto -- não é o model, não é o dict de
    `_serialize_load_log`. Este módulo nunca depende de `services.py`.

    `program_id` foi acrescentado a esta revisão (correção de um gap real
    do plano): `movement_load_display` -> `periodization.
    suggest_progressive_load_kg` compara `last_log.get('program_id')`
    contra o programa atual pra decidir se uma carga de um ciclo ANTERIOR
    é base válida de comparação -- sem esse campo, `latest_top_set`
    perderia essa proteção silenciosamente (toda sugestão de fase
    canônica cairia pro fallback genérico, mesmo quando o log era do
    mesmo programa)."""

    performed_on: date
    weight_kg: Decimal | None
    reps: int | None
    rir: Decimal | None
    created_at: datetime
    program_id: str
    week_in_program: int | None = None


@dataclass(frozen=True)
class ProgressSnapshot:
    latest_top_set: ProgressPoint | None
    curve_points: list  # ProgressPoint, só dentro da janela de 90 dias
    legacy_points: list  # ProgressPoint, só dentro da janela — ver docstring
    has_legacy_history: bool  # histórico completo, SEM filtro de janela
    y_scale: dict | None
    trend_signal: str
    one_rep_max: object | None  # OneRepMaxEstimate de one_rep_max.py, ou None
    weekly_estimates_kg: tuple[float, ...] = ()
    as_of: date | None = None


def _to_point(log) -> ProgressPoint:
    return ProgressPoint(log.performed_on, log.weight_kg, log.reps, log.rir, log.created_at, log.program_id, log.week_in_program)


def _rounded_scale(weights: list) -> dict | None:
    """min/max arredondados pro múltiplo de 2,5kg mais próximo (§3.2) --
    NUNCA o min/max cru dos registros. `weights` vazio -> None. `min==max`
    (série plana) aplica padding de +/-2,5kg pra nunca desenhar uma faixa
    de altura zero."""
    if not weights:
        return None
    low, high = min(weights), max(weights)
    if low == high:
        low, high = max(Decimal('0'), low - _PLATE_INCREMENT_KG), high + _PLATE_INCREMENT_KG
    return {
        'min_kg': (low / _PLATE_INCREMENT_KG).to_integral_value(rounding=ROUND_FLOOR) * _PLATE_INCREMENT_KG,
        'max_kg': (high / _PLATE_INCREMENT_KG).to_integral_value(rounding=ROUND_CEILING) * _PLATE_INCREMENT_KG,
    }


def build_progress_snapshots(*, account_id: int, as_of: date | None = None) -> dict:
    as_of = as_of or timezone.localdate()
    window_start = as_of - timedelta(days=_WINDOW_DAYS)

    # DUAS queries pra CONTA INTEIRA -- nunca uma por movimento.
    curve_logs_by_movement: dict[str, list] = {}
    for log in PublicWorkoutLoadLog.objects.filter(
        account_id=account_id, set_role__in=_CURVE_AND_TREND_ROLES,
    ).order_by('movement_slug', 'performed_on', 'created_at'):
        curve_logs_by_movement.setdefault(log.movement_slug, []).append(log)

    legacy_logs_by_movement: dict[str, list] = {}
    for log in PublicWorkoutLoadLog.objects.filter(account_id=account_id).filter(
        Q(set_role=SetRole.LEGACY_UNKNOWN) | Q(set_role__isnull=True)
    ).order_by('movement_slug', 'performed_on'):
        legacy_logs_by_movement.setdefault(log.movement_slug, []).append(log)

    movement_slugs = set(curve_logs_by_movement) | set(legacy_logs_by_movement)
    snapshots = {}
    for movement_slug in movement_slugs:
        effective = effective_top_sets_by_day(curve_logs_by_movement.get(movement_slug, []))
        windowed = [log for log in effective if log.performed_on >= window_start]
        latest = effective[-1] if effective else None

        all_legacy = legacy_logs_by_movement.get(movement_slug, [])
        # legacy_points respeita a MESMA janela de 90 dias do eixo -- um
        # ponto de 6 meses atrás não cabe no SVG atual. has_legacy_history
        # NÃO filtra: o aluno vê "seu histórico está salvo" mesmo que nada
        # caiba visualmente na janela corrente.
        legacy_windowed = [log for log in all_legacy if log.performed_on >= window_start]

        # DELEGA pro one_rep_max.py já corrigido (§7.7) -- nunca reimplementa
        # estimativa/tendência aqui. A MESMA effective_top_sets_by_day usada
        # aqui é a que `_weekly_best_estimates` chama, então curva e
        # tendência nunca mais discordam sobre qual registro do dia vale.
        trend = detect_one_rep_max_trend_from_logs(
            movement_slug=movement_slug,
            logs=curve_logs_by_movement.get(movement_slug, []),
            as_of=as_of,
        )
        one_rep_max = (
            estimate_one_rep_max(weight_kg=latest.weight_kg, reps=latest.reps, rir=latest.rir)
            if latest else None
        )

        snapshots[movement_slug] = ProgressSnapshot(
            latest_top_set=_to_point(latest) if latest else None,
            curve_points=[_to_point(log) for log in windowed],
            legacy_points=[_to_point(log) for log in legacy_windowed],
            has_legacy_history=bool(all_legacy),
            # Uma escala em kg governa os dots legados e a curva. Os pontos
            # legados continuam sem conexão e com estilo neutro; incluí-los
            # no alcance vertical evita recortar valores fora da faixa dos
            # top sets e mantém os rótulos do eixo verdadeiros.
            y_scale=_rounded_scale([
                log.weight_kg for log in [*windowed, *legacy_windowed]
                if log.weight_kg is not None
            ]),
            trend_signal=trend.label,
            weekly_estimates_kg=trend.weekly_estimates_kg,
            as_of=as_of,
            one_rep_max=one_rep_max,
        )
    return snapshots


__all__ = ['ProgressPoint', 'ProgressSnapshot', 'build_progress_snapshots']
