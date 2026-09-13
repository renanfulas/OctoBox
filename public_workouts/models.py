"""
ARQUIVO: modelos do corredor publico de treinos (/renan/): avaliacao fisica
e, a partir da Onda B2 do CORDA, cobranca (assinatura, pagamento, regua de
avisos).

POR QUE ELE EXISTE:
- a aba "Avaliacoes" precisa persistir historico de peso/medidas em banco
  (nao localStorage) para sobreviver a troca de aparelho/navegador.
- Onda B2: o corredor cobra o aluno diretamente (consultoria online),
  nunca atraves de finance.Payment (V3 do CORDA — misturaria a receita de
  consultoria com o financeiro do box).

PONTOS CRITICOS:
- este app vive em SHARED_APPS (schema public) de proposito: as views do
  corredor publico rodam SEM tenant (ver student_app/views/public_workout_views.py).
  Um modelo em TENANT_APP simplesmente nao existe fora de um schema de box —
  funcionaria nos testes (conftest forca schema_context) e quebraria em
  producao. `plan_slug` e uma referencia "soft" a PUBLIC_WORKOUT_LIBRARY
  (dict Python em public_workout_views.py) — nao ha FK porque o outro lado
  nao e uma tabela.
- auditing.AuditEvent (log_audit_event) e TENANT_APPS — vive por schema de
  box. Chama-lo daqui quebraria do mesmo jeito que R2 do CORDA documenta
  (relation nao existe fora de um schema de box). PublicWorkoutSubscriptionEvent
  abaixo e o equivalente do corredor: mesmo proposito (quem, o que, por
  que), no schema onde o corredor de fato roda.
- Propriedade de diretorio (D.4 do CORDA): este arquivo e migrations/ sao
  da Frente A. PublicWorkoutSubscription/PublicWorkoutPayment/
  PublicWorkoutPaymentNotice sao pedidos pela Frente B (Onda B2) mas
  criados aqui por instrucao explicita do proprio CORDA ("O que entra"
  da Onda B2) — a excecao documentada a regra, nao uma violacao dela.
"""

from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models


class PublicWorkoutAssessment(models.Model):
    plan_slug = models.CharField(max_length=50, db_index=True)
    measured_at = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Override manual (ex.: leitura de bioimpedancia, ou ja calculado via
    # adipometro/Jackson-Pollock). Quando vazio, o relatorio estima BF% pelo
    # metodo US Navy a partir de `measurements` (ver public_workouts/formulas.py).
    body_fat_percent = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    # De onde veio body_fat_percent — so texto livre curto pro relatorio
    # rotular certo ('device', 'skinfold_jp3', 'manual'). Vazio + sem
    # body_fat_percent = o relatorio cai pra estimativa US Navy.
    body_fat_source = models.CharField(max_length=20, blank=True)
    # Vocabulario de chaves conhecido (nao imposto pelo banco de proposito —
    # cada aluno mede um subconjunto diferente): pescoco, cintura, quadril,
    # peito, braco, coxa, panturrilha. Todos em cm.
    measurements = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'public_workout_assessments'
        ordering = ['plan_slug', 'measured_at']
        indexes = [models.Index(fields=['plan_slug', 'measured_at'])]

    def __str__(self) -> str:
        return f'{self.plan_slug} @ {self.measured_at}'


# ---------------------------------------------------------------------------
# Cobranca do corredor (Onda B2 do CORDA). NUNCA finance.Payment (V3): essa
# receita e de consultoria online, nao de mensalidade de box — misturar
# alimentaria overdue_metrics e o financeiro errado (N3 do CORDA documenta
# essa lacuna como escopo futuro, nao bug desta entrega).
# ---------------------------------------------------------------------------


class PublicWorkoutSubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Ativa'
    PAST_DUE = 'past_due', 'Em atraso'
    SUSPENDED = 'suspended', 'Suspensa'
    CANCELED = 'canceled', 'Cancelada'


class PublicWorkoutSubscription(models.Model):
    """Assinatura recorrente do aluno ao corredor de treinos.

    NAO e StudentBoxMembership (D.0 do CORDA): o aluno de consultoria nao
    frequenta aula, nao tem Attendance. A trava do /renan/ consulta este
    model, nunca o do box.
    """

    # student_identity.PublicWorkoutAccount — mesmo raciocinio de
    # student_identity_id em outros modelos do corredor: referencia fraca
    # seria o padrao para FK cross-schema, mas aqui os dois apps sao
    # SHARED_APPS (schema public), entao uma FK de verdade e segura.
    account = models.OneToOneField(
        'student_identity.PublicWorkoutAccount',
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan_slug = models.CharField(max_length=50, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=PublicWorkoutSubscriptionStatus.choices,
        default=PublicWorkoutSubscriptionStatus.ACTIVE,
        db_index=True,
    )
    # Connect Express (R.C do CORDA): conta do personal que recebe o
    # repasse. Resolvida no checkout (stripe_checkout.py), nunca herdada
    # de stripe.api_key global (C1 — race condition com mais de uma conta).
    stripe_connected_account_id = models.CharField(max_length=255, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.plan_slug} [{self.status}]'


class PublicWorkoutSubscriptionEvent(models.Model):
    """Trilha de auditoria de mudanca de estado da assinatura — equivalente
    do corredor a log_audit_event (ver nota no topo do arquivo)."""

    subscription = models.ForeignKey(PublicWorkoutSubscription, on_delete=models.CASCADE, related_name='events')
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.subscription_id}: {self.from_status} -> {self.to_status} ({self.reason})'


class PublicWorkoutPaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    PAID = 'paid', 'Pago'
    OVERDUE = 'overdue', 'Atrasado'
    CANCELED = 'canceled', 'Cancelado'
    REFUNDED = 'refunded', 'Estornado'


class PublicWorkoutPayment(models.Model):
    """Cobranca do corredor — molde de finance.Payment (D.00), nunca a mesma tabela.

    Tres valores em vez de um (C3 do CORDA): com application_fee do Connect,
    gross != net. Sem os tres, a tela financeira do personal (Entrega 5)
    mostraria numero que nao bate com o extrato da Stripe.
    """

    subscription = models.ForeignKey(PublicWorkoutSubscription, on_delete=models.CASCADE, related_name='payments')
    due_date = models.DateField(db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    # Preenchidos na reconciliacao do webhook (invoice.payment_succeeded /
    # balance_transaction) — None ate o pagamento ser confirmado.
    application_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=PublicWorkoutPaymentStatus.choices,
        default=PublicWorkoutPaymentStatus.PENDING,
        db_index=True,
    )
    currency = models.CharField(max_length=3, default='brl')
    stripe_invoice_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self) -> str:
        return f'{self.subscription.plan_slug} - {self.gross_amount} ({self.status})'


class PublicWorkoutPaymentNotice(models.Model):
    """Uma linha da regua de avisos (D-7, D-3, D-1, D0, D+2) de um PublicWorkoutPayment.

    unique (payment, offset_days): o banco e a garantia contra duplicata,
    nao o codigo que cria as 5 linhas.
    """

    payment = models.ForeignKey(PublicWorkoutPayment, on_delete=models.CASCADE, related_name='notices')
    offset_days = models.SmallIntegerField()
    scheduled_for = models.DateField(db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_for']
        constraints = [
            models.UniqueConstraint(fields=['payment', 'offset_days'], name='unique_public_workout_notice_payment_offset'),
        ]

    def __str__(self) -> str:
        return f'{self.payment_id} D{self.offset_days:+d} [{"enviado" if self.sent_at else "pendente"}]'
