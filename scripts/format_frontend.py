#!/usr/bin/env python3
"""
Formata arquivos JS e CSS em `static/` usando jsbeautifier.
Roda em-place e ignora `static/css/design-system` por padrão.
"""
import os
from pathlib import Path
import jsbeautifier

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'

js_opts = jsbeautifier.default_options()
js_opts.indent_size = 2
js_opts.space_in_empty_paren = True
js_opts.jslint_happy = False

css_opts = jsbeautifier.default_options()
css_opts.indent_size = 2

exclude_paths = [STATIC / 'css' / 'design-system']

changed_files = []

for subdir, _, files in os.walk(STATIC):
    for name in files:
        path = Path(subdir) / name
        if any(str(path).startswith(str(p)) for p in exclude_paths):
            continue
        if path.suffix == '.js':
            try:
                text = path.read_text(encoding='utf-8')
                new = jsbeautifier.beautify(text, js_opts)
                if new != text:
                    path.write_text(new, encoding='utf-8')
                    changed_files.append(str(path.relative_to(ROOT)))
            except Exception:
                continue
        elif path.suffix == '.css':
            try:
                text = path.read_text(encoding='utf-8')
                new = jsbeautifier.beautify_css(text, css_opts)
                if new != text:
                    path.write_text(new, encoding='utf-8')
                    changed_files.append(str(path.relative_to(ROOT)))
            except Exception:
                continue

if changed_files:
    print('Arquivos modificados:')
    for f in changed_files:
        print('- ' + f)
else:
    print('Nenhuma modificação necessária.')
