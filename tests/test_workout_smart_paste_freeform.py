"""Testes do parser de texto cru (sem cabecalho) do Smart Paste semanal.

Cobrem o exemplo real de um coach + uma bateria de bugs previsiveis. Sao testes de funcao
pura (SimpleTestCase, sem banco) — exercitam parse_weekly_wod_freeform e o gate
_freeform_should_take_over.
"""

import json

from django.test import SimpleTestCase

from operations.services.wod_paste_freeform_parser import (
    _freeform_should_take_over,
    parse_weekly_wod_freeform,
)
from operations.services.wod_paste_parser import parse_weekly_wod_text


# Texto colado por um coach real: sem cabecalhos de bloco, blocos separados por linha em
# branco + linha de esquema, aquecimento implicito, notas inline, acentos e caracteres "sujos".
MESSY_SAMPLE = """Segunda

Alongar bem

3x
10 v up
10 ohs bastão
12 lunges

5 rounds
3 OHS (pausa de 5s” na última rep)- *barra sair do rack*
(Subindo a carga)

5 rounds
Emom
3 squat snatch (75% PR)- *unbroken*


Cap 16’
400m run
Then
3 rounds
12 front squat
14 HSPU
14 wall boll
12 Push press
Then
400m run

Terça

Alongar bem

Tabata
Hollowrock
Arckrock



6 rounds
Cada 1’30
1 clean pull
2 clean H pull
1 clean below the knee
(Subindo a carga)


Cap 17’
4 rounds
1-2-3-4
Rope Climb
8 Deadlift
6 burpee over the bar
20 remadores
100 su

Quarta


Alongar bem

(Aquecimento)
3x
10 jump squat
15 sit up
100 run

Skill
6-6-4-4-2-2
Front Squat
1' prancha


Cap 16
20- 30-40-30-20
DB snatch
T2B
Pull Up

Quinta

3x
10 push up
10 jump squat
20 v up

Hyrox
Cap 45m

600 run
50 wall boll
600 run
100 push up
600 run
100m lunges kb
600 run
50 step kb
600 run
50 burpees

Sexta

Alongar bem


(Aquecimento)
3x
8 rosca direta
8 shoulder press
50 du

8-8-6-6-4-4
Bench Press
10 sit up (plate)



Cap 17’
3 round
8 devil press
30 box jump over
8 bmu
14 pistol"""


def _block_counts(parsed):
    return [len(day['blocks']) for day in parsed['days']]


def _find_block(parsed, weekday, predicate):
    day = next(d for d in parsed['days'] if d['weekday'] == weekday)
    return next(b for b in day['blocks'] if predicate(b))


def _all_movements(block):
    return block['movements']


