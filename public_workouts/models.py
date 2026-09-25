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

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from model_support.base import TimeStampedModel


class PublicWorkoutStaffCredential(TimeStampedModel):
    """Credencial única da área interna do Curva (cockpit de analytics e fila de
    ativação); não usa usuários ou papéis do OctoBox."""

    username = models.CharField(max_length=80, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['username']

    def __str__(self) -> str:
        return self.username


class PublicWorkoutExperimentStatus(models.TextChoices):
    DRAFT = 'draft', 'Rascunho'
    RUNNING = 'running', 'Em execução'
    PAUSED = 'paused', 'Pausado'
    COMPLETED = 'completed', 'Concluído'


class PublicWorkoutExperiment(TimeStampedModel):
    """Teste controlado da Curva; nunca promove uma variante automaticamente."""

    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    hypothesis = models.TextField(blank=True)
    status = models.CharField(
        max_length=12, choices=PublicWorkoutExperimentStatus.choices,
        default=PublicWorkoutExperimentStatus.DRAFT, db_index=True,
    )
    primary_metric = models.CharField(max_length=40, default='first_payment')
    conversion_days = models.PositiveSmallIntegerField(default=7)
    minimum_sample_size = models.PositiveIntegerField(default=100)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    winner_variant_key = models.SlugField(max_length=80, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(conversion_days__gte=1, conversion_days__lte=30),
                name='public_workout_experiment_conversion_days_range',
            ),
            models.CheckConstraint(
                condition=models.Q(minimum_sample_size__gte=1),
                name='public_workout_experiment_minimum_sample_positive',
            ),
        ]

    def __str__(self) -> str:
        return self.name


class PublicWorkoutExperimentVariant(TimeStampedModel):
    experiment = models.ForeignKey(
        PublicWorkoutExperiment, on_delete=models.CASCADE, related_name='variants',
    )
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=120)
    allocation_weight = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['experiment_id', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['experiment', 'key'], name='unique_public_workout_experiment_variant_key',
            ),
            models.CheckConstraint(
                condition=models.Q(allocation_weight__gte=1),
                name='public_workout_experiment_variant_weight_positive',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.experiment.key}:{self.key}'


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


class PublicWorkoutMovementEquipment(models.TextChoices):
    # Plano curva-carga-completa-reps-rir-recorde, Fase 3 (§5.1): curado a
    # mao, NUNCA inferido de movement_pattern/nome — 'push' cobre tanto
    # supino com barra quanto desenvolvimento com halteres quanto
    # crucifixo na maquina, e uma heuristica automatica erraria uma fracao
    # real dos movimentos silenciosamente.
    BARBELL = 'barbell', 'Barra'
    DUMBBELL = 'dumbbell', 'Halteres'
    MACHINE = 'machine', 'Maquina'
    BODYWEIGHT = 'bodyweight', 'Peso corporal'
    CABLE = 'cable', 'Cabo/polia'
    OTHER = 'other', 'Outro'


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
    # default=OTHER e' seguro aqui (diferente do default fabricado que
    # este mesmo projeto evita pra set_role): OTHER so' significa "nao
    # mostra a calculadora de anilhas ainda" — nunca alimenta 1RM,
    # progresso ou recorde. Curadoria incremental, sem backfill obrigatorio.
    equipment_type = models.CharField(
        max_length=16,
        choices=PublicWorkoutMovementEquipment.choices,
        default=PublicWorkoutMovementEquipment.OTHER,
        db_index=True,
    )
    # Metadado SEPARADO de equipment_type de proposito (plano §5.1):
    # equipment_type=barbell sozinho nao prova que o peso registrado pelo
    # aluno JA inclui a barra (alguns treinadores podem pedir so' o peso
    # das anilhas) — a calculadora so' aparece com os dois confirmados.
    logged_weight_includes_bar = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self) -> str:
        return f'{self.slug} — {self.label_pt}'


class PublicWorkoutProfessionalRole(models.TextChoices):
    TREINO = 'treino', 'Treino'
    NUTRICAO = 'nutricao', 'Nutrição'


