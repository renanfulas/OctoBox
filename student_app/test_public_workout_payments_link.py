"""
ARQUIVO: teste ponta-a-ponta (URL -> view -> sessao -> template) do botao
"Pagamentos" na tela de treino (/renan/<slug>).

POR QUE ELE EXISTE:
- achado do Renan: pra aluno com assinatura ativa e stripe_customer_id
  (ja concluiu o 1o checkout), clicar em "Pagamentos" caia num hub generico
  (/treinos/minha-conta) cujo CTA principal nem sempre e sobre pagamento —
  em vez de abrir o Customer Portal da Stripe direto (ja implementado, so
  nunca ligado aqui). Os testes de template (test_workout_template.py) so
  provam o contrato de render_to_string isolado; este arquivo prova que a
  requisicao HTTP de verdade (com sessao de conta autenticada e programa
  publicado) chega no mesmo resultado.
- segundo achado real (Rafael, cliente legado — seed_legacy_workout_accounts):
  sem stripe_customer_id, a assinatura ja' nasce com status=ACTIVE, entao
  get_customer_journey() nunca cai nos estados de pagamento — o hub
  /treinos/minha-conta nao mostra nada sobre pagar. "Pagamentos" agora
  dispara o checkout de valor negociado (POST /treinos/checkout-
  personalizado, PublicWorkoutCustomCheckoutView) quando o Renan ja'
  preencheu `custom_monthly_price` no admin pra aquela assinatura; sem o
  valor definido ainda, mostra "Fale com o Renan" em vez de link morto.
"""

from django.test import TestCase

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _login_with_subscription(client, *, email, plan_slug, stripe_customer_id='', custom_monthly_price=None):
    account = PublicWorkoutAccount.objects.create(email=email)
    PublicWorkoutSubscription.objects.create(
        account=account, plan_slug=plan_slug, stripe_customer_id=stripe_customer_id,
        custom_monthly_price=custom_monthly_price,
    )
    client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
        account_id=account.pk
    )
    return account


class PaymentsLinkOnWorkoutPageTests(TestCase):
    def setUp(self):
        publish_program(slug='bruno', payload=build_example_payload())

    def test_opens_billing_portal_directly_when_stripe_customer_id_present(self):
        _login_with_subscription(
            self.client, email='com-checkout@example.com', plan_slug='bruno',
            stripe_customer_id='cus_teste123',
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-billing-portal')
        self.assertNotContains(response, 'data-workout-start-custom-checkout')

    def test_starts_custom_checkout_when_price_already_set(self):
        _login_with_subscription(
            self.client, email='valor-definido@example.com', plan_slug='bruno',
            stripe_customer_id='', custom_monthly_price='150.00',
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-workout-start-custom-checkout')
        self.assertNotContains(response, 'data-billing-portal')
        self.assertNotContains(response, 'href="/treinos/minha-conta"')

    def test_asks_to_talk_to_renan_when_price_not_set_yet(self):
        _login_with_subscription(
            self.client, email='sem-valor@example.com', plan_slug='bruno',
            stripe_customer_id='', custom_monthly_price=None,
        )

        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fale com o Renan')
        self.assertNotContains(response, 'data-workout-start-custom-checkout')
        self.assertNotContains(response, 'data-billing-portal')

    def test_anonymous_visitor_sees_unavailable_badge(self):
        response = self.client.get('/renan/bruno')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'indisponível')
        self.assertNotContains(response, 'data-billing-portal')
