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
