"""
ARQUIVO: estimativa de 1RM e tendencia (plato/queda) do corredor de treinos
(Onda A3 do CORDA — docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- `build_student_package` (S2, public_workouts/services.py) deixava
  `one_rep_max_by_movement` vazio de proposito desde a Onda A1 — a formula
  em si (Brzycki/Epley/blend, faixa de confianca) ja estava especificada
  em docs/plans/public-workouts-produtizacao-plan.md (secao 4.4) antes
  mesmo deste arquivo existir: implementar aqui, nao inventar de novo.
- separa CALCULO PURO (estimate_one_rep_max — sem banco, testavel isolado,
  mesmo estilo de public_workouts/formulas.py) de LEITURA DE HISTORICO
  (detect_one_rep_max_trend — le PublicWorkoutLoadLog).

PONTOS CRITICOS:
- Reps EFETIVAS = reps + rir, nao reps cru. O corredor prescreve RIR 1-2;
  usar reps cru subestimaria sistematicamente (as formulas assumem falha
  concentrica, RIR 0). `rir` fracionario (Decimal) e arredondado pro
  inteiro mais proximo antes de somar — o dataclass abaixo (mesmo formato
  do plano) declara `effective_reps: int`.
- Acima de 15 reps efetivas devolve None: ali se mede resistencia a
  fadiga, nao forca maxima (mesma postura que formulas.py ja adota pra
  BF% — nunca finge precisao que a formula nao tem). Brzycki tambem
  divide por zero em 37 reps.
- NUNCA compara 1RM entre `movement_slug` diferentes — nem
  `detect_one_rep_max_trend` faz isso (uma chamada = um movimento so).
  Variacoes do mesmo padrao (ex.: hip-thrust-barbell vs -machine) sao
  slugs separados de proposito (F-D do plano) — misturar produziria
  numero falso.
- `detect_one_rep_max_trend` e a v1 deliberadamente simples (janela de 3
  semanas, limiares fixos documentados abaixo) — e sinal calculado pronto
  pra virar frase num review semanal (Onda 4.5 do plano: "platô de 3
  semanas no hip thrust"), nao uma extrapolacao estatistica sofisticada.
  Os limiares (2.5%/5%) sao um primeiro corte razoavel, nao uma decisao
  de treino fechada — ajustar aqui e mudar constante, nao arquitetura.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

MAX_EFFECTIVE_REPS = 15
_LOW_REP_CEILING = 6
_MODERATE_REP_CEILING = 10

_PLATEAU_BAND_PCT = 0.025  # janela de "sem mudanca real" — 2.5% do valor medio.
_DECLINE_THRESHOLD_PCT = 0.05  # queda de 5%+ do pico da janela = sinal de deload.
_TREND_WINDOW_WEEKS = 3


@dataclass(frozen=True)
class OneRepMaxEstimate:
    value_kg: float
    formula: str  # 'brzycki' | 'blend' | 'epley'
    confidence: str  # 'high' | 'moderate' | 'low'
    effective_reps: int


def _brzycki(*, weight_kg: float, effective_reps: int) -> float:
    return weight_kg * 36 / (37 - effective_reps)


def _epley(*, weight_kg: float, effective_reps: int) -> float:
    return weight_kg * (1 + effective_reps / 30)


def estimate_one_rep_max(*, weight_kg, reps, rir=0) -> OneRepMaxEstimate | None:
    """Estimativa de 1RM. Retorna None acima de 15 reps efetivas.

    | reps efetivas | formula                  | confianca |
    |----------------|--------------------------|-----------|
    | <= 6           | Brzycki                  | alta      |
    | 7-10           | media de Brzycki e Epley | moderada  |
    | 11-15          | Epley                    | baixa     |
    | > 15           | None                     | —         |
    """
    if weight_kg is None or reps is None:
        return None

    weight_kg = float(weight_kg)
    effective_reps = round(float(reps) + float(rir or 0))

    if effective_reps <= 0:
        return None
    if effective_reps > MAX_EFFECTIVE_REPS:
        return None

    if effective_reps <= _LOW_REP_CEILING:
        value_kg = _brzycki(weight_kg=weight_kg, effective_reps=effective_reps)
        formula = 'brzycki'
        confidence = 'high'
    elif effective_reps <= _MODERATE_REP_CEILING:
        value_kg = (
            _brzycki(weight_kg=weight_kg, effective_reps=effective_reps)
            + _epley(weight_kg=weight_kg, effective_reps=effective_reps)
        ) / 2
        formula = 'blend'
        confidence = 'moderate'
    else:
        value_kg = _epley(weight_kg=weight_kg, effective_reps=effective_reps)
        formula = 'epley'
        confidence = 'low'

    return OneRepMaxEstimate(
        value_kg=round(value_kg, 1), formula=formula, confidence=confidence, effective_reps=effective_reps
    )


_LOAD_ROUNDING_KG = 2.5


def estimate_working_weight_kg(*, one_rep_max_kg, target_reps, target_rir=0) -> float | None:
    """Inverso de `estimate_one_rep_max` -- dado um 1RM (estimado ou
    conhecido) e um alvo de reps+RIR pra um set de trabalho, devolve o
    peso a usar. MESMO corte de faixas de `estimate_one_rep_max` (Brzycki/
    blend/Epley invertidos algebricamente -- os 3 sao lineares em peso,
    entao invertem sem precisar de solver numerico). Arredonda pro
    multiplo de 2.5kg mais proximo (mesmo `step` do input de carga do
    aluno). `None` fora da faixa valida (>15 reps efetivas, igual
    `estimate_one_rep_max` -- ali se mede resistencia, nao forca maxima).

    Usado pelo Caminho 4 de `load_suggestion.py` (exercicio SEM fase
    canonica de periodizacao -- estima peso a partir do proprio reps_spec/
    rir_spec do exercicio). NAO usado pelo Caminho 3
    (`periodization.suggest_progressive_load_kg`) -- fase canonica ancora
    na ultima carga REAL registrada, nunca recalcula do zero contra 1RM
    estimado (ver docstring de periodization.py)."""
    if one_rep_max_kg is None or target_reps is None:
        return None

    one_rep_max_kg = float(one_rep_max_kg)
    effective_reps = round(float(target_reps) + float(target_rir or 0))

    if effective_reps <= 0 or effective_reps > MAX_EFFECTIVE_REPS:
        return None

    if effective_reps <= _LOW_REP_CEILING:
        raw_kg = one_rep_max_kg * (37 - effective_reps) / 36  # inverso de _brzycki
    elif effective_reps <= _MODERATE_REP_CEILING:
        brzycki_coeff = 36 / (37 - effective_reps)
        epley_coeff = 1 + effective_reps / 30
        raw_kg = one_rep_max_kg / ((brzycki_coeff + epley_coeff) / 2)  # inverso da media (linear em peso)
    else:
        raw_kg = one_rep_max_kg / (1 + effective_reps / 30)  # inverso de _epley

    return round(raw_kg / _LOAD_ROUNDING_KG) * _LOAD_ROUNDING_KG


@dataclass(frozen=True)
class OneRepMaxTrend:
    movement_slug: str
    label: str  # 'improving' | 'plateau' | 'declining' | 'insufficient_data'
    weekly_estimates_kg: tuple[float, ...]  # janela usada, mais antiga primeiro


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _weekly_best_estimates(*, account_id: int, movement_slug: str) -> list[tuple[date, float]]:
    """Melhor 1RM estimado por semana (segunda-feira como chave), mais
    recente por ultimo. So considera sets com estimativa valida (<=15 reps
    efetivas) — o resto nao entra na tendencia.

    Plano curva-grafico-hierarquia-e-set-role.md (Revisao 8, §7.7): filtra
    `set_role__in=_CURVE_AND_TREND_ROLES` no banco (nunca em Python) e
    aplica `effective_top_sets_by_day` — a MESMA dedup por dia que a curva
    principal usa. Isso mantém gráfico e tendência coerentes quando há
    mais de um registro no mesmo dia."""
    from .models import PublicWorkoutLoadLog
    from .progress_eligibility import _CURVE_AND_TREND_ROLES, effective_top_sets_by_day

    logs = PublicWorkoutLoadLog.objects.filter(
        account_id=account_id, movement_slug=movement_slug,
        set_role__in=_CURVE_AND_TREND_ROLES,
    ).order_by('performed_on')

    return _weekly_best_estimates_from_logs(movement_slug=movement_slug, logs=list(logs))


def _weekly_best_estimates_from_logs(*, movement_slug: str, logs: list) -> list[tuple[date, float]]:
    """Pure aggregation shared by the ORM entry point and batched snapshots."""
    from .progress_eligibility import effective_top_sets_by_day

    best_by_week: dict[date, float] = {}
    for log in effective_top_sets_by_day(logs):
        estimate = estimate_one_rep_max(weight_kg=log.weight_kg, reps=log.reps, rir=log.rir)
        if estimate is None:
            continue
        week = _week_start(log.performed_on)
        if week not in best_by_week or estimate.value_kg > best_by_week[week]:
            best_by_week[week] = estimate.value_kg

    return sorted(best_by_week.items())


def detect_one_rep_max_trend_from_logs(*, movement_slug: str, logs: list, as_of: date | None = None) -> OneRepMaxTrend:
    """Build the weekly signal from already fetched top sets."""
    from django.utils import timezone as django_timezone

    as_of = as_of or django_timezone.localdate()
    weekly = _weekly_best_estimates_from_logs(movement_slug=movement_slug, logs=logs)
    return _trend_from_weekly(movement_slug=movement_slug, weekly=weekly, as_of=as_of)


def detect_one_rep_max_trend(*, account_id: int, movement_slug: str, as_of: date | None = None) -> OneRepMaxTrend:
    """Platô/queda de 1RM sobre uma janela de 3 semanas — v1 deterministica
    (ver PONTOS CRITICOS no topo do arquivo pros limiares).

    - `insufficient_data`: menos de 3 semanas com estimativa valida, OU as
      3 semanas da janela nao sao CONSECUTIVAS (7 dias entre vizinhas —
      3 semanas espalhadas ao longo de 6 meses nao formam uma janela
      coesa), OU a ultima semana da janela nao e' RECENTE (mais de 14 dias
      de `as_of` — 3 semanas consecutivas de janeiro nao autorizam "Em
      evolução" se agora e' setembro). Reaproveita o rotulo
      `insufficient_data` existente em vez de criar um `stale` novo — ver
      plano §7.7 pro motivo.
    - `declining`: ultima semana da janela cai 5%+ abaixo do pico da janela
      (fadiga acumulada — gatilho de deload mais confiavel que "to cansado").
    - `plateau`: as 3 semanas ficam dentro de uma banda de 2.5% da media —
      1RM estavel mesmo que a carga levantada tenha subido.
    - `improving`: nenhum dos dois — a janela mostra progresso real.
    """
    from django.utils import timezone as django_timezone

    as_of = as_of or django_timezone.localdate()
    weekly = _weekly_best_estimates(account_id=account_id, movement_slug=movement_slug)
    return _trend_from_weekly(movement_slug=movement_slug, weekly=weekly, as_of=as_of)


def _trend_from_weekly(*, movement_slug: str, weekly: list[tuple[date, float]], as_of: date) -> OneRepMaxTrend:

    if len(weekly) < _TREND_WINDOW_WEEKS:
        return OneRepMaxTrend(movement_slug=movement_slug, label='insufficient_data', weekly_estimates_kg=())

    window = weekly[-_TREND_WINDOW_WEEKS:]
    weeks = [week for week, _value in window]
    values = tuple(value for _week, value in window)

    if any((weeks[i + 1] - weeks[i]).days != 7 for i in range(len(weeks) - 1)):
        return OneRepMaxTrend(movement_slug=movement_slug, label='insufficient_data', weekly_estimates_kg=())
    if (as_of - weeks[-1]).days > 14:
        return OneRepMaxTrend(movement_slug=movement_slug, label='insufficient_data', weekly_estimates_kg=())

    peak = max(values)
    latest = values[-1]
    if peak > 0 and (peak - latest) / peak >= _DECLINE_THRESHOLD_PCT:
        label = 'declining'
    else:
        average = sum(values) / len(values)
        band = average * _PLATEAU_BAND_PCT
        if average > 0 and (max(values) - min(values)) <= band:
            label = 'plateau'
        else:
            label = 'improving'

    return OneRepMaxTrend(movement_slug=movement_slug, label=label, weekly_estimates_kg=values)


__all__ = [
    'MAX_EFFECTIVE_REPS',
    'OneRepMaxEstimate',
    'OneRepMaxTrend',
    'detect_one_rep_max_trend',
    'detect_one_rep_max_trend_from_logs',
    'estimate_one_rep_max',
    'estimate_working_weight_kg',
]
