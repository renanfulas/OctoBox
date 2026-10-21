"""Contrato executável de séries Curva, separado do parser de texto legado."""

from __future__ import annotations

import math
import re
from decimal import Decimal

ROLES = frozenset({'warmup', 'feeder', 'top_set', 'max_set', 'freeform'})
LOAD_RULES = frozenset({'manual', 'fixed_kg', 'percent_of_top', 'percent_of_rm', 'suggested_top'})
_STAGE_ID = re.compile(r'^[a-z][a-z0-9_-]{0,31}$')


def _number(value, *, minimum, maximum):
    return (
        isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
        and math.isfinite(float(value)) and minimum <= value <= maximum
    )


def validate_guided_prescription(value, *, path='guided_prescription') -> list[str]:
    """Valida apenas o contrato novo; programas antigos continuam válidos."""
    if not isinstance(value, dict):
        return [f'{path}: precisa ser um objeto']
    errors = []
    if value.get('version') != 1 or isinstance(value.get('version'), bool):
        errors.append(f'{path}.version: precisa ser 1')
    stages = value.get('stages')
    if not isinstance(stages, list) or not stages:
        return errors + [f'{path}.stages: lista não vazia obrigatória']
    if len(stages) > 20:
        errors.append(f'{path}.stages: máximo de 20 etapas')
    seen = set()
    total = 0
    for index, stage in enumerate(stages):
        prefix = f'{path}.stages[{index}]'
        if not isinstance(stage, dict):
            errors.append(f'{prefix}: precisa ser um objeto')
            continue
        stage_id = stage.get('stage_id')
        if not isinstance(stage_id, str) or not _STAGE_ID.fullmatch(stage_id):
            errors.append(f'{prefix}.stage_id: identificador inválido')
        elif stage_id in seen:
            errors.append(f'{prefix}.stage_id: identificador repetido')
        else:
            seen.add(stage_id)
        role = stage.get('role')
        if not isinstance(role, str) or role not in ROLES:
            errors.append(f'{prefix}.role: papel inválido')
        minimum, maximum = stage.get('min_sets'), stage.get('max_sets')
        if not isinstance(minimum, int) or isinstance(minimum, bool) or not 0 <= minimum <= 30:
            errors.append(f'{prefix}.min_sets: inteiro entre 0 e 30')
        if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 30:
            errors.append(f'{prefix}.max_sets: inteiro entre 1 e 30')
        if isinstance(minimum, int) and isinstance(maximum, int) and minimum > maximum:
            errors.append(f'{prefix}: min_sets maior que max_sets')
        if isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0:
            total += maximum
        if role == 'freeform' and (minimum != 1 or maximum != 1 or len(stages) != 1):
            errors.append(f'{prefix}: registro livre exige uma única etapa 1×')
        reps_min, reps_max = stage.get('reps_min'), stage.get('reps_max')
        if reps_min is not None and (not isinstance(reps_min, int) or isinstance(reps_min, bool) or not 1 <= reps_min <= 999):
            errors.append(f'{prefix}.reps_min: inteiro entre 1 e 999 ou null')
        if reps_max is not None and (not isinstance(reps_max, int) or isinstance(reps_max, bool) or not 1 <= reps_max <= 999):
            errors.append(f'{prefix}.reps_max: inteiro entre 1 e 999 ou null')
        if reps_max is not None and reps_min is None:
            errors.append(f'{prefix}.reps_max: exige reps_min')
        if isinstance(reps_min, int) and isinstance(reps_max, int) and reps_max < reps_min:
            errors.append(f'{prefix}: reps_max menor que reps_min')
        # Isometria (prancha): a série é medida em segundos, não em repetições.
        hold_min, hold_max = stage.get('hold_seconds_min'), stage.get('hold_seconds_max')
        for name, value in (('hold_seconds_min', hold_min), ('hold_seconds_max', hold_max)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 3600):
                errors.append(f'{prefix}.{name}: inteiro entre 1 e 3600 ou null')
        if hold_max is not None and hold_min is None:
            errors.append(f'{prefix}.hold_seconds_max: exige hold_seconds_min')
        if isinstance(hold_min, int) and isinstance(hold_max, int) and hold_max < hold_min:
            errors.append(f'{prefix}: hold_seconds_max menor que hold_seconds_min')
        if hold_min is not None and reps_min is not None:
            errors.append(f'{prefix}: série por tempo não leva repetições')
        rir = stage.get('rir_target')
        if rir is not None and not _number(rir, minimum=0, maximum=10):
            errors.append(f'{prefix}.rir_target: número entre 0 e 10 ou null')
        rest = stage.get('rest_seconds')
        if not isinstance(rest, int) or isinstance(rest, bool) or not 0 <= rest <= 900:
            errors.append(f'{prefix}.rest_seconds: inteiro entre 0 e 900')
        rule = stage.get('load_rule')
        if not isinstance(rule, dict) or not isinstance(rule.get('kind'), str) or rule['kind'] not in LOAD_RULES:
            errors.append(f'{prefix}.load_rule.kind: regra inválida')
            continue
        kind = rule['kind']
        if kind == 'fixed_kg' and not _number(rule.get('value_kg'), minimum=0, maximum=9999.99):
            errors.append(f'{prefix}.load_rule.value_kg: kg inválido')
        if kind == 'percent_of_rm' and not _number(rule.get('percent'), minimum=1, maximum=200):
            errors.append(f'{prefix}.load_rule.percent: percentual inválido')
        if kind == 'percent_of_top':
            low, high = rule.get('start_percent'), rule.get('end_percent')
            if not _number(low, minimum=1, maximum=100) or not _number(high, minimum=1, maximum=100) or low > high:
                errors.append(f'{prefix}.load_rule: faixa percentual inválida')
        step = rule.get('rounding_step_kg')
        if step is not None and not _number(step, minimum=0.01, maximum=100):
            errors.append(f'{prefix}.load_rule.rounding_step_kg: passo inválido')
    if total > 100:
        errors.append(f'{path}: máximo de 100 séries por movimento')
    return errors


