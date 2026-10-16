"""Textos curtos do dia de treino, sem alterar o nome publicado do programa."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .dashboard import day_keyword


_TITLE_SEPARATOR = re.compile(r'\s+[—–-]\s+')


@dataclass(frozen=True)
class DayPresentation:
    title: str
    detail: str
    full: str


def present_day(day: dict) -> DayPresentation:
    """Prioriza campos editoriais e separa labels legados no primeiro travessão.

    Um label sem divisão continua legível: vira título, sem inventar foco
    muscular. O nome completo permanece disponível para leitura assistiva e
    para a tela de foco do treino guiado.
    """
    label = day_keyword(day_id=day.get('day_id', ''), label=day.get('label', '')).strip()
    parts = _TITLE_SEPARATOR.split(label, maxsplit=1)
    inferred_title = parts[0].strip()
    inferred_detail = parts[1].strip() if len(parts) == 2 else ''
    title = (day.get('display_title') or inferred_title).strip() or label
    detail = (day.get('focus_description') or inferred_detail).strip()
    full = f'{title} — {detail}' if detail else title
    return DayPresentation(title=title, detail=detail, full=full)
