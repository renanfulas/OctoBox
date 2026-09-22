"""
ARQUIVO: testes de roteamento do webhook Stripe do corredor (Onda B2, Fatia B
do CORDA — S3/D.000/P5).

POR QUE ELE EXISTE:
- P5 do CORDA ("webhook de aluno suspende o BOX") e o unico risco com
  potencial catastrofico da Onda B2: errar o roteamento suspenderia o box
  inteiro. Com endpoint proprio, o caminho de codigo que altera Box.status
  simplesmente nao e alcancavel a partir do handler do corredor — este
  arquivo prova isso, alem da autenticacao e da dedup por event_id (N1).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from control.models import Box
from integrations.stripe.models import PaymentWebhookEvent
from public_workouts.billing import get_or_create_subscription, link_stripe_ids
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscriptionStatus, PublicWorkoutTier
from public_workouts.stripe_handlers import (
    PublicWorkoutStripeWebhookAuthError,
    route_public_workout_stripe_event,
)


def _fake_stripe_subscription(*, price_id: str) -> dict:
    return {'items': {'data': [{'price': {'id': price_id}}]}}


def _make_event(*, event_id: str, event_type: str, data_object: dict) -> PaymentWebhookEvent:
    return PaymentWebhookEvent.objects.create(
        event_id=event_id,
        event_type=event_type,
        payload={'id': event_id, 'type': event_type, 'data': {'object': data_object}},
    )


class WebhookAuthAndDedupTests(TestCase):
    def test_view_returns_400_on_invalid_signature(self):
        with patch(
            'public_workouts.stripe_handlers.verify_public_workout_stripe_webhook',
            side_effect=PublicWorkoutStripeWebhookAuthError('Invalid signature'),
        ):
            response = self.client.post(
                reverse('public-workout-stripe-webhook'),
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=1,v1=bad',
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 0)

    def test_view_creates_payment_webhook_event_and_returns_200(self):
        fake_event = {
            'id': 'evt_test_1',
            'type': 'customer.subscription.deleted',
            'data': {'object': {'id': 'sub_does_not_exist'}},
        }
        with patch('public_workouts.stripe_handlers.verify_public_workout_stripe_webhook', return_value=fake_event):
            response = self.client.post(
                reverse('public-workout-stripe-webhook'),
                data=b'{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=1,v1=whatever',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentWebhookEvent.objects.filter(event_id='evt_test_1').count(), 1)

    def test_duplicate_event_id_is_not_persisted_twice(self):
        fake_event = {
            'id': 'evt_test_dup',
            'type': 'customer.subscription.deleted',
            'data': {'object': {'id': 'sub_does_not_exist'}},
        }
        # Evento ja existe (Stripe reenviando) — o INSERT duplicado dentro da
        # view e o unico que precisa estourar IntegrityError. Postgres aborta
        # a transacao inteira apos esse erro — nenhuma query nova pode rodar
        # na mesma transacao de teste depois disso (mesma restricao do teste
        # equivalente do box em tests/test_error_scenarios.py: so assere
        # response.status_code/content, nunca re-consulta o banco). A garantia
        # de "nao duplicou" vem da propria unique constraint —
        # IntegrityError so e levantado se a linha SEGUNDA nao foi gravada.
        PaymentWebhookEvent.objects.create(
            event_id='evt_test_dup', event_type='customer.subscription.deleted', payload=fake_event
        )
        with patch('public_workouts.stripe_handlers.verify_public_workout_stripe_webhook', return_value=fake_event):
            response = self.client.post(
                reverse('public-workout-stripe-webhook'), data=b'{}', content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=1,v1=x',
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Duplicate', response.content)


class RouteToCorrectHandlerTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=self.account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')

    def test_checkout_session_completed_without_coaching_metadata_is_ignored(self):
        event = _make_event(
            event_id='evt_1',
            event_type='checkout.session.completed',
            data_object={'metadata': {}, 'customer': 'cus_1', 'subscription': 'sub_1'},
        )
        route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.stripe_customer_id, '')
        event.refresh_from_db()
        self.assertEqual(event.status, 'processed')

    def test_checkout_session_completed_links_stripe_ids(self):
        event = _make_event(
            event_id='evt_2',
            event_type='checkout.session.completed',
            data_object={
                'metadata': {
                    'product': 'coaching',
                    'public_workout_subscription_id': str(self.subscription.pk),
                    'tier': PublicWorkoutTier.ESSENCIAL,
                },
                'customer': 'cus_1',
                'subscription': 'sub_1',
            },
        )
        with override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'):
            with patch('stripe.Subscription.retrieve', return_value=_fake_stripe_subscription(price_id='price_essencial')):
                route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.stripe_customer_id, 'cus_1')
        self.assertEqual(self.subscription.stripe_subscription_id, 'sub_1')

    def test_checkout_session_completed_validates_price_but_waits_for_paid_invoice(self):
        self.subscription.status = PublicWorkoutSubscriptionStatus.PENDING_PAYMENT
        self.subscription.save(update_fields=['status'])
        event = _make_event(
            event_id='evt_2b',
            event_type='checkout.session.completed',
            data_object={
                'metadata': {
                    'product': 'coaching',
                    'public_workout_subscription_id': str(self.subscription.pk),
                    'tier': PublicWorkoutTier.ESSENCIAL,
                },
                'customer': 'cus_1',
                'subscription': 'sub_1',
            },
        )
        with override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'):
            with patch('stripe.Subscription.retrieve', return_value=_fake_stripe_subscription(price_id='price_essencial')):
                route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)

    def test_checkout_session_completed_does_not_activate_when_real_price_does_not_match_tier(self):
        # RT3: Price ID mudou no dashboard Stripe sem atualizar settings, ou
        # metadata nao propagou. Nunca adivinha — fica como estava,
        # pendente pra revisao manual (log de erro).
        self.subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        self.subscription.save(update_fields=['status'])
        event = _make_event(
            event_id='evt_2c',
            event_type='checkout.session.completed',
            data_object={
                'metadata': {
                    'product': 'coaching',
                    'public_workout_subscription_id': str(self.subscription.pk),
                    'tier': PublicWorkoutTier.ESSENCIAL,
                },
                'customer': 'cus_1',
                'subscription': 'sub_1',
            },
        )
        with override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'):
            with patch('stripe.Subscription.retrieve', return_value=_fake_stripe_subscription(price_id='price_outro_tier')):
                route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.SUSPENDED)
        # link_stripe_ids ja rodou antes do cross-check — nao fica pra tras
        # so porque a ativacao ficou pendente.
        self.assertEqual(self.subscription.stripe_customer_id, 'cus_1')

    def test_checkout_session_completed_without_tier_in_metadata_does_not_activate(self):
        # Compat com evento antigo/reenviado de antes desta mudanca — nunca
        # deveria acontecer pra checkout novo (start_subscription_checkout
        # sempre manda tier), mas nao pode nem quebrar nem adivinhar.
        self.subscription.status = PublicWorkoutSubscriptionStatus.SUSPENDED
        self.subscription.save(update_fields=['status'])
        event = _make_event(
            event_id='evt_2d',
            event_type='checkout.session.completed',
            data_object={
                'metadata': {'product': 'coaching', 'public_workout_subscription_id': str(self.subscription.pk)},
                'customer': 'cus_1',
                'subscription': 'sub_1',
            },
        )
        with override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial', STRIPE_SECRET_KEY='sk_test_x'):
            with patch('stripe.Subscription.retrieve', return_value=_fake_stripe_subscription(price_id='price_essencial')):
                route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.SUSPENDED)

    def test_invoice_event_for_unknown_stripe_subscription_is_a_noop_not_an_error(self):
        event = _make_event(
            event_id='evt_3',
            event_type='invoice.payment_succeeded',
            data_object={'subscription': 'sub_de_outra_conta', 'amount_paid': 8990, 'period_start': 1770000000},
        )
        route_public_workout_stripe_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, 'processed')
        self.assertEqual(self.subscription.payments.count(), 0)

    def test_invoice_payment_succeeded_marks_payment_paid(self):
        self.subscription.status = PublicWorkoutSubscriptionStatus.PENDING_PAYMENT
        self.subscription.save(update_fields=['status'])
        link_stripe_ids(self.subscription, customer_id='cus_1', stripe_subscription_id='sub_1')
        event = _make_event(
            event_id='evt_4',
            event_type='invoice.payment_succeeded',
            data_object={'id': 'in_1', 'subscription': 'sub_1', 'amount_paid': 8990, 'period_start': 1770000000},
        )
        route_public_workout_stripe_event(event)

        payment = self.subscription.payments.get(stripe_invoice_id='in_1')
        self.assertEqual(payment.gross_amount, Decimal('89.90'))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial')
    def test_paid_invoice_can_arrive_before_checkout_session_event(self):
        event = _make_event(
            event_id='evt_4_out_of_order',
            event_type='invoice.payment_succeeded',
            data_object={
                'id': 'in_out_of_order',
                'customer': 'cus_out_of_order',
                'subscription': 'sub_out_of_order',
                'amount_paid': 8990,
                'period_start': 1770000000,
                'lines': {'data': [{'price': {'id': 'price_essencial'}}]},
                'parent': {
                    'subscription_details': {
                        'metadata': {
                            'product': 'coaching',
                            'tier': PublicWorkoutTier.ESSENCIAL,
                            'public_workout_subscription_id': str(self.subscription.pk),
                        },
                    },
                },
            },
        )

        route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)
        self.assertEqual(self.subscription.stripe_customer_id, 'cus_out_of_order')
        self.assertEqual(self.subscription.stripe_subscription_id, 'sub_out_of_order')
        self.assertTrue(self.subscription.payments.filter(stripe_invoice_id='in_out_of_order').exists())

    def test_invoice_metadata_fallback_rejects_another_product(self):
        event = _make_event(
            event_id='evt_4_other_product',
            event_type='invoice.payment_succeeded',
            data_object={
                'id': 'in_other_product',
                'subscription': 'sub_other_product',
                'amount_paid': 8990,
                'subscription_details': {
                    'metadata': {
                        'product': 'box',
                        'public_workout_subscription_id': str(self.subscription.pk),
                    },
                },
            },
        )

        route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        self.assertFalse(self.subscription.payments.exists())

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_essencial')
    def test_invoice_metadata_fallback_rejects_wrong_price(self):
        event = _make_event(
            event_id='evt_4_wrong_price',
            event_type='invoice.payment_succeeded',
            data_object={
                'id': 'in_wrong_price',
                'subscription': 'sub_wrong_price',
                'amount_paid': 14990,
                'lines': {'data': [{'price': {'id': 'price_premium'}}]},
                'subscription_details': {
                    'metadata': {
                        'product': 'coaching',
                        'tier': PublicWorkoutTier.ESSENCIAL,
                        'public_workout_subscription_id': str(self.subscription.pk),
                    },
                },
            },
        )

        route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        self.assertEqual(self.subscription.stripe_subscription_id, '')
        self.assertFalse(self.subscription.payments.exists())

    def test_invoice_payment_failed_marks_subscription_past_due(self):
        # so' downgrade de ACTIVE (billing.py:323) — precondicao explicita
        # desde a Fase 2 (D.2b), ja que get_or_create_subscription nao
        # nasce mais ACTIVE por default.
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])
        link_stripe_ids(self.subscription, customer_id='cus_1', stripe_subscription_id='sub_1')
        event = _make_event(
            event_id='evt_5',
            event_type='invoice.payment_failed',
            data_object={'id': 'in_2', 'subscription': 'sub_1', 'amount_due': 8990, 'due_date': 1770000000},
        )
        route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.PAST_DUE)

    def test_subscription_deleted_marks_canceled(self):
        link_stripe_ids(self.subscription, customer_id='cus_1', stripe_subscription_id='sub_1')
        event = _make_event(
            event_id='evt_6', event_type='customer.subscription.deleted', data_object={'id': 'sub_1'}
        )
        route_public_workout_stripe_event(event)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, PublicWorkoutSubscriptionStatus.CANCELED)

    def test_unknown_event_type_is_marked_processed_without_side_effects(self):
        event = _make_event(event_id='evt_7', event_type='charge.refunded', data_object={})
        route_public_workout_stripe_event(event)

        event.refresh_from_db()
        self.assertEqual(event.status, 'processed')


@pytest.mark.public_schema
class NeverTouchesBoxStatusTests(TestCase):
    """P5 do CORDA: nenhum evento do corredor pode alterar Box.status —
    prova de regressao de arquitetura, nao teste de bug vivo.

    @pytest.mark.public_schema: cria Box (modelo tenant) — precisa rodar no
    schema public, opt-out do schema_context autouse do conftest (mesmo
    padrao de tests/test_auditing_services.py).
    """

    def setUp(self):
        owner = get_user_model().objects.create_user(username='owner-webhook-routing', password='x')
        self.box = Box.objects.create(
            slug='webhook-routing-test',
            schema_name='box_webhook_routing_test',
            display_name='Box de teste',
            status=Box.Status.ACTIVE,
            owner_user=owner,
        )
        self.box_status_before = self.box.status

        account = PublicWorkoutAccount.objects.create(email='aluno@example.com')
        self.subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna')
        link_stripe_ids(self.subscription, customer_id='cus_1', stripe_subscription_id='sub_1')

    def test_full_lifecycle_of_corredor_events_leaves_box_status_untouched(self):
        events = [
            ('evt_a', 'checkout.session.completed', {
                'metadata': {'product': 'coaching', 'public_workout_subscription_id': str(self.subscription.pk)},
                'customer': 'cus_1', 'subscription': 'sub_1',
            }),
            ('evt_b', 'invoice.payment_succeeded', {'id': 'in_a', 'subscription': 'sub_1', 'amount_paid': 8990, 'period_start': 1770000000}),
            ('evt_c', 'invoice.payment_failed', {'id': 'in_b', 'subscription': 'sub_1', 'amount_due': 8990, 'due_date': 1770000000}),
            ('evt_d', 'customer.subscription.deleted', {'id': 'sub_1'}),
        ]
        with patch('stripe.Subscription.retrieve', return_value=_fake_stripe_subscription(price_id='irrelevante')):
            for event_id, event_type, data_object in events:
                route_public_workout_stripe_event(_make_event(event_id=event_id, event_type=event_type, data_object=data_object))

        self.box.refresh_from_db()
        self.assertEqual(self.box.status, self.box_status_before)
