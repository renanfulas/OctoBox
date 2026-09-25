"""Guard against WOD styles silently disappearing in the browser."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / 'static/css/design-system/tokens.css'
WOD_STYLES = (
    ROOT / 'static/css/design-system/operations/dev-coach/coach.css',
    *sorted((ROOT / 'static/css/design-system/operations/workspace').glob('wod-*.css')),
)


def test_wod_css_only_uses_defined_theme_tokens_without_fallback():
    defined = set(re.findall(r'(?m)^\s*(--theme-[\w-]+)\s*:', TOKENS.read_text(encoding='utf-8')))
    for path in WOD_STYLES:
        content = path.read_text(encoding='utf-8')
        unguarded = set(re.findall(r'var\(\s*(--theme-[\w-]+)\s*\)', content))
        assert not (unguarded - defined), f'{path.name}: {sorted(unguarded - defined)}'


def test_wod_css_does_not_mix_gradient_tokens_as_colors():
    gradient_tokens = ('--theme-surface-panel', '--theme-surface-panel-strong',
                       '--theme-card-surface', '--theme-card-surface-strong')
    for path in WOD_STYLES:
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if 'color-mix(' in line:
                assert not any(f'var({token})' in line for token in gradient_tokens), f'{path.name}:{number}'
