"""Diagnósticos de entrada que não podem ser resolvidos por inferência."""

from operations.services.wod_paste_freeform_parser import _match_weekday_line


def duplicate_weekday_errors(source_text: str) -> list[str]:
    """Não mesclar silenciosamente duas seções do mesmo dia."""
    first_lines: dict[int, int] = {}
    errors = []
    for line_number, line in enumerate((source_text or '').splitlines(), start=1):
        match = _match_weekday_line(line.strip())
        if match is None:
            continue
        weekday, label = match
        if weekday in first_lines:
            errors.append(
                f'Linha {line_number}: {label} aparece novamente (primeira seção na linha '
                f'{first_lines[weekday]}). Una os treinos desse dia no texto antes de organizar.'
            )
        else:
            first_lines[weekday] = line_number
    return errors


def duplicate_weekday_sections(source_text: str) -> list[dict]:
    """Mantém visíveis as seções originais em conflito, mesmo se o parser as mesclar."""
    sections = []
    current = None
    for line_number, line in enumerate((source_text or '').splitlines(), start=1):
        match = _match_weekday_line(line.strip())
        if match is not None:
            if current is not None:
                sections.append(current)
            weekday, label = match
            current = {'weekday': weekday, 'label': label, 'line_number': line_number, 'lines': [line]}
        elif current is not None:
            current['lines'].append(line)
    if current is not None:
        sections.append(current)
    grouped = {}
    for section in sections:
        grouped.setdefault(section['weekday'], []).append(section)
    return [
        {
            'label': group[0]['label'],
            'sections': [
                {'line_number': item['line_number'], 'source_text': '\n'.join(item['lines']).strip()}
                for item in group
            ],
        }
        for group in grouped.values() if len(group) > 1
    ]


__all__ = ['duplicate_weekday_errors', 'duplicate_weekday_sections']
