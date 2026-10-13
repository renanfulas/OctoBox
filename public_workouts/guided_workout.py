"""Prescricao executavel por serie para o treino guiado Curva."""

from __future__ import annotations

import re
import math

from .warmup_ramp import stage_ramp_kg
from .guided_prescription import expand_guided_prescription

_SET_PREFIX = re.compile(r'^\s*\d+(?:\s*[-–]\s*\d+)?\s*[x×]', re.I)
_SET_RANGE = re.compile(r'^\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*[x×]', re.I)

_PHASE_PATTERNS = (
    ('prep', re.compile(r'\bprep', re.I)),
    ('feeder', re.compile(r'\bfeeder', re.I)),
    ('top', re.compile(r'\btop\b', re.I)),
    ('max', re.compile(r'\bamrap\b|\bmax\b', re.I)),
)


def _phase(segment: str) -> str:
    return next((name for name, pattern in _PHASE_PATTERNS if pattern.search(segment)), 'plain')


def _freeform_series() -> list[dict]:
    # Um convite para registrar, não uma série prescrita. O aluno escolhe
    # quantas fez; o servidor limita e rotula esses fatos como livres.
    return [{
        'stage': 'freeform', 'role': 'legacy_unknown', 'set_number': 1,
        'reps': None, 'reps_max': None, 'weight_kg': None, 'required': False,
    }]


def build_legacy_series(movement: dict, top_weight_kg=None) -> list[dict]:
    """Adapta texto publicado antes do contrato estruturado."""
    spec = str((movement or {}).get('reps_spec') or '').strip()
    if not spec:
        return _freeform_series()
    segments = [part.strip() for part in spec.split('→') if part.strip()] or [spec]
    result = []
    try:
        anchor = float(top_weight_kg) if top_weight_kg is not None else None
    except (TypeError, ValueError):
        anchor = None
    if anchor is not None and (not math.isfinite(anchor) or anchor < 0):
        anchor = None
    for segment in segments:
        if not _SET_PREFIX.match(segment):
            return _freeform_series()
        stage = _phase(segment)
        count_match = _SET_RANGE.match(segment)
        minimum = int(count_match.group(1))
        set_count = int(count_match.group(2) or minimum)
        if minimum < 1 or set_count < minimum:
            return _freeform_series()
        if set_count > 30 or len(result) + set_count > 100:
            return _freeform_series()
        reps_match = re.search(r'\((\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\)', segment)
        if reps_match is None:
            after_count = re.sub(r'^\s*\d+(?:\s*[-–]\s*\d+)?\s*[x×]\s*', '', segment, flags=re.I)
            after_count = re.split(r'\bRIR\b|\bRPE\b', after_count, maxsplit=1, flags=re.I)[0]
            reps_match = re.search(
                r'(?:^|\b)(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*(?:reps?|repetições)?\b',
                after_count, flags=re.I,
            )
            if reps_match and re.match(r'^\s*(?:s|seg|segundos?|min|minutos?)\b', after_count[reps_match.end():], re.I):
                reps_match = None
        reps_target = int(reps_match.group(1)) if reps_match else None
        reps_max = int(reps_match.group(2)) if reps_match and reps_match.group(2) else reps_target
        if reps_max is not None and reps_max < reps_target:
            return _freeform_series()
        weights = stage_ramp_kg(stage=stage, set_count=set_count, top_weight_kg=anchor)
        role = {'prep': 'warmup', 'feeder': 'feeder', 'top': 'top_set', 'max': 'max_set'}.get(stage, 'top_set')
        for index in range(set_count):
            result.append({
                'stage': stage, 'role': role, 'set_number': len(result) + 1,
                'required': index < minimum,
                'reps': reps_target, 'reps_max': reps_max,
                'weight_kg': weights[index] if index < len(weights) else anchor,
            })
    return result


def build_guided_series(movement: dict, top_weight_kg=None, one_rep_max_kg=None) -> list[dict]:
    """Usa a prescrição publicada; texto legado é somente fallback."""
    guided = (movement or {}).get('guided_prescription')
    if guided is not None:
        return expand_guided_prescription(
            guided, top_weight_kg=top_weight_kg, one_rep_max_kg=one_rep_max_kg,
        )
    return build_legacy_series(movement, top_weight_kg)
