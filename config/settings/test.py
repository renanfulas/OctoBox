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

# Database de teste em memória
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desabilita Celery (Eager mode)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
