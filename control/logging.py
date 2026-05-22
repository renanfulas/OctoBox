"""
ARQUIVO: logging filter para contexto de tenant.

POR QUE ELE EXISTE:
- Logs em produção precisam identificar de qual tenant veio cada linha.
- Sem isto, um erro em box_003 é indistinguível de um erro em box_015.

USO no settings:
    LOGGING = {
        'filters': {
            'tenant_context': {'()': 'control.logging.TenantContextFilter'},
        },
        'formatters': {
            'tenanted': {
                'format': '%(asctime)s [%(tenant)s] %(name)s %(levelname)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'filters': ['tenant_context'],
                'formatter': 'tenanted',
            },
        },
    }
"""

from __future__ import annotations

import logging


class TenantContextFilter(logging.Filter):
    """
    Adiciona o atributo `tenant` ao LogRecord.

    Valor: connection.schema_name (ex.: 'box_001', 'public').
    Se não houver schema ativo (ex.: durante startup), usa 'boot'.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from django.db import connection
            record.tenant = getattr(connection, 'schema_name', None) or 'public'
        except Exception:
            record.tenant = 'boot'
        return True
