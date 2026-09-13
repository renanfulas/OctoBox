"""
ARQUIVO: modelo de avaliacao fisica do corredor publico de treinos (/renan/).

POR QUE ELE EXISTE:
- a aba "Avaliacoes" precisa persistir historico de peso/medidas em banco
  (nao localStorage) para sobreviver a troca de aparelho/navegador.

PONTOS CRITICOS:
- este app vive em SHARED_APPS (schema public) de proposito: as views do
  corredor publico rodam SEM tenant (ver student_app/views/public_workout_views.py).
  Um modelo em TENANT_APP simplesmente nao existe fora de um schema de box —
  funcionaria nos testes (conftest forca schema_context) e quebraria em
  producao. `plan_slug` e uma referencia "soft" a PUBLIC_WORKOUT_LIBRARY
  (dict Python em public_workout_views.py) — nao ha FK porque o outro lado
  nao e uma tabela.
"""

from __future__ import annotations

import uuid

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

    class Meta:
        db_table = 'public_workout_assessments'
        ordering = ['plan_slug', 'measured_at']
        indexes = [models.Index(fields=['plan_slug', 'measured_at'])]

    def __str__(self) -> str:
        return f'{self.plan_slug} @ {self.measured_at}'


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
