import os
os.environ.setdefault('DJANGO_ENV', 'development')
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-secret-key')
os.environ.setdefault('PHONE_BLIND_INDEX_KEY', 'test-only-blind-index-key')
os.environ.setdefault('ENABLE_DEBUG_TOOLBAR', 'false')
from .development import *

# Força o uso de Cache em memória para os testes de telemetria
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Redireciona o Redis para evitar timeouts
REDIS_URL = "redis://localhost:6379/1"

# Database de teste - isola o banco local de `.env` e aceita override
# via TEST_DATABASE_URL (prioritário) ou DATABASE_URL (fallback).
# DATABASE_URL é passado pelo job `test` do performance_check.yml e pelos
# jobs onboarding-corridors / onboarding-real-smoke (que têm serviço PostgreSQL).
#
# Quando DATABASE_URL/TEST_DATABASE_URL está presente, base.py (via
# build_database_config + ENGINE replacement) já configura corretamente
# DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'.
# NÃO rechamar dj_database_url.parse() aqui — isso sobrescreveria o ENGINE
# com 'django.db.backends.postgresql' e quebraria migrate_schemas.
#
# Sem PostgreSQL, cai em SQLite (dev local sem .env ou ambientes especiais)
# e desativa a integração django-tenants que é incompatível com SQLite.
_test_pg_url = (
    os.getenv('TEST_DATABASE_URL', '').strip()
    or os.getenv('DATABASE_URL', '').strip()
)

if _test_pg_url:
    # base.py já parseou DATABASE_URL e garantiu ENGINE=django_tenants.postgresql_backend.
    # Garantir que TEST_DATABASE_URL (quando diferente de DATABASE_URL) seja aplicado
    # re-usando a mesma lógica do base.py, preservando o ENGINE correto.
    import dj_database_url as _dj_db_url
    _parsed = _dj_db_url.parse(
        _test_pg_url,
        conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
        ssl_require=env_bool('DB_SSL_REQUIRE', False),
    )
    # Forçar ENGINE para django_tenants.postgresql_backend independente do que
    # dj_database_url retornar (varia conforme adaptador psycopg2 vs psycopg3).
    _parsed['ENGINE'] = 'django_tenants.postgresql_backend'
    DATABASES = {'default': _parsed}
else:
    # SQLite: django-tenants requer PostgreSQL com suporte a schemas.
    # Remove a integração tenant para que migrate, TenantSyncRouter e pytest
    # funcionem normalmente sobre SQLite (dev local sem DATABASE_URL).
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
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
