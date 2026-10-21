"""
ARQUIVO: testes do perfil (sexo/altura) gravado na avaliacao fisica.

POR QUE ELE EXISTE:
- so Franciele e Rafael tinham sexo/altura no catalogo fixo: qualquer outro
  aluno avaliado por 7 dobras ficava sem %gordura classificado, RCQ e IMC, e
  a formula de dobras caia na MASCULINA por padrao. Estes testes travam o
  relatorio completo pra todo aluno com dobras, o fim do padrao masculino e
  o comando que corrige as avaliacoes ja lancadas.
"""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .formulas import Sex, estimate_body_fat_jackson_pollock_7site
from .models import PublicWorkoutAssessment
from .services import (
    AssessmentValueError,
    assessment_profile,
    build_report,
    parse_skinfold_note,
    record_assessment,
    skinfold_body_fat,
)

_FOLDS = {'peitoral': 8, 'axilar': 15, 'triceps': 20, 'subescapular': 13, 'abdomen': 26, 'iliaca': 13, 'coxa': 27}
_FOLD_FLAGS = [arg for key, value in _FOLDS.items() for arg in (f'--dobra-{key}', str(value))]
_FOLD_NOTE = 'Dobras (mm): triceps=20.0, subescapular=13.0, abdomen=26.0, iliaca=13.0, coxa=27.0, peitoral=8.0, axilar=15.0'


def _jp7(sex, age=24):
    return estimate_body_fat_jackson_pollock_7site(
        sex=sex, age=age, chest_mm=8, midaxillary_mm=15, triceps_mm=20,
        subscapular_mm=13, abdomen_mm=26, suprailiac_mm=13, thigh_mm=27,
    )


def _no_ai():
    # O .env local pode ter ANTHROPIC_API_KEY: nunca chamar a rede em teste.
    return mock.patch('public_workouts.assessment_hero_ai.generate_assessment_hero_text', return_value=None)


class AssessmentProfileServicesTests(TestCase):
    def test_report_is_complete_when_the_assessment_carries_sex_and_height(self):
        # 'juliana' nao tem sexo/altura no catalogo — o caso de todo aluno
        # avaliado por dobras alem de Franciele e Rafael.
        record_assessment(
            plan_slug='juliana', measured_at=date(2026, 10, 1), weight_kg=61,
            body_fat_percent=round(_jp7(Sex.FEMALE), 1), body_fat_source='skinfold_jp7',
            measurements={'cintura': 70, 'quadril': 96}, sex='F', height_cm=165,
        )

        indicators = build_report(plan_slug='juliana', sex=None, height_cm=None)['indicators']

        self.assertAlmostEqual(indicators['bmi']['value'], 61 / 1.65 ** 2, delta=0.1)
        self.assertIsNotNone(indicators['whr'])
        self.assertEqual(indicators['body_fat_percent']['source'], 'skinfold_jp7')
        self.assertIsNotNone(indicators['body_fat_percent']['classification'])

    def test_catalog_profile_wins_over_the_stored_one(self):
        record_assessment(plan_slug='rafael', measured_at=date(2026, 10, 1), weight_kg=70, sex='F', height_cm=150)

        indicators = build_report(plan_slug='rafael', sex='M', height_cm=175)['indicators']

        self.assertAlmostEqual(indicators['bmi']['value'], 70 / 1.75 ** 2, delta=0.1)

    def test_profile_fields_resolve_independently_from_the_latest_assessments(self):
        record_assessment(plan_slug='juliana', measured_at=date(2026, 9, 1), weight_kg=60, height_cm=165)
        record_assessment(plan_slug='juliana', measured_at=date(2026, 10, 1), weight_kg=61, sex='F')

        profile = assessment_profile(list(PublicWorkoutAssessment.objects.filter(plan_slug='juliana').order_by('measured_at')))

        self.assertEqual(profile, {'sex': 'F', 'height_cm': 165.0})

    def test_record_assessment_rejects_invalid_sex_and_height(self):
        with self.assertRaises(AssessmentValueError):
            record_assessment(plan_slug='juliana', measured_at=date(2026, 10, 1), weight_kg=61, sex='X')
        with self.assertRaises(AssessmentValueError):
            record_assessment(plan_slug='juliana', measured_at=date(2026, 10, 1), weight_kg=61, height_cm=0)

    def test_parse_skinfold_note_reads_command_and_self_report_formats(self):
        self.assertEqual(parse_skinfold_note(f'SmartFit. {_FOLD_NOTE}')['axilar'], 15.0)
        self.assertEqual(parse_skinfold_note('Dobras (mm): triceps=20, coxa=27.5'), {'triceps': 20.0, 'coxa': 27.5})
        self.assertEqual(parse_skinfold_note('medi em casa'), {})

    def test_skinfold_body_fat_depends_on_sex_and_falls_back_to_three_sites(self):
        female, female_source = skinfold_body_fat(sex=Sex.FEMALE, age=24, skinfolds=_FOLDS)
        male, _ = skinfold_body_fat(sex=Sex.MALE, age=24, skinfolds=_FOLDS)
        without_axilar = {key: value for key, value in _FOLDS.items() if key != 'axilar'}

        self.assertEqual(female_source, 'skinfold_jp7')
        self.assertAlmostEqual(female, _jp7(Sex.FEMALE), places=6)
        self.assertNotAlmostEqual(female, male, delta=1)
        self.assertEqual(skinfold_body_fat(sex=Sex.FEMALE, age=24, skinfolds=without_axilar)[1], 'skinfold_jp3')
        self.assertEqual(skinfold_body_fat(sex=Sex.FEMALE, age=24, skinfolds={}), (None, ''))


