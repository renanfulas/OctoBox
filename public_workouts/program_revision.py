"""Revisão de programa ativo em rascunho separado e aprovado pelo treinador."""

from django.db import IntegrityError, transaction

from . import schema
from .guided_draft import prepare_guided_payload
from .models import (
    PublicWorkoutProgram,
    PublicWorkoutProgramDraftSource,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
)
from .services import create_program_draft, get_training_profile, serialize_training_profile


class ProgramRevisionError(ValueError):
    pass


def create_guided_revision_draft(*, subscription_id: int):
    """Copia a versão ativa; propostas permanecem editáveis até aprovação explícita."""
    with transaction.atomic():
        subscription = PublicWorkoutSubscription.objects.select_for_update().get(pk=subscription_id)
        if subscription.status != PublicWorkoutSubscriptionStatus.ACTIVE:
            raise ProgramRevisionError('A assinatura precisa estar ativa para revisar o programa.')
        if not subscription.plan_slug:
            raise ProgramRevisionError('Assinatura sem plan_slug.')
        if PublicWorkoutSubscription.objects.filter(plan_slug=subscription.plan_slug).exclude(
            pk=subscription.pk,
        ).exists():
            raise ProgramRevisionError('Slug compartilhado por mais de uma conta; resolva o vínculo antes da revisão.')
        program = PublicWorkoutProgram.objects.select_for_update().filter(
            slug=subscription.plan_slug, is_active=True,
        ).first()
        if program is None:
            raise ProgramRevisionError('Não há programa ativo para revisar neste slug.')
        payload, prepared, unresolved = prepare_guided_payload(program.payload)
        errors = schema.validate_payload(payload)
        if errors:
            raise ProgramRevisionError('Propostas inválidas; revise a prescrição original antes de copiar.')
        profile = get_training_profile(account_id=subscription.account_id)
        try:
            draft = create_program_draft(
                account_id=subscription.account_id,
                slug=subscription.plan_slug,
                payload=payload,
                source=PublicWorkoutProgramDraftSource.MANUAL,
                base_program_id=program.pk,
                training_profile_snapshot=serialize_training_profile(profile) if profile else {},
            )
        except IntegrityError as exc:
            raise ProgramRevisionError('Já existe rascunho pendente para este aluno e slug.') from exc
        return draft, prepared, unresolved
