import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from operations.services import wod_paste_parser
from operations.services.wod_paste_parser import parse_weekly_wod_text


WOD_WEEK_FIXTURE = """
Segunda
Mobilidade

Aquecimento
3x
10 lunges
8 front squat
20 sit up

Skill
Semana 2
7 rounds 65%
7 back squat

Wod
10m
21/15/9

Thruster
Pull up

Cada quebra 3 BOB

Terça

Mobilidade

Aquecimento
3x
10 push up
8 shoulder press
100 run

Skill
Emom 20m
A 6 push jerk
B 10 a 12 t2b
C 5 Hang clean
D 2 RC
E rest

Wod  14m
100 push up
50 push press  40/25
400 run

Quarta
Mobilidade

Aquecimento
3x
5 power snatch
5 ohs
5 s balance

Skill
6 rounds

1 p snatch
1 squat snatch

Wod  14m
1.200 run
60 bjo
40 wall ball
15 bmu / 25 pull up

Quinta
Mobilidade
Aquecimento
3x
20 kbs A
12 v up
30 du

Skill
Semana 2

7 rounds 70%
5 deadlift

Wod
Amrap 16m

Duplas um round para cada
15 t2b
10 deadlift
15 strict hspu

Sexta
Mobilidade

Aquecimento
3x
10 Hollow rock
8 front squat
5 strict t2b
5 strict pull up

Skill

A cada 30s por 15 x
1 squat clean + 1 Hang squat clean

Wod  15m
5 rounds

12 front squat
9 Hang clean
6 S2OH
30 du
""".strip()


