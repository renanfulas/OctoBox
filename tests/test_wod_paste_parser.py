from django.test import SimpleTestCase

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
