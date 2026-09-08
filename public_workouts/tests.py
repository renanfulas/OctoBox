"""
ARQUIVO: testes das formulas e do relatorio de avaliacao fisica.

POR QUE ELE EXISTE:
- as formulas (BF% Navy, RCQ, IMC) e as classificacoes sao a parte com mais
  risco de erro silencioso (numero errado, mas sem exception) — precisam de
  valores de referencia conhecidos, nao so "roda sem quebrar".
"""

from datetime import date

from django.test import TestCase

from .formulas import (
    Sex,
    classify_bmi,
    classify_body_fat,
    classify_whr,
    compute_bmi,
    compute_whr,
    estimate_body_fat_jackson_pollock_3site,
    estimate_body_fat_jackson_pollock_7site,
    estimate_body_fat_navy,
)
from .models import PublicWorkoutAssessment
from .services import build_report, list_assessments, record_assessment


class FormulasTests(TestCase):
    def test_estimate_body_fat_navy_male_reference_value(self):
        # Calculado a mao a partir da formula (waist-neck=47, height=180):
        # 495 / (1.0324 - 0.19077*log10(47) + 0.15456*log10(180)) - 450 ≈ 16.1
        bf = estimate_body_fat_navy(sex=Sex.MALE, height_cm=180, waist_cm=85, neck_cm=38)
        self.assertIsNotNone(bf)
        self.assertAlmostEqual(bf, 16.1, delta=0.3)

    def test_estimate_body_fat_navy_increases_with_waist(self):
        slim = estimate_body_fat_navy(sex=Sex.MALE, height_cm=175, waist_cm=80, neck_cm=38)
        heavier = estimate_body_fat_navy(sex=Sex.MALE, height_cm=175, waist_cm=95, neck_cm=38)
        self.assertLess(slim, heavier)

    def test_estimate_body_fat_navy_female_requires_hip(self):
        self.assertIsNone(
            estimate_body_fat_navy(sex=Sex.FEMALE, height_cm=165, waist_cm=70, neck_cm=32, hip_cm=None)
        )

    def test_estimate_body_fat_navy_returns_none_when_neck_bigger_than_waist(self):
        self.assertIsNone(estimate_body_fat_navy(sex=Sex.MALE, height_cm=175, waist_cm=70, neck_cm=80))

    def test_compute_whr_and_classification_male(self):
        whr = compute_whr(waist_cm=90, hip_cm=100)
        self.assertEqual(whr, 0.9)
        self.assertEqual(classify_whr(sex=Sex.MALE, whr=whr).level, 'warning')
        self.assertEqual(classify_whr(sex=Sex.MALE, whr=0.85).level, 'good')
        self.assertEqual(classify_whr(sex=Sex.MALE, whr=1.05).level, 'risk')

    def test_compute_whr_and_classification_female(self):
        self.assertEqual(classify_whr(sex=Sex.FEMALE, whr=0.75).level, 'good')
        self.assertEqual(classify_whr(sex=Sex.FEMALE, whr=0.82).level, 'warning')
        self.assertEqual(classify_whr(sex=Sex.FEMALE, whr=0.9).level, 'risk')

    def test_compute_bmi_and_classification(self):
        bmi = compute_bmi(weight_kg=70, height_cm=175)
        self.assertEqual(bmi, 22.9)
        self.assertEqual(classify_bmi(bmi).level, 'good')
        self.assertEqual(classify_bmi(17.0).level, 'warning')
        self.assertEqual(classify_bmi(31.0).level, 'risk')

    def test_classify_body_fat_male_and_female_tables_differ(self):
        self.assertEqual(classify_body_fat(sex=Sex.MALE, bf_percent=10).label, 'Atleta')
        self.assertEqual(classify_body_fat(sex=Sex.FEMALE, bf_percent=10).label, 'Gordura essencial')
        self.assertEqual(classify_body_fat(sex=Sex.MALE, bf_percent=30).level, 'risk')

    def test_jackson_pollock_3site_female_reference_value(self):
        # triceps=20mm, iliaca=13mm, coxa=27mm, idade=24 -> soma=60mm
        # BD = 1.0994921 - 0.0009929*60 + 0.0000023*60^2 - 0.0001392*24 ~= 1.044857
        # %BF = 495/BD - 450 ~= 23.7
        bf = estimate_body_fat_jackson_pollock_3site(
            sex=Sex.FEMALE, age=24, fold_a_mm=20, fold_b_mm=13, fold_c_mm=27
        )
        self.assertIsNotNone(bf)
        self.assertAlmostEqual(bf, 23.7, delta=0.3)

    def test_jackson_pollock_3site_returns_none_without_age(self):
        self.assertIsNone(
            estimate_body_fat_jackson_pollock_3site(sex=Sex.FEMALE, age=None, fold_a_mm=20, fold_b_mm=13, fold_c_mm=27)
        )

    def test_jackson_pollock_7site_female_reference_value(self):
        # peitoral=8, axilar=15, triceps=20, subescapular=13, abdomen=26,
        # iliaca=13, coxa=27, idade=24 -> soma=122mm
        # BD = 1.097 - 0.00046971*122 + 0.00000056*122^2 - 0.00012828*24 ~= 1.04495
        # %BF = 495/BD - 450 ~= 23.7
        bf = estimate_body_fat_jackson_pollock_7site(
            sex=Sex.FEMALE,
            age=24,
            chest_mm=8,
            midaxillary_mm=15,
            triceps_mm=20,
            subscapular_mm=13,
            abdomen_mm=26,
            suprailiac_mm=13,
            thigh_mm=27,
        )
        self.assertIsNotNone(bf)
        self.assertAlmostEqual(bf, 23.7, delta=0.3)

    def test_jackson_pollock_7site_returns_none_when_missing_a_fold(self):
        self.assertIsNone(
            estimate_body_fat_jackson_pollock_7site(
                sex=Sex.FEMALE,
                age=24,
                chest_mm=8,
                midaxillary_mm=None,
                triceps_mm=20,
                subscapular_mm=13,
                abdomen_mm=26,
                suprailiac_mm=13,
                thigh_mm=27,
            )
        )


