"""
ARQUIVO: testes de GET /renan/<slug>/preview (Onda B3 do CORDA,
docs/plans/public-workouts-produtizacao-corda.md).

POR QUE ELE EXISTE:
- comparação final lado a lado dos 10 programas reais contra o template
  único (`workout.html`), sem tocar a rota real (`/renan/<slug>`, que
  continua servindo o template legado). Mesmo gate de posse da rota real
  — reusa `_confirm_login_session_owns_slug_or_404`, testado a fundo em
  `test_public_workout_ownership_gate.py` — aqui só confirma que o NOVO
  endpoint aplica a mesma regra, não reprova ela de novo.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from public_workouts.models import PublicWorkoutAccount, PublicWorkoutSubscription
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program, record_load
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME,
    build_public_workout_session_value,
)


def _make_account_with_subscription(*, email, plan_slug) -> PublicWorkoutAccount:
    account = PublicWorkoutAccount.objects.create(email=email)
    PublicWorkoutSubscription.objects.create(account=account, plan_slug=plan_slug)
    return account


def _login(client, account_id):
    client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=account_id)


class PublicWorkoutPreviewEndpointTests(TestCase):
    def _url(self, slug='bruno'):
        return reverse('public-workout-preview', kwargs={'plan_slug': slug})

    def test_unpublished_slug_returns_404(self):
        # Diferente da rota legada (PUBLIC_WORKOUT_LIBRARY, sempre 200 pra
        # slug conhecido): esta consulta PublicWorkoutProgram — sem
        # publish_program, não há o que mostrar.
        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_visitor_sees_published_program(self):
        publish_program(slug='bruno', payload=build_example_payload())

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Programa de exemplo')

    def test_logged_in_account_opening_someone_elses_slug_gets_404_not_403(self):
        publish_program(slug='juliana', payload=build_example_payload())
        account_a = _make_account_with_subscription(email='a@example.com', plan_slug='bruno')
        _login(self.client, account_a.pk)

        response = self.client.get(self._url('juliana'))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_visitor_never_sees_another_accounts_load_history(self):
        publish_program(slug='bruno', payload=build_example_payload())
        owner = _make_account_with_subscription(email='dono@example.com', plan_slug='bruno')
        record_load(
            account_id=owner.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            performed_on='2026-01-05',
            idempotency_key='key-1',
        )

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '100,0 kg')

    def test_owner_logged_in_sees_their_own_recorded_load(self):
        publish_program(slug='bruno', payload=build_example_payload())
        owner = _make_account_with_subscription(email='dono@example.com', plan_slug='bruno')
        record_load(
            account_id=owner.pk,
            movement_slug='agachamento-livre',
            weight_kg=Decimal('100'),
            reps=5,
            performed_on='2026-01-05',
            idempotency_key='key-1',
        )
        _login(self.client, owner.pk)

        response = self.client.get(self._url('bruno'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '100,0')

    def test_shows_pt_br_movement_name_from_catalog(self):
        from public_workouts.models import PublicWorkoutMovement

        payload = build_example_payload()
        publish_program(slug='bruno', payload=payload)
        PublicWorkoutMovement.objects.filter(slug='agachamento-livre').update(label_pt='Agachamento livre — nome revisado')

        response = self.client.get(self._url('bruno'))

        self.assertContains(response, 'Agachamento livre — nome revisado')
