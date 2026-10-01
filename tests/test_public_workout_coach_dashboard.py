"""
ARQUIVO: testes do cockpit do treinador (roster de alunos + ficha do aluno)
— achado do Renan: "saber a evolução de forma fácil, a data que foi o
treino" + "chamar aluno pra saber se está tudo bem" + reaproveitar o fluxo
de rascunho de IA já existente em vez de um editor manual novo.

POR QUE ELE EXISTE:
- Mesmo login proprio do Curva (staff_auth.py) do resto do painel interno
  — garante que a tela nova nao vaza pra visitante anonimo nem depende do
  sistema de papeis do OctoBox (public_workouts nao tem Box/Membership).
- Garante o contrato do link wa.me (numero so' digitos, mensagem
  urlencoded) e que a acao de gerar rascunho no detalhe da ficha usa a
  MESMA funcao que o admin (generate_ai_draft_for_subscription), nao uma
  copia divergente.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from public_workouts.billing import get_or_create_subscription
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutLoadLog,
    PublicWorkoutLoadLogSetRole,
    PublicWorkoutProgramDraft,
    PublicWorkoutProgramDraftStatus,
    PublicWorkoutStaffCredential,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.views import _build_checkin_whatsapp_url


def _make_active_subscription(email, *, plan_slug, whatsapp=''):
    account = PublicWorkoutAccount.objects.create(email=email, whatsapp=whatsapp)
    subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug=plan_slug)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.save(update_fields=['status'])
    return account, subscription


def _log_weight(account, *, movement_slug, weight_kg, performed_on, key_suffix):
    PublicWorkoutLoadLog.objects.create(
        account=account, movement_slug=movement_slug, weight_kg=Decimal(str(weight_kg)),
        reps=8, performed_on=performed_on, set_role=PublicWorkoutLoadLogSetRole.TOP_SET,
        idempotency_key=f'{account.pk}-{movement_slug}-{key_suffix}',
    )


class BuildCheckinWhatsappUrlTests(TestCase):
    def test_none_when_phone_is_blank(self):
        self.assertIsNone(_build_checkin_whatsapp_url(phone='', student_label='Bruno'))

    def test_builds_wa_me_link_with_encoded_message_when_phone_present(self):
        url = _build_checkin_whatsapp_url(phone='5511987654321', student_label='Bruno')

        self.assertTrue(url.startswith('https://wa.me/5511987654321?text='))
        self.assertIn('Bruno', url)


class CoachDashboardAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.roster_url = reverse('public-workout-coach-roster')
        PublicWorkoutStaffCredential.objects.update_or_create(
            username='renan', defaults={'password_hash': make_password('senha-de-teste'), 'is_active': True},
        )

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(self.roster_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('public-workout-staff-login'), response.url)

    def test_logged_in_staff_reaches_the_roster(self):
        self.client.post(reverse('public-workout-staff-login'), {'username': 'renan', 'password': 'senha-de-teste'})

        response = self.client.get(self.roster_url)

        self.assertEqual(response.status_code, 200)


class CoachStudentRosterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        PublicWorkoutStaffCredential.objects.update_or_create(
            username='renan', defaults={'password_hash': make_password('senha-de-teste'), 'is_active': True},
        )
        self.client.post(reverse('public-workout-staff-login'), {'username': 'renan', 'password': 'senha-de-teste'})

    def test_shows_last_workout_date_and_days_since(self):
        account, _sub = _make_active_subscription('bruno@example.com', plan_slug='bruno')
        _log_weight(account, movement_slug='squat', weight_kg=100, performed_on=date.today() - timedelta(days=12), key_suffix='a')

        response = self.client.get(reverse('public-workout-coach-roster'))

        self.assertContains(response, '12 dias sem treinar')

    def test_never_registered_shows_warning_pill_instead_of_a_date(self):
        _make_active_subscription('sem-carga@example.com', plan_slug='sem-carga')

        response = self.client.get(reverse('public-workout-coach-roster'))

        self.assertContains(response, 'nunca registrou')

    def test_whatsapp_button_only_appears_when_phone_is_set(self):
        _make_active_subscription('com-whats@example.com', plan_slug='comwhats', whatsapp='11987654321')
        _make_active_subscription('sem-whats@example.com', plan_slug='semwhats', whatsapp='')

        response = self.client.get(reverse('public-workout-coach-roster'))
        html = response.content.decode()

        self.assertIn('wa.me/11987654321', html)
        self.assertIn('sem WhatsApp', html)

    def test_canceled_subscription_never_appears(self):
        _account, subscription = _make_active_subscription('cancelado@example.com', plan_slug='cancelado')
        subscription.status = PublicWorkoutSubscriptionStatus.CANCELED
        subscription.save(update_fields=['status'])

        response = self.client.get(reverse('public-workout-coach-roster'))

        self.assertNotContains(response, 'cancelado@example.com')


class CoachStudentRosterRiskTests(TestCase):
    # Radar de risco (achado do Renan: "aluno que nao vai geralmente nao
    # renova, que nao progride nao esta tendo resultado") -- confirma que
    # o roster classifica, prioriza e explica, nao so lista.

    def setUp(self):
        self.client = Client()
        PublicWorkoutStaffCredential.objects.update_or_create(
            username='renan', defaults={'password_hash': make_password('senha-de-teste'), 'is_active': True},
        )
        self.client.post(reverse('public-workout-staff-login'), {'username': 'renan', 'password': 'senha-de-teste'})

    def _get_roster(self):
        return self.client.get(reverse('public-workout-coach-roster'))

    def test_stale_student_lands_in_high_risk_lane_with_explicit_reason(self):
        _make_active_subscription('sumido@example.com', plan_slug='sumido')
        # nunca registrou carga -- days_since_last_workout=None -> high

        response = self._get_roster()

        self.assertEqual(response.context['risk_summary']['high'], 1)
        self.assertContains(response, 'nunca registrou treino')

    def test_declining_trend_surfaces_as_a_readable_reason(self):
        account, _sub = _make_active_subscription('declinio@example.com', plan_slug='declinio')
        for offset, weight in ((14, 110), (7, 108), (0, 95)):
            _log_weight(account, movement_slug='squat', weight_kg=weight, performed_on=date.today() - timedelta(days=offset), key_suffix=str(offset))

        response = self._get_roster()

        self.assertContains(response, 'movimento(s) em queda')

    def test_healthy_student_appears_in_neither_lane(self):
        _make_active_subscription('saudavel@example.com', plan_slug='saudavel')
        account = PublicWorkoutAccount.objects.get(email='saudavel@example.com')
        _log_weight(account, movement_slug='squat', weight_kg=100, performed_on=date.today(), key_suffix='a')

        response = self._get_roster()

        self.assertEqual(response.context['risk_summary']['high'], 0)
        self.assertEqual(response.context['risk_summary']['medium'], 0)
        self.assertContains(response, 'Ninguém em alto risco agora.')
        self.assertContains(response, 'Ninguém de olho agora.')

    def test_past_due_subscription_is_always_high_risk(self):
        _account, subscription = _make_active_subscription('atrasado@example.com', plan_slug='atrasado')
        subscription.status = PublicWorkoutSubscriptionStatus.PAST_DUE
        subscription.save(update_fields=['status'])

        response = self._get_roster()

        self.assertEqual(response.context['risk_summary']['high'], 1)
        self.assertContains(response, 'pagamento com problema')

    def test_high_risk_rows_are_sorted_before_healthy_rows(self):
        _make_active_subscription('em-dia@example.com', plan_slug='emdia')
        healthy_account = PublicWorkoutAccount.objects.get(email='em-dia@example.com')
        _log_weight(healthy_account, movement_slug='squat', weight_kg=100, performed_on=date.today(), key_suffix='a')
        _make_active_subscription('sumido-ordenacao@example.com', plan_slug='sumidoordenacao')

        response = self._get_roster()

        levels = [row.risk_level for row in response.context['rows']]
        self.assertEqual(levels[0], 'high')
        self.assertIn('healthy', levels)
        self.assertLess(levels.index('high'), levels.index('healthy'))

    def test_renewal_within_a_week_counts_in_summary_without_forcing_high_risk(self):
        account, subscription = _make_active_subscription('renovando@example.com', plan_slug='renovando')
        _log_weight(account, movement_slug='squat', weight_kg=100, performed_on=date.today(), key_suffix='a')
        subscription.current_period_end = timezone.now() + timedelta(days=3)
        subscription.save(update_fields=['current_period_end'])

        response = self._get_roster()

        self.assertEqual(response.context['risk_summary']['renewing_soon'], 1)
        self.assertEqual(response.context['risk_summary']['high'], 0)
        self.assertContains(response, 'renovação em 3 dia(s)')


class CoachStudentDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        PublicWorkoutStaffCredential.objects.update_or_create(
            username='renan', defaults={'password_hash': make_password('senha-de-teste'), 'is_active': True},
        )
        self.client.post(reverse('public-workout-staff-login'), {'username': 'renan', 'password': 'senha-de-teste'})
        self.account, self.subscription = _make_active_subscription('bruno@example.com', plan_slug='bruno')
        self.detail_url = reverse('public-workout-coach-student-detail', kwargs={'account_id': self.account.pk})

    def test_shows_program_versions(self):
        publish_program(slug='bruno', payload=build_example_payload())

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'v1')

    def test_shows_evolution_chart_card_for_logged_movement(self):
        _log_weight(self.account, movement_slug='squat', weight_kg=100, performed_on=date.today() - timedelta(days=14), key_suffix='a')
        _log_weight(self.account, movement_slug='squat', weight_kg=110, performed_on=date.today(), key_suffix='b')

        response = self.client.get(self.detail_url)

        self.assertContains(response, 'squat')
        self.assertContains(response, '110,0 kg')

    def test_post_generates_ai_draft_and_redirects_with_notice(self):
        from public_workouts.models import (
            PublicWorkoutTrainingExperience,
            PublicWorkoutTrainingGoal,
            PublicWorkoutTrainingLocation,
        )
        from public_workouts.services import save_training_profile

        save_training_profile(
            account_id=self.account.pk, goal=PublicWorkoutTrainingGoal.HYPERTROPHY,
            physical_restrictions=[], physical_restrictions_detail='',
            training_experience=PublicWorkoutTrainingExperience.LESS_THAN_6_MONTHS, days_per_week=3,
            training_location=PublicWorkoutTrainingLocation.FULL_GYM, motivation='', biggest_difficulty='',
            consent_given=True,
        )

        with mock.patch(
            'public_workouts.program_generation_ai.generate_program_draft_payload',
            return_value=(build_example_payload(), 'claude-haiku-4-5-20251001'),
        ):
            response = self.client.post(self.detail_url, follow=True)

        self.assertContains(response, 'rascunho gerado')
        self.assertTrue(PublicWorkoutProgramDraft.objects.filter(account=self.account).exists())

    def test_post_without_subscription_shows_error_notice(self):
        lone_account = PublicWorkoutAccount.objects.create(email='sem-assinatura-detalhe@example.com')
        detail_url = reverse('public-workout-coach-student-detail', kwargs={'account_id': lone_account.pk})

        response = self.client.post(detail_url, follow=True)

        self.assertContains(response, 'nada pra gerar')
