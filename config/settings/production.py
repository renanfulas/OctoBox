"""
ARQUIVO: configuracao de homologacao e producao.

POR QUE ELE EXISTE:
- Endurece o projeto para deploy publico com PostgreSQL, HTTPS e static files de forma previsivel.

O QUE ESTE ARQUIVO FAZ:
1. Desliga DEBUG por padrao.
2. Ativa WhiteNoise para servir static files de forma simples e estavel.
3. Endurece cookies, redirecionamento SSL e cabecalhos de seguranca.
4. Mantem homologacao e producao no mesmo trilho de configuracao.

PONTOS CRITICOS:
- Esse ambiente exige DJANGO_SECRET_KEY forte e ALLOWED_HOSTS correto.
- Se DATABASE_URL estiver errado, a aplicacao nao sobe.
"""

from .base import *  # noqa: F401,F403
from .base import (
    MIDDLEWARE,
    build_https_trusted_origins,
    env_bool,
    env_list_alias,
    env_str,
    merge_public_host_contract,
)
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


DEBUG = env_bool('DJANGO_DEBUG', False)

# 🚀 Segurança de Elite: Isolamento de Host (Previne Host Header Injection)
ALLOWED_HOSTS = env_list_alias(('DJANGO_ALLOWED_HOSTS', 'ALLOWED_HOSTS'), 'octobox.app,www.octobox.app')
CSRF_TRUSTED_ORIGINS = env_list_alias(('DJANGO_CSRF_TRUSTED_ORIGINS', 'CSRF_TRUSTED_ORIGINS'))
CSRF_TRUSTED_ORIGINS = sorted(
    dict.fromkeys([*CSRF_TRUSTED_ORIGINS, *build_https_trusted_origins(ALLOWED_HOSTS)])
)
ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS = merge_public_host_contract(
    ALLOWED_HOSTS,
    CSRF_TRUSTED_ORIGINS,
    extra_hosts=[env_str('RENDER_EXTERNAL_HOSTNAME')],
)

_configured_secret_key = env_str('DJANGO_SECRET_KEY')
if not _configured_secret_key or _configured_secret_key == 'dev-only-secret-key-change-me':
    raise RuntimeError('DJANGO_SECRET_KEY forte e obrigatoria em homologacao/producao.')

MIDDLEWARE = [
    MIDDLEWARE[0],
    'whitenoise.middleware.WhiteNoiseMiddleware',
    *MIDDLEWARE[1:],
]

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SECURE_HSTS_SECONDS = int(__import__('os').getenv('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = 'same-origin'

sentry_dsn = env_str('SENTRY_DSN')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=env_bool('SENTRY_TRACES_SAMPLE_RATE', 0.2),
        send_default_pii=False  # 🚀 Segurança (Epic 8): LGPD enforced
    )

# 🚀 Performance de Elite (Epic 8): Garante Redis em Produção
if not DEBUG and not env_str('REDIS_URL') and not env_str('CACHE_URL'):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('REDIS_URL obrigatoria para Cache em Producao/Homologacao.')
