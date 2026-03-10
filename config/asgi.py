"""
ARQUIVO: ponto de entrada ASGI do projeto.

POR QUE ELE EXISTE:
- Permite servir o sistema em ambientes compatíveis com ASGI.

O QUE ESTE ARQUIVO FAZ:
1. Carrega as settings do projeto.
2. Expõe a aplicação ASGI para servidores externos.

PONTOS CRITICOS:
- Normalmente não precisa ser alterado no MVP.
- Erros aqui afetam deploys que usem ASGI.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
