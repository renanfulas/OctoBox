"""
ARQUIVO: regras de desfazer replicacao por lote do Smart Paste.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from student_app.models import SessionWorkoutStatus


UNDO_WINDOW = timedelta(hours=24)


def batch_can_be_undone(batch) -> tuple[bool, str]:
    if batch is None:
        return False, 'Nenhum lote de replicacao disponivel.'
    if batch.undone_at is not None:
        return False, 'Esse lote ja foi desfeito.'
    if timezone.now() - batch.created_at > UNDO_WINDOW:
        return False, 'A janela de desfazer de 24h expirou.'
    non_draft_exists = batch.session_workouts.exclude(status=SessionWorkoutStatus.DRAFT).exists()
    if non_draft_exists:
        return False, 'Existe WOD deste lote fora de DRAFT; desfazer foi bloqueado para nao apagar algo ja promovido.'
    return True, ''


@transaction.atomic
def undo_replication_batch(*, batch):
    can_undo, reason = batch_can_be_undone(batch)
    if not can_undo:
        raise ValidationError(reason)
    deleted_count, _ = batch.session_workouts.all().delete()
    batch.undone_at = timezone.now()
    batch.save(update_fields=['undone_at', 'updated_at'])
    return deleted_count


__all__ = ['UNDO_WINDOW', 'batch_can_be_undone', 'undo_replication_batch']
