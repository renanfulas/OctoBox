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
    feeder antes da Top) e só quando a faixa do treinador NÃO cruza a da
    fase (8-10 numa semana de Adaptação 12-15 vira 12-15; 6-10 numa de
    Intensidade 3-6 fica 6-10). Acessório mantém a faixa do treinador.
  * RIR alvo das séries de trabalho = RIR da fase. Exceção: no Teste só a
    ÚLTIMA série de trabalho vira AMRAP (RIR 0) — é um teste de retenção
    com AMRAP único, não falha em todas as séries.
- Reps ESCRITAS PELO TREINADOR para a semana (planilha `weeks_table`, ex.:
  "8-12 reps") vencem a faixa do perfil da fase nos movimentos principais,
  inclusive em semanas da fase de referência. Achado real: o "Peak" da
  Milene é 8-12 reps (o perfil canônico diria 1-3) e a "Adaptação" do Bruno
  é 8-10 (o perfil diria 12-15).
- Séries por tempo (isometria) e registro livre não mudam.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import date

from .periodization import PHASE_PROFILES, PhaseProfile, coach_week_reps, current_week_number

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


def week_reps_override(payload: dict | None, *, on: date | None = None) -> tuple[int, int] | None:
    """Reps da planilha do treinador para a semana de `on` (ver `coach_week_reps`)."""
    return coach_week_reps(payload, current_week_number(payload or {}, today=on))


def _disjoint(low, high, phase_low, phase_high) -> bool:
    """Faixa do treinador fora da faixa da fase. Se já se cruzam (6-10 numa
    semana de Intensidade 3-6), a escolha do treinador é compatível e fica."""
    if low is None:
        return False
    high = high or low
    return high < phase_low or low > phase_high


def _scaled_count(count: int, ratio: float) -> int:
    value = count * ratio
    value = math.ceil(value - 1e-9) if ratio < 1 else round(value)
    return max(1, int(value))


def apply_phase_to_series(series: list[dict], *, phase: PhaseProfile | None,
                          reference: PhaseProfile | None,
                          week_reps: tuple[int, int] | None = None,
                          paired_sides: bool = False) -> list[dict]:
    if not series or phase is None or reference is None:
        return series
    same_phase = phase.key == reference.key
    if same_phase and week_reps is None:
        return series
    if series[0].get('role') == 'legacy_unknown':
        return series

    is_main_lift = any(row.get('role') in _LEAD_IN_ROLES for row in series)
    if same_phase and not is_main_lift:
        return series
    ratio = 1.0 if same_phase else phase.sets_multiplier / reference.sets_multiplier
    reps_min, reps_max = week_reps or phase.reps_target_range

    result: list[dict] = []
    index = 0
    while index < len(series):
        row = series[index]
        role = row.get('role')
        if role == 'max_set' and phase.key == 'deload' and not same_phase:
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
        if paired_sides and len(group) % 2 == 0:
            # "3× 8 por lado" publicado como 6 linhas alternadas: escala por lado
            # para nunca sobrar série de um lado só (deload: 2 por lado = 4).
            target = 2 * _scaled_count(len(group) // 2, ratio)
            per_side = True
        else:
            target = _scaled_count(len(group), ratio)
            per_side = False
        for ordinal in range(target):
            base = dict(group[min(ordinal, len(group) - 1)])
            if ordinal >= len(group):
                base['required'] = group[-1].get('required', True)
            if 'stage_ordinal' in base:
                base['stage_ordinal'] = ordinal + 1
            if is_main_lift and (week_reps is not None or _disjoint(
                    base.get('reps'), base.get('reps_max'), reps_min, reps_max)):
                base['reps'], base['reps_max'] = reps_min, reps_max
            if not same_phase:
                if phase.key == 'test':
                    # AMRAP único na última série; as outras seguem o RIR da referência.
                    last = ordinal == target - 1
                    base['rir_target'] = 0.0 if last else (base.get('rir_target') or reference.rir_target)
                    if last:
                        base['amrap'] = True
                else:
                    base['rir_target'] = phase.rir_target
            base['phase_adjusted'] = phase.key
            if per_side:
                base['per_side'] = True
            result.append(base)

    for number, row in enumerate(result, start=1):
        row['set_number'] = number
    return result


def _fmt_rir(value: float) -> str:
    return f'{value:g}'.replace('.', ',')


def phase_week_note(series: list[dict], *, phase: PhaseProfile | None,
                    reference: PhaseProfile | None) -> str:
    """Linha curta para o cartão: o que mudou nesta semana. '' se nada mudou."""
    if phase is None or reference is None:
        return ''
    work = [row for row in series if row.get('phase_adjusted')]
    if not work:
        return ''
    reps, reps_max = work[0].get('reps'), work[0].get('reps_max')
    reps_text = ''
    if reps is not None:
        reps_text = f' · {reps}–{reps_max} reps' if reps_max and reps_max != reps else f' · {reps} reps'
    count = len(work) // 2 if work[0].get('per_side') else len(work)
    label = 'série' if count == 1 else 'séries'
    side = ' por lado' if work[0].get('per_side') else ''
    if phase.key == reference.key:
        rir_text = ''
    elif phase.key == 'test':
        rir_text = ' · última série AMRAP (RIR 0)'
    else:
        rir_text = f' · RIR {_fmt_rir(phase.rir_target)}'
    return f'Esta semana ({phase.label}): {count} {label} de trabalho{side}{reps_text}{rir_text}'


__all__ = ['apply_phase_to_series', 'phase_week_note', 'reference_phase', 'week_reps_override']
