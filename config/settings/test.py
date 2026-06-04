import os

os.environ.setdefault('DJANGO_ENV', 'development')
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-secret-key')
os.environ.setdefault('PHONE_BLIND_INDEX_KEY', 'test-only-blind-index-key')
os.environ.setdefault('ENABLE_DEBUG_TOOLBAR', 'false')

from .development import *

# Forca cache em memoria para os testes de telemetria.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
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
