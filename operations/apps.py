"""
ARQUIVO: configuracao do app operations.

POR QUE ELE EXISTE:
- transforma a fronteira operations em app Django real para receber rotas e views proprias.

O QUE ESTE ARQUIVO FAZ:
1. registra o app operations no projeto.

PONTOS CRITICOS:
- esse app deve concentrar a casca HTTP operacional sem trazer models de volta para dentro dele.
"""

from django.apps import AppConfig


class OperationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'operations'
    verbose_name = 'Operations'

    def ready(self):
        from operations.signals.session_cancellation import connect_session_cancellation_signal
        connect_session_cancellation_signal()
