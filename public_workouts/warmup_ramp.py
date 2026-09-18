"""
ARQUIVO: ramp de aquecimento (Prep/Feeder) em kg, relativo ao peso do Top
set (Onda B3+ do CORDA — "carga sugerida", extensão pedida pelo Renan:
"a Ramp, e a sincronia com a periodização dessas cargas").

POR QUE ELE EXISTE:
- Prep/Feeder são séries de aquecimento ESPECÍFICO antes do Top — já
  segmentadas no `reps_spec` (`"2×Prep → 1×Feeder → 3×Top (6-8)"`,
  `templatetags/public_workouts_extras.py::reps_phases`) mas sem peso
  nenhum sugerido até agora. A carga de cada uma é uma FRAÇÃO da carga do
  Top set — nunca uma fase de periodização independente, por isso mora
  num módulo separado de `periodization.py`: são dois conceitos de
  "fase" já distintos no código e não podem se confundir — `reps_phases`/
  este módulo tratam do estágio de UM exercício (Prep/Feeder/Top/Max);
  `periodization.PHASE_PROFILES` trata do mesociclo inteiro (Adaptação/
  Volume/.../Deload).
- Sincronia com a periodização é automática POR CONSTRUÇÃO, não por
  código extra: o ramp escala a partir do `top_weight_kg` que
  `movement_load_display` já calculou pra ESTA semana (fase progressiva
  quando existe, senão %RM explícito ou estimativa por texto). Se o Top
  muda de semana pra semana, o ramp muda junto automaticamente — nunca há
  um segundo cálculo de progressão paralelo e desalinhado.

PONTOS CRÍTICOS:
- Percentuais têm fonte real, não são chute: ~40-55% pro Prep, ~60-80%
  pro Feeder — de protocolos de "ramp-up sets"/"feeder sets" (BarBend,
  StrongFirst): "once you reach 50-60% of your working set weight, the
  rest of your ramp-up sets should be 10-15% increases per set" e "any
  set at or above ~85-90% counts as a working set" (ou seja, o Feeder
  precisa ficar visivelmente abaixo de 85%, nunca virar um segundo Top).
  Top usa o próprio peso (já é a referência, ≥85-90% por definição). Max
  (AMRAP depois do Top) usa a MESMA carga do último Top set — prática
  padrão de testar quantas reps saem no mesmo peso, não uma fração nova.
- Ramp DENTRO do próprio estágio (ex.: "2×Prep" = 2 sets) interpola
  linearmente do piso ao teto da faixa — 1 set só usa o meio da faixa
  (não há "ramp" possível com 1 ponto só).
- `extract_leading_set_count` nunca devolve 0 (mínimo 1) — mesmo sem um
  prefixo "N×" reconhecível (formato incomum), sempre rampa pelo menos 1
  set em vez de devolver uma lista vazia sem explicação.
"""

from __future__ import annotations

import re

_STAGE_PCT_RANGES = {
    'prep': (0.40, 0.55),
    'feeder': (0.60, 0.80),
}

_LEADING_SET_COUNT_RE = re.compile(r'^(\d+)(?:\s*-\s*(\d+))?\s*[×x]')

_LOAD_ROUNDING_KG = 2.5


def _round_to_nearest_load(value: float) -> float:
    return round(value / _LOAD_ROUNDING_KG) * _LOAD_ROUNDING_KG


def extract_leading_set_count(segment: str) -> int:
    """'2-3× Prep' -> 2 (média arredondada da faixa). '1× Feeder' -> 1.
    Sem prefixo "N×" reconhecível -> 1 (nunca 0)."""
    match = _LEADING_SET_COUNT_RE.match(segment.strip())
    if not match:
        return 1
    low = int(match.group(1))
    high = int(match.group(2)) if match.group(2) else low
    return max(1, round((low + high) / 2))


def stage_ramp_kg(*, stage: str, set_count: int, top_weight_kg: float) -> list[float]:
    """Pesos crescentes pro estágio `stage` (prep/feeder/top/max),
    `set_count` sets, relativos a `top_weight_kg`. `top`/`max` sempre
    devolvem `[top_weight_kg] * set_count` (Top é a própria referência;
    Max/AMRAP usa a mesma carga do último Top set). `prep`/`feeder`
    interpolam linearmente dentro da faixa científica (ver docstring do
    módulo). Lista vazia pra qualquer outro estágio (ex.: 'plain') ou sem
    `top_weight_kg`."""
    if not top_weight_kg:
        return []

    set_count = max(1, set_count)

    if stage in ('top', 'max'):
        return [top_weight_kg] * set_count

    pct_range = _STAGE_PCT_RANGES.get(stage)
    if pct_range is None:
        return []

    low, high = pct_range
    weights = []
    for index in range(set_count):
        pct = (low + high) / 2 if set_count == 1 else low + (high - low) * index / (set_count - 1)
        weights.append(_round_to_nearest_load(pct * top_weight_kg))
    return weights


__all__ = ['extract_leading_set_count', 'stage_ramp_kg']
