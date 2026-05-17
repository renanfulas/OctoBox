import os
os.environ.setdefault('DJANGO_ENV', 'development')
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-secret-key')
os.environ.setdefault('PHONE_BLIND_INDEX_KEY', 'test-only-blind-index-key')
os.environ.setdefault('ENABLE_DEBUG_TOOLBAR', 'false')
from .development import *
import dj_database_url

# Força o uso de Cache em memória para os testes de telemetria
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Redireciona o Redis para evitar timeouts
REDIS_URL = "redis://localhost:6379/1"

# Database de teste - isola o banco local de `.env` e aceita override
# via TEST_DATABASE_URL (prioritário) ou DATABASE_URL (fallback, usado no job `test`
# do performance_check.yml que sobe um serviço postgres mas passa DATABASE_URL).
# Quando nenhuma variável PostgreSQL está definida (ex.: onboarding-corridors no CI
# que só tem SQLite disponível), cai no branch SQLite e desativa a integração
# django-tenants, que é incompatível com SQLite (requer schema_name no backend).
_test_pg_url = (
    os.getenv('TEST_DATABASE_URL', '').strip()
    or os.getenv('DATABASE_URL', '').strip()
)

if _test_pg_url:
    DATABASES = {
        'default': dj_database_url.parse(
            _test_pg_url,
            conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
            ssl_require=env_bool('DB_SSL_REQUIRE', False),
        )
    }
    # django-tenants exige backend PostgreSQL tenant-aware.
    # dj_database_url retorna 'django.db.backends.postgresql' — substituir.
    _engine = DATABASES['default'].get('ENGINE', '')
    if (
        _engine in ('django.db.backends.postgresql', 'django.db.backends.postgresql_psycopg2')
        or _engine.endswith('psycopg')
    ):
        DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'
else:
    # SQLite: django-tenants requer PostgreSQL com suporte a schemas.
    # Remove a integração tenant para que migrate, TenantSyncRouter e pytest
    # funcionem normalmente sobre SQLite (jobs onboarding-corridors e onboarding-real-smoke).
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django_tenants']
    DATABASE_ROUTERS = [r for r in DATABASE_ROUTERS if 'TenantSyncRouter' not in r]

# Desabilita Celery (Eager mode)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
