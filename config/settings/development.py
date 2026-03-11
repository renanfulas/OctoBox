"""
ARQUIVO: configuracao de desenvolvimento local.

POR QUE ELE EXISTE:
- Mantem o ambiente local rapido para desenvolvimento sem carregar o endurecimento completo de producao.

O QUE ESTE ARQUIVO FAZ:
1. Liga DEBUG por padrao.
2. Usa SQLite quando DATABASE_URL nao for informado.
3. Relaxa cookies e HTTPS para rodar localmente.

PONTOS CRITICOS:
- Esse arquivo nao deve ser usado como referencia de seguranca para homologacao publica ou producao.
"""

from .base import *  # noqa: F401,F403
from .base import env_bool

DEBUG = env_bool('DJANGO_DEBUG', True)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'