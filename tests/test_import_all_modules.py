"""
ARQUIVO: smoke de import do runtime vivo do projeto.

POR QUE ELE EXISTE:
- garante que os modulos canonicos do runtime principal possam ser importados
  sem erro no ambiente de teste.

O QUE ESTE ARQUIVO FAZ:
1. percorre apenas os pacotes canonicos do runtime atual.
2. ignora settings, scripts experimentais, mirror legado e modulos opcionais
   que falham de proposito fora de seus ambientes especificos.
3. reporta falhas de importacao do que realmente compoe o app vivo.

PONTOS CRITICOS:
- este teste mede o runtime principal, nao o repositorio inteiro como arquivo.
- scripts soltos e superficies legadas devem ter trilho proprio, nao poluir
  este smoke.
"""

import importlib
import pkgutil
import unittest


RUNTIME_PACKAGE_PREFIXES = (
    'access',
    'api',
    'auditing',
    'catalog',
    'communications',
    'dashboard',
    'finance',
    'guide',
    'integrations',
    'jobs',
    'knowledge',
    'model_support',
    'monitoring',
    'onboarding',
    'operations',
    'quick_sales',
    'shared_support',
    'student_app',
    'student_identity',
    'students',
)

EXCLUDED_MODULES = {
    'auditing.tasks',
    'boxcore.dashboard.dashboard_views',
    'config.settings.production',
}

EXCLUDED_PREFIXES = (
    'tests',
    'OctoBox',
    'venv',
    '.venv',
)


class ImportAllModulesTest(unittest.TestCase):
    def test_import_all_project_modules(self):
        failures = []
        visited = set()

        for package_name in RUNTIME_PACKAGE_PREFIXES:
            try:
                package = importlib.import_module(package_name)
            except Exception as exc:
                failures.append((package_name, repr(exc)))
                continue

            modules_to_import = [package_name]
            package_path = getattr(package, '__path__', None)
            if package_path is not None:
                for _, module_name, _ in pkgutil.walk_packages(package_path, prefix=f'{package_name}.'):
                    modules_to_import.append(module_name)

            for module_name in modules_to_import:
                if module_name in visited:
                    continue
                visited.add(module_name)

                if module_name in EXCLUDED_MODULES:
                    continue
                if module_name.startswith(EXCLUDED_PREFIXES):
                    continue

                try:
                    importlib.import_module(module_name)
                except Exception as exc:
                    failures.append((module_name, repr(exc)))

        if failures:
            messages = [f'{name}: {error}' for name, error in failures]
            self.fail('Import failures:\n' + '\n'.join(messages))


if __name__ == '__main__':
    unittest.main()