class WodPasteParserTests(SimpleTestCase):
    def test_w01_preserves_weekdays_strength_reps_loads_and_amrap_timecap(self):
        source = '''Segunda
Aquecimento
5 min remo
Força
Deadlift 5x5 75%
WOD AMRAP 12 min
10 burpees
12 wall balls 9 kg

Quarta
Mobilidade
8 min flow de quadril'''

        parsed = parse_weekly_wod_text(source)

        self.assertEqual([day['weekday'] for day in parsed['days']], [0, 2])
        monday = parsed['days'][0]
        self.assertEqual([block['kind'] for block in monday['blocks']], ['warmup', 'strength', 'metcon'])
        self.assertEqual(monday['blocks'][0]['movements'][0]['reps_spec'], '5 min')
        deadlift = monday['blocks'][1]['movements'][0]
        self.assertEqual(deadlift['movement_slug'], 'deadlift')
        self.assertEqual(deadlift['sets'], 5)
        self.assertEqual(deadlift['reps_spec'], '5')
        self.assertEqual(deadlift['load_spec'], '75%')
        self.assertEqual(deadlift['load_percentage_rm'], 75.0)
        amrap = monday['blocks'][2]
        self.assertEqual(amrap['score_type'], 'amrap')
        self.assertEqual(amrap['timecap_min'], 12)
        wall_balls = amrap['movements'][1]
        self.assertEqual(wall_balls['reps_spec'], '12')
        self.assertEqual(wall_balls['load_spec'], '9 kg')
        wednesday = parsed['days'][1]['blocks'][0]['movements'][0]
        self.assertEqual(wednesday['movement_label_raw'], '8 min flow de quadril')
        self.assertEqual(wednesday['reps_spec'], '8 min')
        self.assertEqual(parsed['parse_warnings'], [])

    def test_w07_fixed_seven_day_week_has_all_weekdays_and_no_warnings(self):
        source = '''Segunda
WOD AMRAP 10 min
8 burpees

Terça
Força
Deadlift 3x5 60%
WOD For time 12 min
10 push up

Quarta
WOD EMOM 10 min
6 power snatch 40 kg

Quinta
WOD AMRAP 9 min
10 box jump

Sexta
Força
Back squat 3x5 70%
WOD For time 14 min
12 wall balls 9 kg

Sábado
WOD AMRAP 12 min
8 lunges

Domingo
Mobilidade
8 min flow de quadril'''

        parsed = parse_weekly_wod_text(source)

        self.assertEqual([day['weekday'] for day in parsed['days']], list(range(7)))
        self.assertEqual(len(parsed['days']), 7)
        self.assertEqual(parsed['parse_warnings'], [])
        self.assertEqual(parsed['days'][0]['blocks'][0]['score_type'], 'amrap')
        self.assertEqual(parsed['days'][1]['blocks'][0]['kind'], 'strength')
        self.assertEqual(parsed['days'][4]['blocks'][0]['movements'][0]['load_spec'], '70%')
        self.assertEqual(
            parsed['days'][6]['blocks'][0]['movements'][0]['movement_label_raw'],
            '8 min flow de quadril',
        )

    def test_w02_custom_movement_keeps_ladder_timecap_and_fixed_load_without_slug_guess(self):
        parsed = parse_weekly_wod_text('''Sexta
WOD For time 18 min
21-15-9 Atlas carry customizado 24 kg''')

        self.assertEqual(len(parsed['days']), 1)
        self.assertEqual(parsed['days'][0]['weekday'], 4)
        block = parsed['days'][0]['blocks'][0]
        self.assertEqual(block['score_type'], 'for_time')
        self.assertEqual(block['timecap_min'], 18)
        self.assertIn('21-15-9', block['format_spec'])
        movement = block['movements'][0]
        self.assertIsNone(movement['movement_slug'])
        self.assertIn('Atlas carry customizado', movement['movement_label_raw'])
        self.assertEqual(movement['load_spec'], '24 kg')
        self.assertEqual(parsed['parse_warnings'], [])

    def test_w06_keeps_only_explicit_weekdays_and_does_not_infer_missing_days(self):
        parsed = parse_weekly_wod_text('''Segunda
WOD AMRAP 10 min
8 burpees

Quinta-feira
WOD EMOM 12 min''')

        self.assertEqual([day['weekday'] for day in parsed['days']], [0, 3])
        self.assertEqual(len(parsed['days']), 2)
        self.assertEqual(parsed['days'][0]['blocks'][0]['score_type'], 'amrap')
        self.assertEqual(parsed['days'][0]['blocks'][0]['movements'][0]['reps_spec'], '8')
        thursday = parsed['days'][1]['blocks'][0]
        self.assertEqual(thursday['score_type'], 'emom')
        self.assertEqual(thursday['timecap_min'], 12)
        self.assertEqual(parsed['parse_warnings'], [])

    def test_movement_dictionary_cache_refreshes_when_file_changes(self):
        with TemporaryDirectory() as temporary_directory:
            dictionary_path = Path(temporary_directory) / 'wod-movement-dictionary.md'
            dictionary_path.write_text('| `alpha_move` | alpha move |\n', encoding='utf-8')

            with patch.object(wod_paste_parser, '_wod_movement_dictionary_path', return_value=dictionary_path):
                wod_paste_parser._load_wod_movement_dictionary_cached.cache_clear()

                first_entries = wod_paste_parser.load_wod_movement_dictionary()
                first_modified_at_ns = dictionary_path.stat().st_mtime_ns

                dictionary_path.write_text('| `beta_move` | beta move |\n', encoding='utf-8')
                os.utime(
                    dictionary_path,
                    ns=(first_modified_at_ns + 1_000_000_000, first_modified_at_ns + 1_000_000_000),
                )

                second_entries = wod_paste_parser.load_wod_movement_dictionary()

        self.assertIn('alpha_move', {slug for slug, _aliases in first_entries})
        self.assertNotIn('alpha_move', {slug for slug, _aliases in second_entries})
        self.assertIn('beta_move', {slug for slug, _aliases in second_entries})

    def test_parser_builds_schema_for_real_week_fixture_without_warnings(self):
        parsed = parse_weekly_wod_text(WOD_WEEK_FIXTURE)

        self.assertIsNone(parsed['week_label'])
        self.assertEqual(parsed['parse_warnings'], [])
        self.assertEqual(len(parsed['days']), 5)

        monday = parsed['days'][0]
        self.assertEqual(monday['weekday'], 0)
        self.assertEqual([block['kind'] for block in monday['blocks']], ['mobility', 'warmup', 'skill', 'metcon'])
        self.assertEqual(monday['blocks'][1]['rounds'], 3)
        self.assertEqual(monday['blocks'][1]['movements'][0]['movement_slug'], 'lunge')
        self.assertEqual(monday['blocks'][2]['title'], 'Semana 2')
        self.assertEqual(monday['blocks'][2]['rounds'], 7)
        self.assertEqual(monday['blocks'][2]['movements'][0]['load_percentage_rm'], 65.0)
        self.assertEqual(monday['blocks'][3]['timecap_min'], 10)
        self.assertEqual(monday['blocks'][3]['format_spec'], '21/15/9')
        self.assertEqual(monday['blocks'][3]['notes'], 'Cada quebra 3 BOB')

        tuesday_skill = parsed['days'][1]['blocks'][2]
        self.assertEqual(tuesday_skill['score_type'], 'emom')
        self.assertEqual(tuesday_skill['interval_seconds'], 60)
        self.assertEqual(tuesday_skill['movements'][0]['emom_label'], 'A')
        self.assertEqual(tuesday_skill['movements'][1]['reps_spec'], '10 a 12')
        self.assertEqual(tuesday_skill['movements'][3]['movement_slug'], 'rope_climb')
        self.assertEqual(tuesday_skill['movements'][4]['notes'], 'descanso')

        tuesday_metcon = parsed['days'][1]['blocks'][3]
        self.assertEqual(tuesday_metcon['movements'][1]['load_rx_male_kg'], 40.0)
        self.assertEqual(tuesday_metcon['movements'][1]['load_rx_female_kg'], 25.0)

        wednesday_metcon = parsed['days'][2]['blocks'][3]
        self.assertEqual(len(wednesday_metcon['movements']), 5)
        self.assertEqual(wednesday_metcon['movements'][3]['movement_slug'], 'bar_muscle_up')
        self.assertFalse(wednesday_metcon['movements'][3]['is_scaled_alternative'])
        self.assertTrue(wednesday_metcon['movements'][4]['is_scaled_alternative'])

        thursday_skill = parsed['days'][3]['blocks'][2]
        self.assertEqual(thursday_skill['title'], 'Semana 2')
        self.assertEqual(thursday_skill['movements'][0]['movement_slug'], 'deadlift')
        self.assertEqual(thursday_skill['movements'][0]['load_percentage_rm'], 70.0)

        thursday_metcon = parsed['days'][3]['blocks'][3]
        self.assertEqual(thursday_metcon['score_type'], 'amrap')
        self.assertEqual(thursday_metcon['notes'], 'Duplas um round para cada')

        friday_skill = parsed['days'][4]['blocks'][2]
        self.assertEqual(friday_skill['interval_seconds'], 30)
        self.assertEqual(friday_skill['rounds'], 15)
        self.assertEqual(len(friday_skill['movements']), 2)
        self.assertEqual(friday_skill['movements'][0]['movement_slug'], 'squat_clean')
        self.assertEqual(friday_skill['movements'][1]['movement_slug'], 'hang_squat_clean')

    def test_parser_marks_line_outside_day_as_warning(self):
        parsed = parse_weekly_wod_text("Linha solta\nSegunda\nMobilidade")

        self.assertEqual(len(parsed['parse_warnings']), 1)
        self.assertEqual(parsed['parse_warnings'][0]['line_number'], 1)
        self.assertIn('fora de um dia', parsed['parse_warnings'][0]['message'])
