"""
ARQUIVO: guarda de `patch()` mirando modulo que vai virar fachada (Fase 0 do split).

POR QUE ELE EXISTE:
- docs/plans/split-arquivos-grandes-plano.md, risco 1 e ADR-2. `patch('m.X')` so
  tem efeito se o codigo que usa X procurar o nome no modulo `m` na hora da
  chamada. Quando a view muda de arquivo e `m` vira fachada que so reexporta, o
  patch continua "funcionando" sem erro, mas o codigo real passa a chamar o X de
  verdade: o teste de checkout chama a Stripe, o de OAuth chama o Google.

O QUE ESTE ARQUIVO FAZ:
1. Varre todo arquivo de teste do repositorio atras de strings exatamente
   `'<modulo_fachada>.<nome>'` (patch(), @patch, monkeypatch.setattr...).
2. Para cada uma, exige que alguma funcao DEFINIDA no proprio modulo leia esse
   nome como global (e o que faz o patch valer). Fachada que so reexporta nao
   tem funcao nenhuma lendo o nome, entao o patch nela falha aqui.
3. Excecoes so por (arquivo, funcao de teste, alvo), com o motivo, em
   PATCH_EXCEPTIONS. Excecao que nao casa mais com nenhum patch tambem falha,
   para a lista nao apodrecer.

FORA DO ALCANCE:
- `patch('m.Classe.metodo')` (tres niveis ou mais) nao entra: altera o objeto
  compartilhado, vale igual pela fachada ou pelo modulo novo.
- `patch.object(modulo, 'nome')` nao e varrido; nao ha nenhum hoje para estes
  modulos. Se aparecer, prefira a forma com string.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

from tests.source_tree_test_support import REPO_ROOT, is_test_file, iter_python_files


# Os cinco modulos que o plano transforma em fachada.
FACADE_MODULES = (
    'public_workouts.models',
    'public_workouts.services',
    'public_workouts.templatetags.public_workouts_extras',
    'student_app.views.public_workout_views',
    'student_identity.public_workout_views',
)

# (arquivo de teste, funcao de teste, alvo do patch): motivo.
PATCH_EXCEPTIONS = {
    (
        'tests/test_public_workout_access_split.py',
        'test_unknown_slug_stays_404_and_published_slug_is_synthesized',
        'public_workouts.services.get_active_program',
    ): (
        'Passa so pela view: _synthesize_public_workout_plan '
        '(student_app/views/public_workout_access.py) importa get_active_program de '
        'public_workouts.services DENTRO da funcao, na hora da chamada, entao o patch na '
        'fachada continua valendo depois da Fase 3. Hoje a regra geral ja cobre (services '
        'ainda define e usa o nome); a excecao vale quando services virar pacote. '
        'NAO vale para test_services_validates_against_catalog_without_importing_view: '
        'ali o caminho e _validate_plan_slug, que le get_active_program como global do '
        'proprio modulo e por isso o patch tem que ir para services.programs.'
    ),
}

_TARGET_RE = re.compile(
    r'^(?P<module>' + '|'.join(re.escape(module) for module in FACADE_MODULES) + r')\.(?P<name>[A-Za-z_]\w*)$'
)


def _iter_test_files():
    this_file = Path(__file__).resolve()
    for path in iter_python_files(skip_migrations=True):
        if path.resolve() != this_file and is_test_file(path):
            yield path


@lru_cache(maxsize=1)
def _collect_patch_targets():
    """((arquivo relativo, funcao de teste, linha, modulo, nome), ...) de cada string-alvo."""
    found = []
    for path in _iter_test_files():
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()

        def visit(node, function_name):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Decorador (@patch) pertence ao teste que ele decora.
                function_name = node.name
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                match = _TARGET_RE.match(node.value)
                if match:
                    found.append((relative, function_name, node.lineno, match['module'], match['name']))
            for child in ast.iter_child_nodes(node):
                visit(child, function_name)

        visit(tree, '<modulo>')
    return tuple(found)


@lru_cache(maxsize=None)
def _names_read_by_module_functions(module_path: str) -> frozenset[str]:
    """Globais que alguma funcao/lambda definida no modulo le na hora da chamada."""
    origin = importlib.util.find_spec(module_path).origin
    tree = ast.parse(Path(origin).read_text(encoding='utf-8'))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Load):
                    names.add(inner.id)
    return frozenset(names)


def test_scan_finds_the_known_patch_targets():
    # Sanidade do proprio scanner: se ele parar de achar os alvos conhecidos de
    # hoje (checkout e OAuth), a guarda passaria por nao ver nada.
    targets = {(module, name) for _file, _func, _line, module, name in _collect_patch_targets()}

    assert ('student_identity.public_workout_views', 'start_subscription_checkout') in targets
    assert ('student_identity.public_workout_views', '_build_public_workout_google_provider') in targets
    assert ('public_workouts.services', 'get_active_program') in targets


def test_patch_targets_on_facade_modules_point_where_the_name_is_looked_up():
    violations = []
    for relative, function_name, line, module, name in _collect_patch_targets():
        if (relative, function_name, f'{module}.{name}') in PATCH_EXCEPTIONS:
            continue
        if name not in _names_read_by_module_functions(module):
            violations.append(f'{relative}:{line} ({function_name}) patch em {module}.{name}')

    assert not violations, (
        'patch() mirando nome que nenhuma funcao do proprio modulo usa; com fachada, o '
        'codigo real escapa do mock. Aponte o patch para o modulo onde o nome e procurado '
        '(ADR-2 de docs/plans/split-arquivos-grandes-plano.md) ou registre a excecao com o '
        'motivo em PATCH_EXCEPTIONS:\n' + '\n'.join(violations)
    )


def test_every_patch_exception_still_matches_a_patch():
    present = {
        (relative, function_name, f'{module}.{name}')
        for relative, function_name, _line, module, name in _collect_patch_targets()
    }
    stale = sorted(key for key in PATCH_EXCEPTIONS if key not in present)

    assert not stale, f'excecoes que nao casam mais com nenhum patch (remova de PATCH_EXCEPTIONS): {stale}'
