#!/usr/bin/env python
"""
ARQUIVO: ponto de entrada dos comandos do Django.

POR QUE ELE EXISTE:
- Permite rodar o projeto, testes, migrations e comandos administrativos.
- Define qual arquivo de configuração principal será usado.

O QUE ESTE ARQUIVO FAZ:
1. Define o módulo principal de settings do projeto.
2. Carrega o executor de comandos do Django.
3. Encaminha os comandos digitados no terminal.

PONTOS CRITICOS:
- Mudar o DJANGO_SETTINGS_MODULE quebra a inicialização inteira do projeto.
- Erros aqui afetam runserver, test, migrate e qualquer comando interno.
"""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
