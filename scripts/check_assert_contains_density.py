"""
ARQUIVO: gate de CI que aplica a ADR-012 (structural-asserts > mega-copy-asserts).

POR QUE ELE EXISTE:
- docs/adr/ADR-012-test-design-structural-asserts.md documenta a regra ha meses,
  mas nunca teve enforcement automatico: uma auditoria em 2026-08-27 encontrou
  27 test methods violando o limite documentado, alguns por 2-5x.
- a regra so vale a pena se parar teste NOVO de repetir o padrao. Nao reescreve
  os 27 existentes (isso e trabalho a parte, deliberadamente fora de escopo aqui).

O QUE ESTE ARQUIVO FAZ:
1. varre arquivos de teste (mesmo escopo do pytest.ini) por metodo de teste.
2. conta chamadas a assertContains(...) dentro de cada metodo, via AST (nao
   regex — precisa resistir a chamadas multi-linha e defs aninhados).
3. classifica cada chamada como ESTRUTURAL (string parece id="...",
   data-x="...", href="...", name="..." value="...") ou COPY (o resto —
   frase solta, titulo, texto de produto). So COPY conta pro limite: a ADR-012
   endossa explicitamente asserts estruturais em volume — o proprio exemplo
   canonico dela (test_finance_center_renders_dashboard_and_plan_portfolio)
   tem 9 assertContains, quase todos estruturais. Contar tudo sem distinguir
   quebraria o exemplo que a ADR usa pra ensinar o jeito certo.
4. compara contagem de COPY contra THRESHOLD. Violacoes ja catalogadas em
   BASELINE_PATH nao quebram o build (divida conhecida); violacao NOVA quebra.

PONTOS CRITICOS:
- THRESHOLD=8 fica no topo da faixa "5-10" que a propria ADR-012 aceita como
  guidance, mesmo a secao "anti-pattern proibido" da ADR falando em ">5x".
  Escolha deliberada: 5 travaria boa parte dos casos legados de uma vez so se
  algum dia forem tocados incidentalmente; 8 da fricção real sem ser hostil.
- a heuristica estrutural (STRUCTURAL_PATTERN) e propositalmente simples e vai
  ter falso-negativo (copy que parece atributo, estrutural que nao usa '=').
  Isso e um tripwire pra revisao humana, nao um linter perfeito — na duvida,
  o volume alto ainda pede uma olhada manual contra a ADR-012.
- BASELINE_PATH e uma lista de excecoes, igual .secrets.baseline (detect-secrets)
  ja usado neste repo — mesmo padrao, escopo diferente.
- Baseline "furado" (entrada que nao viola mais) so gera aviso, nao falha —
  incentiva quem tocar no arquivo a limpar a entrada, sem forcar um PR dedicado.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / 'scripts' / 'assert_contains_density_baseline.txt'
THRESHOLD = 8

IGNORED_DIRS = {'.venv', 'node_modules', 'tests/e2e'}
IGNORED_FILES = {'test_csv_injection.py', 'test_whale.py'}

# Assert "estrutural" na definicao da ADR-012: id=, data-*=, name=/value=, href=.
# Cobre string literal direta e f-string (ast.JoinedStr) com esse prefixo.
STRUCTURAL_PATTERN = re.compile(r'(^|[\'"\s])(id|data-[\w-]+|name|value|href)=["\']')
# Path de rota (ex.: "/renan/henrique/manifest.webmanifest") tambem e contrato
# estrutural, nao copy — confere que uma URL existe, nao redacao de produto.
URL_PATH_PATTERN = re.compile(r'^/[\w./-]*$')


def iter_test_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ('tests.py', 'test_*.py', '*_tests.py'):
        for path in REPO_ROOT.rglob(pattern):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.name in IGNORED_FILES:
                continue
            files.append(path)
    return sorted(set(files))


def static_text_of(node: ast.AST | None) -> str:
    """Reconstroi a parte literal (nao-interpolada) de uma string ou f-string."""
    if node is None:
        return ''
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return ''.join(
            piece.value for piece in node.values if isinstance(piece, ast.Constant)
        )
    return ''


def is_structural_assert(call_node: ast.Call) -> bool:
    text_arg = None
    for kw in call_node.keywords:
        if kw.arg == 'text':
            text_arg = kw.value
            break
    if text_arg is None and len(call_node.args) >= 2:
        text_arg = call_node.args[1]
    text = static_text_of(text_arg)
    return bool(STRUCTURAL_PATTERN.search(text)) or bool(URL_PATH_PATTERN.match(text.strip()))


def count_copy_assert_contains_calls(func_node: ast.FunctionDef) -> int:
    count = 0
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            attr = node.func
            if isinstance(attr, ast.Attribute) and attr.attr == 'assertContains':
                if not is_structural_assert(node):
                    count += 1
    return count


def find_violations(path: Path) -> list[tuple[str, int]]:
    try:
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    rel = path.relative_to(REPO_ROOT).as_posix()
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            count = count_copy_assert_contains_calls(node)
            if count > THRESHOLD:
                violations.append((f'{rel}::{node.name}', count))
    return violations


def load_baseline() -> set[str]:
    if not BASELINE_PATH.exists():
        return set()
    lines = BASELINE_PATH.read_text(encoding='utf-8').splitlines()
    return {line.strip() for line in lines if line.strip() and not line.strip().startswith('#')}


def main() -> int:
    baseline = load_baseline()
    all_violations: dict[str, int] = {}
    for path in iter_test_files():
        for key, count in find_violations(path):
            all_violations[key] = count

    new_violations = {k: v for k, v in all_violations.items() if k not in baseline}
    stale_baseline = sorted(baseline - all_violations.keys())

    if stale_baseline:
        print('ℹ️  Entradas na baseline que nao violam mais (pode remover de'
              f' {BASELINE_PATH.relative_to(REPO_ROOT)}):')
        for entry in stale_baseline:
            print(f'   - {entry}')
        print()

    if new_violations:
        print(f'❌ {len(new_violations)} teste(s) NOVO(S) violando ADR-012'
              f' (mais de {THRESHOLD} assertContains(copy) no mesmo metodo):')
        for key, count in sorted(new_violations.items(), key=lambda kv: -kv[1]):
            print(f'   {count:3d}  {key}')
        print()
        print('Veja docs/adr/ADR-012-test-design-structural-asserts.md — troque')
        print('assertContains de copy por asserts estruturais (block IDs,')
        print('data-attributes, anchors, identificadores de dado).')
        print()
        print(f'Se a excecao for deliberada, adicione a linha em {BASELINE_PATH.relative_to(REPO_ROOT)}')
        print('com uma justificativa em comentario acima.')
        return 1

    print(f'✅ Nenhum teste novo viola ADR-012 (limite: {THRESHOLD} assertContains/metodo).')
    print(f'   {len(baseline)} excecao(oes) conhecida(s) na baseline (divida legada, nao bloqueia).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