class AddAssessmentCommandProfileTests(TestCase):
    def _add(self, *args):
        with _no_ai():
            call_command('add_public_workout_assessment', *args, stdout=StringIO())

    def test_skinfolds_without_known_sex_fail_instead_of_assuming_male(self):
        with self.assertRaises(CommandError):
            self._add('juliana', '--date', '2026-10-01', '--age', '24', *_FOLD_FLAGS)

        self.assertFalse(PublicWorkoutAssessment.objects.filter(plan_slug='juliana').exists())

    def test_sex_and_height_are_stored_and_give_the_full_report(self):
        self._add(
            'juliana', '--date', '2026-10-01', '--sex', 'F', '--height', '165', '--weight', '61',
            '--age', '24', '--cintura', '70', '--quadril', '96', *_FOLD_FLAGS,
        )

        assessment = PublicWorkoutAssessment.objects.get(plan_slug='juliana')
        self.assertEqual(assessment.sex, 'F')
        self.assertEqual(assessment.height_cm, Decimal('165.0'))
        self.assertEqual(assessment.body_fat_source, 'skinfold_jp7')
        self.assertAlmostEqual(float(assessment.body_fat_percent), _jp7(Sex.FEMALE), delta=0.1)
        indicators = build_report(plan_slug='juliana', sex=None, height_cm=None)['indicators']
        self.assertTrue(indicators['bmi'] and indicators['whr'] and indicators['body_fat_percent'])

    def test_next_assessment_inherits_the_stored_profile(self):
        self._add('juliana', '--date', '2026-09-01', '--sex', 'F', '--height', '165', '--weight', '62')
        self._add('juliana', '--date', '2026-10-01', '--weight', '61', '--age', '24', *_FOLD_FLAGS)

        latest = PublicWorkoutAssessment.objects.get(plan_slug='juliana', measured_at=date(2026, 10, 1))
        self.assertEqual(latest.sex, 'F')
        self.assertEqual(latest.height_cm, Decimal('165.0'))
        self.assertAlmostEqual(float(latest.body_fat_percent), _jp7(Sex.FEMALE), delta=0.1)

    def test_sex_contradicting_the_catalog_is_rejected(self):
        with self.assertRaises(CommandError):
            self._add('franciele', '--date', '2026-10-01', '--sex', 'M', '--weight', '66')


class CompleteAssessmentProfileCommandTests(TestCase):
    def setUp(self):
        # Avaliacao antiga: 7 dobras de uma aluna fora do catalogo, calculada
        # pela formula masculina (o padrao silencioso de antes) e sem sexo.
        self.legacy = PublicWorkoutAssessment.objects.create(
            plan_slug='juliana', measured_at=date(2026, 9, 1), weight_kg=Decimal('61'),
            body_fat_percent=Decimal(str(round(_jp7(Sex.MALE), 1))), body_fat_source='skinfold_jp7',
            measurements={'cintura': 70, 'quadril': 96}, notes=_FOLD_NOTE,
        )

    def _complete(self, *args):
        out = StringIO()
        with _no_ai():
            call_command('complete_public_workout_assessment_profile', 'juliana', *args, stdout=out)
        return out.getvalue()

    def test_fills_the_profile_and_keeps_body_fat_by_default(self):
        before = self.legacy.body_fat_percent

        output = self._complete('--sex', 'F', '--height', '165')

        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.sex, 'F')
        self.assertEqual(self.legacy.height_cm, Decimal('165.0'))
        self.assertEqual(self.legacy.body_fat_percent, before)
        self.assertIn('--recompute', output)  # avisa pra conferir o %gordura
        indicators = build_report(plan_slug='juliana', sex=None, height_cm=None)['indicators']
        self.assertTrue(indicators['bmi'] and indicators['whr'] and indicators['body_fat_percent'])

    def test_recompute_fixes_body_fat_calculated_with_the_male_formula(self):
        self._complete('--sex', 'F', '--height', '165', '--recompute', '--age', '24')

        self.legacy.refresh_from_db()
        self.assertAlmostEqual(float(self.legacy.body_fat_percent), _jp7(Sex.FEMALE), delta=0.1)

    def test_dry_run_writes_nothing(self):
        before = self.legacy.body_fat_percent

        output = self._complete('--sex', 'F', '--height', '165', '--recompute', '--age', '24', '--dry-run')

        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.sex, '')
        self.assertEqual(self.legacy.body_fat_percent, before)
        self.assertIn('--dry-run', output)

    def test_recompute_requires_age_and_writes_nothing_without_it(self):
        with self.assertRaises(CommandError):
            self._complete('--sex', 'F', '--height', '165', '--recompute')

        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.sex, '')

    def test_running_twice_changes_nothing_the_second_time(self):
        self._complete('--sex', 'F', '--height', '165', '--recompute', '--age', '24')
        recomputed = PublicWorkoutAssessment.objects.get(pk=self.legacy.pk).body_fat_percent

        output = self._complete('--sex', 'F', '--height', '165', '--recompute', '--age', '24')

        self.assertIn('Nada a mudar', output)
        self.assertEqual(PublicWorkoutAssessment.objects.get(pk=self.legacy.pk).body_fat_percent, recomputed)


