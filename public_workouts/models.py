"""
ARQUIVO: modelos do corredor publico de treinos (/renan/): avaliacao fisica,
catalogo de movimentos (Onda A0), snapshot de programa (Onda A1) e, a partir
da Onda B2, cobranca (assinatura, pagamento, regua de avisos).

POR QUE ELE EXISTE:
- a aba "Avaliacoes" precisa persistir historico de peso/medidas em banco
  (nao localStorage) para sobreviver a troca de aparelho/navegador.
- Onda A0: o corredor precisa de um vocabulario de movimentos com link de
  referencia (MuscleWiki) para os 10 programas migrarem (Onda A2) sem
  perder o "Ver no MuscleWiki" que cada exercicio ja tem hoje.
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
- PublicWorkoutMovement e um catalogo PROPRIO do corredor (V1 do CORDA,
  secao D.00) — nunca estende `student_app.MovementLibrary` (tabela por
  box). Pode ser SEMEADO a partir dela (copia read-only dos movimentos de
  CrossFit ja curados), nunca escreve nela: um movimento de musculacao do
  corredor gravado em MovementLibrary apareceria no picker de WOD do coach
  de um box que nao tem nada a ver com isso.
- `movement_pattern` fica em branco no seed automatico de proposito. O
  proprio CORDA (R.N) cita a classificacao de movement_pattern como
  decisao que exige "saber treinar" — nao e algo pra um script advinhar
  silenciosamente. Fica como campo livre (nao TextChoices) esperando
  revisao humana; `status='pending'` sinaliza isso no extraido do HTML.
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

import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel


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
    # Referencia fraca (N5 do CORDA): so preenchido quando a pessoa tambem
    # e aluno de box com StudentIdentity. Nunca ressincronizado — trocar de
    # identidade de um lado nao apaga nem altera avaliacoes ja lancadas.
    student_identity_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'public_workout_assessments'
        ordering = ['plan_slug', 'measured_at']
        indexes = [models.Index(fields=['plan_slug', 'measured_at'])]

    def __str__(self) -> str:
        return f'{self.plan_slug} @ {self.measured_at}'


class PublicWorkoutMovementModality(models.TextChoices):
    CROSSFIT = 'crossfit', 'CrossFit'
    STRENGTH = 'strength', 'Musculacao'
    BOTH = 'both', 'Ambos'


class PublicWorkoutMovementStatus(models.TextChoices):
    # Curado (semeado da lista de essenciais de CrossFit, ja revisada) ou
    # promovido manualmente depois de revisao.
    ACTIVE = 'active', 'Ativo'
    # Default do extrator automatico (extract_movements_from_html): nasceu
    # de HTML sem revisao humana, nao deve aparecer como sugestao "oficial"
    # ate alguem confirmar nome/pattern.
    PENDING = 'pending', 'Pendente de revisao'


class PublicWorkoutMovement(models.Model):
    """Catalogo de movimentos do corredor — nunca `student_app.MovementLibrary`.

    Semeado por `extract_movements_from_html` (management command): dos 10
    HTMLs legados (modality=STRENGTH, status=PENDING) e de uma copia
    read-only da lista de essenciais de CrossFit que ja existe em
    `student_app/management/commands/seed_movement_library.py`
    (modality=CROSSFIT, status=ACTIVE — lista ja curada, nao extraida).
    """

    slug = models.SlugField(max_length=80, unique=True)
    label_pt = models.CharField(max_length=160)
    label_en = models.CharField(max_length=160, blank=True)
    reference_url = models.URLField(max_length=255, blank=True)
    modality = models.CharField(max_length=16, choices=PublicWorkoutMovementModality.choices, db_index=True)
    # Texto livre de proposito (ver docstring do modulo): taxonomia ainda
    # nao revisada por quem treina. Ex.: 'squat', 'hinge', 'push', 'pull'.
    movement_pattern = models.CharField(max_length=32, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=PublicWorkoutMovementStatus.choices,
        default=PublicWorkoutMovementStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self) -> str:
        return f'{self.slug} — {self.label_pt}'


class PublicWorkoutProgram(models.Model):
    """Snapshot publicado e imutavel de um programa (Onda A1 do CORDA).

    `payload` e o contrato de public_workouts/schema.py, ja validado
    (D.2, frase 2: e a PRESCRICAO publicada, nunca o que o aluno produz
    depois — carga fica em PublicWorkoutLoadLog, fora deste payload).
    `program_label`/`started_on`/`weeks` sao denormalizados do payload
    pra dar pra consultar sem parsear JSON.

    "Publicar v2" e so mais uma linha (version=2), nunca UPDATE em v1 —
    reverter e trocar qual linha tem is_active=True (Pronto quando #1 da
    Onda A1). O banco garante no maximo uma linha ativa por slug (Pronto
    quando #2) via UniqueConstraint parcial.
    """

    slug = models.CharField(max_length=50, db_index=True)
    program_id = models.CharField(max_length=80, db_index=True)
    program_label = models.CharField(max_length=160)
    started_on = models.DateField()
    weeks = models.PositiveSmallIntegerField()
    version = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(fields=['program_id', 'version'], name='unique_public_workout_program_version'),
            models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(is_active=True),
                name='unique_active_public_workout_program_per_slug',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.slug} v{self.version} [{"ativo" if self.is_active else "inativo"}]'


# ---------------------------------------------------------------------------
# Corredor de treinos — conta, login e backup (Onda B1 do CORDA).
#
# Moram AQUI, e nao em student_identity/, porque D.000 e D.00 do CORDA
# (docs/plans/public-workouts-produtizacao-corda.md) proibem o corredor de
# adicionar modelo ou migration ao app principal: o produto consome servicos
# do OctoBox, nunca estende modelos dele.
#
# A tensao com D.4 (que da public_workouts/ a Frente A) se resolve por
# sequenciamento, nao por endereco: a onda que precisa do modelo cria a
# migration e avisa a outra frente. Colisao de migration e inconveniencia de
# processo; modelo de um produto na tabela do outro e dano permanente.
# ---------------------------------------------------------------------------


class PublicWorkoutAccount(TimeStampedModel):
    """Conta do corredor de treinos — so e-mail, sem senha (S1 do CORDA).

    Vinculo com StudentIdentity e por referencia FRACA
    (student_identity_id, sem FK) e so quando a pessoa TAMBEM for aluno de
    box, resolvido por e-mail no momento da criacao da conta — nunca
    ressincronizado depois. E informativo, nunca autoritativo (N5): trocar
    o e-mail de um lado nao altera o outro, e nenhum dos dois quebra.
    """

    email = models.EmailField(unique=True, db_index=True)
    student_identity_id = models.IntegerField(null=True, blank=True, db_index=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.email


class PublicWorkoutLoginToken(TimeStampedModel):
    """Token de login por e-mail do corredor de treinos.

    Molde de StudentAppInvitation (D.00 — copia o padrao de token de uso
    unico, nunca a tabela: convite de box e login de treino sao coisas
    diferentes dividindo o mesmo campo, exatamente o que V5 do CORDA
    proibe).
    """

    account = models.ForeignKey(PublicWorkoutAccount, on_delete=models.CASCADE, related_name='login_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and not self.is_expired

    def mark_used(self) -> None:
        self.used_at = timezone.now()

    def __str__(self) -> str:
        state = 'usado' if self.used_at else ('expirado' if self.is_expired else 'pendente')
        return f'Login token {self.account.email} [{state}]'


class PublicWorkoutLocalStorageBackup(TimeStampedModel):
    """Copia bruta do `localStorage` do aluno, subida ANTES do hard reset (Onda B3).

    F-B do plano de produto (docs/plans/public-workouts-produtizacao-plan.md):
    o upload subiu de 3.5 para 1.7 porque, entre o hard reset e a
    normalizacao (mais tarde), qualquer aluno que limpasse o navegador
    perderia o historico sem backup — e o `localStorage` e a UNICA copia
    que existe, nunca esteve no servidor. Salva primeiro, entende depois:
    sem parsing nem validacao de estrutura interna, so o blob como o
    navegador mandou.
    """

    plan_slug = models.CharField(max_length=50, db_index=True)
    store_key = models.CharField(max_length=100, blank=True)
    raw_blob = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['plan_slug', '-created_at'])]

    def __str__(self) -> str:
        return f'{self.plan_slug} backup @ {self.created_at:%Y-%m-%d %H:%M}'


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

    account = models.OneToOneField(
        PublicWorkoutAccount,
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
