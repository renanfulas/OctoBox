"""Abertura do programa pelo aluno (painel de analytics do treinador).

Fica fora de `public_workouts/models.py` pela trava de tamanho
(tests/test_file_size_ratchet.py) e já no formato do ADR-3 de
docs/plans/split-arquivos-grandes-plano.md: FK por string, mesmo app e mesma
tabela, então mover não gera migração. `models.py` reexporta as classes —
quem importa de `public_workouts.models` não muda. Na Fase 5 do plano este
arquivo vira um submódulo de `public_workouts/models/`.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class PublicWorkoutProgramOpenDevice(models.TextChoices):
    MOBILE = 'mobile', 'Celular'
    TABLET = 'tablet', 'Tablet'
    DESKTOP = 'desktop', 'Computador'
    UNKNOWN = 'unknown', 'Desconhecido'


class PublicWorkoutProgramOpen(models.Model):
    """Fato de uso do produto: o aluno abriu a pagina do treino.

    Separado de PublicWorkoutFunnelEvent de proposito -- o funil depende de
    PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED (atribuicao de marketing, desligado
    por padrao), e o painel de analytics do treinador precisa saber se o
    aluno abre o treino mesmo com o funil desligado. Recargas seguidas da
    mesma pagina nao viram aberturas novas (ver record_program_open)."""

    account = models.ForeignKey(
        'public_workouts.PublicWorkoutAccount', on_delete=models.CASCADE, related_name='program_opens',
    )
    plan_slug = models.SlugField(max_length=80, blank=True)
    device = models.CharField(
        max_length=8, choices=PublicWorkoutProgramOpenDevice.choices, default=PublicWorkoutProgramOpenDevice.UNKNOWN,
    )
    opened_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'public_workouts'
        ordering = ['-opened_at']
        indexes = [models.Index(fields=['account', 'opened_at'], name='pw_open_account_at_idx')]
