"""Fila operacional Curva: trabalho, SLO, ownership e transicoes."""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .catalog import PUBLIC_WORKOUT_LIBRARY
from .models import (
    PublicWorkoutAssessment,
    PublicWorkoutLoadLog,
    PublicWorkoutLocalStorageBackup,
    PublicWorkoutMealPlan,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutTrainingSession,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWorkItemType,
)
from .service_policy import get_tier_service_policy, operations_enabled

logger = logging.getLogger(__name__)

_ACTIVE_ITEM_STATUSES = (
    PublicWorkoutWorkItemStatus.OPEN,
    PublicWorkoutWorkItemStatus.IN_PROGRESS,
    PublicWorkoutWorkItemStatus.BLOCKED,
)
# Segmentos fixos de /renan/ (student_app/public_urls.py) que um slug nao pode ocupar.
_RESERVED_PLAN_SLUGS = frozenset({'offline', 'sw'})
_PLAN_SLUG_MAX_LENGTH = 40


def _professional_for(role: str):
    return PublicWorkoutProfessional.objects.filter(role=role, is_active=True).order_by('id').first()


def _plan_slug_in_use(slug: str) -> bool:
    """Avaliacoes, sessoes e backups sao chaveados por slug: reaproveitar um
    slug antigo entregaria o historico de outra pessoa ao aluno novo."""
    return (
        slug in _RESERVED_PLAN_SLUGS
        or slug in PUBLIC_WORKOUT_LIBRARY
        or PublicWorkoutSubscription.objects.filter(plan_slug=slug).exists()
        or PublicWorkoutProgram.objects.filter(slug=slug).exists()
        or PublicWorkoutProgramDraft.objects.filter(slug=slug).exists()
        or PublicWorkoutAssessment.objects.filter(plan_slug=slug).exists()
        or PublicWorkoutTrainingSession.objects.filter(plan_slug=slug).exists()
        or PublicWorkoutLocalStorageBackup.objects.filter(plan_slug=slug).exists()
    )


def available_plan_slug(email: str) -> str:
    """Slug legivel a partir do e-mail (parte local, sem acento), nunca ja usado."""
    local_part = unicodedata.normalize('NFKD', email.split('@', 1)[0]).encode('ascii', 'ignore').decode()
    base = re.sub(r'[^a-z0-9]', '', local_part.lower())[:_PLAN_SLUG_MAX_LENGTH] or 'aluno'
    candidate, suffix = base, 2
    while _plan_slug_in_use(candidate):
        candidate = f'{base}{suffix}'
        suffix += 1
    return candidate


def _assign_plan_slug_if_missing(subscription) -> None:
    # Sem slug, o rascunho por IA recusa ("defina plan_slug antes de gerar")
    # e a assinatura paga espera um passo manual no admin.
    if subscription.plan_slug:
        return
    subscription.plan_slug = available_plan_slug(subscription.account.email)
    subscription.save(update_fields=['plan_slug', 'updated_at'])
    logger.info(
        'curva_plan_slug_assigned subscription_id=%s plan_slug=%s', subscription.pk, subscription.plan_slug,
    )


def _enqueue_staff_work_item_alert(item) -> None:
    from .outbox import TOPIC_STAFF_WORK_ITEM_OPENED, enqueue_outbox

    enqueue_outbox(topic=TOPIC_STAFF_WORK_ITEM_OPENED, aggregate_type='work_item', aggregate_id=item.pk, version=1)


def _create_item(*, subscription, item_type, due_hours, effort_minutes, role):
    policy = get_tier_service_policy(subscription.tier)
    return PublicWorkoutWorkItem.objects.get_or_create(
        subscription=subscription,
        item_type=item_type,
        cycle_key='onboarding',
        defaults={
            'account': subscription.account,
            'status': PublicWorkoutWorkItemStatus.OPEN,
            'priority': policy.priority,
            'estimated_effort_minutes': effort_minutes,
            'assigned_to': _professional_for(role),
            'due_at': timezone.now() + timedelta(hours=due_hours),
        },
    )


