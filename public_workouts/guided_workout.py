"""Prescricao executavel por serie para o treino guiado Curva."""

from __future__ import annotations

import re
import math
import logging

from .warmup_ramp import stage_ramp_factors, stage_ramp_kg
from .guided_prescription import expand_guided_prescription
from .phase_prescription import apply_phase_to_series, reference_phase
from .rest_policy import phase_midpoint_percent, rest_seconds_for

logger = logging.getLogger(__name__)

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


_TIMED = re.compile(
    r'(?P<sets>\d{1,2})(?:\s*[-–]\s*(?P<sets_max>\d{1,2}))?\s*(?:[x×]|s[ée]ries?\s*[·:\-–]?)\s*'
    r'(?P<low>\d{1,4})(?:\s*[-–]\s*(?P<high>\d{1,4}))?\s*(?P<unit>segundos?|segs?|s|minutos?|min)\b',
    re.I,
)


def _timed_series(spec: str) -> list[dict] | None:
    """Isometria escrita como "2 séries · 30-45 seg" ou "Top Set 2× 45-60s": séries por tempo."""
    if '→' in spec:
        return None
    match = _TIMED.search(spec)
    if match is None:
        return None
    factor = 60 if match.group('unit').lower().startswith('min') else 1
    minimum = int(match.group('sets'))
    set_count = int(match.group('sets_max') or minimum)
    low = int(match.group('low')) * factor
    high = int(match.group('high') or match.group('low')) * factor
    if not 1 <= minimum <= set_count <= 30 or not 1 <= low <= high <= 3600:
        return None
    role = 'warmup' if _phase(spec) == 'prep' else 'top_set'
    return [{
        'stage': _phase(spec), 'role': role, 'set_number': index + 1, 'required': index < minimum,
        'reps': None, 'reps_max': None, 'weight_kg': None, 'top_factor': None, 'rounding_step_kg': 2.5,
        'hold_seconds': low, 'hold_seconds_max': high,
    } for index in range(set_count)]


def _apply_rest_policy(series: list[dict], movement: dict, *, top_weight_kg=None,
                       one_rep_max_kg=None, phase_profile=None) -> list[dict]:
    movement = movement or {}
    policy = movement.get('rest_policy')
    explicit = movement.get('rest_seconds')
    for row in series:
        fallback = explicit if isinstance(explicit, int) and not isinstance(explicit, bool) else 90
        if policy == 'percentage_of_1rm':
            percent = None
            try:
                if top_weight_kg is not None and one_rep_max_kg is not None and float(one_rep_max_kg) > 0:
                    percent = float(top_weight_kg) / float(one_rep_max_kg) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                percent = None
            if percent is None:
                percent = phase_midpoint_percent(phase_profile)
            row['rest_seconds'] = rest_seconds_for(
                role=row.get('role'), percent_of_1rm=percent, fallback_seconds=fallback,
            )
        elif isinstance(explicit, int) and not isinstance(explicit, bool):
            row['rest_seconds'] = explicit
        elif 'rest_seconds' not in row:
            row['rest_seconds'] = 90
    return series


def build_legacy_series(movement: dict, top_weight_kg=None, *, one_rep_max_kg=None,
                        phase_profile=None) -> list[dict]:
    """Adapta texto publicado antes do contrato estruturado."""
    spec = str((movement or {}).get('reps_spec') or '').strip()
    if not spec:
        return _apply_rest_policy(
            _freeform_series(), movement, top_weight_kg=top_weight_kg,
            one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
        )
    timed = _timed_series(spec)
    if timed is not None:
        return _apply_rest_policy(
            timed, movement, top_weight_kg=top_weight_kg,
            one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
        )
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
            return _apply_rest_policy(
                _freeform_series(), movement, top_weight_kg=top_weight_kg,
                one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
            )
        stage = _phase(segment)
        count_match = _SET_RANGE.match(segment)
        minimum = int(count_match.group(1))
        set_count = int(count_match.group(2) or minimum)
        if minimum < 1 or set_count < minimum:
            return _apply_rest_policy(
                _freeform_series(), movement, top_weight_kg=top_weight_kg,
                one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
            )
        if set_count > 30 or len(result) + set_count > 100:
            return _apply_rest_policy(
                _freeform_series(), movement, top_weight_kg=top_weight_kg,
                one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
            )
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
            return _apply_rest_policy(
                _freeform_series(), movement, top_weight_kg=top_weight_kg,
                one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
            )
        weights = stage_ramp_kg(stage=stage, set_count=set_count, top_weight_kg=anchor)
        role = {'prep': 'warmup', 'feeder': 'feeder', 'top': 'top_set', 'max': 'max_set'}.get(stage, 'top_set')
        factors = stage_ramp_factors(stage=stage, set_count=set_count)
        if role == 'top_set' and not factors:
            factors = [1.0] * set_count
        for index in range(set_count):
            result.append({
                'stage': stage, 'role': role, 'set_number': len(result) + 1,
                'required': index < minimum,
                'reps': reps_target, 'reps_max': reps_max,
                'weight_kg': weights[index] if index < len(weights) else anchor,
                'top_factor': factors[index] if index < len(factors) else None,
                'rounding_step_kg': 2.5,
            })
    return _apply_rest_policy(
        result, movement, top_weight_kg=top_weight_kg,
        one_rep_max_kg=one_rep_max_kg, phase_profile=phase_profile,
    )


def build_guided_series(movement: dict, top_weight_kg=None, one_rep_max_kg=None,
                        phase_profile=None, payload=None) -> list[dict]:
    """Usa a prescrição publicada; texto legado é somente fallback.

    Com `payload` (periodização canônica), séries/reps/RIR de trabalho são
    ajustados à fase da semana — ver `phase_prescription.py`."""
    guided = (movement or {}).get('guided_prescription')
    if guided is not None:
        series = None
        try:
            series = expand_guided_prescription(
                guided, top_weight_kg=top_weight_kg, one_rep_max_kg=one_rep_max_kg,
                phase_profile=phase_profile,
            )
        except ValueError as exc:
            logger.error('Prescricao guiada invalida para movimento %s: %s',
                         (movement or {}).get('movement_slug'), exc)
    else:
        series = None
    if series is None:
        series = build_legacy_series(
            movement, top_weight_kg, one_rep_max_kg=one_rep_max_kg,
            phase_profile=phase_profile,
        )
    if payload is not None:
        series = apply_phase_to_series(series, phase=phase_profile, reference=reference_phase(payload))
    return series
