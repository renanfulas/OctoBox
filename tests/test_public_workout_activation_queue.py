"""
ARQUIVO: testes da fila "quem pagou e esta esperando o treino"
(PublicWorkoutActivationQueueView) e do login proprio do Curva
(CurvaStaffLoginView/CurvaStaffLogoutView, staff_auth.py).

POR QUE ELE EXISTE:
- Garante que a fila reflete o mesmo criterio de AwaitingActivationFilter
  (admin.py) sem depender do admin — e que ela nunca some por causa de
  PUBLIC_WORKOUT_OPERATIONS_ENABLED estar desligada (a flag so afeta o
  work item de enriquecimento, nao a linha base).
- Garante que o acesso as telas internas do corredor usa SO o login
  proprio do Curva (sessao com username, sem auth.User) — nunca o sistema
  de papeis do OctoBox, que nao se aplica aqui (public_workouts nao tem
  Box/Membership).
"""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutProgram,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftSource,
    PublicWorkoutStaffCredential,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
    PublicWorkoutTrainingExperience,
    PublicWorkoutTrainingGoal,
    PublicWorkoutTrainingLocation,
    PublicWorkoutTrainingProfile,
    PublicWorkoutWorkItem,
    PublicWorkoutWorkItemStatus,
    PublicWorkoutWorkItemType,
)
from public_workouts.staff_auth import SESSION_KEY
from public_workouts.views import PublicWorkoutActivationQueueView

_TEST_PASSWORDS = {'renan': 'senha-de-teste-1', 'giovanna': 'senha-de-teste-2'}


def _build_view():
    view = PublicWorkoutActivationQueueView()
    request = RequestFactory().get('/public-workouts/ativacoes/')
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    view.request = request
    view.kwargs = {}
    return view


def _make_active_subscription(email, *, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='giovanna'):
    account = PublicWorkoutAccount.objects.create(email=email)
    subscription = get_or_create_subscription(account=account, tier=tier, plan_slug=plan_slug)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.save(update_fields=['status'])
    return account, subscription


class ActivationQueueQuerysetTests(TestCase):
    def test_active_subscription_without_program_is_in_the_queue(self):
        _make_active_subscription('sem-programa@example.com')

        view = PublicWorkoutActivationQueueView()
        rows = view.get_queryset()

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].missing_training)

    def test_pending_payment_subscription_never_appears(self):
        account = PublicWorkoutAccount.objects.create(email='nao-pagou@example.com')
        get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug='naopagou')

        view = PublicWorkoutActivationQueueView()
        rows = view.get_queryset()

        self.assertEqual(len(rows), 0)

    def test_active_subscription_with_published_program_is_not_in_the_queue(self):
        _make_active_subscription('pronto@example.com', plan_slug='pronto')
        PublicWorkoutProgram.objects.create(
            slug='pronto', program_id='pronto', program_label='Programa', started_on=date(2026, 1, 1),
            weeks=8, version=1, is_active=True, payload={'schema_version': 1},
        )

        view = PublicWorkoutActivationQueueView()
        rows = view.get_queryset()

        self.assertEqual(len(rows), 0)

    def test_completo_tier_without_meal_plan_is_flagged_for_nutrition(self):
        _make_active_subscription(
            'completo@example.com', tier=PublicWorkoutTier.COMPLETO, plan_slug='completo',
        )
        PublicWorkoutProgram.objects.create(
            slug='completo', program_id='completo', program_label='Programa', started_on=date(2026, 1, 1),
            weeks=8, version=1, is_active=True, payload={'schema_version': 1},
        )

        view = PublicWorkoutActivationQueueView()
        rows = view.get_queryset()

        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].missing_training)
        self.assertTrue(rows[0].missing_nutrition)


class ActivationQueueContextTests(TestCase):
    def test_enriches_row_with_training_profile_and_pending_draft(self):
        account, _subscription = _make_active_subscription('anamnese@example.com', plan_slug='anamnese')
        PublicWorkoutTrainingProfile.objects.create(
            account=account, goal=PublicWorkoutTrainingGoal.HYPERTROPHY,
            training_experience=PublicWorkoutTrainingExperience.LESS_THAN_6_MONTHS,
            days_per_week=3, training_location=PublicWorkoutTrainingLocation.FULL_GYM,
        )
        PublicWorkoutProgramDraft.objects.create(
            account=account, slug='anamnese', payload={'schema_version': 1},
            source=PublicWorkoutProgramDraftSource.AI_GENERATED,
        )

        view = _build_view()
        view.object_list = view.get_queryset()
        context = view.get_context_data()

        row = context['rows'][0]
        self.assertTrue(row.training_profile_filled)
        self.assertIsNotNone(row.pending_draft)
        self.assertEqual(context['summary']['total'], 1)

    def test_flags_overdue_work_item(self):
        account, subscription = _make_active_subscription('atrasado@example.com', plan_slug='atrasado')
        PublicWorkoutWorkItem.objects.create(
            account=account, subscription=subscription, item_type=PublicWorkoutWorkItemType.TRAINING_PROGRAM,
            cycle_key='onboarding', status=PublicWorkoutWorkItemStatus.OPEN,
            due_at=timezone.now() - timedelta(hours=1),
        )

        view = _build_view()
        view.object_list = view.get_queryset()
        context = view.get_context_data()

        row = context['rows'][0]
        self.assertIsNotNone(row.training_work_item)
        self.assertTrue(row.training_overdue)
        self.assertEqual(context['summary']['overdue'], 1)