class PublicWorkoutProfessional(TimeStampedModel):
    """Profissional de conteudo do corredor (Entrega 5, Fase 4 — D.5/ADR-3).

    NAO e' o multi-personal completo (Connect Express, contas conectadas —
    C5 do CORDA original continua fora de escopo). Resolve exatamente um
    problema: atribuir autoria e credencial (CREF/CRN) a um conteudo, sem
    hardcodar nome/registro em template solto.
    """

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=16, choices=PublicWorkoutProfessionalRole.choices)
    registration_council = models.CharField(max_length=16)  # 'CREF' ou 'CRN'
    registration_number = models.CharField(max_length=32)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    # Zero = ainda nao configurado. Capacidade e medida em minutos de
    # trabalho profissional, nao em "numero de alunos" (tiers consomem
    # esforcos diferentes e a fila de work items ja conhece esse custo).
    weekly_capacity_minutes = models.PositiveIntegerField(default=0)
    internal_hourly_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)],
    )

    def __str__(self) -> str:
        return f'{self.name} ({self.registration_council} {self.registration_number})'


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
    # Nullable (D.5): nao quebra os programas legados ja publicados antes
    # da Fase 4 existir. Migracao de dado povoa retroativamente com a
    # linha do Renan — decisao de conteudo, nao automatica (ADR-3).
    authored_by = models.ForeignKey(PublicWorkoutProfessional, null=True, blank=True, on_delete=models.PROTECT)
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


class PublicWorkoutProgramDelivery(models.Model):
    """Entrega idempotente do aviso de programa publicado."""

    program = models.OneToOneField(PublicWorkoutProgram, on_delete=models.CASCADE, related_name='delivery')
    attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f'entrega {self.program} [{"enviada" if self.sent_at else "pendente"}]'


class PublicWorkoutMealPlanDelivery(models.Model):
    meal_plan = models.OneToOneField('PublicWorkoutMealPlan', on_delete=models.CASCADE, related_name='delivery')
    attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)


class PublicWorkoutOutboxStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    PROCESSING = 'processing', 'Processando'
    SENT = 'sent', 'Enviada'
    DEAD = 'dead', 'Falha definitiva'


