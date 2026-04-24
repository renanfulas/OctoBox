"""
ARQUIVO: heuristicas curtas para tipagem explicita de `ClassSession`.

POR QUE ELE EXISTE:
- prepara a migracao do corredor de aulas para `class_type` explicito.

O QUE ESTE ARQUIVO FAZ:
1. define as palavras-chave de inferencia por titulo.
2. oferece um helper deterministico para backfill e leituras futuras.

PONTOS CRITICOS:
- a heuristica e conservadora; em duvida, cai para `other`.
- esta camada nao deve tentar "adivinhar demais" para nao confundir tipos de aula.
"""

from __future__ import annotations

import re


CLASS_TYPE_PATTERNS = (
    ('mobility', (r'\bmob(?:ility)?\b', r'mobilidade', r'alongamento', r'flexibilidade', r'flow')),
    ('oly', (r'halterofilia', r'\boly\b', r'olimpic[ao]?', r'weightlifting', r'clean', r'snatch')),
    ('strength', (r'forca', r'strength', r'powerlifting', r'levantamento')),
    ('open_gym', (r'open gym', r'open-gym', r'livre', r'uso livre')),
    ('cross', (r'crossfit', r'\bcross\b', r'wod', r'metcon')),
)


def infer_class_type_from_session_title(title: str | None) -> str:
    normalized_title = (title or '').strip().lower()
    if not normalized_title:
        return 'other'

    for class_type, patterns in CLASS_TYPE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, normalized_title, flags=re.IGNORECASE):
                return class_type
    return 'other'


__all__ = ['CLASS_TYPE_PATTERNS', 'infer_class_type_from_session_title']
