"""Séries, repetições e RIR da SEMANA, derivados da fase da periodização.

POR QUE EXISTE: a prescrição publicada (`reps_spec`/`guided_prescription`)
é escrita uma vez e valia igual em todas as semanas — o banner dizia
"Deload · 8–10 reps · RIR 4,5" e o cartão continuava "3× Top (10-12)".

REGRA (relativa ao que o treinador escreveu, nunca absoluta):
- A prescrição publicada vale para a FASE DE REFERÊNCIA do programa (a fase
  mais frequente fora o deload — é para ela que o treinador escreveu).
- Na fase de referência nada muda.
- Em outra fase:
  * séries de trabalho (`top_set`) = publicadas × (multiplicador da fase /
    multiplicador da referência); redução arredonda para cima, aumento
    arredonda normal, mínimo 1. Aquecimento/feeder nunca mudam.
  * no deload a série AMRAP/max sai (semana de recuperação).
  * repetições: só nos movimentos principais (os que têm aquecimento ou
    feeder antes da Top) — viram a faixa da fase. Acessório mantém a faixa
    do treinador (12-15 de elevação lateral não vira 3-6 em Intensidade).
  * RIR alvo das séries de trabalho = RIR da fase.
- Séries por tempo (isometria) e registro livre não mudam.
"""

from __future__ import annotations

import math
from collections import Counter

from .periodization import PHASE_PROFILES, PhaseProfile

_WORK_ROLES = {'top_set'}
_LEAD_IN_ROLES = {'warmup', 'feeder'}


def reference_phase(payload: dict | None) -> PhaseProfile | None:
    weeks = ((payload or {}).get('periodization') or {}).get('weeks') or []
    keys = [row.get('phase_type') for row in weeks if row.get('phase_type') in PHASE_PROFILES]
    if not keys:
        return None
    non_deload = [key for key in keys if key != 'deload'] or keys
    counts = Counter(non_deload)
    top = max(counts.values())
    # Empate: a primeira fase que aparece no mesociclo.
    key = next(key for key in non_deload if counts[key] == top)
    return PHASE_PROFILES[key]


def _scaled_count(count: int, ratio: float) -> int:
    value = count * ratio
    value = math.ceil(value - 1e-9) if ratio < 1 else round(value)
    return max(1, int(value))


def apply_phase_to_series(series: list[dict], *, phase: PhaseProfile | None,
                          reference: PhaseProfile | None) -> list[dict]:
    if not series or phase is None or reference is None or phase.key == reference.key:
        return series
    if series[0].get('role') == 'legacy_unknown':
        return series

    is_main_lift = any(row.get('role') in _LEAD_IN_ROLES for row in series)
    ratio = phase.sets_multiplier / reference.sets_multiplier
    reps_min, reps_max = phase.reps_target_range

    result: list[dict] = []
    index = 0
    while index < len(series):
        row = series[index]
        role = row.get('role')
        if role == 'max_set' and phase.key == 'deload':
            index += 1
            continue
        if role not in _WORK_ROLES or row.get('hold_seconds') is not None:
            result.append(dict(row))
            index += 1
            continue
        # Agrupa as séries de trabalho consecutivas do mesmo estágio.
        stage = row.get('stage')
        group = []
        while (index < len(series) and series[index].get('role') in _WORK_ROLES
               and series[index].get('stage') == stage and series[index].get('hold_seconds') is None):
            group.append(series[index])
            index += 1
        target = _scaled_count(len(group), ratio)
        for ordinal in range(target):
            base = dict(group[min(ordinal, len(group) - 1)])
            if ordinal >= len(group):
                base['required'] = group[-1].get('required', True)
            if 'stage_ordinal' in base:
                base['stage_ordinal'] = ordinal + 1
            if is_main_lift:
                base['reps'], base['reps_max'] = reps_min, reps_max
            base['rir_target'] = phase.rir_target
            base['phase_adjusted'] = phase.key
            result.append(base)

    for number, row in enumerate(result, start=1):
        row['set_number'] = number
    return result


def _fmt_rir(value: float) -> str:
    return f'{value:g}'.replace('.', ',')


def phase_week_note(series: list[dict], *, phase: PhaseProfile | None,
                    reference: PhaseProfile | None) -> str:
    """Linha curta para o cartão: o que mudou nesta semana. '' se nada mudou."""
    if phase is None or reference is None or phase.key == reference.key:
        return ''
    work = [row for row in series if row.get('phase_adjusted')]
    if not work:
        return ''
    reps, reps_max = work[0].get('reps'), work[0].get('reps_max')
    reps_text = ''
    if reps is not None:
        reps_text = f' · {reps}–{reps_max} reps' if reps_max and reps_max != reps else f' · {reps} reps'
    label = 'série' if len(work) == 1 else 'séries'
    return f'Esta semana ({phase.label}): {len(work)} {label} de trabalho{reps_text} · RIR {_fmt_rir(phase.rir_target)}'


__all__ = ['apply_phase_to_series', 'phase_week_note', 'reference_phase']
