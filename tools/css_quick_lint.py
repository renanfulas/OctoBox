#!/usr/bin/env python3
"""
ARQUIVO: linter rápido de CSS em Python.

POR QUE ELE EXISTE:
- Permite checar rapidamente erros de sintaxe em CSS quando stylelint/npm não estão disponíveis.

O QUE ESTE ARQUIVO FAZ:
1. Procura por chaves, parênteses, colchetes e aspas desbalanceados.
2. Detecta comentários de bloco não fechados.
3. Ajuda a evitar que erros simples quebrem o build.

PONTOS CRÍTICOS:
- Não substitui o stylelint, serve apenas como verificação rápida.
- Mudanças podem afetar a detecção de erros de sintaxe em pipelines sem npm.
"""
from pathlib import Path
import sys
import re


def find_css_files(root: Path):
    for p in root.rglob('*.css'):
        yield p


def check_file(path: Path):
    text = path.read_text(encoding='utf-8', errors='replace')
    errors = []

    # Check comments
    if text.count('/*') != text.count('*/'):
        errors.append('Unclosed block comment (/* ... */)')

    # Check braces, parentheses, brackets and quotes via a simple stack.
    # We'll scan char-by-char while ignoring characters inside block comments
    # or inside string literals so we don't mistake apostrophes inside
    # comments (e.g., Don't) for unbalanced quotes.
    stack = []
    pairs = {'{': '}', '(': ')', '[': ']'}
    opens = set(pairs.keys())
    closes = {v: k for k, v in pairs.items()}

    # For braces/parentheses/brackets, iterate per char but ignore chars inside
    # strings and comments. We track comment and string state as we go.
    in_single = False
    in_double = False
    in_comment = False
    lineno = 1
    for i, ch in enumerate(text):
        if ch == '\n':
            lineno += 1
        # comment start
        if not in_single and not in_double and text[i:i+2] == '/*':
            in_comment = True
            continue
        if in_comment and text[i:i+2] == '*/':
            in_comment = False
            continue
        if in_comment:
            continue
        # quotes
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if in_single or in_double:
            continue
        if ch in opens:
            stack.append((ch, lineno))
        elif ch in closes:
            if stack and stack[-1][0] == closes[ch]:
                stack.pop()
            else:
                errors.append(f"Unmatched closing '{ch}' at line {lineno}")

    for open_ch, open_line in stack:
        errors.append(f"Unclosed '{open_ch}' opened at line {open_line}")

    return errors


def main():
    root = Path.cwd()
    css_files = list(find_css_files(root))
    if not css_files:
        print('No CSS files found under', root)
        return 0

    total_issues = 0
    report = []
    for f in css_files:
        errs = check_file(f)
        if errs:
            total_issues += len(errs)
            report.append((f, errs))

    if not report:
        print('Quick CSS lint: no obvious syntax issues found.')
        return 0

    print('\nQuick CSS lint report — potential issues:')
    for f, errs in report:
        print(f"\nFile: {f}")
        for e in errs:
            print('  -', e)

    print(f"\nTotal potential issues: {total_issues} in {len(report)} file(s)")
    return 2


if __name__ == '__main__':
    sys.exit(main())