def ensure_required_work_items(subscription_id: int) -> list[PublicWorkoutWorkItem]:
    """Abre somente trabalho cujas pre-condicoes ja foram cumpridas."""
    if not operations_enabled():
        return []
    created_items = []
    with transaction.atomic():
        subscription = (
            PublicWorkoutSubscription.objects.select_for_update().select_related('account').get(pk=subscription_id)
        )
        if subscription.status != PublicWorkoutSubscriptionStatus.ACTIVE:
            return []
        _assign_plan_slug_if_missing(subscription)
        policy = get_tier_service_policy(subscription.tier)
        account = subscription.account

        has_training_profile = hasattr(account, 'training_profile')
        has_active_program = bool(
            subscription.plan_slug
            and PublicWorkoutProgram.objects.filter(slug=subscription.plan_slug, is_active=True).exists()
        )
        if has_training_profile and not has_active_program:
            item, created = _create_item(
                subscription=subscription,
                item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM,
                due_hours=policy.training_initial_slo_hours,
                effort_minutes=policy.training_initial_effort_minutes,
                role=PublicWorkoutProfessionalRole.TREINO,
            )
            if created:
                created_items.append(item)
                _enqueue_staff_work_item_alert(item)
                logger.info(
                    'curva_work_item_created item_id=%s subscription_id=%s item_type=%s due_at=%s',
                    item.pk, subscription.pk, item.item_type, item.due_at.isoformat(),
                )

        needs_nutrition = subscription.tier in (PublicWorkoutTier.COMPLETO, PublicWorkoutTier.PREMIUM)
        has_nutrition_profile = hasattr(account, 'nutrition_profile')
        has_meal_plan = PublicWorkoutMealPlan.objects.filter(account=account, is_active=True).exists()
        if (
            needs_nutrition and has_nutrition_profile and not has_meal_plan
            and policy.nutrition_initial_slo_hours is not None
            and policy.nutrition_initial_effort_minutes is not None
        ):
            item, created = _create_item(
                subscription=subscription,
                item_type=PublicWorkoutWorkItemType.NUTRITION_PLAN,
                due_hours=policy.nutrition_initial_slo_hours,
                effort_minutes=policy.nutrition_initial_effort_minutes,
                role=PublicWorkoutProfessionalRole.NUTRICAO,
            )
            if created:
                created_items.append(item)
                _enqueue_staff_work_item_alert(item)
                logger.info(
                    'curva_work_item_created item_id=%s subscription_id=%s item_type=%s due_at=%s',
                    item.pk, subscription.pk, item.item_type, item.due_at.isoformat(),
                )
    return created_items


def transition_work_item(item_id: int, *, to_status: str, actual_effort_minutes=None, blocked_reason=''):
    allowed = {
        PublicWorkoutWorkItemStatus.OPEN: {
            PublicWorkoutWorkItemStatus.IN_PROGRESS, PublicWorkoutWorkItemStatus.BLOCKED,
            PublicWorkoutWorkItemStatus.DONE, PublicWorkoutWorkItemStatus.CANCELED,
        },
        PublicWorkoutWorkItemStatus.IN_PROGRESS: {
            PublicWorkoutWorkItemStatus.BLOCKED, PublicWorkoutWorkItemStatus.DONE,
            PublicWorkoutWorkItemStatus.CANCELED,
        },
        PublicWorkoutWorkItemStatus.BLOCKED: {
            PublicWorkoutWorkItemStatus.IN_PROGRESS, PublicWorkoutWorkItemStatus.DONE,
            PublicWorkoutWorkItemStatus.CANCELED,
        },
        PublicWorkoutWorkItemStatus.DONE: set(),
        PublicWorkoutWorkItemStatus.CANCELED: set(),
    }
    with transaction.atomic():
        item = PublicWorkoutWorkItem.objects.select_for_update().get(pk=item_id)
        if to_status == item.status:
            return item
        if to_status not in allowed[item.status]:
            raise ValueError(f'transicao de work item invalida: {item.status} -> {to_status}')
        from_status = item.status
        now = timezone.now()
        if to_status == PublicWorkoutWorkItemStatus.IN_PROGRESS and item.started_at is None:
            item.started_at = now
        if to_status == PublicWorkoutWorkItemStatus.DONE:
            item.completed_at = now
            if actual_effort_minutes is not None:
                item.actual_effort_minutes = actual_effort_minutes
        item.blocked_reason = blocked_reason if to_status == PublicWorkoutWorkItemStatus.BLOCKED else ''
        item.status = to_status
        item.save(update_fields=[
            'status', 'started_at', 'completed_at', 'actual_effort_minutes',
            'blocked_reason', 'updated_at',
        ])
        logger.info(
            'curva_work_item_transition item_id=%s from_status=%s to_status=%s overdue=%s',
            item.pk, from_status, to_status, item.due_at < now,
        )
        return item


