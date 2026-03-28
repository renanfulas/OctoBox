"""
ARQUIVO: seletor de configuracao por ambiente do projeto.

POR QUE ELE EXISTE:
- Permite usar configuracoes diferentes para desenvolvimento, homologacao e producao sem duplicar tudo.

O QUE ESTE ARQUIVO FAZ:
1. Le a variavel DJANGO_ENV.
2. Carrega development ou production conforme o ambiente.
3. Mantem um ponto unico de entrada para manage.py, WSGI e ASGI.

PONTOS CRITICOS:
- Um valor errado em DJANGO_ENV muda banco, seguranca e comportamento de static files.
"""

import os

environment = os.getenv('DJANGO_ENV', 'development').strip().lower()
explicit_settings_module = os.getenv('DJANGO_SETTINGS_MODULE', '').strip().lower()

# Quando o chamador aponta para um submodulo especifico, como
# `config.settings.test`, o import desse pacote acontece antes do submodulo.
# Nesse caso nao devemos carregar development/production aqui, para nao
# interferir no modulo explicito escolhido.
if explicit_settings_module in {'', __name__.lower()}:
    if environment in {'production', 'staging', 'homolog', 'homologation'}:
        from .production import *  # noqa: F401,F403
    else:
        from .development import *  # noqa: F401,F403
