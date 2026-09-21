"""
ARQUIVO: teste ponta-a-ponta do cadastro a frio + fila de ativação
(Entrega 5, Fase 2 — docs/plans/public-workouts-escala-e-nutricao-corda.md).

POR QUE ELE EXISTE:
- e o "Pronto quando" literal da Fase 2: um desconhecido paga sem cookie
  nem plan_slug, fica PENDING_PAYMENT até o webhook confirmar via tier/
  price real (D.3), vira ACTIVE só depois, aparece na fila (D.2) só nesse
  momento, e some da fila quando Renan/esposa atribuem um plan_slug.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from integrations.stripe.models import PaymentWebhookEvent
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription, PublicWorkoutSubscriptionStatus, PublicWorkoutTier
from public_workouts.stripe_handlers import route_public_workout_stripe_event


def _fila_de_ativacao():
    return PublicWorkoutSubscription.objects.filter(
        status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug__isnull=True
    )


class ColdSignupToActivationQueueTests(TestCase):
    @override_settings(
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'
    )
    def test_full_lifecycle_from_cold_signup_to_queue_to_slug_assignment(self):
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_cold')
            response = self.client.post(
                reverse('public-workout-cold-signup'),
                {'email': 'desconhecido@example.com', 'tier': PublicWorkoutTier.ESSENCIAL},
            )
        self.assertEqual(response.status_code, 200)

        account = PublicWorkoutAccount.objects.get(email='desconhecido@example.com')
        subscription = account.subscription
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        self.assertIsNone(subscription.plan_slug)
        self.assertNotIn(subscription.pk, _fila_de_ativacao().values_list('pk', flat=True))

        # Checkout abandonado (nunca completou) nao pode aparecer na fila —
        # continua PENDING_PAYMENT, invisivel pra Renan/esposa (RT7).
        self.assertNotIn(subscription.pk, _fila_de_ativacao().values_list('pk', flat=True))

        # Stripe confirma o pagamento — webhook checkout.session.completed
        # com o Price ID real batendo o tier da metadata (D.3).
        event = PaymentWebhookEvent.objects.create(
            event_id='evt_cold_signup',
            event_type='checkout.session.completed',
            payload={
                'id': 'evt_cold_signup',
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'metadata': {
                            'product': 'coaching',
                            'public_workout_subscription_id': str(subscription.pk),
                            'tier': PublicWorkoutTier.ESSENCIAL,
                        },
                        'customer': 'cus_cold_1',
                        'subscription': 'sub_cold_1',
                    }
                },
            },
        )
        with patch('stripe.Subscription.retrieve', return_value={'items': {'data': [{'price': {'id': 'price_essencial'}}]}}):
            route_public_workout_stripe_event(event)

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)
        self.assertIsNone(subscription.plan_slug)
        # So agora, pago de verdade e ainda sem slug, aparece na fila (D.2).
        self.assertIn(subscription.pk, _fila_de_ativacao().values_list('pk', flat=True))

        # Renan/esposa revisam a fila e atribuem o plan_slug (fluxo manual,
        # fora de escopo desta fase — so o efeito sobre a fila e testado aqui).
        subscription.plan_slug = 'desconhecido'
        subscription.save(update_fields=['plan_slug'])

        self.assertNotIn(subscription.pk, _fila_de_ativacao().values_list('pk', flat=True))
