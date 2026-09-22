"""Read model da jornada do cliente Curva.

Combina verdades que ja existem (assinatura, anamneses e programa publicado)
sem criar uma segunda maquina de estados persistida.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import (
    PublicWorkoutMealPlan,
    PublicWorkoutProgram,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)


@dataclass(frozen=True)
class CustomerJourney:
    state: str
    eyebrow: str
    title: str
    description: str
    action: str
    progress: int
    plan_slug: str = ''
    tier: str = ''
    needs_nutrition: bool = False
    can_manage_billing: bool = False
    next_charge: str = ''
    monthly_price: str = ''
    has_meal_plan: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def get_customer_journey(account) -> CustomerJourney:
    subscription = getattr(account, 'subscription', None)
    if subscription is None:
        return CustomerJourney(
            state='payment_pending', eyebrow='Contratação',
            title='Escolha seu plano para começar',
            description='Seu cadastro está pronto. Falta escolher o plano e concluir o pagamento.',
            action='choose_plan', progress=10,
        )

    common = {
        'plan_slug': subscription.plan_slug or '',
        'tier': subscription.tier,
        'needs_nutrition': subscription.tier in (PublicWorkoutTier.COMPLETO, PublicWorkoutTier.PREMIUM),
        'can_manage_billing': bool(subscription.stripe_customer_id),
        'next_charge': subscription.current_period_end.date().isoformat() if subscription.current_period_end else '',
        'monthly_price': {
            PublicWorkoutTier.ESSENCIAL: 'R$ 97/mês',
            PublicWorkoutTier.COMPLETO: 'R$ 267/mês',
            PublicWorkoutTier.PREMIUM: 'R$ 397/mês',
        }.get(subscription.tier, ''),
    }

    if subscription.status == PublicWorkoutSubscriptionStatus.PENDING_PAYMENT:
        return CustomerJourney(
            state='payment_processing', eyebrow='Pagamento',
            title='Estamos confirmando sua assinatura',
            description='Se você acabou de sair da Stripe, isso costuma levar apenas alguns segundos.',
            action='refresh', progress=20, **common,
        )
    if subscription.status in (PublicWorkoutSubscriptionStatus.PAST_DUE, PublicWorkoutSubscriptionStatus.SUSPENDED):
        return CustomerJourney(
            state='payment_problem', eyebrow='Pagamento',
            title='Sua assinatura precisa de atenção',
            description='Atualize a forma de pagamento para recuperar o acesso automaticamente.',
            action='manage_billing', progress=20, **common,
        )
    if subscription.status == PublicWorkoutSubscriptionStatus.CANCELED:
        return CustomerJourney(
            state='canceled', eyebrow='Assinatura',
            title='Sua assinatura está cancelada',
            description='Seu histórico continua salvo. Você pode escolher um plano para voltar.',
            action='choose_plan', progress=10, **common,
        )

    if not hasattr(account, 'training_profile'):
        return CustomerJourney(
            state='training_intake_pending', eyebrow='Etapa 1 de 3',
            title='Conte sobre seu treino',
            description='A anamnese orienta a primeira versão do programa e a revisão profissional.',
            action='training_intake', progress=42, **common,
        )

    if common['needs_nutrition'] and not hasattr(account, 'nutrition_profile'):
        return CustomerJourney(
            state='nutrition_intake_pending', eyebrow='Etapa 2 de 3',
            title='Complete sua anamnese nutricional',
            description='Essas respostas permitem que a nutricionista prepare um plano realmente individual.',
            action='nutrition_intake', progress=62, **common,
        )

    has_program = bool(subscription.plan_slug) and PublicWorkoutProgram.objects.filter(
        slug=subscription.plan_slug, is_active=True
    ).exists()
    has_meal_plan = PublicWorkoutMealPlan.objects.filter(account=account, is_active=True).exists()
    common['has_meal_plan'] = has_meal_plan
    if has_program and common['needs_nutrition'] and not has_meal_plan:
        return CustomerJourney(
            state='nutrition_in_progress', eyebrow='Treino liberado',
            title='Seu treino está pronto; a nutrição está em revisão',
            description='Você já pode começar o programa. O plano alimentar aparecerá assim que a nutricionista publicar.',
            action='open_program', progress=92, **common,
        )
    if has_program and (not common['needs_nutrition'] or has_meal_plan):
        return CustomerJourney(
            state='program_ready', eyebrow='Programa pronto',
            title='Seu treino está liberado',
            description='Abra o programa e registre sua evolução a cada sessão.',
            action='open_program', progress=100, **common,
        )

    return CustomerJourney(
        state='program_in_progress', eyebrow='Etapa final',
        title='Seu programa está em preparação',
        description='A equipe está montando e revisando seu programa. Você receberá um e-mail quando estiver pronto.',
        action='wait', progress=82, **common,
    )


__all__ = ['CustomerJourney', 'get_customer_journey']
