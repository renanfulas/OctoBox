from datetime import date

from django.test import SimpleTestCase

from public_workouts.guided_workout import build_guided_series
from public_workouts.periodization import PHASE_PROFILES, suggest_progressive_load_kg
from public_workouts.phase_prescription import phase_week_note, reference_phase

PAYLOAD = {
    'program_id': 'p1',
    'started_on': '2026-10-05',
    'periodization': {'weeks': [
        {'week_number': 1, 'phase_type': 'adaptation'},
        {'week_number': 2, 'phase_type': 'volume'},
        {'week_number': 3, 'phase_type': 'volume'},
        {'week_number': 4, 'phase_type': 'volume'},
        {'week_number': 5, 'phase_type': 'deload'},
    ]},
}
MAIN = {'movement_slug': 'squat', 'reps_spec': '1× Prep (10) → 1× Feeder (6) → 3× Top (8-12)'}
ACCESSORY = {'movement_slug': 'lateral', 'reps_spec': '3× Top (12-15)'}
VOLUME, DELOAD = PHASE_PROFILES['volume'], PHASE_PROFILES['deload']


def _work(series):
    return [row for row in series if row['role'] == 'top_set']


class PhasePrescriptionTests(SimpleTestCase):
    def test_reference_is_most_frequent_non_deload_phase(self):
        self.assertEqual(reference_phase(PAYLOAD).key, 'volume')

    def test_reference_phase_keeps_published_prescription(self):
        series = build_guided_series(MAIN, phase_profile=VOLUME, payload=PAYLOAD)
        self.assertEqual(len(_work(series)), 3)
        self.assertEqual((_work(series)[0]['reps'], _work(series)[0]['reps_max']), (8, 12))
        self.assertEqual(phase_week_note(series, phase=VOLUME, reference=VOLUME), '')

    def test_deload_cuts_work_sets_and_keeps_warmups(self):
        series = build_guided_series(MAIN, phase_profile=DELOAD, payload=PAYLOAD)
        self.assertEqual(len(_work(series)), 2)  # 3 × 0,5/1,15 = 1,3 -> 2
        self.assertEqual([row['role'] for row in series[:2]], ['warmup', 'feeder'])
        self.assertEqual(_work(series)[0]['rir_target'], DELOAD.rir_target)
        self.assertEqual([row['set_number'] for row in series], [1, 2, 3, 4])

    def test_main_lift_takes_phase_reps_only_when_coach_range_is_outside_it(self):
        intensity = PHASE_PROFILES['intensity']
        # 8-12 não cruza 3-6: o principal assume a faixa da fase.
        main = _work(build_guided_series(MAIN, phase_profile=intensity, payload=PAYLOAD))
        self.assertEqual((main[0]['reps'], main[0]['reps_max']), (3, 6))
        # 8-12 cruza Adaptação 12-15: a escolha do treinador fica.
        adaptation = PHASE_PROFILES['adaptation']
        main = _work(build_guided_series(MAIN, phase_profile=adaptation, payload=PAYLOAD))
        self.assertEqual((main[0]['reps'], main[0]['reps_max']), (8, 12))
        # Acessório nunca muda as reps.
        acc = _work(build_guided_series(ACCESSORY, phase_profile=intensity, payload=PAYLOAD))
        self.assertEqual((acc[0]['reps'], acc[0]['reps_max']), (12, 15))

    def test_deload_drops_amrap(self):
        movement = {'movement_slug': 'x', 'reps_spec': '1× Feeder (6) → 3× Top (8-10) → 1× AMRAP'}
        series = build_guided_series(movement, phase_profile=DELOAD, payload=PAYLOAD)
        self.assertNotIn('max_set', [row['role'] for row in series])

    def test_week_note_text(self):
        series = build_guided_series(MAIN, phase_profile=DELOAD, payload=PAYLOAD)
        self.assertEqual(
            phase_week_note(series, phase=DELOAD, reference=VOLUME),
            'Esta semana (Deload): 2 séries de trabalho · 8–12 reps · RIR 4,5',
        )

    def test_label_first_legacy_text_is_parsed(self):
        movement = {'movement_slug': 'x', 'reps_spec': (
            'Preparatória 2× 8 / 5 → Feeder 1× 10 → Top Set 3× 8-10 → Max Set 1× AMRAP (até a falha)')}
        roles = [row['role'] for row in build_guided_series(movement)]
        self.assertEqual(roles, ['warmup', 'warmup', 'feeder', 'top_set', 'top_set', 'top_set', 'max_set'])

    def test_label_first_with_extra_instruction_stays_freeform(self):
        for spec in ('Top Set 3x 8-12 → 1x dropset', 'Feeder 1x 8-10 Opcional'):
            self.assertEqual(build_guided_series({'reps_spec': spec})[0]['role'], 'legacy_unknown')

    def test_alternating_sides_keep_the_pair_in_deload(self):
        movement = {'movement_slug': 'bulgaro', 'reps_spec': '3× 8 por lado', 'guided_prescription': {
            'version': 1, 'stages': [{'stage_id': 'plain-1', 'role': 'top_set', 'min_sets': 6, 'max_sets': 6,
                                      'reps_min': 8, 'reps_max': 8, 'rest_seconds': 20,
                                      'load_rule': {'kind': 'manual'}}]}}
        series = build_guided_series(movement, phase_profile=DELOAD, payload=PAYLOAD)
        self.assertEqual(len(_work(series)), 4)  # 2 por lado, nunca 3 linhas
        self.assertEqual(phase_week_note(series, phase=DELOAD, reference=VOLUME),
                         'Esta semana (Deload): 2 séries de trabalho por lado · 8 reps · RIR 4,5')

    def test_per_side_text_with_one_row_per_set_scales_normally(self):
        movement = {'movement_slug': 'deadbug', 'reps_spec': '2× Top (8-10 por lado)'}
        work = _work(build_guided_series(movement, phase_profile=DELOAD, payload=PAYLOAD))
        self.assertEqual(len(work), 1)

    def test_without_payload_nothing_changes(self):
        series = build_guided_series(MAIN, phase_profile=DELOAD)
        self.assertEqual(len(_work(series)), 3)


