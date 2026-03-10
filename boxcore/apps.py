"""
ARQUIVO: configuração oficial do app boxcore no Django.

POR QUE ELE EXISTE:
- Registra o app no ecossistema do Django.

O QUE ESTE ARQUIVO FAZ:
1. Define o nome técnico do app.
2. Define o tipo padrão de chave primária.
3. Carrega sinais de auditoria no startup do app.

PONTOS CRITICOS:
- Trocar o nome do app aqui sem refletir no projeto quebra imports e migrations.
"""

from django.apps import AppConfig


class BoxcoreConfig(AppConfig):
    name = 'boxcore'

    def ready(self):
        from boxcore.auditing import signals  # noqa: F401
