"""
ARQUIVO: teste de importação de todos os módulos do projeto.

POR QUE ELE EXISTE:
- Garante que todos os módulos do projeto possam ser importados sem erro, protegendo contra regressões de import.

O QUE ESTE ARQUIVO FAZ:
1. Percorre todos os módulos do projeto e tenta importá-los.
2. Reporta falhas de importação para facilitar manutenção e refatoração.

PONTOS CRÍTICOS:
- Falhas aqui indicam problemas de dependência ou erros de importação que podem quebrar o deploy ou testes.
"""
import os
import sys
import pkgutil
import importlib
import unittest


class ImportAllModulesTest(unittest.TestCase):
    def test_import_all_project_modules(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        failures = []

        for finder, name, ispkg in pkgutil.walk_packages([project_root]):
            # skip virtualenvs and hidden dirs
            if name.startswith('venv') or name.startswith('.venv'):
                continue
            # avoid importing tests package itself recursively
            if name.startswith('tests'):
                continue

            try:
                importlib.import_module(name)
            except Exception as exc:
                failures.append((name, repr(exc)))

        if failures:
            msgs = [f"{n}: {e}" for n, e in failures]
            self.fail('Import failures:\n' + '\n'.join(msgs))


if __name__ == '__main__':
    unittest.main()
