"""
ARQUIVO: modelos de configuração operacional do guide.

POR QUE ELE EXISTE:
- Centraliza as configurações dinâmicas do guide, permitindo ajustes sem deploy.

O QUE ESTE ARQUIVO FAZ:
1. Define o modelo OperationalRuntimeSetting para armazenar pares chave-valor.
2. Registra o usuário e data de atualização de cada configuração.

PONTOS CRITICOS:
- Mudanças no modelo podem impactar a leitura e escrita de configurações em tempo real.
"""
from django.conf import settings
from django.db import models


class OperationalRuntimeSetting(models.Model):
    key = models.CharField(max_length=120, unique=True)
    value = models.CharField(max_length=120)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operational_runtime_settings_updated',
    )

    class Meta:
        verbose_name = 'Configuracao operacional'
        verbose_name_plural = 'Configuracoes operacionais'

    def __str__(self):
        return f'{self.key}={self.value}'