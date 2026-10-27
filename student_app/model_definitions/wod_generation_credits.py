"""Monthly usage ledger for automatic workout generation."""

from django.db import models

from model_support.base import TimeStampedModel


class WodGenerationCreditLedger(TimeStampedModel):
    """Cota mensal de geracoes automaticas de treino via Haiku ("Monte um treino pra mim").

    Por que existe:
    - a geracao automatica de treino (Fase 3, futura) vai consumir 1 credito por uso.
    - a cota e por BOX, nao por coach — o modelo vive no TENANT_APP student_app, entao o
      isolamento por box ja vem do schema (sem precisar de FK pra Box).
    - um "periodo" e um mes-calendario (dia 1 a dia 1 do mes seguinte); cada mes tem sua
      propria linha, criada sob demanda (get_or_create_current_ledger) — reset automatico,
      sem job agendado.

    Pontos criticos:
    - free_credits_used nunca ultrapassa free_credits_total (consumo checa antes de gastar).
    - purchased_credits_available e alimentado pelo webhook de pagamento avulso (Fase 2,
      ainda nao implementada) — fica zerado ate la, sem quebrar nada.
    - consumo deve rodar dentro de transaction.atomic + select_for_update (ver
      operations/services/wod_generation_credits.py) pra nao dar credito duplo sob
      concorrencia (dois cliques quase simultaneos no botao).
    """

    period_start = models.DateField(unique=True)
    free_credits_total = models.PositiveSmallIntegerField(default=2)
    free_credits_used = models.PositiveSmallIntegerField(default=0)
    purchased_credits_available = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Cota de Geracao de Treino (Haiku)'
        verbose_name_plural = 'Cotas de Geracao de Treino (Haiku)'
        ordering = ['-period_start']

    @property
    def free_credits_remaining(self):
        return max(0, self.free_credits_total - self.free_credits_used)

    @property
    def credits_remaining(self):
        return self.free_credits_remaining + self.purchased_credits_available

    def __str__(self):
        return f'Creditos {self.period_start:%m/%Y}: {self.credits_remaining} restantes'



__all__ = ['WodGenerationCreditLedger']
