"""
ARQUIVO: testes de public_workouts/dashboard.py (painel Início/Sua semana).
"""

from datetime import date

from django.test import SimpleTestCase

from public_workouts.dashboard import build_program_summary, build_week_overview
from public_workouts.schema import build_example_payload


class BuildWeekOverviewTests(SimpleTestCase):
    def test_returns_seven_days_monday_to_sunday(self):
        payload = build_example_payload()
        today = date(2026, 1, 7)  # quarta-feira

        week = build_week_overview(payload=payload, completed_dates=set(), today=today)

        self.assertEqual([day.day_id for day in week], ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'])
        self.assertEqual(week[0].date, date(2026, 1, 5))  # segunda daquela semana
        self.assertEqual(week[-1].date, date(2026, 1, 11))  # domingo daquela semana

    def test_marks_today_correctly(self):
        payload = build_example_payload()
        today = date(2026, 1, 7)  # quarta-feira

        week = build_week_overview(payload=payload, completed_dates=set(), today=today)

        wednesday = next(day for day in week if day.day_id == 'qua')
        self.assertTrue(wednesday.is_today)
        self.assertEqual(sum(1 for day in week if day.is_today), 1)

    def test_has_program_true_only_for_prescribed_weekdays(self):
        payload = build_example_payload()  # dia unico: day_id='seg'

        week = build_week_overview(payload=payload, completed_dates=set(), today=date(2026, 1, 7))

        by_id = {day.day_id: day for day in week}
        self.assertTrue(by_id['seg'].has_program)
        self.assertFalse(by_id['ter'].has_program)

    def test_is_complete_true_when_date_in_completed_dates(self):
        payload = build_example_payload()
        monday = date(2026, 1, 5)

        week = build_week_overview(payload=payload, completed_dates={monday}, today=date(2026, 1, 7))

        by_id = {day.day_id: day for day in week}
        self.assertTrue(by_id['seg'].is_complete)
        self.assertFalse(by_id['ter'].is_complete)

    def test_week_boundary_sunday_still_belongs_to_the_same_week(self):
        payload = build_example_payload()
        sunday = date(2026, 1, 11)

        week = build_week_overview(payload=payload, completed_dates=set(), today=sunday)

        self.assertEqual(week[0].date, date(2026, 1, 5))
        self.assertEqual(week[-1].date, sunday)
        self.assertTrue(week[-1].is_today)


class BuildProgramSummaryTests(SimpleTestCase):
    def test_includes_program_label_and_weeks(self):
        payload = build_example_payload()

        summary = build_program_summary(payload)

        self.assertIn(payload['program_label'], summary['headline'])
        self.assertIn(str(payload['weeks']), summary['headline'])

    def test_body_counts_days_and_movements(self):
        payload = build_example_payload()  # 1 dia, 1 bloco, 1 movimento (is_tracked=True)

        summary = build_program_summary(payload)

        self.assertIn('1 dia por semana', summary['body'])
        self.assertIn('1 exercício no total', summary['body'])
        self.assertIn('com carga acompanhada', summary['body'])

    def test_pluralizes_days_and_movements(self):
        payload = build_example_payload()
        second_day = dict(payload['days'][0])
        second_day['day_id'] = 'qua'
        payload['days'].append(second_day)

        summary = build_program_summary(payload)

        self.assertIn('2 dias por semana', summary['body'])
        self.assertIn('2 exercícios no total', summary['body'])

    def test_no_days_shows_empty_state_message(self):
        payload = build_example_payload()
        payload['days'] = []

        summary = build_program_summary(payload)

        self.assertEqual(summary['body'], 'Ainda não há dias configurados neste programa.')

    def test_no_tracked_movements_omits_tracked_clause(self):
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['is_tracked'] = False

        summary = build_program_summary(payload)

        self.assertNotIn('acompanhada', summary['body'])