class ServicesTests(TestCase):
    def test_record_assessment_rejects_unknown_plan_slug(self):
        from .services import UnknownPlanSlugError

        with self.assertRaises(UnknownPlanSlugError):
            record_assessment(plan_slug='nao-existe-esse-plano', measured_at=date(2026, 1, 1))

    def test_list_assessments_orders_by_measured_at(self):
        record_assessment(plan_slug='rafael', measured_at=date(2026, 2, 1), weight_kg=71)
        record_assessment(plan_slug='rafael', measured_at=date(2026, 1, 1), weight_kg=72)
        ordered = list_assessments(plan_slug='rafael')
        self.assertEqual([a.measured_at for a in ordered], [date(2026, 1, 1), date(2026, 2, 1)])

    def test_build_report_with_no_assessments_returns_empty_shape(self):
        report = build_report(plan_slug='rafael', sex='M', height_cm=175)
        self.assertEqual(report, {'assessments': [], 'summary': None, 'indicators': None})

    def test_build_report_computes_deltas_and_indicators(self):
        record_assessment(
            plan_slug='rafael',
            measured_at=date(2026, 1, 1),
            weight_kg=75,
            measurements={'cintura': 88, 'pescoco': 39, 'quadril': 98},
        )
        record_assessment(
            plan_slug='rafael',
            measured_at=date(2026, 2, 1),
            weight_kg=72,
            measurements={'cintura': 84, 'pescoco': 39, 'quadril': 98},
        )

        report = build_report(plan_slug='rafael', sex='M', height_cm=175)

        self.assertEqual(report['summary']['count'], 2)
        self.assertEqual(report['summary']['weight_kg']['delta'], -3)
        self.assertEqual(report['summary']['measurements']['cintura']['delta'], -4)
        self.assertIsNotNone(report['indicators']['bmi'])
        self.assertIsNotNone(report['indicators']['whr'])
        self.assertEqual(report['indicators']['body_fat_percent']['source'], 'navy_estimate')

    def test_manual_body_fat_override_wins_over_navy_estimate(self):
        record_assessment(
            plan_slug='rafael',
            measured_at=date(2026, 1, 1),
            weight_kg=75,
            body_fat_percent=18.5,
            measurements={'cintura': 88, 'pescoco': 39},
        )
        report = build_report(plan_slug='rafael', sex='M', height_cm=175)
        self.assertEqual(report['indicators']['body_fat_percent']['source'], 'manual')
        self.assertEqual(report['indicators']['body_fat_percent']['value'], 18.5)

    def test_build_report_without_sex_skips_whr_and_body_fat(self):
        record_assessment(
            plan_slug='franciele',
            measured_at=date(2026, 1, 1),
            weight_kg=60,
            measurements={'cintura': 70, 'quadril': 95},
        )
        report = build_report(plan_slug='franciele', sex=None, height_cm=None)
        self.assertIsNone(report['indicators']['whr'])
        self.assertIsNone(report['indicators']['body_fat_percent'])
        self.assertIsNone(report['indicators']['bmi'])


class ModelTests(TestCase):
    def test_str_representation(self):
        assessment = PublicWorkoutAssessment.objects.create(plan_slug='rafael', measured_at=date(2026, 1, 1))
        self.assertEqual(str(assessment), 'rafael @ 2026-01-01')
