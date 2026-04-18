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
# explicito por TEST_DATABASE_URL quando o CI quiser um alvo diferente.
test_database_url = os.getenv('TEST_DATABASE_URL', '').strip()
if test_database_url:
    DATABASES = {
        'default': dj_database_url.parse(
            test_database_url,
            conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
            ssl_require=env_bool('DB_SSL_REQUIRE', False),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }

# Desabilita Celery (Eager mode)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
