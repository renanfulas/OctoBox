"""
ARQUIVO: testes dos helpers de configuracao base.

POR QUE ELE EXISTE:
- protege a troca entre cache local de desenvolvimento e cache compartilhado de producao.

O QUE ESTE ARQUIVO FAZ:
1. garante fallback local quando nenhuma URL de cache foi configurada.
2. garante backend Redis compartilhado quando REDIS_URL ou CACHE_URL existem.
"""

import os
from unittest.mock import patch

from django.test import SimpleTestCase

from config.settings.base import build_cache_config, is_local_runtime_mode


class SettingsHelperTests(SimpleTestCase):
    def test_is_local_runtime_mode_is_false_when_env_is_empty_and_debug_is_off(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_local_runtime_mode())

    def test_is_local_runtime_mode_uses_development_env_explicitly(self):
        with patch.dict(os.environ, {'DJANGO_ENV': 'development'}, clear=True):
            self.assertTrue(is_local_runtime_mode())

    def test_is_local_runtime_mode_uses_debug_flag_explicitly(self):
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'true'}, clear=True):
            self.assertTrue(is_local_runtime_mode())

    def test_build_cache_config_uses_locmem_when_no_external_cache_url_exists(self):
        with patch.dict(os.environ, {}, clear=True):
            cache_config = build_cache_config()

        self.assertEqual(cache_config['BACKEND'], 'django.core.cache.backends.locmem.LocMemCache')
        self.assertEqual(cache_config['LOCATION'], 'octobox-default')

    def test_build_cache_config_uses_redis_when_redis_url_exists(self):
        with patch.dict(os.environ, {'REDIS_URL': 'redis://cache.example:6379/1'}, clear=True):
            cache_config = build_cache_config()

        self.assertEqual(cache_config['BACKEND'], 'django_redis.cache.RedisCache')
        self.assertEqual(cache_config['LOCATION'], 'redis://cache.example:6379/1')
        self.assertEqual(cache_config['KEY_PREFIX'], 'octobox')
        self.assertTrue(cache_config['OPTIONS']['IGNORE_EXCEPTIONS'])

    def test_build_cache_config_allows_disabling_ignore_exceptions_explicitly(self):
        with patch.dict(
            os.environ,
            {
                'REDIS_URL': 'redis://cache.example:6379/1',
                'CACHE_IGNORE_EXCEPTIONS': 'false',
            },
            clear=True,
        ):
            cache_config = build_cache_config()

        self.assertFalse(cache_config['OPTIONS']['IGNORE_EXCEPTIONS'])