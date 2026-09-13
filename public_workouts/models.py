"""
ARQUIVO: modelos de fundacao de dados do corredor publico de treinos (/renan/)
— avaliacao fisica e, a partir da Onda A0 do CORDA, catalogo de movimentos.

POR QUE ELE EXISTE:
- a aba "Avaliacoes" precisa persistir historico de peso/medidas em banco
  (nao localStorage) para sobreviver a troca de aparelho/navegador.
- Onda A0: o corredor precisa de um vocabulario de movimentos com link de
  referencia (MuscleWiki) para os 10 programas migrarem (Onda A2) sem
  perder o "Ver no MuscleWiki" que cada exercicio ja tem hoje.

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
"""

from __future__ import annotations

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
