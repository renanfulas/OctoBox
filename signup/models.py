"""
ARQUIVO: model do cadastro pendente Early Adopter.

POR QUE ELE EXISTE:
- Persiste a intencao de compra do dono de box ANTES do pagamento Stripe.
- Permite recovery: se o cliente abandona o checkout da Stripe, o registro fica disponivel
  para retomar a conversa via WhatsApp ou email.
- Liga o pagamento Stripe a um futuro onboarding (criacao de User + Box).

O QUE ESTE ARQUIVO FAZ:
1. Define PendingSignup com status, plano escolhido e referencias Stripe.
2. Guarda magic_token para o link de ativacao apos pagamento confirmado.
3. Mantem auditoria minima (created_at, updated_at, activated_at).

PONTOS CRITICOS:
- O email NUNCA e usado como chave unica: a mesma pessoa pode tentar pagar varias vezes.
- O magic_token e gerado apenas apos status = paid.
- Status segue uma maquina simples: pending -> paid -> activated, ou pending -> canceled/failed.
"""
from __future__ import annotations

from django.db import models


class PendingSignupStatus(models.TextChoices):
    PENDING = 'pending', 'Aguardando pagamento'
    PAID = 'paid', 'Pagamento confirmado'
    ACTIVATED = 'activated', 'Conta ativada'
    CANCELED = 'canceled', 'Cancelado pelo cliente'
    FAILED = 'failed', 'Falhou'


class PendingSignupPlan(models.TextChoices):
    MONTHLY = 'monthly', 'Mensal R$ 97'
    ANNUAL = 'annual', 'Anual R$ 997'


class PendingSignup(models.Model):
    """Captura de Early Adopter ainda nao convertido em conta ativa."""

    # Identificacao do interessado
    email = models.EmailField(db_index=True)
    full_name = models.CharField(max_length=120)
    box_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)

    # Plano escolhido na landing
    plan = models.CharField(
        max_length=16,
        choices=PendingSignupPlan.choices,
        default=PendingSignupPlan.ANNUAL,
    )

    # Estado da maquina de signup
    status = models.CharField(
        max_length=16,
        choices=PendingSignupStatus.choices,
        default=PendingSignupStatus.PENDING,
        db_index=True,
    )

    # Referencias Stripe (preenchidas conforme o fluxo avanca)
    stripe_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)

    # Onboarding pos-pagamento
    magic_token = models.CharField(max_length=64, blank=True, db_index=True)
    magic_token_expires_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_signup_origin',
    )

    # Origem e contexto comercial
    landing_referer = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True, help_text='Anotacoes manuais do operador (WhatsApp, follow-up, etc).')

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cadastro pendente'
        verbose_name_plural = 'Cadastros pendentes (Early Adopters)'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['plan', 'status']),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.email}) — {self.get_plan_display()} — {self.get_status_display()}'

    @property
    def is_paid(self):
        return self.status in (PendingSignupStatus.PAID, PendingSignupStatus.ACTIVATED)

    @property
    def display_amount_brl(self):
        return 'R$ 97,00' if self.plan == PendingSignupPlan.MONTHLY else 'R$ 997,00'
