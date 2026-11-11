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

    def test_main_lift_takes_phase_reps_accessory_keeps_its_own(self):
        adaptation = PHASE_PROFILES['adaptation']
        main = _work(build_guided_series(MAIN, phase_profile=adaptation, payload=PAYLOAD))
        acc = _work(build_guided_series(ACCESSORY, phase_profile=adaptation, payload=PAYLOAD))
        self.assertEqual((main[0]['reps'], main[0]['reps_max']), (12, 15))
        self.assertEqual((acc[0]['reps'], acc[0]['reps_max']), (12, 15))
        intensity = PHASE_PROFILES['intensity']
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
            'Esta semana (Deload): 2 séries de trabalho · 8–10 reps · RIR 4,5',
        )

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