class FreeformSampleStructureTests(SimpleTestCase):
    """O exemplo real do coach vira 5 dias organizados, sem perder informacao."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parsed = parse_weekly_wod_freeform(MESSY_SAMPLE)

    def test_splits_into_five_weekdays_in_order(self):
        self.assertEqual([d['weekday'] for d in self.parsed['days']], [0, 1, 2, 3, 4])
        self.assertEqual(
            [d['weekday_label'] for d in self.parsed['days']],
            ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta'],
        )

    def test_block_counts_per_day(self):
        # Segunda: aquecimento + 3x + 5 rounds + 5 rounds/EMOM + chipper Cap 16'
        # Quinta: 3x + Hyrox (cabecalho + movimentos foram fundidos em UM bloco)
        self.assertEqual(_block_counts(self.parsed), [5, 4, 4, 2, 4])

    def test_nothing_is_dropped_silently(self):
        self.assertEqual(self.parsed['parse_warnings'], [])
        haystack = json.dumps(self.parsed, ensure_ascii=False)
        for token in (
            'Hollowrock', 'Arckrock', 'remadores', 'devil press', 'pistol',
            'bmu', 'step kb', 'rosca direta', 'prancha', 'Subindo a carga', 'unbroken',
        ):
            self.assertIn(token, haystack, f'sumiu do payload: {token!r}')

    def test_implicit_warmup_becomes_warmup_block_without_movements(self):
        block = self.parsed['days'][0]['blocks'][0]
        self.assertEqual(block['kind'], 'mobility')
        self.assertEqual(block['title'], 'Alongar bem')
        self.assertEqual(block['movements'], [])

    def test_emom_block_detected_with_interval_and_load(self):
        emom = _find_block(self.parsed, 0, lambda b: b.get('score_type') == 'emom')
        self.assertEqual(emom['interval_seconds'], 60)
        snatch = emom['movements'][0]
        self.assertEqual(snatch['movement_slug'], 'squat_snatch')
        self.assertEqual(snatch['reps_spec'], '3')
        self.assertEqual(snatch['load_spec'], '75%')
        self.assertEqual(snatch['load_percentage_rm'], 75.0)
        self.assertIn('unbroken', snatch['notes'])

    def test_chipper_with_timecap_then_connector_and_no_phantom_movement(self):
        chipper = _find_block(self.parsed, 0, lambda b: b.get('timecap_min') == 16)
        self.assertEqual(len(chipper['movements']), 6)
        # "Then" preservado como nota, deduplicado (aparece 2x no texto), sem virar movimento
        self.assertEqual(chipper['notes'], 'Then')
        self.assertNotIn('then', [(m['movement_label_raw'] or '').lower() for m in chipper['movements']])

    def test_movement_note_and_load_kept_on_strength_block(self):
        strength = _find_block(self.parsed, 0, lambda b: b['kind'] == 'strength')
        self.assertIn('Subindo a carga', strength['notes'])
        ohs = strength['movements'][0]
        self.assertEqual(ohs['movement_slug'], 'overhead_squat')
        self.assertIn('barra sair do rack', ohs['notes'])

    def test_tabata_block_keeps_unresolved_movements_for_review(self):
        tabata = _find_block(self.parsed, 1, lambda b: b.get('score_type') == 'tabata')
        labels = [m['movement_label_raw'] for m in tabata['movements']]
        self.assertEqual(labels, ['Hollowrock', 'Arckrock'])
        self.assertTrue(all(not m['movement_slug'] for m in tabata['movements']))

    def test_interval_minutes_seconds_scheme(self):
        block = _find_block(self.parsed, 1, lambda b: b.get('interval_seconds') == 90)
        self.assertEqual(block['rounds'], 6)

    def test_skill_block_with_rep_ladder(self):
        skill = _find_block(self.parsed, 2, lambda b: b['kind'] == 'skill')
        self.assertEqual(skill['format_spec'], '6-6-4-4-2-2')

    def test_rep_ladder_with_stray_space_is_normalized(self):
        block = _find_block(self.parsed, 2, lambda b: b.get('timecap_min') == 16)
        self.assertEqual(block['format_spec'].split()[-1], '20-30-40-30-20')

    def test_quinta_merges_hyrox_header_with_its_movements(self):
        quinta = self.parsed['days'][3]
        self.assertEqual(len(quinta['blocks']), 2)
        hyrox = quinta['blocks'][1]
        self.assertEqual(hyrox['timecap_min'], 45)
        self.assertEqual(len(hyrox['movements']), 10)
        run_600 = next(m for m in hyrox['movements'] if m['movement_label_raw'] == '600 run')
        self.assertEqual(run_600['reps_spec'], '600')
        self.assertEqual(run_600['movement_slug'], 'run')

    def test_cap_variants_all_parse(self):
        # "Cap 16'" (Segunda), "Cap 16" (Quarta), "Cap 45m" (Quinta)
        self.assertEqual(_find_block(self.parsed, 0, lambda b: b.get('timecap_min') == 16)['score_type'], 'for_time')
        self.assertTrue(any(b.get('timecap_min') == 16 for b in self.parsed['days'][2]['blocks']))
        self.assertTrue(any(b.get('timecap_min') == 45 for b in self.parsed['days'][3]['blocks']))

    def test_inline_paren_note_is_kept_on_movement(self):
        ladder = _find_block(self.parsed, 4, lambda b: b.get('format_spec') == '8-8-6-6-4-4')
        sit_up = next(m for m in ladder['movements'] if m['movement_label_raw'] == '10 sit up')
        self.assertIn('plate', sit_up['notes'])

    def test_idempotent(self):
        self.assertEqual(parse_weekly_wod_freeform(MESSY_SAMPLE), self.parsed)

    def test_crlf_line_endings_produce_same_structure(self):
        crlf = parse_weekly_wod_freeform(MESSY_SAMPLE.replace('\n', '\r\n'))
        self.assertEqual(_block_counts(crlf), _block_counts(self.parsed))
        self.assertEqual(crlf, self.parsed)


class FreeformEdgeCaseTests(SimpleTestCase):
    """Bugs previsiveis: vazios, acentos, duplicatas, lixo, espacos."""

    def test_empty_input(self):
        self.assertEqual(
            parse_weekly_wod_freeform(''),
            {'week_label': None, 'parse_warnings': [], 'days': []},
        )

    def test_whitespace_only_input(self):
        self.assertEqual(parse_weekly_wod_freeform('   \n  \n\t\n'), {'week_label': None, 'parse_warnings': [], 'days': []})

    def test_none_input(self):
        self.assertEqual(parse_weekly_wod_freeform(None), {'week_label': None, 'parse_warnings': [], 'days': []})

    def test_line_before_any_weekday_becomes_warning_not_crash(self):
        parsed = parse_weekly_wod_freeform('lixo solto\nSegunda\n3x\n10 run')
        self.assertEqual(len(parsed['days']), 1)
        self.assertEqual(len(parsed['parse_warnings']), 1)
        self.assertEqual(parsed['parse_warnings'][0]['line_text'], 'lixo solto')

    def test_duplicate_weekday_merges_blocks_into_one_day(self):
        parsed = parse_weekly_wod_freeform('Segunda\n3x\n10 run\n\nSegunda\n5 rounds\n10 deadlift')
        self.assertEqual(len(parsed['days']), 1)
        self.assertEqual(parsed['days'][0]['weekday'], 0)
        self.assertEqual(len(parsed['days'][0]['blocks']), 2)

    def test_accents_and_case_in_weekday(self):
        for text in ('TERÇA\n3x\n10 run', 'terca\n3x\n10 run', 'Terça-feira\n3x\n10 run'):
            parsed = parse_weekly_wod_freeform(text)
            self.assertEqual(parsed['days'][0]['weekday'], 1, text)

    def test_then_connector_does_not_create_movement(self):
        parsed = parse_weekly_wod_freeform('Segunda\nCap 10\n10 run\nThen\n10 burpee')
        block = parsed['days'][0]['blocks'][0]
        self.assertEqual(len(block['movements']), 2)
        self.assertIn('Then', block['notes'])

    def test_trailing_and_blank_only_lines_are_tolerated(self):
        parsed = parse_weekly_wod_freeform('Segunda  \n\n3x   \n10 run  \n   \n5 rounds\n10 row')
        self.assertEqual(len(parsed['days'][0]['blocks']), 2)

    def test_unresolved_movement_keeps_structure(self):
        parsed = parse_weekly_wod_freeform('Segunda\n3x\n10 zzqq')
        movement = parsed['days'][0]['blocks'][0]['movements'][0]
        self.assertIsNone(movement['movement_slug'])
        self.assertEqual(movement['reps_spec'], '10')
        self.assertEqual(movement['movement_label_raw'], '10 zzqq')

    def test_day_with_only_warmup(self):
        parsed = parse_weekly_wod_freeform('Segunda\nAlongar bem')
        self.assertEqual(len(parsed['days'][0]['blocks']), 1)
        block = parsed['days'][0]['blocks'][0]
        self.assertEqual(block['kind'], 'mobility')
        self.assertEqual(block['movements'], [])


class FreeformGateTests(SimpleTestCase):
    """O gate decide quando cair no parser freeform sem regredir o parser com cabecalho."""

    HEADER_SAMPLE = 'Segunda\nMobilidade\n\nAquecimento\n3x\n10 lunges\n8 front squat\n20 sit up'

    def test_gate_takes_over_for_headerless_text(self):
        header_parse = parse_weekly_wod_text(MESSY_SAMPLE)
        self.assertTrue(_freeform_should_take_over(header_parse))

    def test_gate_does_not_take_over_for_header_based_text(self):
        header_parse = parse_weekly_wod_text(self.HEADER_SAMPLE)
        self.assertGreater(sum(len(d['blocks']) for d in header_parse['days']), 0)
        self.assertFalse(_freeform_should_take_over(header_parse))

    def test_gate_takes_over_on_empty_parse(self):
        self.assertTrue(_freeform_should_take_over({'days': [], 'parse_warnings': []}))
        self.assertTrue(_freeform_should_take_over(None))
