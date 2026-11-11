"""Operational Curva rest-time policy for the coach's current prescriptions.

The ranges stay visible in workout copy; the guided timer uses a midpoint so
each set can start a deterministic countdown. A trainee can still extend or
skip the timer from the guided screen.
"""

from __future__ import annotations

from typing import Any


REST_BANDS = (
    {'key': 'feeder', 'label': 'Feeder · 50% 1RM', 'range_seconds': (20, 30), 'timer_seconds': 25},
    {'key': 'preparatory', 'label': 'Preparatória · 60–75% 1RM', 'range_seconds': (45, 60), 'timer_seconds': 52},
    {'key': 'work_75_85', 'label': '75–85% 1RM', 'range_seconds': (90, 90), 'timer_seconds': 90},
    {'key': 'work_85_95', 'label': '85–95% 1RM', 'range_seconds': (120, 180), 'timer_seconds': 150},
    {'key': 'work_95_100', 'label': '95–100% 1RM', 'range_seconds': (180, 300), 'timer_seconds': 240},
    {'key': 'biset', 'label': 'Bi-set · após o par', 'range_seconds': (90, 120), 'timer_seconds': 105},
)


def rest_seconds_for(*, role: str | None = None, percent_of_1rm: float | None = None,
                     fallback_seconds: int = 90) -> int:
    """Return the midpoint/default timer value for the configured rest band.

    Feeder and preparatory stages use their stage rule. Other resistance
    stages use the actual (or phase-estimated) percentage of 1RM. A movement
    below 75% that is not explicitly a feeder/preparatory set uses the
    preparatory band as a conservative fallback.
    """
    if role == 'feeder':
        return 25
    if role in {'warmup', 'preparatory', 'prep'}:
        return 52
    if percent_of_1rm is None:
        return int(fallback_seconds)
    try:
        percent = float(percent_of_1rm)
    except (TypeError, ValueError):
        return int(fallback_seconds)
    if percent >= 95:
        return 240
    if percent >= 85:
        return 150
    if percent >= 75:
        return 90
    return 52


def rest_range_label(*, role: str | None = None, percent_of_1rm: float | None = None) -> str:
    """Human-readable target range matching :func:`rest_seconds_for`."""
    if role == 'feeder':
        return '20–30 s'
    if role in {'warmup', 'preparatory', 'prep'}:
        return '45–60 s'
    if percent_of_1rm is None:
        return 'conforme à %1RM'
    try:
        percent = float(percent_of_1rm)
    except (TypeError, ValueError):
        return 'conforme à %1RM'
    if percent >= 95:
        return '3–5 min'
    if percent >= 85:
        return '2–3 min'
    if percent >= 75:
        return '1 min 30 s'
    return '45–60 s'


def phase_midpoint_percent(phase: Any = None) -> float | None:
    """Read a phase profile's midpoint without coupling payloads to the UI."""
    values = getattr(phase, 'intensity_pct_range', None)
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        return None
    try:
        return (float(values[0]) + float(values[1])) / 2
    except (TypeError, ValueError):
        return None


__all__ = ['REST_BANDS', 'phase_midpoint_percent', 'rest_range_label', 'rest_seconds_for']
