"""
ARQUIVO: testes do analytics do treinador (Curva) -- coach_analytics.py +
CoachAnalyticsView.

POR QUE ELE EXISTE:
- Garante que cada sinal (sumiu, abre e nao treina, RIR alto, recorde,
  sem push) vira a ACAO certa, com motivo em texto.
- Garante que abrir o treino gera um registro com o dispositivo, e que
  recarregar a pagina em seguida nao infla a contagem.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from public_workouts.billing import get_or_create_subscription
from public_workouts.coach_analytics import build_coach_analytics, classify_device, record_program_open
from public_workouts.models import (
    PublicWorkoutAccount,
    PublicWorkoutLoadLog,
    PublicWorkoutLoadLogAchievementKind,
    PublicWorkoutLoadLogSetRole,
    PublicWorkoutProgramOpen,
    PublicWorkoutStaffCredential,
    PublicWorkoutSubscriptionStatus,
    PublicWorkoutTier,
)

IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148'
DESKTOP_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'


def _student(email, *, plan_slug):
    account = PublicWorkoutAccount.objects.create(email=email)
    subscription = get_or_create_subscription(account=account, tier=PublicWorkoutTier.ESSENCIAL, plan_slug=plan_slug)
    subscription.status = PublicWorkoutSubscriptionStatus.ACTIVE
    subscription.save(update_fields=['status'])
    return account


def _log(account, *, days_ago, weight=100, rir=None, record=False, suffix=''):
    PublicWorkoutLoadLog.objects.create(
        account=account, movement_slug='squat', weight_kg=Decimal(str(weight)), reps=8, rir=rir,
        performed_on=timezone.localdate() - timedelta(days=days_ago), set_role=PublicWorkoutLoadLogSetRole.TOP_SET,
        idempotency_key=f'{account.pk}-{days_ago}-{suffix}',
        achievement_kind=PublicWorkoutLoadLogAchievementKind.LOAD_RECORD if record else None,
        achievement_previous_weight_kg=Decimal(weight - 5) if record else None,
    )


def _student_row(analytics, account):
    return next(row for row in analytics['students'] if row['account_id'] == account.pk)


def _action_keys(row):
    return [action['key'] for action in row['actions']]


class ClassifyDeviceTests(TestCase):
    def test_classifies_common_user_agents(self):
        self.assertEqual(classify_device(IPHONE_UA), 'mobile')
        self.assertEqual(classify_device(DESKTOP_UA), 'desktop')
        self.assertEqual(classify_device('Mozilla/5.0 (iPad; CPU OS 17_0)'), 'tablet')
        self.assertEqual(classify_device(''), 'unknown')


class RecordProgramOpenTests(TestCase):
    def test_reload_within_dedupe_window_is_not_a_new_open(self):
        account = _student('ana@example.com', plan_slug='ana')
        now = timezone.now()

        record_program_open(account=account, plan_slug='ana', user_agent=IPHONE_UA, at=now)
        record_program_open(account=account, plan_slug='ana', user_agent=IPHONE_UA, at=now + timedelta(minutes=5))
        record_program_open(account=account, plan_slug='ana', user_agent=IPHONE_UA, at=now + timedelta(hours=2))

        self.assertEqual(PublicWorkoutProgramOpen.objects.filter(account=account).count(), 2)
        self.assertEqual(PublicWorkoutProgramOpen.objects.first().device, 'mobile')


class BuildCoachAnalyticsTests(TestCase):
    def test_student_who_vanished_gets_reengage_action(self):
        account = _student('bruno@example.com', plan_slug='bruno')
        _log(account, days_ago=15)

        row = _student_row(build_coach_analytics(window_days=30), account)

        self.assertEqual(row['actions'][0]['key'], 'reengage')
        self.assertEqual(row['tone'], 'act')

    def test_opens_without_training_is_flagged_and_mobile_share_counted(self):
        account = _student('carla@example.com', plan_slug='carla')
        _log(account, days_ago=1)
        for days_ago in (2, 4, 6):
            PublicWorkoutProgramOpen.objects.create(
                account=account, device='mobile', opened_at=timezone.now() - timedelta(days=days_ago),
            )

        row = _student_row(build_coach_analytics(window_days=30), account)

        self.assertIn('opens_no_train', _action_keys(row))
        self.assertEqual(row['opens_without_training'], 3)
        self.assertEqual(row['mobile_percent'], 100)

    def test_high_rir_suggests_raising_load_and_record_suggests_celebrating(self):
        account = _student('davi@example.com', plan_slug='davi')
        for index, days_ago in enumerate((1, 3, 5, 8, 10, 12)):
            _log(account, days_ago=days_ago, rir=Decimal('4'), record=index == 0, suffix=str(index))

        row = _student_row(build_coach_analytics(window_days=30), account)

        self.assertIn('too_easy', _action_keys(row))
        self.assertIn('celebrate', _action_keys(row))
        self.assertEqual(row['records'], 1)

    def test_decisions_group_students_and_put_urgent_first(self):
        vanished = _student('eva@example.com', plan_slug='eva')
        _log(vanished, days_ago=20)

        analytics = build_coach_analytics(window_days=30)

        self.assertEqual(analytics['decisions'][0]['key'], 'reengage')
        self.assertEqual(analytics['decisions'][0]['students'][0]['account_id'], vanished.pk)

    def test_invalid_window_falls_back_to_default(self):
        self.assertEqual(build_coach_analytics(window_days=12)['window_days'], 30)


class LoadEvolutionTests(TestCase):
    def test_compares_last_top_set_before_window_with_latest(self):
        account = _student('gil@example.com', plan_slug='gil')
        _log(account, days_ago=40, weight=100, suffix='a')
        _log(account, days_ago=10, weight=105, suffix='b')
        _log(account, days_ago=2, weight=112.5, suffix='c')

        evolution = build_coach_analytics(window_days=30)['load_evolution']

        movement = evolution['students'][0]['movements'][0]
        self.assertEqual(movement['baseline_kg'], '100')
        self.assertEqual(movement['current_kg'], '112,5')
        self.assertEqual(movement['delta_kg_label'], '+12,5')
        self.assertEqual(movement['delta_percent'], 12)
        self.assertEqual(movement['sessions'], 2)
        self.assertTrue(movement['spark_points'])
        self.assertEqual(evolution['top_gains'][0]['account_id'], account.pk)

    def test_exercise_summary_counts_students_and_ignores_warmups(self):
        first = _student('hugo@example.com', plan_slug='hugo')
        second = _student('ines@example.com', plan_slug='ines')
        for account in (first, second):
            _log(account, days_ago=12, weight=80, suffix='a')
            _log(account, days_ago=3, weight=85, suffix='b')
        PublicWorkoutLoadLog.objects.create(
            account=first, movement_slug='bench', weight_kg=Decimal('40'), reps=10,
            performed_on=timezone.localdate(), set_role=PublicWorkoutLoadLogSetRole.WARMUP,
            idempotency_key=f'{first.pk}-warmup',
        )

        exercises = build_coach_analytics(window_days=30)['load_evolution']['exercises']

        self.assertEqual([(e['slug'], e['students']) for e in exercises], [('squat', 2)])

    def test_student_without_load_in_window_is_left_out(self):
        account = _student('joana@example.com', plan_slug='joana')
        _log(account, days_ago=60, weight=50, suffix='a')

        self.assertEqual(build_coach_analytics(window_days=30)['load_evolution']['students'], [])


class CoachAnalyticsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('public-workout-coach-analytics')
        PublicWorkoutStaffCredential.objects.update_or_create(
            username='renan', defaults={'password_hash': make_password('senha-de-teste'), 'is_active': True},
        )

    def test_lives_at_treinos_coach(self):
        self.assertEqual(self.url, '/treinos/coach')

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('public-workout-staff-login'), response.url)

    def test_staff_sees_decisions_and_period_switch(self):
        account = _student('fabio@example.com', plan_slug='fabio')
        _log(account, days_ago=14)
        self.client.post(reverse('public-workout-staff-login'), {'username': 'renan', 'password': 'senha-de-teste'})

        response = self.client.get(self.url, {'periodo': '90'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sumiram do treino')
        self.assertContains(response, 'Evolução das cargas')
        self.assertContains(response, '?periodo=7')
        self.assertEqual(response.context['analytics']['window_days'], 90)