class FrancielePatternTests(TestCase):
    """Caso real de producao (12/10/2026): aluna nova fora do catalogo, com
    7 dobras ja calculadas pela formula certa, inserida direto no banco com
    a altura nas medidas e medidas por lado — a tela mostrava 'altura_cm',
    'coxa_d', 'antebraco_e' crus e nenhum IMC/RCQ/%gordura classificado."""

    def setUp(self):
        from public_workouts.schema import build_example_payload
        from public_workouts.services import publish_program

        publish_program(slug='giulia', payload=build_example_payload())
        self.assessment = PublicWorkoutAssessment.objects.create(
            plan_slug='giulia', measured_at=date(2026, 10, 12), weight_kg=Decimal('57'),
            body_fat_percent=Decimal('22.0'), body_fat_source='skinfold_jp7',
            measurements={
                'coxa': 56.75, 'braco': 25, 'ombro': 100, 'peito': 85, 'coxa_d': 57, 'coxa_e': 56.5,
                'abdomen': 70.5, 'braco_d': 24, 'braco_e': 26, 'cintura': 79, 'quadril': 101.5,
                'altura_cm': 160, 'antebraco_d': 22, 'antebraco_e': 21, 'panturrilha': 36.6,
            },
            notes='Sexo: feminino; idade: 26 anos; estatura: 160 cm. Dobras cutâneas JP7 em mm: peitoral=10, '
                  'axilar=10, triceps=15, subescapular=13, abdomen=20, iliaca=11, coxa=31.',
        )

    def test_assessment_ends_up_in_the_franciele_pattern(self):
        with _no_ai():
            call_command('complete_public_workout_assessment_profile', 'giulia', '--sex', 'F', stdout=StringIO())

        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.sex, 'F')
        self.assertEqual(self.assessment.height_cm, Decimal('160.0'))  # veio da altura_cm das medidas
        self.assertEqual(
            sorted(self.assessment.measurements),
            ['abdomen', 'braco', 'cintura', 'coxa', 'ombro', 'panturrilha', 'peito', 'quadril'],
        )
        self.assertEqual(self.assessment.body_fat_percent, Decimal('22.0'))  # ja estava certo
        self.assertIn('Medidas por lado (D/E): antebraco 22/21 cm; braco 24/26 cm; coxa 57/56,5 cm', self.assessment.notes)
        indicators = build_report(plan_slug='giulia', sex=None, height_cm=None)['indicators']
        self.assertAlmostEqual(indicators['bmi']['value'], 57 / 1.6 ** 2, delta=0.1)
        self.assertIsNotNone(indicators['whr'])
        self.assertEqual(indicators['body_fat_percent']['source'], 'skinfold_jp7')

    def test_recompute_reads_the_skinfold_note_format_of_these_assessments(self):
        with _no_ai():
            call_command(
                'complete_public_workout_assessment_profile', 'giulia', '--sex', 'F', '--recompute', '--age', '26',
                stdout=StringIO(),
            )

        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.body_fat_percent, Decimal('22.0'))  # mesma formula, mesmo resultado

    def test_height_contradicting_the_stored_altura_cm_is_rejected(self):
        with self.assertRaises(CommandError):
            with _no_ai():
                call_command(
                    'complete_public_workout_assessment_profile', 'giulia', '--sex', 'F', '--height', '170',
                    stdout=StringIO(),
                )

    def test_new_student_outside_the_catalog_can_get_the_next_assessment(self):
        with _no_ai():
            call_command('complete_public_workout_assessment_profile', 'giulia', '--sex', 'F', stdout=StringIO())
            call_command(
                'add_public_workout_assessment', 'giulia', '--date', '2026-11-12', '--weight', '56', '--age', '26',
                *_FOLD_FLAGS, stdout=StringIO(),
            )

        latest = PublicWorkoutAssessment.objects.get(plan_slug='giulia', measured_at=date(2026, 11, 12))
        self.assertEqual((latest.sex, latest.height_cm), ('F', Decimal('160.0')))
        self.assertAlmostEqual(float(latest.body_fat_percent), _jp7(Sex.FEMALE, age=26), delta=0.1)
        self.assertEqual(build_report(plan_slug='giulia', sex=None, height_cm=None)['summary']['count'], 2)
