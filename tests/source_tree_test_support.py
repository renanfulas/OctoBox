"""
ARQUIVO: varredura da arvore de codigo para testes que leem o repositorio como texto.

POR QUE ELE EXISTE:
- A guarda de patch em fachada (test_facade_patch_guard.py) e a trava de tamanho
  (test_file_size_ratchet.py) precisam do mesmo criterio de "arquivo de teste" e
  da mesma poda de pastas.

PONTO CRITICO:
- os.walk com poda, nunca rglob: no checkout principal ha .venv e
  .claude/worktrees/* (copias inteiras do repo) que um rglob percorreria inteiros.
"""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

_SKIP_DIRS = {'node_modules', '__pycache__', 'staticfiles', 'htmlcov', 'venv'}


def is_test_file(path: Path) -> bool:
    """Mesmo criterio do pytest.ini (tests.py, test_*.py, *_tests.py), mais
    conftest, helpers de teste (`_test_` no nome) e tudo dentro de pastas tests/."""
    name = path.name
    return (
        'tests' in path.relative_to(REPO_ROOT).parts[:-1]
        or name.startswith('test_')
        or name in ('tests.py', 'conftest.py')
        or name.endswith('_tests.py')
        or '_test_' in name
    )


def iter_python_files(*, skip_migrations: bool = False):
    skip = _SKIP_DIRS | {'migrations'} if skip_migrations else _SKIP_DIRS
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.') and d not in skip)
        for filename in sorted(filenames):
            if filename.endswith('.py'):
                yield Path(dirpath) / filename


def count_lines(path: Path) -> int:
    """Mesmo numero do `wc -l`, mais a ultima linha sem quebra; CRLF conta igual."""
    data = path.read_bytes()
    return data.count(b'\n') + (1 if data and not data.endswith(b'\n') else 0)
