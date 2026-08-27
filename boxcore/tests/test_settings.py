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

from django.conf import settings
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
        # Sem REDIS_URL, build_cache_config faz fallback para locmem
        # APENAS em runtime local (dev). Em prod/staging exige REDIS_URL
        # (Epic 8: hardening explicito). Marcar DJANGO_DEBUG=true sinaliza
        # ambiente local — sem isso o teste antigo passava apenas porque
        # o env de pytest tinha algum DEBUG herdado.
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'true'}, clear=True):
            cache_config = build_cache_config()

        self.assertEqual(cache_config['BACKEND'], 'django.core.cache.backends.locmem.LocMemCache')
        # Sprint 4 schema-per-tenant: LOCATION incorpora sufixo do tenant
        # ativo via build_box_cache_key_prefix para isolar caches entre
        # boxes. Em pytest e 'octobox-default:box_test'; em DEV legado
        # era 'octobox-default'.
        self.assertTrue(cache_config['LOCATION'].startswith('octobox-default'))

    def test_build_cache_config_uses_redis_when_redis_url_exists(self):
        with patch.dict(os.environ, {'REDIS_URL': 'redis://cache.example:6379/1'}, clear=True):
            cache_config = build_cache_config()

        self.assertEqual(cache_config['BACKEND'], 'django_redis.cache.RedisCache')
        self.assertEqual(cache_config['LOCATION'], 'redis://cache.example:6379/1')
        # Sprint 4 schema-per-tenant: KEY_PREFIX inclui sufixo do tenant
        # ativo (ver comentario equivalente no teste anterior).
        self.assertTrue(cache_config['KEY_PREFIX'].startswith('octobox'))
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

    def test_build_cache_config_key_function_is_opt_in(self):
        # Onda 4: sem key_function explicito, nenhum alias ganha KEY_FUNCTION
        # por acidente — só 'default' deve receber (ver CACHES em base.py).
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'true'}, clear=True):
            cache_config = build_cache_config()
        self.assertNotIn('KEY_FUNCTION', cache_config)

    def test_build_cache_config_key_function_is_passed_through_when_given(self):
        def _dummy_key_function(key, key_prefix, version):
            return f'{key_prefix}:{version}:{key}'

        with patch.dict(os.environ, {'DJANGO_DEBUG': 'true'}, clear=True):
            cache_config = build_cache_config(key_function=_dummy_key_function)
        self.assertIs(cache_config['KEY_FUNCTION'], _dummy_key_function)

    def test_only_default_alias_has_key_function_in_real_settings(self):
        # Onda 4, Passo 0 e Passo 3: 'sessions' e 'platform' NUNCA podem
        # ganhar KEY_FUNCTION — sessão particionada por schema derruba login
        # em produção (ver comentário em SESSION_CACHE_ALIAS); chave global
        # particionada por schema quebra invalidação de papel e o labirinto
        # do honeypot (ver shared_support/platform_cache.py).
        self.assertIn('KEY_FUNCTION', settings.CACHES['default'])
        self.assertNotIn('KEY_FUNCTION', settings.CACHES['sessions'])
        self.assertNotIn('KEY_FUNCTION', settings.CACHES['platform'])