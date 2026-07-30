"""
ARQUIVO: implementacao real dos models do app intelligence_network.

POR QUE ELE EXISTE:
- persiste o hub de rede: agregado anonimo de canal por cohort de box,
  contribuido por cada tenant (ver intelligence_network/contribution.py).

O QUE ESTE ARQUIVO FAZ:
1. define NetworkChannelAggregate: uma celula (box x canal x janela)
   contribuida por um box ativo.

PONTOS CRITICOS:
- SEM FK cross-schema (licao do Sprint 2 — FK de public para tenant e
  fragil). box_slug e denormalizado, so uma string.
- so contem CONTAGEM agregada: nenhum nome, telefone, email ou qualquer
  campo que identifique aluno ou lead individual.
- box_slug aqui identifica o BOX contribuinte (necessario para o piso de
  k-anonimato contar boxes distintas), nao um aluno — nunca e exposto
  para OUTRO box; so o agregado por cohort (ver intelligence_network/benchmark.py).
- segment_key existe para uso futuro (cruzar canal x segmento de aluno,
  Onda 7); esta onda so contribui no nivel de canal (segment_key='').
"""

from django.db import models

from model_support.base import TimeStampedModel

INTELLIGENCE_NETWORK_APP_LABEL = 'intelligence_network'


class NetworkChannelAggregate(TimeStampedModel):
    box_slug = models.CharField(max_length=64, db_index=True)
    box_cohort = models.CharField(max_length=32, db_index=True)
    segment_key = models.CharField(max_length=64, blank=True, db_index=True)
    channel = models.CharField(max_length=32, db_index=True)
    window = models.CharField(max_length=24)

    captured_total = models.PositiveIntegerField()
    converted_total = models.PositiveIntegerField()
    retained_90d_total = models.PositiveIntegerField(default=0)

    k_floor_applied = models.PositiveSmallIntegerField()
    contributed_at = models.DateTimeField(db_index=True)

    class Meta:
        app_label = INTELLIGENCE_NETWORK_APP_LABEL
        ordering = ['-contributed_at']
        constraints = [
            models.UniqueConstraint(
                fields=['box_slug', 'channel', 'window'],
                name='unique_network_channel_aggregate_cell',
            )
        ]
        indexes = [
            models.Index(fields=['box_cohort', 'channel', 'window'], name='net_channel_cohort_idx'),
        ]

    def __str__(self):
        return f'{self.box_cohort}:{self.channel}:{self.window} ({self.box_slug})'


__all__ = ['INTELLIGENCE_NETWORK_APP_LABEL', 'NetworkChannelAggregate']
