"""
ARQUIVO: testes de public_workouts/dashboard.py (painel Início/Sua semana).
"""

from datetime import date

from django.test import SimpleTestCase

from public_workouts.dashboard import (
    build_program_summary, build_week_overview, build_workout_day_selection, day_keyword, day_short_label,
)
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


class BuildWorkoutDaySelectionTests(SimpleTestCase):
    def test_selects_today_instead_of_payload_order(self):
        payload = build_example_payload()
        tuesday = dict(payload['days'][0], day_id='ter', label='Terça — Superior')
        payload['days'] = [payload['days'][0], tuesday]

        selection = build_workout_day_selection(payload=payload, today=date(2026, 1, 6))

        self.assertEqual(selection['selected_day_id'], 'ter')
        self.assertFalse(selection['is_rest_day'])
        self.assertIsNone(selection['next_day'])

    def test_rest_day_previews_next_prescribed_day_across_week_boundary(self):
        payload = build_example_payload()
        monday = dict(payload['days'][0], day_id='seg', label='Segunda — Inferior')
        thursday = dict(payload['days'][0], day_id='qui', label='Quinta — Superior B')
        payload['days'] = [thursday, monday]

        selection = build_workout_day_selection(payload=payload, today=date(2026, 1, 11))

        self.assertTrue(selection['is_rest_day'])
        self.assertEqual(selection['selected_day_id'], 'seg')
        self.assertEqual(selection['next_day'], {
            'day_id': 'seg', 'short_label': 'Seg', 'label': 'Inferior',
        })

    def test_empty_program_has_no_selected_day(self):
        payload = build_example_payload()
        payload['days'] = []

        selection = build_workout_day_selection(payload=payload, today=date(2026, 1, 7))

        self.assertIsNone(selection['selected_day_id'])
        self.assertIsNone(selection['next_day'])


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


class DayShortLabelTests(SimpleTestCase):
    def test_known_day_id_returns_three_letter_abbreviation(self):
        self.assertEqual(day_short_label('seg'), 'Seg')
        self.assertEqual(day_short_label('sab'), 'Sáb')

    def test_unknown_day_id_returns_itself(self):
        self.assertEqual(day_short_label('xyz'), 'xyz')


class DayKeywordTests(SimpleTestCase):
    def test_strips_hyphen_prefixed_weekday_name(self):
        # franciele: 'Segunda - Pernas Quadríceps'
        self.assertEqual(day_keyword(day_id='seg', label='Segunda - Pernas Quadríceps'), 'Pernas Quadríceps')

    def test_strips_em_dash_prefixed_weekday_name(self):
        # bruno: 'Upper A — Push Pesado' nao tem prefixo de dia -- so' testa
        # o caso que TEM: 'Segunda — Inferior — Glúteo' (johnespanha).
        self.assertEqual(
            day_keyword(day_id='seg', label='Segunda — Inferior — Glúteo + Abdômen'),
            'Inferior — Glúteo + Abdômen',
        )

    def test_label_without_weekday_prefix_is_returned_unchanged(self):
        # juliana/henrique: label e' so' a palavra-chave, sem nome de dia.
        self.assertEqual(day_keyword(day_id='seg', label='Quadríceps'), 'Quadríceps')
        self.assertEqual(day_keyword(day_id='seg', label='Upper A — Push Pesado'), 'Upper A — Push Pesado')

    def test_unknown_day_id_returns_label_unchanged(self):
        self.assertEqual(day_keyword(day_id='xyz', label='Segunda - Pernas'), 'Segunda - Pernas')

    def test_empty_label_returns_empty(self):
        self.assertEqual(day_keyword(day_id='seg', label=''), '')
