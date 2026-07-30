"""
ARQUIVO: implementacao real dos models do app intelligence.

POR QUE ELE EXISTE:
- persiste o feature layer minimo de leads: contagem deterministica por
  canal e janela, versionada e reproduzivel. Nenhum score, nenhum modelo —
  so fato (ver docs/architecture/operational-intelligence-ml-layer.md,
  regra-mestra "ML nunca escreve verdade primaria").

O QUE ESTE ARQUIVO FAZ:
1. define LeadChannelDailyFact: uma celula (janela x canal x procedencia)
   do feature layer de leads.

PONTOS CRITICOS:
- toda saida carrega rule_version + computed_at + input_window, conforme o
  contrato obrigatorio do documento pai. Esta tabela nunca produz
  recomendacao — so contagem; por isso nao existe campo is_recommendation
  aqui (seria uma coluna sempre False, sem informacao nova).
- 'provenance' (declared | legacy_inferred | missing) e o eixo de
  estratificacao, NAO 'confidence_bucket': source_confidence so existe no
  nivel de Student (pos-conversao, via students/domain/acquisition_resolution.py),
  nao no nivel de StudentIntake, que e a materia-prima aqui. Uma copia
  renomeada de provenance como "confidence_bucket" seria fabricar uma
  dimensao sem dado novo — ver desvio registrado em
  docs/plans/leads-ml-technical-execution-guide.md, Onda 6.
"""

from django.db import models

from model_support.base import TimeStampedModel

INTELLIGENCE_APP_LABEL = 'intelligence'


class LeadChannelProvenance(models.TextChoices):
    DECLARED = 'declared', 'Declarado'
    CONFIRMED = 'confirmed', 'Confirmado'
    LEGACY_INFERRED = 'legacy_inferred', 'Inferido de legado'
    MISSING = 'missing', 'Sem atribuicao'


class LeadChannelDailyFact(TimeStampedModel):
    window_start = models.DateField(db_index=True)
    window_end = models.DateField()
    channel = models.CharField(max_length=32, blank=True, db_index=True)
    provenance = models.CharField(max_length=24, choices=LeadChannelProvenance.choices)

    captured_total = models.PositiveIntegerField(default=0)
    converted_total = models.PositiveIntegerField(default=0)
    rejected_total = models.PositiveIntegerField(default=0)
    open_total = models.PositiveIntegerField(default=0)
    median_days_to_conversion = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    rule_version = models.CharField(max_length=32)
    computed_at = models.DateTimeField(db_index=True)
    input_window = models.CharField(max_length=24)

    class Meta:
        app_label = INTELLIGENCE_APP_LABEL
        ordering = ['-window_start', 'channel']
        constraints = [
            models.UniqueConstraint(
                fields=['window_start', 'channel', 'provenance', 'rule_version'],
                name='unique_lead_channel_fact_cell',
            )
        ]
        indexes = [
            models.Index(fields=['window_start', 'channel'], name='lead_channel_fact_window_idx'),
        ]

    def __str__(self):
        return f'{self.window_start}:{self.channel or "(sem canal)"}:{self.provenance}'


__all__ = ['INTELLIGENCE_APP_LABEL', 'LeadChannelDailyFact', 'LeadChannelProvenance']