class LoadProgressionTests(SimpleTestCase):
    def _log(self, weight, reps, rir, on='2026-10-12'):
        return {'weight_kg': weight, 'reps': reps, 'rir': rir, 'performed_on': on, 'program_id': 'p1'}

    def test_same_phase_hitting_top_reps_progresses(self):
        value = suggest_progressive_load_kg(
            payload=PAYLOAD, current_phase=VOLUME, last_log=self._log(100, 12, 2.5), reps_max_target=12,
        )
        self.assertEqual(value, 102.5)

    def test_same_phase_below_top_reps_holds(self):
        value = suggest_progressive_load_kg(
            payload=PAYLOAD, current_phase=VOLUME, last_log=self._log(100, 10, 2.5), reps_max_target=12,
        )
        self.assertEqual(value, 100)

    def test_same_phase_too_hard_holds(self):
        value = suggest_progressive_load_kg(
            payload=PAYLOAD, current_phase=VOLUME, last_log=self._log(100, 12, 0), reps_max_target=12,
        )
        self.assertEqual(value, 100)

    def test_phase_change_jump_is_capped(self):
        # Adaptação (56%) -> Volume (67%) seria +19,6%; limitado a +10%.
        value = suggest_progressive_load_kg(
            payload=PAYLOAD, current_phase=VOLUME, last_log=self._log(50, 15, 3, on='2026-10-06'),
        )
        self.assertEqual(value, 55)

    def test_hold_load_phase_never_progresses(self):
        payload = {**PAYLOAD, 'periodization': {'weeks': [{'week_number': 1, 'phase_type': 'maintenance'}]}}
        value = suggest_progressive_load_kg(
            payload=payload, current_phase=PHASE_PROFILES['maintenance'],
            last_log=self._log(100, 10, 3, on=date(2026, 10, 6).isoformat()), reps_max_target=10,
        )
        self.assertEqual(value, 100)

    def test_week_boundary_follows_program_start_not_iso_week(self):
        # Programa começa na quarta (2026-10-07): terça 13 é semana 1, quarta 14 é semana 2,
        # mesma semana ISO. A progressão dupla precisa valer.
        payload = {**PAYLOAD, 'started_on': '2026-10-07',
                   'periodization': {'weeks': [{'week_number': 1, 'phase_type': 'volume'},
                                               {'week_number': 2, 'phase_type': 'volume'}]}}
        value = suggest_progressive_load_kg(
            payload=payload, current_phase=VOLUME, last_log=self._log(100, 12, 2.5, on='2026-10-13'),
            reps_max_target=12, today=date(2026, 10, 14),
        )
        self.assertEqual(value, 102.5)
        same_week = suggest_progressive_load_kg(
            payload=payload, current_phase=VOLUME, last_log=self._log(100, 12, 2.5, on='2026-10-07'),
            reps_max_target=12, today=date(2026, 10, 13),
        )
        self.assertEqual(same_week, 100)

    def test_deload_never_progresses(self):
        payload = {**PAYLOAD, 'started_on': '2026-10-05',
                   'periodization': {'weeks': [{'week_number': 1, 'phase_type': 'deload'},
                                               {'week_number': 2, 'phase_type': 'deload'}]}}
        value = suggest_progressive_load_kg(
            payload=payload, current_phase=DELOAD, last_log=self._log(80, 10, 5, on='2026-10-06'),
            reps_max_target=10, today=date(2026, 10, 13),
        )
        self.assertEqual(value, 80)

    def test_leaving_deload_returns_to_pre_deload_load(self):
        # 100 kg em Volume -> deload x 57,5/67 = 85,8 -> 85 ; de volta: 85 x 67/57,5 = 99 -> 100.
        into = suggest_progressive_load_kg(
            payload=PAYLOAD, current_phase=DELOAD, last_log=self._log(100, 10, 2.5, on='2026-10-26'),
            target_reps=10, target_rir=4.5,
        )
        self.assertEqual(into, 85)
        back = suggest_progressive_load_kg(
            payload={**PAYLOAD, 'periodization': {'weeks': PAYLOAD['periodization']['weeks'] + [
                {'week_number': 6, 'phase_type': 'volume'}]}},
            current_phase=VOLUME, last_log=self._log(85, 10, 4.5, on='2026-11-02'),
            target_reps=10, target_rir=2.5,
        )
        self.assertEqual(back, 100)

    def test_phase_change_follows_reps_and_rir_of_the_week(self):
        # Mesmas reps, RIR 2,5 -> 1,5 (Volume -> Força-Hipertrofia): ~+3%, não +13% do %RM-meio.
        payload = {**PAYLOAD, 'periodization': {'weeks': [
            {'week_number': 1, 'phase_type': 'volume'}, {'week_number': 2, 'phase_type': 'strength_hypertrophy'}]}}
        value = suggest_progressive_load_kg(
            payload=payload, current_phase=PHASE_PROFILES['strength_hypertrophy'],
            last_log=self._log(100, 10, 2.5, on='2026-10-06'), target_reps=10, target_rir=1.5,
        )
        self.assertEqual(value, 102.5)


