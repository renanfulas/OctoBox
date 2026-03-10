"""
ARQUIVO: ponto de entrada WSGI do projeto.

POR QUE ELE EXISTE:
- Permite servir o sistema em ambientes tradicionais de deploy Django.

O QUE ESTE ARQUIVO FAZ:
1. Carrega as settings do projeto.
2. Expõe a aplicação WSGI para servidores externos.

PONTOS CRITICOS:
- Normalmente não precisa ser alterado no desenvolvimento inicial.
- Erros aqui afetam publicação em produção com WSGI.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