class CurvaStaffLoginTests(TestCase):
    """Login proprio do Curva — NAO usa auth.User nem django.contrib.auth.

    public_workouts nao e' multi-tenant (sem Box/Membership): as unicas
    duas contas (Renan, Giovanna) sao validadas contra
    PublicWorkoutStaffCredential (hash pbkdf2, nunca texto puro, mesma
    tabela do cockpit de analytics) e a sessao guarda so' o username — ver
    staff_auth.py.
    """

    def setUp(self):
        self.client = Client()
        self.queue_url = reverse('public-workout-activation-queue')
        self.login_url = reverse('public-workout-staff-login')
        self.logout_url = reverse('public-workout-staff-logout')
        # update_or_create, nao create(): a migration de seed ja grava uma
        # linha 'renan' nesta mesma tabela (compartilhada com o cockpit de
        # analytics) -- create() bateria em unique constraint de username.
        self.credentials = {}
        for username, password in _TEST_PASSWORDS.items():
            credential, _created = PublicWorkoutStaffCredential.objects.update_or_create(
                username=username, defaults={'password_hash': make_password(password), 'is_active': True},
            )
            self.credentials[username] = credential

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(self.queue_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)

    def test_wrong_password_shows_error_and_does_not_authenticate(self):
        response = self.client.post(self.login_url, {'username': 'renan', 'password': 'senha-errada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inválidos')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_unknown_username_shows_the_same_error(self):
        # Mesma mensagem de "usuario errado" — nao revela quais contas existem.
        response = self.client.post(self.login_url, {'username': 'ninguem', 'password': 'qualquer'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inválidos')

    def test_correct_credentials_log_in_and_reach_the_queue(self):
        _make_active_subscription('logado@example.com')

        login_response = self.client.post(
            self.login_url, {'username': 'renan', 'password': 'senha-de-teste-1'},
        )
        self.assertRedirects(login_response, self.queue_url)

        queue_response = self.client.get(self.queue_url)
        self.assertEqual(queue_response.status_code, 200)
        self.assertContains(queue_response, 'logado@example.com')

    def test_login_extends_session_beyond_the_global_30min_default(self):
        # SESSION_COOKIE_AGE global e' 1800s (30min, pensado pro admin do
        # OctoBox B2B) — sem set_expiry proprio, Renan/Giovanna cairiam da
        # fila de ativacao a cada 30min de inatividade durante o dia.
        self.client.post(self.login_url, {'username': 'renan', 'password': 'senha-de-teste-1'})

        self.assertEqual(self.client.session.get_expiry_age(), 8 * 60 * 60)

    def test_username_is_case_insensitive(self):
        response = self.client.post(
            self.login_url, {'username': 'RENAN', 'password': 'senha-de-teste-1'},
        )
        self.assertRedirects(response, self.queue_url)

    def test_login_redirects_to_next_url_when_present(self):
        response = self.client.post(
            f'{self.login_url}?next={self.queue_url}',
            {'username': 'giovanna', 'password': 'senha-de-teste-2', 'next': self.queue_url},
        )
        self.assertRedirects(response, self.queue_url)

    def test_login_ignores_an_external_next_url(self):
        # url_has_allowed_host_and_scheme bloqueia redirect pra fora do host —
        # sem isso um link de login forjado poderia mandar a sessao recem-criada
        # pra um dominio de phishing via ?next=.
        response = self.client.post(
            self.login_url,
            {'username': 'renan', 'password': 'senha-de-teste-1', 'next': 'https://evil.example.com/'},
        )
        self.assertRedirects(response, self.queue_url)

    def test_logout_clears_the_session(self):
        self.client.post(self.login_url, {'username': 'renan', 'password': 'senha-de-teste-1'})
        self.assertIn(SESSION_KEY, self.client.session)

        self.client.post(self.logout_url)

        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.client.get(self.queue_url).status_code, 302)

    def test_session_is_invalidated_if_credential_is_deactivated(self):
        self.client.post(self.login_url, {'username': 'renan', 'password': 'senha-de-teste-1'})
        self.assertEqual(self.client.get(self.queue_url).status_code, 200)

        self.credentials['renan'].is_active = False
        self.credentials['renan'].save(update_fields=['is_active', 'updated_at'])

        self.assertEqual(self.client.get(self.queue_url).status_code, 302)

    def test_login_updates_last_login_at(self):
        credential = self.credentials['renan']
        self.assertIsNone(credential.last_login_at)

        self.client.post(self.login_url, {'username': 'renan', 'password': 'senha-de-teste-1'})

        credential.refresh_from_db()
        self.assertIsNotNone(credential.last_login_at)
