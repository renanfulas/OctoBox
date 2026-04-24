"""
ARQUIVO: parser deterministico do Smart Paste semanal de WOD.

POR QUE ELE EXISTE:
- organiza texto livre PT-BR em um schema unico antes de qualquer fallback LLM.

O QUE ESTE ARQUIVO FAZ:
1. identifica dias da semana e blocos.
2. extrai metadados de bloco como rounds, timecap e intervalos.
3. resolve movimentos por dicionario canonico.

PONTOS CRITICOS:
- nao autocorrige silenciosamente quando nao reconhece uma linha.
- weekday tokenizer roda antes do matcher de movimento para evitar confusao.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path


WEEKDAY_LINES = (
    (0, 'Segunda', ('segunda', 'segunda-feira')),
    (1, 'Terca', ('terca', 'terca-feira')),
    (2, 'Quarta', ('quarta', 'quarta-feira')),
    (3, 'Quinta', ('quinta', 'quinta-feira')),
    (4, 'Sexta', ('sexta', 'sexta-feira')),
    (5, 'Sabado', ('sabado', 'sabado-feira')),
    (6, 'Domingo', ('domingo',)),
)

BLOCK_HEADERS = (
    ('mobility', ('mobilidade',)),
    ('warmup', ('aquecimento',)),
    ('skill', ('skill',)),
    ('metcon', ('wod',)),
    ('cooldown', ('cooldown', 'descanso ativo')),
)


def _normalize_token(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value or '')
    ascii_value = ''.join(char for char in normalized if not unicodedata.combining(char))
    ascii_value = ascii_value.lower().replace('-', ' ')
    ascii_value = re.sub(r'[^a-z0-9/%.+ ]+', ' ', ascii_value)
    return re.sub(r'\s+', ' ', ascii_value).strip()


def _as_float(raw_value: str) -> float:
    return float(raw_value.replace('.', '').replace(',', '.'))


@lru_cache(maxsize=1)
def load_wod_movement_dictionary() -> list[tuple[str, tuple[str, ...]]]:
    dictionary_path = Path(__file__).resolve().parents[2] / 'docs' / 'reference' / 'wod-movement-dictionary.md'
    entries: list[tuple[str, tuple[str, ...]]] = []
    for line in dictionary_path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| `'):
            continue
        parts = [part.strip() for part in line.strip().strip('|').split('|')]
        if len(parts) != 2:
            continue
        slug = parts[0].strip('` ')
        if slug == 'slug' or not re.fullmatch(r'[a-z0-9_]+', slug):
            continue
        aliases = [alias.strip() for alias in parts[1].split(',') if alias.strip()]
        normalized_aliases = sorted({_normalize_token(slug), *(_normalize_token(alias) for alias in aliases)}, key=len, reverse=True)
        entries.append((slug, tuple(normalized_aliases)))
    return entries


def _match_weekday(line: str):
    normalized = _normalize_token(line.rstrip(':'))
    for weekday, label, aliases in WEEKDAY_LINES:
        if normalized in aliases:
            return weekday, label
    return None


def _match_block_header(line: str):
    normalized = _normalize_token(line)
    for kind, aliases in BLOCK_HEADERS:
        for alias in aliases:
            if normalized == alias or normalized.startswith(f'{alias} '):
                rest = line[len(line.split()[0]):].strip() if ' ' in normalized else ''
                if normalized == alias:
                    rest = ''
                else:
                    rest = line.strip()[len(line.strip().split(maxsplit=1)[0]):].strip()
                return kind, rest
    return None


def _build_day(weekday: int, weekday_label: str) -> dict:
    return {
        'weekday': weekday,
        'weekday_label': weekday_label,
        'blocks': [],
    }


def _build_block(kind: str, sort_order: int) -> dict:
    return {
        'kind': kind,
        'title': None,
        'notes': None,
        'timecap_min': None,
        'rounds': None,
        'interval_seconds': None,
        'score_type': None,
        'format_spec': None,
        'movements': [],
        'sort_order': sort_order,
    }


def _add_note(block: dict, note: str):
    note = note.strip()
    if not note:
        return
    if block['notes']:
        block['notes'] = f"{block['notes']} {note}"
    else:
        block['notes'] = note


def _parse_block_metadata(line: str):
    normalized = _normalize_token(line)
    metadata = {}
    if re.fullmatch(r'\d+x', normalized):
        rounds = int(normalized[:-1])
        metadata.update({'rounds': rounds, 'format_spec': line.strip()})
        return metadata
    match = re.fullmatch(r'(\d+)\s+rounds?(?:\s+(\d+(?:[.,]\d+)?)%)?', normalized)
    if match:
        metadata.update({'rounds': int(match.group(1)), 'format_spec': line.strip()})
        if match.group(2):
            metadata['inherited_load_percentage_rm'] = float(match.group(2).replace(',', '.'))
        return metadata
    match = re.fullmatch(r'emom\s+(\d+)m', normalized)
    if match:
        metadata.update(
            {
                'timecap_min': int(match.group(1)),
                'interval_seconds': 60,
                'score_type': 'emom',
                'format_spec': line.strip(),
            }
        )
        return metadata
    match = re.fullmatch(r'amrap\s+(\d+)m', normalized)
    if match:
        metadata.update({'timecap_min': int(match.group(1)), 'score_type': 'amrap', 'format_spec': line.strip()})
        return metadata
    match = re.fullmatch(r'(\d+)m', normalized)
    if match:
        metadata.update({'timecap_min': int(match.group(1))})
        return metadata
    match = re.fullmatch(r'a cada (\d+)s por (\d+)\s*x', normalized)
    if match:
        metadata.update(
            {
                'interval_seconds': int(match.group(1)),
                'rounds': int(match.group(2)),
                'format_spec': line.strip(),
                'score_type': 'rounds_reps',
            }
        )
        return metadata
    match = re.fullmatch(r'(\d+)/(\d+)/(\d+)', normalized)
    if match:
        metadata.update({'score_type': 'rounds_reps', 'format_spec': line.strip()})
        return metadata
    match = re.fullmatch(r'(\d+)\s+rounds?', normalized)
    if match:
        metadata.update({'rounds': int(match.group(1)), 'format_spec': line.strip()})
        return metadata
    return None


def _is_block_note_candidate(line: str) -> bool:
    normalized = _normalize_token(line)
    return (
        normalized.startswith('cada quebra')
        or normalized.startswith('duplas')
        or 'um round para cada' in normalized
    )


def resolve_movement_slug(name_fragment: str) -> str | None:
    normalized_name = _normalize_token(name_fragment)
    if not normalized_name:
        return None
    exact_match = None
    partial_match = None
    for slug, aliases in load_wod_movement_dictionary():
        for alias in aliases:
            if normalized_name == alias:
                if exact_match is None or len(alias) > len(exact_match[1]):
                    exact_match = (slug, alias)
            elif normalized_name.endswith(f' {alias}') or normalized_name.startswith(f'{alias} ') or f' {alias} ' in f' {normalized_name} ':
                if partial_match is None or len(alias) > len(partial_match[1]):
                    partial_match = (slug, alias)
    if exact_match is not None:
        return exact_match[0]
    if partial_match is not None:
        return partial_match[0]
    return None


def _parse_single_movement(
    raw_text: str,
    *,
    sort_order: int,
    inherited_load_percentage_rm: float | None,
    emom_label: str | None = None,
    is_scaled_alternative: bool = False,
):
    text = raw_text.strip()
    if not text:
        return None
    if _normalize_token(text) == 'rest':
        return {
            'movement_slug': None,
            'movement_label_raw': text,
            'sets': None,
            'reps_spec': None,
            'load_spec': None,
            'load_rx_male_kg': None,
            'load_rx_female_kg': None,
            'load_percentage_rm': None,
            'emom_label': emom_label,
            'notes': 'descanso',
            'is_scaled_alternative': is_scaled_alternative,
            'sort_order': sort_order,
        }

    reps_spec = None
    load_spec = None
    load_rx_male_kg = None
    load_rx_female_kg = None
    load_percentage_rm = inherited_load_percentage_rm
    notes = None
    working_text = text

    reps_match = re.match(r'^(?P<reps>\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*a\s*\d+)?(?:/\d+)?)\s+(?P<name>.+)$', working_text, flags=re.IGNORECASE)
    if reps_match:
        reps_spec = reps_match.group('reps').strip()
        working_text = reps_match.group('name').strip()

    load_match = re.match(
        r'^(?P<name>.+?)\s+(?P<load>(?:\d+(?:[.,]\d+)?/\d+(?:[.,]\d+)?)|(?:\d+(?:[.,]\d+)?)%)$',
        working_text,
    )
    if load_match:
        working_text = load_match.group('name').strip()
        load_spec = load_match.group('load').strip()

    if load_spec and load_spec.endswith('%'):
        load_percentage_rm = float(load_spec[:-1].replace(',', '.'))
    elif load_spec and '/' in load_spec:
        male_value, female_value = load_spec.split('/', 1)
        load_rx_male_kg = _as_float(male_value)
        load_rx_female_kg = _as_float(female_value)

    movement_slug = resolve_movement_slug(working_text)
    if movement_slug is None and reps_spec is None:
        return None

    return {
        'movement_slug': movement_slug,
        'movement_label_raw': text,
        'sets': None,
        'reps_spec': reps_spec,
        'load_spec': load_spec,
        'load_rx_male_kg': load_rx_male_kg,
        'load_rx_female_kg': load_rx_female_kg,
        'load_percentage_rm': load_percentage_rm,
        'emom_label': emom_label,
        'notes': notes,
        'is_scaled_alternative': is_scaled_alternative,
        'sort_order': sort_order,
    }


def _parse_movement_line(line: str, block: dict):
    emom_label = None
    working_line = line.strip()
    emom_match = re.match(r'^([A-E])\s+(.+)$', working_line, flags=re.IGNORECASE)
    if emom_match:
        emom_label = emom_match.group(1).upper()
        working_line = emom_match.group(2).strip()

    inherited_load = block.get('_inherited_load_percentage_rm')
    movement_payloads = []
    sequence_parts = [part.strip() for part in re.split(r'\s+\+\s+', working_line) if part.strip()]
    for sequence_part in sequence_parts:
        alternatives = [part.strip() for part in re.split(r'\s+/\s+', sequence_part) if part.strip()]
        if len(alternatives) > 1 and all(re.match(r'^\d', part) for part in alternatives):
            for alt_index, alternative in enumerate(alternatives):
                movement_payload = _parse_single_movement(
                    alternative,
                    sort_order=len(block['movements']) + len(movement_payloads),
                    inherited_load_percentage_rm=inherited_load,
                    emom_label=emom_label,
                    is_scaled_alternative=alt_index > 0,
                )
                if movement_payload is None:
                    return None
                movement_payloads.append(movement_payload)
            continue

        movement_payload = _parse_single_movement(
            sequence_part,
            sort_order=len(block['movements']) + len(movement_payloads),
            inherited_load_percentage_rm=inherited_load,
            emom_label=emom_label,
        )
        if movement_payload is None:
            return None
        movement_payloads.append(movement_payload)
    return movement_payloads


def parse_weekly_wod_text(text: str) -> dict:
    result = {
        'week_label': None,
        'parse_warnings': [],
        'days': [],
    }
    current_day = None
    current_block = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue

        weekday_match = _match_weekday(stripped_line)
        if weekday_match is not None:
            weekday, weekday_label = weekday_match
            current_day = _build_day(weekday, weekday_label)
            result['days'].append(current_day)
            current_block = None
            continue

        if current_day is None:
            result['parse_warnings'].append(
                {
                    'line_number': line_number,
                    'line_text': stripped_line,
                    'message': 'linha fora de um dia da semana',
                }
            )
            continue

        header_match = _match_block_header(stripped_line)
        if header_match is not None:
            kind, remainder = header_match
            current_block = _build_block(kind, sort_order=len(current_day['blocks']))
            current_day['blocks'].append(current_block)
            if remainder:
                metadata = _parse_block_metadata(remainder)
                if metadata:
                    current_block.update({key: value for key, value in metadata.items() if not key.startswith('_')})
                    if 'inherited_load_percentage_rm' in metadata:
                        current_block['_inherited_load_percentage_rm'] = metadata['inherited_load_percentage_rm']
                    if current_block['kind'] == 'metcon' and current_block['score_type'] is None and current_block['timecap_min'] is not None:
                        current_block['score_type'] = 'for_time'
                else:
                    current_block['title'] = remainder
            continue

        if current_block is None:
            result['parse_warnings'].append(
                {
                    'line_number': line_number,
                    'line_text': stripped_line,
                    'message': 'linha fora de um bloco reconhecido',
                }
            )
            continue

        metadata = _parse_block_metadata(stripped_line)
        if metadata is not None:
            current_block.update({key: value for key, value in metadata.items() if not key.startswith('_')})
            if 'inherited_load_percentage_rm' in metadata:
                current_block['_inherited_load_percentage_rm'] = metadata['inherited_load_percentage_rm']
            if current_block['kind'] == 'metcon' and current_block['score_type'] is None:
                if current_block['timecap_min'] is not None or current_block['format_spec'] or current_block['rounds'] is not None:
                    current_block['score_type'] = 'for_time'
            continue

        if _is_block_note_candidate(stripped_line):
            _add_note(current_block, stripped_line)
            continue

        movement_payloads = _parse_movement_line(stripped_line, current_block)
        if movement_payloads is not None:
            current_block['movements'].extend(movement_payloads)
            continue

        if re.match(r'^semana\s+\d+$', _normalize_token(stripped_line)) and not current_block['title']:
            current_block['title'] = stripped_line
            continue

        _add_note(current_block, stripped_line)

    for day in result['days']:
        for block in day['blocks']:
            block.pop('_inherited_load_percentage_rm', None)
            if block['kind'] == 'metcon' and block['score_type'] is None and block['movements']:
                block['score_type'] = 'for_time'
    return result


__all__ = ['load_wod_movement_dictionary', 'parse_weekly_wod_text', 'resolve_movement_slug']
