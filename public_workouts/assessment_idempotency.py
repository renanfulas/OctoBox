"""Gravação idempotente da avaliação física (F2 offline-first,
docs/plans/curva-offline-first-estrategia.md).

A autoavaliação feita sem internet sobe pela fila do aparelho
(offline-data.js) com `idempotency_key`. Reenvio depois de resposta perdida
devolve a MESMA linha: o unique do banco é a trava, como em record_load.

A recuperação filtra também pelo `plan_slug`: uma chave usada por outro aluno
nunca devolve a avaliação dele — o IntegrityError original sobe, e a view
responde 409.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from .models import PublicWorkoutAssessment


def _existing(idempotency_key: str, plan_slug: str):
    return PublicWorkoutAssessment.objects.filter(idempotency_key=idempotency_key, plan_slug=plan_slug).first()


def create_assessment_once(*, idempotency_key: str | None = None, **fields) -> PublicWorkoutAssessment:
    if idempotency_key:
        existing = _existing(idempotency_key, fields['plan_slug'])
        if existing is not None:
            return existing
    try:
        # Savepoint: o IntegrityError não envenena a transação de quem chama
        # antes da consulta de recuperação.
        with transaction.atomic():
            return PublicWorkoutAssessment.objects.create(idempotency_key=idempotency_key or None, **fields)
    except IntegrityError:
        if not idempotency_key:
            raise
        existing = _existing(idempotency_key, fields['plan_slug'])
        if existing is None:
            raise
        return existing
