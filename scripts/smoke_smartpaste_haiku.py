"""Read-only production smoke for the SmartPaste Haiku response contract."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from operations.services.wod_paste_parser import load_wod_movement_dictionary
from operations.services.wod_slug_resolver import (
    _STATIC_INSTRUCTIONS,
    _call_anthropic,
    _parse_and_validate,
)


def main():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        raise SystemExit('smartpaste_haiku_smoke=missing_key')

    dictionary = load_wod_movement_dictionary()
    static_block = _STATIC_INSTRUCTIONS + '\n\nDicionario canonico:\n' + '\n'.join(
        f'{slug}: {", ".join(aliases)}' for slug, aliases in dictionary
    )
    names = ['10 wall waks']
    dynamic_block = 'Identifique os itens por id:\n' + json.dumps([
        {'id': 0, 'texto': names[0], 'contexto': 'Terça · EMOM de ginástica'},
    ], ensure_ascii=False)
    raw_text = _call_anthropic(
        static_block=static_block,
        dynamic_block=dynamic_block,
        api_key=api_key,
    )
    if not raw_text:
        raise SystemExit('smartpaste_haiku_smoke=provider_error')
    result = _parse_and_validate(
        raw_text=raw_text,
        valid_slugs={slug for slug, _aliases in dictionary},
        unrecognized_names=names,
    )
    if result.get(names[0], {}).get('slug') != 'wall_walk':
        raise SystemExit('smartpaste_haiku_smoke=invalid_or_unresolved')
    print('smartpaste_haiku_smoke=pass resolved=1')


if __name__ == '__main__':
    main()
