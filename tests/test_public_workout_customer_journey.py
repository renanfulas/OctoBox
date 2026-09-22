from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from public_workouts.billing import get_or_create_subscription
from public_workouts.journey import get_customer_journey
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutNutritionProfile,
    PublicWorkoutProgramDelivery,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutTrainingProfile,
)
from public_workouts.notifications import notify_program_ready
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.stripe_handlers import route_public_workout_stripe_event
from integrations.stripe.models import PaymentWebhookEvent
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


class CustomerJourneyTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='journey@example.com')
        self.subscription = get_or_create_subscription(
            account=self.account, tier=PublicWorkoutTier.COMPLETO, plan_slug='bruno'
        )

    def _activate(self):
        self.subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        self.subscription.save(update_fields=['status'])

    def _training_profile(self):
        PublicWorkoutTrainingProfile.objects.create(
            account=self.account, goal='hypertrophy', physical_restrictions=[],
            training_experience='more_than_2_years', days_per_week=4,
            training_location='full_gym', consent_ai_processing_at='2026-09-20T00:00:00Z',
        )

    def test_pending_payment_is_processing(self):
        self.assertEqual(get_customer_journey(self.account).state, 'payment_processing')

    def test_active_complete_requires_training_then_nutrition(self):
        self._activate()
        self.assertEqual(get_customer_journey(self.account).state, 'training_intake_pending')
        self._training_profile()
        self.account = PublicWorkoutAccount.objects.get(pk=self.account.pk)
        self.assertEqual(get_customer_journey(self.account).state, 'nutrition_intake_pending')

    def test_ready_program_is_final_state(self):
        self._activate()
        self.subscription.tier = PublicWorkoutTier.ESSENCIAL
        self.subscription.save(update_fields=['tier'])
        self._training_profile()
        publish_program(slug='bruno', payload=build_example_payload())
        self.account = PublicWorkoutAccount.objects.get(pk=self.account.pk)
        self.assertEqual(get_customer_journey(self.account).state, 'program_ready')