def complete_onboarding_work_item(*, subscription, item_type: str) -> PublicWorkoutWorkItem | None:
    item = PublicWorkoutWorkItem.objects.filter(
        subscription=subscription, item_type=item_type, cycle_key='onboarding',
        status__in=_ACTIVE_ITEM_STATUSES,
    ).order_by('created_at').first()
    if item is None:
        return None
    return transition_work_item(item.pk, to_status=PublicWorkoutWorkItemStatus.DONE)


def cancel_open_work_items(subscription_id: int) -> int:
    count = 0
    for item_id in PublicWorkoutWorkItem.objects.filter(
        subscription_id=subscription_id, status__in=_ACTIVE_ITEM_STATUSES,
    ).values_list('id', flat=True):
        transition_work_item(item_id, to_status=PublicWorkoutWorkItemStatus.CANCELED)
        count += 1
    return count


def ensure_recurring_review_work_items(*, now=None) -> list[PublicWorkoutWorkItem]:
    """Abre revisoes Premium da semana uma unica vez.

    Sem registro de treino recente, abre contato leve em vez de uma revisao
    tecnica vazia. Nutricao ainda nao possui check-in estruturado; havendo
    plano ativo, a revisao semanal contratada e aberta normalmente.
    """
    if not operations_enabled():
        return []
    now = now or timezone.now()
    cycle_key = f'{now.isocalendar().year}-W{now.isocalendar().week:02d}'
    created_items = []
    subscriptions = PublicWorkoutSubscription.objects.filter(
        status=PublicWorkoutSubscriptionStatus.ACTIVE,
        tier=PublicWorkoutTier.PREMIUM,
    ).select_related('account')
    for subscription in subscriptions:
        policy = get_tier_service_policy(subscription.tier)
        recent_since = now.date() - timedelta(days=policy.training_review_cadence_days or 7)
        has_recent_training = PublicWorkoutLoadLog.objects.filter(
            account=subscription.account, performed_on__gte=recent_since,
        ).exists()
        training_type = (
            PublicWorkoutWorkItemType.TRAINING_REVIEW
            if has_recent_training else PublicWorkoutWorkItemType.CUSTOMER_SUCCESS_CONTACT
        )
        training_role = PublicWorkoutProfessionalRole.TREINO
        item, created = PublicWorkoutWorkItem.objects.get_or_create(
            subscription=subscription, item_type=training_type, cycle_key=cycle_key,
            defaults={
                'account': subscription.account,
                'priority': policy.priority,
                'estimated_effort_minutes': (
                    policy.training_review_effort_minutes if has_recent_training else 10
                ),
                'assigned_to': _professional_for(training_role),
                'due_at': now + timedelta(hours=48),
            },
        )
        if created:
            created_items.append(item)

        if PublicWorkoutMealPlan.objects.filter(account=subscription.account, is_active=True).exists():
            item, created = PublicWorkoutWorkItem.objects.get_or_create(
                subscription=subscription,
                item_type=PublicWorkoutWorkItemType.NUTRITION_REVIEW,
                cycle_key=cycle_key,
                defaults={
                    'account': subscription.account,
                    'priority': policy.priority,
                    'estimated_effort_minutes': policy.nutrition_review_effort_minutes or 30,
                    'assigned_to': _professional_for(PublicWorkoutProfessionalRole.NUTRICAO),
                    'due_at': now + timedelta(hours=48),
                },
            )
            if created:
                created_items.append(item)
    return created_items


__all__ = [
    'available_plan_slug', 'cancel_open_work_items', 'complete_onboarding_work_item',
    'ensure_recurring_review_work_items', 'ensure_required_work_items', 'transition_work_item',
]