class CoachWeekTableTests(SimpleTestCase):
    """A planilha do treinador (weeks_table) vence o perfil canônico da fase."""

    def _payload(self, phase_types, reps):
        return {
            'program_id': 'p1', 'started_on': '2026-10-05',
            'periodization': {
                'weeks': [{'week_number': i + 1, 'phase_type': t} for i, t in enumerate(phase_types)],
                'weeks_table': [{'week': f'S{i + 1}', 'reps': r, 'focus': '', 'guidance': ''}
                                for i, r in enumerate(reps)],
            },
        }

    def test_peak_week_uses_coach_reps_not_one_to_three(self):
        # Caso real (Milene): "Peak" 8-12 reps; o perfil canônico daria 1-3.
        payload = self._payload(['volume', 'volume', 'peak'], ['10-12 reps', '12-15 reps', '8-12 reps'])
        work = _work(build_guided_series(MAIN, phase_profile=PHASE_PROFILES['peak'], payload=payload,
                                         on=date(2026, 10, 19)))
        self.assertEqual((work[0]['reps'], work[0]['reps_max']), (8, 12))

    def test_coach_reps_apply_even_in_the_reference_phase(self):
        # Semana 2 é Volume (referência), mas o treinador pediu 12-15.
        payload = self._payload(['volume', 'volume', 'peak'], ['10-12 reps', '12-15 reps', '8-12 reps'])
        series = build_guided_series(MAIN, phase_profile=VOLUME, payload=payload, on=date(2026, 10, 12))
        work = _work(series)
        self.assertEqual(len(work), 3)
        self.assertEqual((work[0]['reps'], work[0]['reps_max']), (12, 15))
        self.assertEqual(phase_week_note(series, phase=VOLUME, reference=VOLUME),
                         'Esta semana (Volume): 3 séries de trabalho · 12–15 reps')

    def test_text_that_is_not_a_plain_range_is_ignored(self):
        payload = self._payload(['volume', 'deload'], ['Faixas de cada exercício', 'Execução confortável, RIR 4-5'])
        work = _work(build_guided_series(MAIN, phase_profile=DELOAD, payload=payload, on=date(2026, 10, 12)))
        self.assertEqual((work[0]['reps'], work[0]['reps_max']), (8, 12))

    def test_test_week_is_a_single_amrap_on_the_last_work_set(self):
        payload = self._payload(['maintenance', 'maintenance', 'test'], ['8-10 reps', '6-8 reps', '6-8 reps'])
        test = PHASE_PROFILES['test']
        series = build_guided_series(MAIN, phase_profile=test, payload=payload, on=date(2026, 10, 19))
        work = _work(series)
        self.assertEqual([row['rir_target'] for row in work[:-1]], [PHASE_PROFILES['maintenance'].rir_target] * (len(work) - 1))
        self.assertEqual((work[-1]['rir_target'], work[-1].get('amrap')), (0.0, True))
        self.assertEqual((work[0]['reps'], work[0]['reps_max']), (6, 8))
        self.assertIn('última série AMRAP (RIR 0)', phase_week_note(
            series, phase=test, reference=PHASE_PROFILES['maintenance']))

    def test_banner_and_chart_show_coach_reps(self):
        from public_workouts.periodization import build_chart_points_from_weeks
        from public_workouts.templatetags.public_workouts_extras import periodization_phase_banner
        payload = self._payload(['volume', 'volume', 'peak'], ['10-12 reps', '12-15 reps', '8-12 reps'])
        points = build_chart_points_from_weeks(payload['periodization']['weeks'], payload)
        self.assertEqual([point['reps'] for point in points], ['10-12', '12-15', '8-12'])
        from freezegun import freeze_time
        with freeze_time('2026-10-20'):
            banner = periodization_phase_banner(payload)
        self.assertEqual((banner['reps_min'], banner['reps_max'], banner['pct_mid']), (8, 12, 75))
