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
from .base import MIDDLEWARE, env_bool, env_str

DEBUG = env_bool('DJANGO_DEBUG', False)

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
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', True)
SECURE_HSTS_SECONDS = int(__import__('os').getenv('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'