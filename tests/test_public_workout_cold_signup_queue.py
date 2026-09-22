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
from django.utils import timezone

from integrations.stripe.models import PaymentWebhookEvent
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutProfessional,
    PublicWorkoutProfessionalRole,
    PublicWorkoutSubscription,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutWaitlistEntry,
    PublicWorkoutWaitlistStatus,
)
from public_workouts.stripe_handlers import route_public_workout_stripe_event


def _fila_de_ativacao():
    return PublicWorkoutSubscription.objects.filter(
        status=PublicWorkoutSubscriptionStatus.ACTIVE, plan_slug__isnull=True
    )


class ColdSignupToActivationQueueTests(TestCase):
    @override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='enforce')
    def test_enforce_without_configured_capacity_joins_waitlist_without_account_or_checkout(self):
        with patch('stripe.checkout.Session.create') as mock_create:
            response = self.client.post(
                reverse('public-workout-cold-signup'),
                {'email': 'fila@example.com', 'tier': PublicWorkoutTier.ESSENCIAL, 'accept_contract': '1'},
            )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json()['waitlisted'])
        self.assertFalse(PublicWorkoutAccount.objects.filter(email='fila@example.com').exists())
        self.assertTrue(PublicWorkoutWaitlistEntry.objects.filter(email='fila@example.com').exists())
        mock_create.assert_not_called()

    @override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='enforce')
    def test_configured_capacity_allows_checkout(self):
        PublicWorkoutProfessional.objects.create(
            name='Treinador', role=PublicWorkoutProfessionalRole.TREINO,
            registration_council='CREF', registration_number='1',
            weekly_capacity_minutes=1000,
        )
        with self.settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'):
            with patch('stripe.checkout.Session.create') as mock_create:
                mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/capacity')
                response = self.client.post(
                    reverse('public-workout-cold-signup'),
                    {'email': 'vaga@example.com', 'tier': PublicWorkoutTier.ESSENCIAL, 'accept_contract': '1'},
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_url', response.json())

    @override_settings(
        PUBLIC_WORKOUT_CAPACITY_MODE='enforce',
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial',
        STRIPE_SECRET_KEY='sk_test_x',
    )
    def test_valid_waitlist_invitation_reserves_checkout_even_when_capacity_is_full(self):
        entry = PublicWorkoutWaitlistEntry.objects.create(
            email='convidado@example.com', tier=PublicWorkoutTier.ESSENCIAL,
            status=PublicWorkoutWaitlistStatus.INVITED,
            invited_at=timezone.now(), expires_at=timezone.now() + timezone.timedelta(days=3),
        )
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/invited')
            response = self.client.post(reverse('public-workout-cold-signup'), {
                'email': entry.email, 'tier': entry.tier, 'accept_contract': '1',
                'invite_token': str(entry.invite_token),
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn('checkout_url', response.json())

    @override_settings(PUBLIC_WORKOUT_CAPACITY_MODE='enforce')
    def test_expired_invitation_does_not_bypass_capacity(self):
        entry = PublicWorkoutWaitlistEntry.objects.create(
            email='expirado@example.com', tier=PublicWorkoutTier.ESSENCIAL,
            status=PublicWorkoutWaitlistStatus.INVITED,
            invited_at=timezone.now() - timezone.timedelta(days=4),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        response = self.client.post(reverse('public-workout-cold-signup'), {
            'email': entry.email, 'tier': entry.tier, 'accept_contract': '1',
            'invite_token': str(entry.invite_token),
        })

        self.assertEqual(response.status_code, 202)
        entry.refresh_from_db()
        self.assertEqual(entry.status, PublicWorkoutWaitlistStatus.EXPIRED)
    @override_settings(
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'
    )
    def test_full_lifecycle_from_cold_signup_to_queue_to_slug_assignment(self):
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_create.return_value = MagicMock(url='https://checkout.stripe.com/pay/cs_test_cold')
            response = self.client.post(
                reverse('public-workout-cold-signup'),
                {'email': 'desconhecido@example.com', 'tier': PublicWorkoutTier.ESSENCIAL, 'accept_contract': '1'},
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

        # Checkout concluido vincula e valida o Price ID, mas ainda nao
        # ativa: trabalho humano so com invoice.payment_succeeded.
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
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        paid_event = PaymentWebhookEvent.objects.create(
            event_id='evt_cold_signup_paid',
            event_type='invoice.payment_succeeded',
            payload={
                'id': 'evt_cold_signup_paid', 'type': 'invoice.payment_succeeded',
                'data': {'object': {
                    'id': 'in_cold_1', 'subscription': 'sub_cold_1',
                    'amount_paid': 9700, 'period_start': 1789862400,
                }},
            },
        )
        route_public_workout_stripe_event(paid_event)

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
