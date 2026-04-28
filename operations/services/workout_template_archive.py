"""
ARQUIVO: soft-archive e restore de templates de WOD.

POR QUE ELE EXISTE:
- "excluir todos" é destrutivo demais para uma operação de box; arquivar
  preserva a operação por 30 dias e permite restaurar sem suporte.

O QUE ESTE ARQUIVO FAZ:
1. arquiva um ou todos os templates do box (seta archived_at + archived_by).
2. restaura um template arquivado (limpa archived_at/archived_by).
3. limpa templates arquivados há mais de 30 dias (usado por tarefa periódica).
4. lista templates arquivados com prazo de expiração visível.

PONTOS CRÍTICOS:
- filtra por box implicitamente via queryset recebido pelo caller — o caller
  é responsável por garantir isolamento multi-tenant antes de chamar.
- templates ativos (archived_at=None) ficam no catálogo normal; arquivados
  ficam ocultos da busca padrão mas aparecem na tela de arquivados.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from operations.models import WorkoutTemplate


_ARCHIVE_RETENTION_DAYS = 30


def archive_template(*, template: WorkoutTemplate, actor) -> None:
    template.archived_at = timezone.now()
    template.archived_by = actor
    template.is_active = False
    template.save(update_fields=['archived_at', 'archived_by', 'is_active', 'updated_at'])


def archive_all_templates(*, box_id: int, actor) -> int:
    now = timezone.now()
    updated = WorkoutTemplate.objects.filter(
        archived_at__isnull=True,
    ).update(
        archived_at=now,
        archived_by=actor,
        is_active=False,
    )
    return updated


def restore_template(*, template: WorkoutTemplate) -> None:
    template.archived_at = None
    template.archived_by = None
    template.is_active = True
    template.save(update_fields=['archived_at', 'archived_by', 'is_active', 'updated_at'])


def delete_expired_archives() -> int:
    cutoff = timezone.now() - timedelta(days=_ARCHIVE_RETENTION_DAYS)
    qs = WorkoutTemplate.objects.filter(archived_at__lt=cutoff)
    count = qs.count()
    qs.delete()
    return count


def build_archived_template_list(*, box_id: int) -> list[dict]:
    cutoff = timezone.now() - timedelta(days=_ARCHIVE_RETENTION_DAYS)
    templates = (
        WorkoutTemplate.objects.filter(archived_at__isnull=False)
        .select_related('archived_by')
        .order_by('-archived_at')
    )
    result = []
    for t in templates:
        expires_at = t.archived_at + timedelta(days=_ARCHIVE_RETENTION_DAYS)
        days_left = (expires_at - timezone.now()).days
        result.append({
            'id': t.id,
            'name': t.name,
            'archived_at_label': t.archived_at.strftime('%d/%m/%Y %H:%M'),
            'archived_by_label': (
                t.archived_by.get_full_name() or t.archived_by.username
                if t.archived_by else 'sistema'
            ),
            'days_left': max(days_left, 0),
            'expires_soon': days_left <= 7,
        })
    return result


__all__ = [
    'archive_template',
    'archive_all_templates',
    'restore_template',
    'delete_expired_archives',
    'build_archived_template_list',
]