def _rounded(value, step):
    return round(float(value) / float(step)) * float(step)


def expand_guided_prescription(value: dict, *, top_weight_kg=None, one_rep_max_kg=None) -> list[dict]:
    """Expande um contrato validado; sugestão de kg nunca é fato realizado."""
    errors = validate_guided_prescription(value)
    if errors:
        raise ValueError('; '.join(errors))
    series = []
    for stage in value['stages']:
        rule = stage['load_rule']
        count = stage['max_sets']
        step = rule.get('rounding_step_kg', 2.5)
        for ordinal in range(1, count + 1):
            kind = rule['kind']
            weight = None
            top_factor = None
            if kind == 'fixed_kg':
                weight = rule['value_kg']
            elif kind == 'suggested_top':
                top_factor = 1.0
                if _number(top_weight_kg, minimum=0, maximum=9999.99):
                    weight = _rounded(top_weight_kg, step)
            elif kind == 'percent_of_rm' and _number(one_rep_max_kg, minimum=0, maximum=9999.99):
                weight = _rounded(float(one_rep_max_kg) * rule['percent'] / 100, step)
            elif kind == 'percent_of_top':
                low = rule['start_percent']
                high = rule['end_percent']
                percent = (low + high) / 2 if count == 1 else low + (high - low) * (ordinal - 1) / (count - 1)
                top_factor = percent / 100
                if _number(top_weight_kg, minimum=0, maximum=9999.99):
                    weight = _rounded(float(top_weight_kg) * top_factor, step)
            series.append({
                'stage': stage['stage_id'], 'stage_id': stage['stage_id'],
                'stage_ordinal': ordinal,
                'role': 'legacy_unknown' if stage['role'] == 'freeform' else stage['role'],
                'set_number': len(series) + 1,
                'required': ordinal <= stage['min_sets'],
                'reps': stage.get('reps_min'), 'reps_max': stage.get('reps_max') or stage.get('reps_min'),
                'rir_target': stage.get('rir_target'), 'rest_seconds': stage['rest_seconds'],
                'weight_kg': weight, 'load_source': kind,
                'top_factor': top_factor, 'rounding_step_kg': step,
                'hold_seconds': stage.get('hold_seconds_min'),
                'hold_seconds_max': stage.get('hold_seconds_max') or stage.get('hold_seconds_min'),
            })
    return series


def propose_guided_prescription(movement: dict) -> dict | None:
    """Gera proposta para revisão; não altera o draft nem publica automaticamente."""
    from .guided_text_proposal import propose_stage_first_text
    from .guided_workout import build_legacy_series

    stage_first = propose_stage_first_text(movement)
    if stage_first is not None:
        return stage_first

    rows = build_legacy_series(movement)
    if not rows or rows[0]['role'] == 'legacy_unknown':
        return None
    stages = []
    for row in rows:
        if stages and stages[-1]['role'] == row['role'] and stages[-1]['_stage'] == row['stage']:
            stage = stages[-1]
            stage['max_sets'] += 1
            stage['min_sets'] += int(row['required'])
            continue
        role = row['role']
        rule = {'kind': 'manual'}
        if row.get('hold_seconds') is not None:
            # Isometria: proposta por tempo, sem carga derivada da Top.
            stages.append({
                'stage_id': f'{row["stage"]}-{len(stages) + 1}', '_stage': row['stage'],
                'role': role, 'min_sets': int(row['required']), 'max_sets': 1,
                'reps_min': None, 'reps_max': None,
                'hold_seconds_min': row['hold_seconds'], 'hold_seconds_max': row['hold_seconds_max'],
                'rest_seconds': 60, 'load_rule': rule,
            })
            continue
        if role == 'warmup':
            rule = {'kind': 'percent_of_top', 'start_percent': 40, 'end_percent': 55}
        elif role == 'feeder':
            rule = {'kind': 'percent_of_top', 'start_percent': 60, 'end_percent': 80}
        elif role in {'top_set', 'max_set'}:
            rule = {'kind': 'suggested_top'}
        stages.append({
            'stage_id': f'{row["stage"]}-{len(stages) + 1}', '_stage': row['stage'],
            'role': role, 'min_sets': int(row['required']), 'max_sets': 1,
            'reps_min': row['reps'], 'reps_max': row['reps_max'],
            'rest_seconds': 90, 'load_rule': rule,
        })
    for stage in stages:
        del stage['_stage']
    return {'version': 1, 'stages': stages}
