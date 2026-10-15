"""Leitura conservadora de etapas escritas antes da prescrição estruturada.

Este módulo só prepara propostas para revisão do treinador. O treino publicado
continua sendo interpretado pelo adaptador legado até uma aprovação explícita.
"""

from __future__ import annotations

import re


_STAGE = re.compile(
    r'^\s*(Preparat\.?|Prep|Feeder|Top(?:\s+Set)?|AMRAP|Max)\s+'
    r'(\d+)(?:\s*[-–]\s*(\d+))?\s*[x×]\s*(.*?)\s*$', re.I,
)
_REPS = re.compile(r'^(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?(?:\s*reps?)?$', re.I)
_SPLIT_REPS = re.compile(r'^(\d{1,3})\s*/\s*(\d{1,3})$')
_OPTIONAL = re.compile(r'^(?:Opcional|(.+?)\s+Opcional)\s*$', re.I)


def _stage_details(label: str):
    key = label.lower()
    if key.startswith(('preparat', 'prep')):
        return 'prep', 'warmup', {'kind': 'percent_of_top', 'start_percent': 40, 'end_percent': 55}
    if key == 'feeder':
        return 'feeder', 'feeder', {'kind': 'percent_of_top', 'start_percent': 60, 'end_percent': 80}
    if key.startswith('top'):
        return 'top', 'top_set', {'kind': 'suggested_top'}
    return 'max', 'max_set', {'kind': 'suggested_top'}


def propose_stage_first_text(movement: dict) -> dict | None:
    """Aceita somente segmentos inteiros e contagens explícitas.

Uma duração, instrução adicional ou repetição incompatível devolve None para
que o movimento inteiro permaneça livre; nunca descartamos uma parte do texto.
"""
    spec = str((movement or {}).get('reps_spec') or '').strip()
    if not spec or '→' not in spec and _STAGE.fullmatch(spec) is None:
        return None

    stages = []
    for segment in spec.split('→'):
        match = _STAGE.fullmatch(segment)
        if match is None:
            return None
        label, minimum_text, maximum_text, tail = match.groups()
        minimum = int(minimum_text)
        maximum = int(maximum_text or minimum_text)
        if not 1 <= minimum <= maximum <= 30:
            return None

        stage_key, role, load_rule = _stage_details(label)
        optional_match = _OPTIONAL.fullmatch(tail)
        optional = optional_match is not None
        if optional:
            tail = (optional_match.group(1) or '').strip()
        if optional and role != 'max_set':
            return None

        split_reps = _SPLIT_REPS.fullmatch(tail)
        if split_reps:
            if minimum != 2 or maximum != 2 or optional:
                return None
            reps_pairs = [(int(value), int(value)) for value in split_reps.groups()]
        elif tail.lower() == 'progressivo' and role == 'warmup':
            reps_pairs = [(None, None)]
        elif not tail and role == 'max_set' and optional:
            reps_pairs = [(None, None)]
        else:
            reps = _REPS.fullmatch(tail)
            if reps is None:
                return None
            low, high = int(reps.group(1)), int(reps.group(2) or reps.group(1))
            if not 1 <= low <= high <= 999:
                return None
            reps_pairs = [(low, high)]

        for pair_index, (reps_min, reps_max) in enumerate(reps_pairs):
            if reps_min is not None and not 1 <= reps_min <= 999:
                return None
            stage_load_rule = load_rule.copy()
            if split_reps and role == 'warmup':
                percent = 40 if pair_index == 0 else 55
                stage_load_rule.update(start_percent=percent, end_percent=percent)
            stages.append({
                'stage_id': f'{stage_key}-{len(stages) + 1}',
                'role': role,
                'min_sets': 0 if optional else (1 if split_reps else minimum),
                'max_sets': 1 if split_reps else maximum,
                'reps_min': reps_min,
                'reps_max': reps_max,
                'rest_seconds': 90,
                'load_rule': stage_load_rule,
            })

    return {'version': 1, 'stages': stages} if stages else None