class PublicWorkoutAccountViewTests(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='conta@example.com')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk
        )

    def test_anonymous_is_sent_to_magic_login(self):
        self.client.cookies.clear()
        response = self.client.get(reverse('public-workout-account'))
        self.assertRedirects(response, '/treinos/login?next=/treinos/minha-conta', fetch_redirect_response=False)

    def test_account_renders_next_step(self):
        response = self.client.get(reverse('public-workout-account'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escolha seu plano para começar')

    def test_nutrition_intake_saves_sensitive_consent(self):
        subscription = get_or_create_subscription(account=self.account, tier=PublicWorkoutTier.COMPLETO)
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.save(update_fields=['status'])
        response = self.client.post(reverse('public-workout-nutrition-intake'), {
            'objetivo': 'Melhorar composição corporal', 'rotina_alimentar': 'Quatro refeições',
            'comorbidades': 'Nenhuma', 'alergias_restricoes': 'Nenhuma',
            'medicamentos': 'Nenhum', 'preferencias': 'Arroz e feijão',
            'historico': 'Já tentou dieta', 'consent': 'on',
        })
        self.assertRedirects(response, '/treinos/minha-conta?anamnese=salva', fetch_redirect_response=False)
        profile = self.account.nutrition_profile
        self.assertIsNotNone(profile.consent_health_processing_at)
        self.assertEqual(profile.consent_version, 'nutrition-v1')

    def test_essencial_cannot_open_nutrition_intake(self):
        subscription = get_or_create_subscription(account=self.account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.save(update_fields=['status'])
        response = self.client.get(reverse('public-workout-nutrition-intake'))
        self.assertRedirects(response, '/treinos/minha-conta', fetch_redirect_response=False)


class ProgramReadyNotificationTests(TestCase):
    def test_delivery_is_idempotent_and_contains_magic_link(self):
        account = PublicWorkoutAccount.objects.create(email='pronto@example.com')
        subscription = get_or_create_subscription(
            account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno'
        )
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.save(update_fields=['status'])
        program = publish_program(slug='bruno', payload=build_example_payload())
        gateway = MagicMock()
        with patch('public_workouts.notifications.get_student_email_gateway', return_value=gateway):
            self.assertTrue(notify_program_ready(program, base_url='https://app.example.com/'))
            self.assertTrue(notify_program_ready(program, base_url='https://app.example.com/'))
        self.assertEqual(gateway.send.call_count, 1)
        self.assertIn('/treinos/login?token=', gateway.send.call_args.kwargs['body'])
        self.assertTrue(PublicWorkoutProgramDelivery.objects.get(program=program).sent_at)


class NewCustomerLoginGateTests(TestCase):
    def test_new_paid_program_redirects_anonymous_visitor_to_magic_login(self):
        account = PublicWorkoutAccount.objects.create(email='protegido@example.com')
        subscription = get_or_create_subscription(
            account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='bruno'
        )
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.requires_login = True
        subscription.save(update_fields=['status', 'requires_login'])
        publish_program(slug='bruno', payload=build_example_payload())

        response = self.client.get('/renan/bruno')

        self.assertRedirects(response, '/treinos/login?next=/renan/bruno', fetch_redirect_response=False)

    @patch('student_identity.public_workout_views.start_subscription_checkout')
    def test_active_customer_returning_to_landing_must_prove_email_ownership(self, checkout):
        account = PublicWorkoutAccount.objects.create(email='ativo-volta@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.save(update_fields=['status'])

        response = self.client.post(reverse('public-workout-cold-signup'), {
            'email': account.email, 'tier': PublicWorkoutTier.PREMIUM, 'accept_contract': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['login_required'])
        self.assertIn('/treinos/login', response.json()['checkout_url'])
        self.assertNotIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        checkout.assert_not_called()

    @patch('student_identity.public_workout_views.start_subscription_checkout')
    def test_abandoned_checkout_email_cannot_claim_existing_account_session(self, checkout):
        account = PublicWorkoutAccount.objects.create(email='pendente-volta@example.com')
        get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)

        response = self.client.post(reverse('public-workout-cold-signup'), {
            'email': account.email, 'tier': PublicWorkoutTier.ESSENCIAL, 'accept_contract': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['login_required'])
        self.assertNotIn(PUBLIC_WORKOUT_SESSION_COOKIE_NAME, response.cookies)
        checkout.assert_not_called()

    @override_settings(
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO='price_completo',
        STRIPE_SECRET_KEY='sk_test_x',
    )
    @patch('student_identity.public_workout_views.start_subscription_checkout')
    def test_authenticated_canceled_customer_can_renew_without_login_loop(self, checkout):
        checkout.return_value = 'https://checkout.stripe.com/pay/cs_renew'
        account = PublicWorkoutAccount.objects.create(email='renovacao@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.status = PublicWorkoutSubscriptionStatus.CANCELED
        subscription.save(update_fields=['status'])
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=account.pk,
        )

        response = self.client.post(reverse('public-workout-cold-signup'), {
            'email': account.email, 'tier': PublicWorkoutTier.COMPLETO, 'accept_contract': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.stripe.com/pay/cs_renew')
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
        self.assertEqual(subscription.tier, PublicWorkoutTier.COMPLETO)
        checkout.assert_called_once()


class CustomerPortalReconciliationTests(TestCase):
    @override_settings(
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_e',
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_COMPLETO='price_c',
        PUBLIC_WORKOUT_STRIPE_PRICE_ID_PREMIUM='price_p',
    )
    def test_subscription_updated_reconciles_tier_status_and_next_cycle(self):
        account = PublicWorkoutAccount.objects.create(email='upgrade@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
        subscription.stripe_subscription_id = 'sub_upgrade'
        subscription.save(update_fields=['status', 'stripe_subscription_id'])
        event = PaymentWebhookEvent.objects.create(
            event_id='evt_subscription_updated_upgrade',
            event_type='customer.subscription.updated',
            payload={
                'id': 'evt_subscription_updated_upgrade',
                'type': 'customer.subscription.updated',
                'data': {'object': {
                    'id': 'sub_upgrade', 'status': 'active', 'current_period_end': 1790000000,
                    'items': {'data': [{'price': {'id': 'price_p'}}]},
                }},
            },
        )

        route_public_workout_stripe_event(event)

        subscription.refresh_from_db()
        self.assertEqual(subscription.tier, PublicWorkoutTier.PREMIUM)
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.ACTIVE)
        self.assertIsNotNone(subscription.current_period_end)

    @override_settings(PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL='price_e')
    def test_unknown_portal_price_never_changes_local_tier(self):
        account = PublicWorkoutAccount.objects.create(email='unknown-price@example.com')
        subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL)
        subscription.stripe_subscription_id = 'sub_unknown'
        subscription.save(update_fields=['stripe_subscription_id'])
        event = PaymentWebhookEvent.objects.create(
            event_id='evt_subscription_updated_unknown', event_type='customer.subscription.updated',
            payload={'data': {'object': {
                'id': 'sub_unknown', 'status': 'active',
                'items': {'data': [{'price': {'id': 'price_not_configured'}}]},
            }}},
        )

        route_public_workout_stripe_event(event)

        subscription.refresh_from_db()
        self.assertEqual(subscription.tier, PublicWorkoutTier.ESSENCIAL)
        self.assertEqual(subscription.status, PublicWorkoutSubscriptionStatus.PENDING_PAYMENT)
