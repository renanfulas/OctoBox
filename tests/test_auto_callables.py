"""
ARQUIVO: smoke estrutural dos entrypoints basicos do projeto.

POR QUE ELE EXISTE:
- substitui o antigo teste que executava callables arbitrarios sem contrato.
- protege o boot minimo do projeto sem disparar side effects aleatorios.

O QUE ESTE ARQUIVO FAZ:
1. valida o roteamento de settings do `manage.py`.
2. garante que `manage.main()` carrega env e delega ao Django corretamente.

PONTOS CRITICOS:
- este teste mede boot estrutural, nao cobertura generica de helpers.
- novas validacoes aqui devem usar entrypoints explicitos e seguros.
"""

import os
import unittest
from unittest.mock import patch

import manage


class StructuralEntryPointsSmokeTest(unittest.TestCase):
    def test_default_settings_module_switches_to_test_for_test_command(self):
        self.assertEqual(
            manage._default_settings_module(['manage.py', 'test']),
            'config.settings.test',
        )
        self.assertEqual(
            manage._default_settings_module(['manage.py', 'check']),
            'config.settings',
        )

    def test_is_test_command_only_flags_django_test_subcommand(self):
        self.assertTrue(manage._is_test_command(['manage.py', 'test']))
        self.assertFalse(manage._is_test_command(['manage.py']))
        self.assertFalse(manage._is_test_command(['manage.py', 'tests\\test_auto_callables.py']))
        self.assertFalse(manage._is_test_command(['manage.py', 'check']))

    @patch.dict(os.environ, {}, clear=True)
    @patch('manage.load_project_env')
    @patch('django.core.management.execute_from_command_line')
    @patch('manage.sys.argv', ['manage.py', 'check'])
    def test_manage_main_loads_env_and_delegates_to_django(self, execute_mock, load_env_mock):
        manage.main()

        load_env_mock.assert_called_once_with(manage.BASE_DIR, include_test_file=False)
        self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.settings')
        execute_mock.assert_called_once_with(['manage.py', 'check'])

    @patch.dict(os.environ, {}, clear=True)
    @patch('manage.load_project_env')
    @patch('django.core.management.execute_from_command_line')
    @patch('manage.sys.argv', ['manage.py', 'test'])
    def test_manage_main_uses_test_settings_for_test_subcommand(self, execute_mock, load_env_mock):
        manage.main()

        load_env_mock.assert_called_once_with(manage.BASE_DIR, include_test_file=True)
        self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.settings.test')
        execute_mock.assert_called_once_with(['manage.py', 'test'])


if __name__ == '__main__':
    unittest.main()
