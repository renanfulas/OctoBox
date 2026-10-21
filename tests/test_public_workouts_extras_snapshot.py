"""
ARQUIVO: snapshot da biblioteca de templatetags `public_workouts_extras` (Fase 0 do split).

POR QUE ELE EXISTE:
- docs/plans/split-arquivos-grandes-plano.md, Fase 0, item 3 (risco 3). Na Fase 1
  a logica sai para public_workouts/presenters/ e o modulo vira so registros
  (`register.filter('movement_name', movement_name)`). `@register.filter` e
  `@register.simple_tag` se comportam diferente no template, inclusive no escape
  de HTML: recadastrar um filtro como tag, perder `is_safe` ou trocar a
  assinatura quebra a tela sem erro claro.

O QUE ESTE ARQUIVO FAZ:
- Le o `register` real e compara, para cada um dos 37 registros: o tipo
  (filter, simple_tag...), as opcoes ligadas (is_safe, needs_autoescape,
  expects_localtime, takes_context) e a assinatura sem anotacoes.

COMO MANTER:
- Registro novo ou alterado DE PROPOSITO (fora de PR de split): atualize
  EXPECTED_LIBRARY no mesmo PR. Num PR de split, nunca.
"""

from __future__ import annotations

import inspect

from django import template

from public_workouts.templatetags import public_workouts_extras


_FILTER_FLAGS = ('expects_localtime', 'is_safe', 'needs_autoescape')

# Gerado do main 6a0c8ca0 (21/10/2026) por describe_library() e congelado aqui.
# nome no template: (tipo, opcoes ligadas, assinatura sem anotacoes)
EXPECTED_LIBRARY: dict[str, tuple[str, tuple[str, ...], str]] = {
    'current_period_phase': ('simple_tag', (), '(payload)'),
    'current_period_week_number': ('filter', (), '(payload)'),
    'cycle_summary_rows': ('simple_tag', (), '(progress_snapshots, movement_labels)'),
    'day_short': ('filter', (), '(day_id)'),
    'dict_get': ('filter', (), '(dictionary, key)'),
    'glossary_highlight': ('filter', (), '(text, ramp=None)'),
    'guided_series': ('simple_tag', (), '(movement, top_weight_kg=None, one_rep_max_by_movement=None)'),
    'hero_progress_chart': ('simple_tag', (), '(progress_snapshots, movement_labels=None)'),
    'humanize_movement_slug': ('filter', (), '(movement_slug)'),
    'initial': ('filter', (), '(name)'),
    'load_chart_points': ('filter', (), '(entries)'),
    'movement_load_display': (
        'simple_tag', (), '(movement, payload, phase, one_rep_max_by_movement, progress_snapshots=None)',
    ),
    'movement_name': ('filter', (), '(movement, movement_labels=None)'),
    'movement_shows_plate_calculator': ('filter', (), '(movement_slug)'),
    'periodization_chart_points': ('filter', (), '(periodization)'),
    'periodization_phase_banner': ('simple_tag', (), '(payload)'),
    'personal_record': ('filter', (), '(entries)'),
    'personal_record_rows': ('simple_tag', (), '(entries, movement_labels=None)'),
    'program_summary': ('simple_tag', (), '(payload)'),
    'program_week_progress': ('simple_tag', (), '(payload)'),
    'progress_chart_for_movement': ('simple_tag', (), '(movement_slug, progress_snapshots)'),
    'reps_phases': ('filter', (), '(reps_spec, top_weight_kg=None)'),
    'resolve_movement_display_name': ('filter', (), '(movement_slug, movement_labels)'),
    'share_content_for_chart': ('simple_tag', (), '(chart, movement_label)'),
    'sibling_variations': ('filter', (), '(movement_slug)'),
    'todays_default_load_entry': ('simple_tag', (), '(load_history, movement_slug)'),
    'todays_load_entry': ('simple_tag', (), '(load_history, movement_slug, set_role)'),
    'todays_logged_idempotency_key': ('simple_tag', (), '(load_history, movement_slug)'),
    'todays_logged_reps': ('simple_tag', (), '(load_history, movement_slug)'),
    'todays_logged_rir': ('simple_tag', (), '(load_history, movement_slug)'),
    'todays_logged_weight': ('simple_tag', (), '(load_history, movement_slug)'),
    'todays_top_set_weight': ('simple_tag', (), '(load_history, movement_slug)'),
    'week_overview': ('simple_tag', (), '(payload, load_history=None)'),
    'week_streak_label': ('simple_tag', (), '(week_days)'),
    'workout_day_presentation': ('simple_tag', (), '(day)'),
    'workout_day_selection': ('simple_tag', (), '(payload)'),
    'workout_greeting': ('simple_tag', (), "(name='')"),
}


def _plain_signature(func) -> str:
    signature = inspect.signature(inspect.unwrap(func))
    parameters = [
        parameter.replace(annotation=inspect.Parameter.empty)
        for parameter in signature.parameters.values()
    ]
    return str(signature.replace(parameters=parameters, return_annotation=inspect.Signature.empty))


def _tag_kind(compile_func) -> str:
    # wraps() copia __qualname__ da funcao do usuario; o code object guarda o
    # helper do Django que montou o compilador (simple_tag, inclusion_tag...).
    qualname = compile_func.__code__.co_qualname
    for kind in ('simple_block_tag', 'simple_tag', 'inclusion_tag'):
        if f'.{kind}.' in f'.{qualname}':
            return kind
    return 'tag'


def describe_library(library: template.Library | None = None) -> dict[str, tuple[str, tuple[str, ...], str]]:
    library = library or public_workouts_extras.register
    described = {}
    for name, func in library.filters.items():
        flags = tuple(flag for flag in _FILTER_FLAGS if getattr(func, flag, False))
        described[name] = ('filter', flags, _plain_signature(func))
    for name, compile_func in library.tags.items():
        kind = _tag_kind(compile_func)
        if kind == 'tag':
            described[name] = (kind, (), _plain_signature(compile_func))
            continue
        closure = inspect.getclosurevars(compile_func).nonlocals
        flags = ('takes_context',) if closure.get('takes_context') else ()
        described[name] = (kind, flags, _plain_signature(closure['func']))
    return described


def test_library_registrations_match_snapshot():
    actual = describe_library()

    missing = sorted(set(EXPECTED_LIBRARY) - set(actual))
    added = sorted(set(actual) - set(EXPECTED_LIBRARY))
    changed = sorted(
        f'{name}: era {EXPECTED_LIBRARY[name]}, agora {actual[name]}'
        for name in set(EXPECTED_LIBRARY) & set(actual)
        if EXPECTED_LIBRARY[name] != actual[name]
    )

    assert not missing, f'registros sumiram de public_workouts_extras: {missing}'
    assert not changed, 'registros mudaram de tipo, opcao ou assinatura:\n' + '\n'.join(changed)
    assert not added, f'registros novos sem snapshot (adicione em EXPECTED_LIBRARY): {added}'


def test_library_has_37_registrations():
    assert len(describe_library()) == 37
