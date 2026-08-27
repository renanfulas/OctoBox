"""
ARQUIVO: gate de saida da Onda 4 (particionamento de cache por box).
docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md

POR QUE EXISTE:
- Prova os tres itens do gate de saida da onda: (1) mesma chave logica em
  dois schemas nao colide mais no alias 'default' (o oposto do que a
  demonstracao original do plano provou antes do fix); (2) chaves do alias
  'platform' permanecem globais por design, mesmo com KEY_FUNCTION ativa no
  'default'; (3) um ciclo de login+request autenticado completo nao quebra
  sob Redis REAL (RealRedisLoginCycleTests) — LocMemCache sozinho nao prova
  o gate, porque o mecanismo de KEY_FUNCTION eh identico entre backends mas
  o proprio plano pede explicitamente "nao LocMem" para o passo de login.
- Cobre tambem o bug nomeado explicitamente no corpo da Onda 4: antes desta
  onda, export_quota:{user_id}:{scope} somava exportacoes entre boxes
  (superdev, com Membership em todos os boxes, esgotava a cota de um box
  por atividade em outro).

ESTRATEGIA:
- _as_schema(slug) segue o MESMO padrao ja usado em
  tests/test_tenant_isolation_observability.py::_as_box — seta
  connection.schema_name direto, sem exigir que o schema exista de verdade
  (as operacoes aqui sao so de cache, nunca tocam o banco).
"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager

from django.core.cache import cache, caches
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.module_loading import import_string

from access.roles import ROLE_HONEYPOT
from shared_support.box_runtime import box_partitioned_key_function
from shared_support.platform_cache import platform_cache


@contextmanager
def _as_schema(slug):
    """Simula 'box <slug> ativo' setando connection.schema_name (o que
    get_box_runtime_slug le) — mesmo padrao de _as_box em
    test_tenant_isolation_observability.py. Nao toca o banco."""
    prev = getattr(connection, 'schema_name', None)
    connection.schema_name = slug
    try:
        yield
    finally:
        connection.schema_name = prev


class DefaultCachePartitionsBySchemaTests(TestCase):
    """Alias 'default': KEY_FUNCTION espelhada em config/settings/test.py
    (Onda 4, Passo 1) — mesmo mecanismo (BaseCache.key_func) do Redis de
    producao. Cobertura contra Redis real vive em RealRedisLoginCycleTests."""

    def tearDown(self):
        with _as_schema('box_alpha_cachetest'):
            cache.delete('segredo')
        with _as_schema('box_beta_cachetest'):
            cache.delete('segredo')

    def test_same_logical_key_does_not_leak_across_schemas(self):
        with _as_schema('box_alpha_cachetest'):
            cache.set('segredo', 'SEGREDO-ALPHA', timeout=30)

        with _as_schema('box_beta_cachetest'):
            # Antes do fix, esta leitura devolvia 'SEGREDO-ALPHA' (vazamento
            # demonstrado no corpo da Onda 4 do plano).
            self.assertIsNone(cache.get('segredo'))
            cache.set('segredo', 'SEGREDO-BETA', timeout=30)

        with _as_schema('box_alpha_cachetest'):
            self.assertEqual(cache.get('segredo'), 'SEGREDO-ALPHA')

    def test_export_quota_does_not_bleed_between_boxes(self):
        """Bug nomeado explicitamente no corpo da Onda 4 do plano."""
        from shared_support.security import check_export_quota

        with _as_schema('box_alpha_cachetest'):
            self.assertTrue(check_export_quota(user_id=990001, scope='annual', limit=2)[0])
            self.assertTrue(check_export_quota(user_id=990001, scope='annual', limit=2)[0])
            allowed, _ = check_export_quota(user_id=990001, scope='annual', limit=2)
            self.assertFalse(allowed, 'cota deveria estar esgotada em A')

        with _as_schema('box_beta_cachetest'):
            allowed, _ = check_export_quota(user_id=990001, scope='annual', limit=2)
            self.assertTrue(
                allowed,
                'cota de B foi contaminada pelo consumo em A — regressao do bug nomeado no plano',
            )

        with _as_schema('box_alpha_cachetest'):
            cache.delete('export_quota:990001:annual')
        with _as_schema('box_beta_cachetest'):
            cache.delete('export_quota:990001:annual')


class PlatformCacheStaysGlobalTests(TestCase):
    """Alias 'platform': NUNCA deve particionar por schema — chaves indexadas
    por user_id (auth_user so existe em public) ou que protegem um recurso
    compartilhado (conta Stripe unica) precisam do MESMO valor em qualquer
    schema, senao a invalidacao de papel e o labirinto do honeypot furam."""

    def tearDown(self):
        platform_cache.delete('chave_global_onda4')

    def test_same_logical_key_is_visible_across_schemas(self):
        with _as_schema('box_alpha_cachetest'):
            platform_cache.set('chave_global_onda4', 'VALOR-UNICO', timeout=30)

        with _as_schema('box_beta_cachetest'):
            self.assertEqual(platform_cache.get('chave_global_onda4'), 'VALOR-UNICO')

    def test_honeypot_trigger_in_one_box_is_visible_in_another(self):
        """Fio-a-fio do Passo 3: honeypot_service + access.roles.get_user_role
        precisam concordar no MESMO alias, senao um atacante marcado escapa
        do labirinto so trocando de box."""
        from shared_support.security.honeypot_service import (
            SHADOW_ROLE_CACHE_PREFIX,
            is_honeypot_active_globally,
            trigger_honeypot_for_user,
        )

        fake_user_id = 990002
        try:
            with _as_schema('box_alpha_cachetest'):
                trigger_honeypot_for_user(fake_user_id)

            with _as_schema('box_beta_cachetest'):
                self.assertTrue(is_honeypot_active_globally())
                self.assertEqual(
                    platform_cache.get(f'{SHADOW_ROLE_CACHE_PREFIX}{fake_user_id}'),
                    ROLE_HONEYPOT,
                )
        finally:
            platform_cache.delete(f'{SHADOW_ROLE_CACHE_PREFIX}{fake_user_id}')
            platform_cache.delete('octobox:honeypot:active_threats')


# ---------------------------------------------------------------------------
# Gate (3): "login de staff funcionando sob a KEY_FUNCTION ativa, com
# Postgres real, nao LocMem" — CACHES['test'] usa LocMemCache (necessario
# pros dois blocos acima rodarem sem depender de infra externa). Este bloco
# troca so os TRES aliases de cache para Redis real via override_settings,
# mantendo o Postgres real que a suite ja usa (pytest-django/TestCase).
# ---------------------------------------------------------------------------

_REDIS_URL = (
    os.environ.get('REDIS_URL')
    or os.environ.get('CACHE_URL')
    # Container local (docker-compose.postgres.yml + redis) remapeia
    # 6379/tcp -> 6380 no host, mesmo padrao do Postgres em 5433.
    or 'redis://127.0.0.1:6380/1'
)


def _real_redis_cache_config(key_prefix, *, key_function=None):
    config = {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': _REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        # Prefixo exclusivo deste teste — nunca colide com chaves reais de
        # dev/producao (que usam 'octobox'/'octobox-sessions'/'octobox-platform').
        'KEY_PREFIX': key_prefix,
    }
    if key_function is not None:
        config['KEY_FUNCTION'] = key_function
    return config


_REAL_REDIS_CACHES = {
    'default': _real_redis_cache_config('octobox-test-realredis-default', key_function=box_partitioned_key_function),
    'sessions': _real_redis_cache_config('octobox-test-realredis-sessions'),
    'platform': _real_redis_cache_config('octobox-test-realredis-platform'),
}


def _real_redis_is_reachable() -> bool:
    try:
        _real_redis_config = _real_redis_cache_config('octobox-test-realredis-healthcheck')
        backend_cls = import_string(_real_redis_config['BACKEND'])
        backend = backend_cls(_real_redis_config['LOCATION'], _real_redis_config)
        backend.set('onda4_healthcheck', '1', timeout=5)
        return True
    except Exception:
        return False


@unittest.skipUnless(
    _real_redis_is_reachable(),
    'Redis real indisponivel para este gate (ver ADR/plano da Onda 4) — '
    'CI hoje declara REDIS_URL mas nao sobe um service container de Redis.',
)
@override_settings(CACHES=_REAL_REDIS_CACHES)
class RealRedisLoginCycleTests(TestCase):
    """Gate (3) do plano. IMPORTANTE: nunca chamar .clear() nos aliases
    aqui — django-redis faz FLUSHDB da conexao inteira, que pode ser
    compartilhada com o Redis de dev local. Limpeza e sempre por chave
    explicita, sob o KEY_PREFIX exclusivo deste teste.

    BUG REAL ACHADO EM CI (docs/plans/ondas-correcao-tenancy-billing-
    2026-08-25.md, bloco da Onda 4): a versao anterior checava
    disponibilidade do Redis DENTRO de setUpClass, DEPOIS de chamar
    super().setUpClass() — que ja abre o bloco atomic() de classe do
    TestCase. Levantar unittest.SkipTest a partir dai faz o unittest pular
    tearDownClass (e assim o rollback desse atomic) por design — a
    conexao do worker xdist fica com uma transacao pendurada, e QUALQUER
    teste rodando depois no mesmo worker (nao so deste arquivo) quebra com
    psycopg.OperationalError('the connection is closed'). Reproduzido
    isolando os 3 arquivos de teste novos desta PR um a um contra o CI real
    (que declara REDIS_URL mas nao sobe nenhum service container de Redis
    — a causa raiz nao e concorrencia, e essa combinacao especifica).
    Fix: decidir o skip ANTES de super().setUpClass() rodar, via
    @unittest.skipUnless no nivel da classe — nao ha atomic() pra sobrar
    pendurado se a classe inteira nunca chega a ser montada."""

    def test_authenticated_request_cycle_does_not_400_or_logout(self):
        """Reproduz o mecanismo do bug descrito no corpo da Onda 4: sem o
        pre-requisito do Passo 0 (sessao em alias proprio, sem
        KEY_FUNCTION), esta segunda request devolveria HTTP 400
        (SessionInterrupted) ou trataria a sessao como nova (logout
        silencioso)."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username='onda4-login-probe',
            password='senha-forte-onda4-2026',
            email='onda4-probe@example.com',
        )
        self.client.force_login(user)

        first = self.client.get(reverse('role-operations'))
        self.assertNotEqual(first.status_code, 400, 'HTTP 400 = SessionInterrupted (bug que o Passo 0 fecha)')

        second = self.client.get(reverse('role-operations'))
        self.assertNotEqual(second.status_code, 400)
        self.assertEqual(
            second.status_code, first.status_code,
            'status mudou entre duas requests autenticadas seguidas — sinal de logout silencioso',
        )

    def test_default_cache_still_partitions_by_schema_under_real_redis(self):
        with _as_schema('box_alpha_realredis'):
            cache.set('segredo_redis', 'ALPHA', timeout=30)
        try:
            with _as_schema('box_beta_realredis'):
                self.assertIsNone(cache.get('segredo_redis'))
        finally:
            with _as_schema('box_alpha_realredis'):
                cache.delete('segredo_redis')
