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
    efetivas) — o resto nao entra na tendencia."""
    from .models import PublicWorkoutLoadLog

    logs = PublicWorkoutLoadLog.objects.filter(account_id=account_id, movement_slug=movement_slug).order_by(
        'performed_on'
    )

    best_by_week: dict[date, float] = {}
    for log in logs:
        estimate = estimate_one_rep_max(weight_kg=log.weight_kg, reps=log.reps, rir=log.rir)
        if estimate is None:
            continue
        week = _week_start(log.performed_on)
        if week not in best_by_week or estimate.value_kg > best_by_week[week]:
            best_by_week[week] = estimate.value_kg

    return sorted(best_by_week.items())


def detect_one_rep_max_trend(*, account_id: int, movement_slug: str) -> OneRepMaxTrend:
    """Platô/queda de 1RM sobre uma janela de 3 semanas — v1 deterministica
    (ver PONTOS CRITICOS no topo do arquivo pros limiares).

    - `insufficient_data`: menos de 3 semanas com estimativa valida.
    - `declining`: ultima semana da janela cai 5%+ abaixo do pico da janela
      (fadiga acumulada — gatilho de deload mais confiavel que "to cansado").
    - `plateau`: as 3 semanas ficam dentro de uma banda de 2.5% da media —
      1RM estavel mesmo que a carga levantada tenha subido.
    - `improving`: nenhum dos dois — a janela mostra progresso real.
    """
    weekly = _weekly_best_estimates(account_id=account_id, movement_slug=movement_slug)

    if len(weekly) < _TREND_WINDOW_WEEKS:
        return OneRepMaxTrend(movement_slug=movement_slug, label='insufficient_data', weekly_estimates_kg=())

    window = weekly[-_TREND_WINDOW_WEEKS:]
    values = tuple(value for _week, value in window)

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
    'estimate_one_rep_max',
]
