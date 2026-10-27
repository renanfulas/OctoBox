"""Presentation and validation helpers for weekly WOD views."""

from __future__ import annotations

import re

from django.urls import reverse

from operations.model_definitions import ClassType
from operations.services.wod_input_contracts import duplicate_weekday_errors
from operations.services.wod_paste_parser import resolve_movement_slug


def _first_form_error(form, fallback_message):
    if not form.errors:
        return fallback_message
    first_errors = next(iter(form.errors.values()), [])
    if first_errors:
        return first_errors[0]
    return fallback_message


def _blocking_parse_errors(parsed_payload, source_text=''):
    """Return format errors without treating SmartPlan's advisory warnings as fatal."""
    errors = list(parsed_payload.get('parse_errors') or [])
    errors.extend(duplicate_weekday_errors(source_text))
    if parsed_payload.get('source_format'):
        return list(dict.fromkeys(errors))
    errors.extend(
        (
            f"Linha {warning.get('line_number', '?')}: "
            f"{warning.get('message', 'trecho não reconhecido')} — "
            f"“{warning.get('line_text', '')}”"
        )
        for warning in parsed_payload.get('parse_warnings') or []
    )
    return list(dict.fromkeys(errors))


def _smartplan_v2_uncertainty_errors(normalized_text):
    """Require the coach to resolve explicit uncertainty markers from SmartPlan."""
    errors = []
    for line in (normalized_text or '').splitlines():
        if re.search(r'\[\?[^\]]*\]', line):
            excerpt = re.sub(r'^\s*(?:[▸•*-]\s*)?', '', line).strip()
            if excerpt:
                errors.append(
                    f'Especifique o movimento ou a prescrição marcada como dúvida: “{excerpt}”.'
                )
    return errors


def _projection_guard_error(preview, cleaned_projection):
    """Mensagem acionavel quando nao ha aulas para projetar; None se pode prosseguir.

    Distingue 'nenhuma aula na semana' (precisa cadastrar a grade) de 'nenhuma aula do(s)
    tipo(s) selecionado(s)' (precisa ajustar o filtro ou criar aulas desse tipo).
    """
    week_label = cleaned_projection['target_week_start'].strftime('%d/%m/%Y')
    grade_path = reverse('class-grid')
    if preview.get('sessions_in_week_total', 0) == 0:
        return (
            f'Nenhuma aula cadastrada na semana de {week_label}. '
            f'Cadastre a grade em Grade de aulas ({grade_path}) antes de projetar.'
        )
    if (
        preview.get('totals', {}).get('sessions_found', 0) == 0
        and preview.get('sessions_canceled_selected_total', 0) > 0
    ):
        canceled_count = preview['sessions_canceled_selected_total']
        return (
            f'{canceled_count} aula(s) do(s) tipo(s) selecionado(s) na semana de {week_label} '
            f'estão canceladas e não receberão WOD. Reative essas aulas ou ajuste os tipos '
            f'em Grade de aulas ({grade_path}) antes de projetar.'
        )
    if preview.get('sessions_active_in_week_total', 0) == 0:
        canceled_count = preview.get('sessions_canceled_total', 0)
        return (
            f'As {canceled_count} aula(s) cadastrada(s) na semana de {week_label} '
            f'estão canceladas e não receberão WOD. Reative as aulas ou ajuste a grade '
            f'em Grade de aulas ({grade_path}) antes de projetar.'
        )
    if preview.get('totals', {}).get('sessions_found', 0) == 0:
        labels = ', '.join(str(ClassType(value).label) for value in cleaned_projection['class_types'])
        return (
            f'Nenhuma aula do(s) tipo(s) {labels} na semana de {week_label}. '
            f'Ajuste os tipos de aula ou cadastre aulas desse tipo na Grade de aulas ({grade_path}).'
        )
    return None


def _clear_unknown_review_slugs(parsed_payload, slug_dictionary):
    """Reabre slugs legados digitados fora do catálogo para Haiku ou revisão manual."""
    valid_slugs = {slug for slug, _aliases in slug_dictionary}
    valid_slugs.add('custom')
    for day in parsed_payload.get('days', []):
        for block in day.get('blocks', []):
            for movement in block.get('movements', []):
                slug = (movement.get('movement_slug') or '').strip()
                if slug and slug not in valid_slugs:
                    movement['movement_slug'] = ''


def _resolve_known_weekly_movement_slugs(parsed_payload, resolver=None):
    """Resolve exact catalog aliases locally before paying for Haiku slug review.

    The structural normalizer intentionally leaves every slug empty. Recovering a
    broken week must not turn every already-known exercise into an LLM candidate.
    """
    for day in parsed_payload.get('days', []):
        for block in day.get('blocks', []):
            for movement in block.get('movements', []):
                if movement.get('movement_slug'):
                    continue
                slug = (resolver or resolve_movement_slug)(movement.get('movement_label_raw') or '')
                if slug:
                    movement['movement_slug'] = slug



__all__ = [
    '_blocking_parse_errors',
    '_clear_unknown_review_slugs',
    '_first_form_error',
    '_projection_guard_error',
    '_resolve_known_weekly_movement_slugs',
    '_smartplan_v2_uncertainty_errors',
    'duplicate_weekday_errors',
    'resolve_movement_slug',
]
