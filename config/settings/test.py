import os

os.environ.setdefault('DJANGO_ENV', 'development')
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-secret-key')
os.environ.setdefault('PHONE_BLIND_INDEX_KEY', 'test-only-blind-index-key')
os.environ.setdefault('ENABLE_DEBUG_TOOLBAR', 'false')

from .development import *

from shared_support.box_runtime import box_partitioned_key_function

# Forca cache em memoria para os testes de telemetria.
#
# Onda 4, Passo 1 (2026-08-26): espelha a MESMA KEY_FUNCTION de producao no
# alias 'default' — sem isso o gate de saida da onda ("suite inteira verde
# com KEY_FUNCTION espelhada") nao provaria nada: a suite rodaria 100% verde
# contra uma config que nao tem a particao por schema, e so quebraria depois,
# em producao. LocMemCache honra KEY_FUNCTION igual Redis (a logica de
# key_func vive em BaseCache, nao por backend) — o teste de fronteira
# (mesma chave logica, dois schemas, sem colisao) e real, nao teatro.
#
# Precisa dos TRES aliases que base.py define:
# - 'default': particionado por schema via KEY_FUNCTION (dado de tenant).
# - 'sessions': SESSION_CACHE_ALIAS aponta aqui, sem KEY_FUNCTION (Onda 4,
#   Passo 0) — sem este alias, todo request autenticado em teste levantaria
#   InvalidCacheBackendError na hora de ler/gravar a sessao.
# - 'platform': chaves globais por design (papel/honeypot por user_id,
#   anti-card-testing), sem KEY_FUNCTION — ver shared_support/platform_cache.py.
# LOCATION diferente entre os tres mantem LocMemCache isolado por alias
# (mesma garantia que KEY_PREFIX diferente da em Redis).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-default',
        'KEY_FUNCTION': box_partitioned_key_function,
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-sessions',
    },
    'platform': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-platform',
    },
}

# Redireciona o Redis para evitar timeouts em testes.
REDIS_URL = 'redis://localhost:6379/1'

# PostgreSQL e o caminho padrao do projeto. TEST_DATABASE_URL tem prioridade
# sobre DATABASE_URL quando a suite roda; sem ambos, base.py usa o PostgreSQL
# local padrao em 127.0.0.1:5433.
#
# Nao rechamar dj_database_url.parse() para DATABASE_URL aqui: base.py ja parseia
# e troca o ENGINE para django_tenants.postgresql_backend. Reparsear por cima
# quebraria migrate_schemas em alguns adaptadores.
_test_pg_url = os.getenv('TEST_DATABASE_URL', '').strip()

if _test_pg_url:
    import dj_database_url as _dj_db_url

    _parsed = _dj_db_url.parse(
        _test_pg_url,
        conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
        ssl_require=env_bool('DB_SSL_REQUIRE', False),
    )
    _parsed['ENGINE'] = 'django_tenants.postgresql_backend'
    DATABASES = {'default': _parsed}

if 'sqlite' in DATABASES['default'].get('ENGINE', ''):
    # Escape legado: django-tenants requer PostgreSQL com suporte a schemas.
    # Remove a integracao tenant apenas quando SQLite foi explicitamente
    # liberado por OCTOBOX_ALLOW_SQLITE_FALLBACK=1.
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django_tenants']
    DATABASE_ROUTERS = [r for r in DATABASE_ROUTERS if 'TenantSyncRouter' not in r]
    MIDDLEWARE = [
        m for m in MIDDLEWARE
        if m not in (
            'control.middleware.TenantBySessionMiddleware',
            'integrations.middleware.WebhookIdempotencyMiddleware',
        )
    ]

# Desabilita Celery (Eager mode)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