class PublicWorkoutOutboxMessage(models.Model):
    topic = models.CharField(max_length=48, db_index=True)
    aggregate_type = models.CharField(max_length=32)
    aggregate_id = models.CharField(max_length=64)
    version = models.PositiveIntegerField(default=1)
    idempotency_key = models.CharField(max_length=160, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=PublicWorkoutOutboxStatus.choices,
        default=PublicWorkoutOutboxStatus.PENDING, db_index=True,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error = models.CharField(max_length=255, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_attempt_at', 'created_at']


class PublicWorkoutProgramDraftSource(models.TextChoices):
    AI_GENERATED = 'ai_generated', 'Gerado por IA'
    MANUAL = 'manual', 'Manual'


class PublicWorkoutProgramDraftStatus(models.TextChoices):
    PENDING_REVIEW = 'pending_review', 'Aguardando revisão'
    APPROVED = 'approved', 'Aprovado'
    REJECTED = 'rejected', 'Rejeitado'


class PublicWorkoutProgramDraft(models.Model):
    """Rascunho de programa pendente de revisão humana — NUNCA visível ao
    aluno (isso é PublicWorkoutProgram, tabela irmã, imutável).

    Existe porque `publish_program()`/PublicWorkoutProgram nao tem — e nunca
    tiveram — um estado "ainda nao publicado": toda linha nasce com
    `is_active=True` no mesmo transaction.atomic() que a cria (ver
    services.py). Em vez de adicionar um status "pendente" na tabela imutavel
    (arriscando algum leitor esquecer de filtrar por is_active/exp0r conteudo
    nao revisado), este e' o padrao ja usado no app pra "conteudo aceito
    passar por revisao antes de virar snapshot real": staging table +
    aprovacao chama a funcao de publicacao existente sem modifica-la — mesmo
    espirito de PublicWorkoutMealPlanAdmin (admin.py), so que aqui o rascunho
    E' mutavel ate ser aprovado (nao ha versao publicada ainda pra proteger).

    `training_profile_snapshot` e' copia congelada (nao FK) do que a IA viu
    no momento da geracao — PublicWorkoutTrainingProfile e' mutavel (E12,
    revalidacao), entao so' um snapshot responde "o que a IA realmente leu"
    de forma estavel depois que o aluno editar a propria anamnese.
    """

    # String reference (nao a classe direto): PublicWorkoutAccount so' e'
    # definida mais abaixo neste mesmo arquivo (secao "Corredor de treinos —
    # conta, login e backup") — PublicWorkoutProgramDraft fica perto de
    # PublicWorkoutProgram de proposito (tabelas irmas), nao perto de Account.
    account = models.ForeignKey('PublicWorkoutAccount', on_delete=models.CASCADE, related_name='program_drafts')
    slug = models.CharField(max_length=50, db_index=True)
    payload = models.JSONField()
    source = models.CharField(max_length=20, choices=PublicWorkoutProgramDraftSource.choices)
    status = models.CharField(
        max_length=16,
        choices=PublicWorkoutProgramDraftStatus.choices,
        default=PublicWorkoutProgramDraftStatus.PENDING_REVIEW,
        db_index=True,
    )
    training_profile_snapshot = models.JSONField(default=dict, blank=True)
    ai_model = models.CharField(max_length=64, blank=True)
    generation_error = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # So' um rascunho PENDENTE por vez por (aluno, slug) — clique
            # duplo em "Gerar rascunho com IA" nao cria dois; revisar/rejeitar
            # o existente libera gerar outro (a constraint e' parcial, so'
            # trava enquanto status='pending_review').
            models.UniqueConstraint(
                fields=['account', 'slug'],
                condition=models.Q(status=PublicWorkoutProgramDraftStatus.PENDING_REVIEW),
                name='unique_pending_review_draft_per_account_slug',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.slug} draft [{self.status}] ({self.source})'


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
    # Preenchido so' pelo login por Google (identity.photo_url em
    # oauth_providers.py) -- login por e-mail nunca tem foto pra oferecer,
    # entao resolve_or_create_public_workout_account (public_workout_login.py)
    # so' atualiza este campo quando um photo_url de verdade for passado,
    # nunca limpa o que ja existe com string vazia (mesma pegadinha real ja
    # corrigida pro /aluno/ — PR "corrige foto do Google perdida").
    photo_url = models.URLField(blank=True, default='')

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
    # Preparado pro cadastro a frio (Entrega 5, Fase 2) — ainda sem nenhum
    # caminho de codigo que cria assinatura com este valor (ADR-7).
    PENDING_PAYMENT = 'pending_payment', 'Aguardando pagamento'


class PublicWorkoutTier(models.TextChoices):
    ESSENCIAL = 'essencial', 'Essencial'
    COMPLETO = 'completo', 'Completo'
    PREMIUM = 'premium', 'Premium'


class PublicWorkoutGuaranteeModel(models.TextChoices):
    REFUND_GUARANTEE = 'refund_guarantee', 'Cobranca imediata com garantia de reembolso'
    LIMITED_TRIAL = 'limited_trial', 'Trial com entrega limitada'
    FULL_TRIAL = 'full_trial', 'Trial completo'


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
    # Nullable a partir da Entrega 5/Fase 2 (D.2, ADR-2): cadastro a frio
    # cria a assinatura ANTES de existir slug/PublicWorkoutProgram — a fila
    # de ativacao e a query `status=ACTIVE, plan_slug__isnull=True`, nunca
    # uma tabela propria. A unicidade de assinatura por conta continua
    # vindo do OneToOneField acima, nunca deste campo (P6 do CORDA).
    plan_slug = models.CharField(max_length=50, null=True, blank=True)
    tier = models.CharField(
        max_length=16,
        choices=PublicWorkoutTier.choices,
        default=PublicWorkoutTier.ESSENCIAL,
        db_index=True,
    )
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
    # Novas contratacoes exigem magic link; legados continuam na ponte B0
    # ate a migracao explicita, sem hard cut nos clientes atuais.
    requires_login = models.BooleanField(default=False)
    # Contrato comercial aceito na contratacao. Defaults preservam linhas
    # legadas; novas contratacoes gravam explicitamente as versoes vigentes.
    offer_version = models.CharField(max_length=40, blank=True)
    service_policy_version = models.CharField(max_length=40, blank=True)
    terms_version = models.CharField(max_length=24, blank=True)
    privacy_version = models.CharField(max_length=24, blank=True)
    guarantee_model = models.CharField(
        max_length=24,
        choices=PublicWorkoutGuaranteeModel.choices,
        default=PublicWorkoutGuaranteeModel.REFUND_GUARANTEE,
    )
    contract_accepted_at = models.DateTimeField(null=True, blank=True)
    contracted_price_id = models.CharField(max_length=255, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Parcial: linhas em fila (D.2) tem plan_slug vazio e nao
            # precisam entrar num indice de busca por slug.
            models.Index(
                fields=['plan_slug'],
                name='pw_sub_plan_slug_not_null_idx',
                condition=models.Q(plan_slug__isnull=False),
            ),
        ]

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


class PublicWorkoutAcquisitionSession(models.Model):
    """Envelope first-party da origem comercial, sem PII sensivel."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_source = models.CharField(max_length=80, blank=True)
    first_medium = models.CharField(max_length=80, blank=True)
    first_campaign = models.CharField(max_length=120, blank=True)
    first_referrer = models.CharField(max_length=180, blank=True)
    last_source = models.CharField(max_length=80, blank=True)
    last_medium = models.CharField(max_length=80, blank=True)
    last_campaign = models.CharField(max_length=120, blank=True)
    last_referrer = models.CharField(max_length=180, blank=True)
    landing_variant = models.CharField(max_length=40, blank=True)
    offer_version = models.CharField(max_length=40, blank=True)
    account = models.ForeignKey(
        PublicWorkoutAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    subscription = models.OneToOneField(
        PublicWorkoutSubscription, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='acquisition_session',
    )
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)


class PublicWorkoutExperimentAssignment(models.Model):
    """Exposição estável de uma sessão a uma variante de experimento."""

    experiment = models.ForeignKey(
        PublicWorkoutExperiment, on_delete=models.PROTECT, related_name='assignments',
    )
    variant = models.ForeignKey(
        PublicWorkoutExperimentVariant, on_delete=models.PROTECT, related_name='assignments',
    )
    acquisition_session = models.ForeignKey(
        PublicWorkoutAcquisitionSession, on_delete=models.CASCADE, related_name='experiment_assignments',
    )
    assigned_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['experiment', 'acquisition_session'],
                name='unique_public_workout_experiment_session_assignment',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.experiment.key}:{self.variant.key}:{self.acquisition_session_id}'


class PublicWorkoutFunnelEvent(models.Model):
    """Fato analitico append-only; nunca comanda estado de negocio."""

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event_type = models.CharField(max_length=48, db_index=True)
    acquisition_session = models.ForeignKey(
        PublicWorkoutAcquisitionSession, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='events',
    )
    account = models.ForeignKey(
        PublicWorkoutAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    subscription = models.ForeignKey(
        PublicWorkoutSubscription, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    tier = models.CharField(max_length=16, blank=True)
    channel = models.CharField(max_length=32, blank=True, db_index=True)
    source = models.CharField(max_length=80, blank=True)
    medium = models.CharField(max_length=80, blank=True)
    campaign = models.CharField(max_length=120, blank=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    client_event_id = models.UUIDField(null=True, blank=True, unique=True)
    correlation_id = models.UUIDField(null=True, blank=True, db_index=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at']


class PublicWorkoutWaitlistStatus(models.TextChoices):
    WAITING = 'waiting', 'Aguardando vaga'
    INVITED = 'invited', 'Convidado'
    CONVERTED = 'converted', 'Convertido'
    EXPIRED = 'expired', 'Expirado'
    CANCELED = 'canceled', 'Cancelado'


class PublicWorkoutWaitlistEntry(models.Model):
    """Demanda capturada quando o limite operacional impede novo checkout."""

    email = models.EmailField(db_index=True)
    tier = models.CharField(max_length=16, choices=PublicWorkoutTier.choices, db_index=True)
    status = models.CharField(
        max_length=16, choices=PublicWorkoutWaitlistStatus.choices,
        default=PublicWorkoutWaitlistStatus.WAITING, db_index=True,
    )
    acquisition_session = models.ForeignKey(
        PublicWorkoutAcquisitionSession, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='waitlist_entries',
    )
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    consented_at = models.DateTimeField(default=timezone.now)
    invited_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'tier'],
                condition=models.Q(status=PublicWorkoutWaitlistStatus.WAITING),
                name='unique_waiting_public_workout_email_tier',
            ),
        ]


class PublicWorkoutTestimonial(models.Model):
    """Prova social publicavel somente com consentimento e aprovacao."""

    account = models.ForeignKey(
        PublicWorkoutAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    display_name = models.CharField(max_length=80)
    quote = models.TextField(max_length=600)
    result_summary = models.CharField(max_length=180, blank=True)
    consented_at = models.DateTimeField()
    consent_version = models.CharField(max_length=24)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-created_at']


class PublicWorkoutMetricSnapshot(models.Model):
    """Snapshot diário reproduzível; fatos continuam nas tabelas de origem."""

    metric_date = models.DateField(db_index=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    payload = models.JSONField(default=dict)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-metric_date', '-captured_at']
        constraints = [
            models.UniqueConstraint(
                fields=['metric_date', 'schema_version'],
                name='unique_public_workout_metric_snapshot_day_version',
            ),
        ]


class PublicWorkoutCampaignSpend(models.Model):
    source = models.CharField(max_length=80)
    campaign = models.CharField(max_length=120)
    starts_on = models.DateField()
    ends_on = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='brl')
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-starts_on', 'source', 'campaign']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'campaign', 'starts_on', 'ends_on'],
                name='unique_public_workout_campaign_spend_period',
            ),
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F('starts_on')),
                name='public_workout_campaign_spend_valid_period',
            ),
        ]


class PublicWorkoutWorkItemType(models.TextChoices):
    TRAINING_PROGRAM = 'training_program', 'Montar treino'
    NUTRITION_PLAN = 'nutrition_plan', 'Montar plano nutricional'
    TRAINING_REVIEW = 'training_review', 'Revisao de treino'
    NUTRITION_REVIEW = 'nutrition_review', 'Revisao nutricional'
    CUSTOMER_SUCCESS_CONTACT = 'customer_success_contact', 'Contato de acompanhamento'


class PublicWorkoutWorkItemStatus(models.TextChoices):
    OPEN = 'open', 'Aberto'
    IN_PROGRESS = 'in_progress', 'Em andamento'
    BLOCKED = 'blocked', 'Bloqueado'
    DONE = 'done', 'Concluido'
    CANCELED = 'canceled', 'Cancelado'


class PublicWorkoutWorkItem(models.Model):
    account = models.ForeignKey(PublicWorkoutAccount, on_delete=models.CASCADE, related_name='work_items')
    subscription = models.ForeignKey(
        PublicWorkoutSubscription, on_delete=models.CASCADE, related_name='work_items'
    )
    item_type = models.CharField(max_length=32, choices=PublicWorkoutWorkItemType.choices)
    cycle_key = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16, choices=PublicWorkoutWorkItemStatus.choices,
        default=PublicWorkoutWorkItemStatus.OPEN, db_index=True,
    )
    priority = models.PositiveSmallIntegerField(default=100, db_index=True)
    estimated_effort_minutes = models.PositiveSmallIntegerField(default=30)
    actual_effort_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        PublicWorkoutProfessional, null=True, blank=True, on_delete=models.PROTECT,
        related_name='work_items',
    )
    due_at = models.DateTimeField(db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    blocked_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'due_at', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['subscription', 'item_type', 'cycle_key'],
                name='unique_public_workout_work_item_cycle',
            ),
        ]


# ---------------------------------------------------------------------------
# Anamnese de treino (D4 do plano de produto: "tudo que alimenta a IA comeca
# a coletar antes da IA existir" — docs/plans/public-workouts-produtizacao-plan.md,
# secao 1.5). Os 7 campos ja' estavam documentados ali havia tempo; este e' o
# primeiro codigo que os persiste. D.00: modelo proprio do corredor, nenhuma
# FK pra fora de public_workouts/ — mesma fronteira do resto do app.
# ---------------------------------------------------------------------------


class PublicWorkoutTrainingGoal(models.TextChoices):
    HYPERTROPHY = 'hypertrophy', 'Hipertrofia'
    STRENGTH = 'strength', 'Força'
    FAT_LOSS = 'fat_loss', 'Emagrecimento'
    GENERAL_HEALTH = 'general_health', 'Saúde geral'
    ATHLETIC_PERFORMANCE = 'athletic_performance', 'Performance esportiva'


class PublicWorkoutTrainingExperience(models.TextChoices):
    NEVER_TRAINED = 'never_trained', 'Nunca treinou'
    LESS_THAN_6_MONTHS = 'less_than_6_months', 'Menos de 6 meses'
    SIX_MONTHS_TO_2_YEARS = '6_months_to_2_years', 'De 6 meses a 2 anos'
    MORE_THAN_2_YEARS = 'more_than_2_years', 'Mais de 2 anos'


class PublicWorkoutTrainingLocation(models.TextChoices):
    FULL_GYM = 'full_gym', 'Academia completa'
    HOME_BASIC_EQUIPMENT = 'home_basic_equipment', 'Casa, com equipamento básico'
    HOME_BODYWEIGHT_ONLY = 'home_bodyweight_only', 'Casa, só peso do corpo'
    OUTDOOR_OR_TRAVEL = 'outdoor_or_travel', 'Ao ar livre / viajando'


class PublicWorkoutPhysicalRestrictionTag(models.TextChoices):
    JOELHO = 'joelho', 'Joelho'
    OMBRO = 'ombro', 'Ombro'
    LOMBAR = 'lombar', 'Lombar'
    QUADRIL = 'quadril', 'Quadril'
    PUNHO_COTOVELO = 'punho_cotovelo', 'Punho/cotovelo'
    TORNOZELO = 'tornozelo', 'Tornozelo'
    CARDIOVASCULAR = 'cardiovascular', 'Cardiovascular'
    OUTRA = 'outra', 'Outra'
    NENHUMA = 'nenhuma', 'Nenhuma'


class PublicWorkoutTrainingProfile(TimeStampedModel):
    """Anamnese de treino — os 7 campos de 1.5 do plano de produto.

    Campos 1-5 (goal/physical_restrictions/training_experience/
    days_per_week/training_location) sao estruturados — alimentam selecao
    de exercicio, volume, complexidade e substituicao. Campos 6-7
    (motivation/biggest_difficulty) sao texto livre curto — a resposta
    literal importa mais que uma categoria, e vao pro prompt da IA quase
    verbatim (ver program_generation_ai.py).

    `consent_ai_processing_at`: consentimento EXPLICITO e SEPARADO do
    consentimento generico de cadastro (N4/D2 do plano — campos 6/7 podem
    conter dado de saude sensivel indo pra API da Anthropic). Nulo = sem
    consentimento — `save_training_profile` (services.py) recusa persistir
    sem isso, entao nenhuma linha deste modelo existe sem consentimento
    dado (nao adianta um staff tentar criar uma direto pelo Django admin:
    nenhum admin e' registrado pra este model de proposito, exatamente pra
    nao abrir um caminho que contorne essa regra).

    `revalidated_at`: gancho pra E12 (plano de produto) — reperguntar "mudou
    algo desde a ultima vez?" em vez do formulario inteiro a cada programa
    novo. Nao usado ainda nesta fatia.
    """

    account = models.OneToOneField(PublicWorkoutAccount, on_delete=models.CASCADE, related_name='training_profile')
    goal = models.CharField(max_length=32, choices=PublicWorkoutTrainingGoal.choices)
    physical_restrictions = models.JSONField(default=list, blank=True)
    physical_restrictions_detail = models.TextField(blank=True)
    training_experience = models.CharField(max_length=24, choices=PublicWorkoutTrainingExperience.choices)
    days_per_week = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(7)])
    training_location = models.CharField(max_length=24, choices=PublicWorkoutTrainingLocation.choices)
    motivation = models.TextField(blank=True)
    biggest_difficulty = models.TextField(blank=True)
    consent_ai_processing_at = models.DateTimeField(null=True, blank=True)
    revalidated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f'Anamnese de treino — {self.account.email}'


# ---------------------------------------------------------------------------
# Nutricao (Entrega 6, Fase 4 do CORDA de escala/nutricao). D.00: modelos
# proprios do corredor, nenhuma FK pra fora de public_workouts/ — mesma
# fronteira que ja vale pro resto deste app.
# ---------------------------------------------------------------------------


class PublicWorkoutNutritionProfile(TimeStampedModel):
    """Anamnese nutricional — NAO reusa os 7 campos da anamnese de treino
    (comorbidade e rotina alimentar nao tem equivalente la)."""

    account = models.OneToOneField(PublicWorkoutAccount, on_delete=models.CASCADE, related_name='nutrition_profile')
    comorbidades = models.TextField(blank=True)
    alergias_restricoes = models.TextField(blank=True)
    rotina_alimentar = models.TextField(blank=True)
    preferencias = models.TextField(blank=True)
    objetivo = models.TextField(blank=True)
    medicamentos = models.TextField(blank=True)
    historico = models.TextField(blank=True)
    consent_health_processing_at = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=24, blank=True)

    def __str__(self) -> str:
        return f'Anamnese nutricional — {self.account.email}'


class PublicWorkoutMealPlan(models.Model):
    """Snapshot publicado do plano alimentar — mesmo padrao de
    PublicWorkoutProgram (D-1 do CORDA): nunca UPDATE, nova versao e' nova
    linha, is_active decide qual serve. `payload` validado por
    nutrition_schema.assert_valid_payload() antes de save() (D.6) — nunca
    so' documentado.

    Por `account`, nunca `slug` (D.6): o plano alimentar nao tem — e nao
    deveria ganhar — o conceito de link publico compartilhavel que o
    treino tem. Sempre privado, sempre atras de login.
    """

    account = models.ForeignKey(PublicWorkoutAccount, on_delete=models.CASCADE, related_name='meal_plans')
    version = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False, db_index=True)
    authored_by = models.ForeignKey(PublicWorkoutProfessional, on_delete=models.PROTECT)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(fields=['account', 'version'], name='unique_meal_plan_version'),
            models.UniqueConstraint(
                fields=['account'],
                condition=models.Q(is_active=True),
                name='unique_active_meal_plan_per_account',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.account.email} v{self.version} [{"ativo" if self.is_active else "inativo"}]'


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


class PublicWorkoutRefundRequestStatus(models.TextChoices):
    REQUESTED = 'requested', 'Solicitado'
    PROCESSING = 'processing', 'Processando'
    REFUNDED = 'refunded', 'Reembolsado'
    REJECTED = 'rejected', 'Rejeitado'
    FAILED = 'failed', 'Falhou'


class PublicWorkoutRefundRequest(models.Model):
    subscription = models.OneToOneField(
        PublicWorkoutSubscription, on_delete=models.CASCADE, related_name='refund_request',
    )
    payment = models.ForeignKey(
        PublicWorkoutPayment, on_delete=models.PROTECT, related_name='refund_requests',
    )
    status = models.CharField(
        max_length=16, choices=PublicWorkoutRefundRequestStatus.choices,
        default=PublicWorkoutRefundRequestStatus.REQUESTED, db_index=True,
    )
    reason = models.TextField(blank=True)
    stripe_refund_id = models.CharField(max_length=255, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


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


class PublicWorkoutLoadLogAchievementKind(models.TextChoices):
    # Plano curva-carga-completa-reps-rir-recorde (Fase 4, §6.1) -- so' um
    # valor por enquanto (maior carga do movimento), mas TextChoices desde
    # ja (mesmo padrao de SetRole abaixo) pra nao reformar o campo se um
    # segundo tipo de conquista aparecer depois.
    LOAD_RECORD = 'load_record', 'Nova maior carga'


class PublicWorkoutLoadLogSetRole(models.TextChoices):
    # Plano curva-grafico-hierarquia-e-set-role.md (Revisao 8), §7.2 —
    # separa aquecimento/aproximacao de serie principal pra a curva de
    # progresso/recorde nunca misturar registros nao-comparaveis.
    # `LEGACY_UNKNOWN` e' obrigatorio no enum (nao so' um valor usado sem
    # declarar): historico anterior a este campo precisa de um estado que
    # o proprio model reconheça, nunca inventando `top_set` sobre dado que
    # nunca teve essa classificacao.
    WARMUP = 'warmup', 'Aquecimento'
    FEEDER = 'feeder', 'Aproximação'
    TOP_SET = 'top_set', 'Série principal'
    MAX_SET = 'max_set', 'Esforço máximo'
    LEGACY_UNKNOWN = 'legacy_unknown', 'Histórico anterior (não classificado)'


class PublicWorkoutLoadLog(models.Model):
    """Registro de carga por (conta, movimento, data) — S3 do CORDA (Onda A1, Fatia B).

    Chave de identidade e `account` (PublicWorkoutAccount), NUNCA
    StudentIdentity: decisao escrita entre as duas frentes (D.5) trocando
    a assinatura originalmente congelada na Onda S0 (`student_identity_id:
    int` obrigatorio) — a maioria dos clientes de consultoria nunca pisou
    num box e nao tem StudentIdentity nenhuma. Quem TAMBEM for aluno de
    box ja carrega essa referencia fraca em `account.student_identity_id`
    (Onda B1) — nao duplicada aqui.
    """

    account = models.ForeignKey(PublicWorkoutAccount, on_delete=models.CASCADE, related_name='load_logs')
    movement_slug = models.SlugField(max_length=80, db_index=True)
    # None e valido: movimento de peso corporal / carga livre (load_type
    # 'free' no schema do programa) as vezes so registra reps.
    weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    reps = models.PositiveIntegerField(null=True, blank=True)
    # RIR aceita meio-ponto (ex.: "RIR 1.5") — mesmo vocabulario livre do
    # rir_spec no schema do programa (public_workouts/schema.py).
    rir = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0)])
    performed_on = models.DateField(db_index=True)
    # Referencia solta (D.2 — carga nunca entra no snapshot imutavel do
    # programa, R7): so denormaliza de onde veio, sem FK pra
    # PublicWorkoutProgram (o registro sobrevive a uma nova versao publicada).
    program_id = models.CharField(max_length=80, blank=True)
    week_in_program = models.PositiveIntegerField(null=True, blank=True)
    # Garantia de idempotencia do S3 (D.5): reenvio da outbox (Onda B3) com a
    # mesma chave nunca duplica linha — o banco e a trava, nao o codigo.
    idempotency_key = models.CharField(max_length=128, unique=True)
    # Correcao real (plano curva-carga-completa-reps-rir-recorde, Fase 3,
    # §4.1): `supersedes` aponta pro registro que ESTE substitui. FK vive
    # no registro NOVO, nunca no antigo -- o antigo nao sabe de antemao
    # que vai ser corrigido. on_delete=SET_NULL: nao ha rota de delecao
    # destes logs hoje, mas se algum dia houver, perder o VINCULO de
    # correcao e' aceitavel; cascatear a delecao da correcao NAO seria.
    supersedes = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='corrections',
    )
    # Denormalizado de proposito (nao e' so' "nao tem correcao apontando
    # pra mim", calculado por subquery): toda consulta de ESTADO ATUAL
    # (curva, recorde, sugestao, eco de hoje) filtra por is_active=True
    # antes de qualquer outra coisa -- um indice direto e' muito mais
    # barato que reavaliar NOT EXISTS em cada leitura. Vira False na MESMA
    # transacao que cria a correcao (services.py::correct_load), nunca
    # calculado a posteriori.
    is_active = models.BooleanField(default=True, db_index=True)
    # Nullable de proposito (Migrations A/B, 0028/0029) -- NUNCA
    # default='top_set' no field, fabricaria precisao sobre o historico
    # existente. Vira NOT NULL so' na Migration C, que fica FORA da pasta
    # migrations/ de proposito (ver docs/plans/
    # pending-migration-set-role-not-null.py) -- achado real via CI: um
    # `migrate` sem alvo aplica TODAS as migrations pendentes, e um banco
    # de teste recem-criado (CI, `--create-db`) passaria qualquer cheque
    # de "zero linha NULL" trivialmente (banco vazio), tornando a coluna
    # NOT NULL cedo demais e quebrando testes que criam
    # PublicWorkoutLoadLog sem set_role explicito. So' vira uma migration
    # de verdade (e so' entao este campo perde o `null=True`) quando o
    # backfill em produção for confirmado -- ver checkpoint no plano,
    # §7.12.
    set_role = models.CharField(
        max_length=16, choices=PublicWorkoutLoadLogSetRole.choices, null=True,
    )
    # Fase 4 do plano curva-carga-completa-reps-rir-recorde (§6.2):
    # resultado da conquista CALCULADO E GRAVADO na mesma transacao que
    # cria esta linha (services.py::_lock_and_resolve_achievement) --
    # nunca recalculado numa leitura posterior. E' o que garante replay
    # estavel depois de uma resposta perdida (retry com a mesma
    # idempotency_key devolve esta MESMA linha, com o MESMO resultado, em
    # vez de comparar contra um "estado atual" que pode ja ter mudado).
    # NULL == "sem evento" (a maioria das linhas), nunca um valor
    # fabricado depois do fato.
    achievement_kind = models.CharField(
        max_length=16, choices=PublicWorkoutLoadLogAchievementKind.choices, null=True, blank=True,
    )
    # Peso anterior que este registro superou -- o cliente deriva
    # delta_kg subtraindo (weight_kg - achievement_previous_weight_kg) na
    # serializacao, nunca grava o delta em si (evita um segundo campo que
    # poderia divergir do peso se algum dia um dos dois for editado).
    achievement_previous_weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_on', '-created_at']
        indexes = [
            models.Index(fields=['account', 'movement_slug', 'performed_on']),
            models.Index(fields=['account', 'set_role', 'movement_slug', 'performed_on'], name='pwll_acct_role_move_day_idx'),
        ]
        constraints = [
            # Migration B (§7.2): defesa em profundidade contra qualquer
            # escrita que nao passe por record_load/correct_load (edicao
            # direta no Admin, por exemplo). Aceita NULL de proposito --
            # nao depende do backfill ter completado; so' quando a
            # Migration C (pendente, fora de migrations/) for aplicada de
            # verdade essa coluna vira NOT NULL e este constraint troca de
            # forma junto.
            models.CheckConstraint(
                condition=(
                    models.Q(set_role__in=PublicWorkoutLoadLogSetRole.values)
                    | models.Q(set_role__isnull=True)
                ),
                name='public_workouts_loadlog_set_role_valid_or_null',
            ),
            # Fase 4 (§6.2): os dois campos de conquista nascem juntos ou
            # nao nascem -- defesa em profundidade contra uma escrita
            # parcial (fora de record_load/correct_load) que gravasse
            # achievement_kind sem o peso anterior, deixando delta_kg
            # impossivel de calcular na serializacao.
            models.CheckConstraint(
                condition=(
                    models.Q(achievement_kind__isnull=True, achievement_previous_weight_kg__isnull=True)
                    | models.Q(achievement_kind__isnull=False, achievement_previous_weight_kg__isnull=False)
                ),
                name='public_workouts_loadlog_achievement_kind_and_previous_weight_together',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.account_id} · {self.movement_slug} @ {self.performed_on}'
