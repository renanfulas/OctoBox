"""
ARQUIVO: configuracao do app real de auditoria.

POR QUE ELE EXISTE:
- Permite instalar a fronteira de auditoria como app Django proprio.

O QUE ESTE ARQUIVO FAZ:
1. Define o nome tecnico do app.
2. Carrega sinais de auditoria no startup correto.

PONTOS CRITICOS:
- Sem o ready, login e logout deixam de registrar trilha automatica.
"""

from django.apps import AppConfig


class AuditingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditing'

    def ready(self):
        from auditing import signals  # noqa: F401
