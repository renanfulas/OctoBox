"""
ARQUIVO: unit tests da logica pura do app do aluno.

POR QUE ELE EXISTE:
- O tests.py legado e quase todo de integracao (view + DB). As funcoes puras
  do dominio e da camada de aplicacao so tinham cobertura indireta (1 caminho
  feliz para a prescricao). Aqui isolamos as regras de calculo e formatacao
  para fixar contratos e arrestar regressao de borda barata e rapida.

O QUE ESTE ARQUIVO TESTA (sem tocar o DB no corpo do teste):
1. domain/workout_prescription: arredondamento HALF_UP ao incremento de 2.5kg.
2. use_cases: rotulo de prescricao, payload/preview de recomendacao, helpers
   de leitura de movimento e de status de presenca.
3. cache_keys: formato versionado das chaves e normalizacao do tenant.
4. timezone, brazilian_holidays, templatetags: helpers de apresentacao.

NOTA DE EXECUCAO:
- Usamos django.test.TestCase (e nao SimpleTestCase) de proposito: o autouse
  `_tenant_schema_context` do conftest envolve cada teste em schema_context,
  o que toca a conexao. TestCase habilita acesso ao banco e evita o guard de
  DB do pytest-django, mantendo o padrao do resto do repo.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from operations.models import AttendanceStatus
from student_app.application import cache_keys
from student_app.application.timezone import localize_box_datetime, resolve_box_timezone
from student_app.application.use_cases import (
    _build_student_recommendation_payload_from_rm,
    _format_attendance_status,
    _movement_value,
    build_student_prescription_label,
    build_student_recommendation_payload,
    build_student_recommendation_preview,
)
from student_app.brazilian_holidays import get_brazilian_holiday_name
from student_app.domain.workout_prescription import (
    ROUNDING_INCREMENT,
    build_workout_prescription,
    round_to_increment,
)
from student_app.models import WorkoutLoadType
from student_app.templatetags.student_app_formatters import format_rm_value


class WorkoutPrescriptionRoundingTests(TestCase):
    def test_round_to_increment_uses_half_up_to_nearest_two_and_a_half(self):
        # 71.25 / 2.5 = 28.5 -> HALF_UP -> 29 -> 72.50
        self.assertEqual(round_to_increment(Decimal('71.25')), Decimal('72.50'))
        # 71.24 / 2.5 = 28.496 -> 28 -> 70.00
        self.assertEqual(round_to_increment(Decimal('71.24')), Decimal('70.00'))
        # Valor ja no incremento permanece estavel.
        self.assertEqual(round_to_increment(Decimal('70.00')), Decimal('70.00'))

    def test_round_to_increment_is_noop_when_increment_not_positive(self):
        self.assertEqual(round_to_increment(Decimal('73.3'), Decimal('0')), Decimal('73.3'))
        self.assertEqual(round_to_increment(Decimal('73.3'), Decimal('-2.5')), Decimal('73.3'))

    def test_build_workout_prescription_computes_raw_and_rounded_load(self):
        prescription = build_workout_prescription(
            one_rep_max_kg=Decimal('102.5'),
            percentage=Decimal('70'),
        )
        self.assertEqual(prescription.one_rep_max_kg, Decimal('102.5'))
        self.assertEqual(prescription.percentage, Decimal('70'))
        self.assertEqual(prescription.raw_load_kg, Decimal('71.75'))
        self.assertEqual(prescription.rounded_load_kg, Decimal('72.50'))

    def test_build_workout_prescription_observation_mentions_increment(self):
        prescription = build_workout_prescription(
            one_rep_max_kg=Decimal('100'),
            percentage=Decimal('80'),
        )
        self.assertIn('80.00%', prescription.observation)
        self.assertIn(f'{ROUNDING_INCREMENT}kg', prescription.observation)


class PrescriptionLabelTests(TestCase):
    def test_label_for_percentage_of_rm(self):
        movement = {
            'sets': 5,
            'reps': 3,
            'load_type': WorkoutLoadType.PERCENTAGE_OF_RM,
            'load_value': Decimal('80'),
        }
        self.assertEqual(
            build_student_prescription_label(movement=movement),
            '5 séries · 3 reps · @ 80% do RM',
        )

    def test_label_for_fixed_kg(self):
        movement = {
            'sets': 3,
            'reps': 5,
            'load_type': WorkoutLoadType.FIXED_KG,
            'load_value': Decimal('40'),
        }
        self.assertEqual(
            build_student_prescription_label(movement=movement),
            '3 séries · 5 reps · @ 40 kg',
        )

    def test_label_for_free_load(self):
        self.assertEqual(
            build_student_prescription_label(movement={'load_type': WorkoutLoadType.FREE}),
            'carga livre',
        )

    def test_label_falls_back_when_empty(self):
        self.assertEqual(
            build_student_prescription_label(movement={}),
            'Sem detalhe de prescrição',
        )


class RecommendationPayloadTests(TestCase):
    def test_free_load_has_no_recommended_kg(self):
        payload = build_student_recommendation_payload(movement={'load_type': WorkoutLoadType.FREE})
        self.assertEqual(payload['load_context_label'], 'Carga livre')
        self.assertIsNone(payload['recommended_load_kg'])

    def test_fixed_kg_recommends_the_fixed_value(self):
        payload = build_student_recommendation_payload(
            movement={'load_type': WorkoutLoadType.FIXED_KG, 'load_value': Decimal('42')},
        )
        self.assertEqual(payload['load_context_label'], 'Carga fixa')
        self.assertEqual(payload['recommended_load_kg'], Decimal('42'))

    def test_percentage_without_student_defers_recommendation(self):
        payload = build_student_recommendation_payload(
            movement={'load_type': WorkoutLoadType.PERCENTAGE_OF_RM, 'load_value': Decimal('70')},
        )
        self.assertEqual(payload['load_context_label'], 'Percentual do RM')
        self.assertIsNone(payload['recommended_load_kg'])
        self.assertEqual(payload['percentage'], Decimal('70'))

    def test_payload_from_rm_computes_load_when_max_present(self):
        exercise_max = SimpleNamespace(one_rep_max_kg=Decimal('100'))
        payload = _build_student_recommendation_payload_from_rm(
            movement={'load_type': WorkoutLoadType.PERCENTAGE_OF_RM, 'load_value': Decimal('70')},
            exercise_max=exercise_max,
        )
        self.assertEqual(payload['recommended_load_kg'], Decimal('70.00'))
        self.assertEqual(payload['base_rm_kg'], Decimal('100'))

    def test_payload_from_rm_without_max_asks_for_registration(self):
        payload = _build_student_recommendation_payload_from_rm(
            movement={'load_type': WorkoutLoadType.PERCENTAGE_OF_RM, 'load_value': Decimal('70')},
            exercise_max=None,
        )
        self.assertIsNone(payload['recommended_load_kg'])
        self.assertIn('Registre seu RM', payload['recommendation_copy'])

    def test_preview_returns_tuple_view_of_payload(self):
        preview = build_student_recommendation_preview(movement={'load_type': WorkoutLoadType.FREE})
        self.assertEqual(preview[0], 'Carga livre')
        self.assertIsNone(preview[1])
        self.assertIsInstance(preview[2], str)


class MovementAndAttendanceHelperTests(TestCase):
    def test_movement_value_reads_dict_and_object(self):
        self.assertEqual(_movement_value({'sets': 5}, 'sets'), 5)
        self.assertIsNone(_movement_value({'sets': 5}, 'reps'))
        self.assertEqual(_movement_value(SimpleNamespace(sets=4), 'sets'), 4)
        self.assertIsNone(_movement_value(SimpleNamespace(sets=4), 'reps'))

    def test_format_attendance_status_branches(self):
        self.assertEqual(_format_attendance_status(attendance=None), 'Sem reserva')
        self.assertEqual(
            _format_attendance_status(attendance=SimpleNamespace(status=AttendanceStatus.CHECKED_IN)),
            'Presença confirmada',
        )
        self.assertEqual(
            _format_attendance_status(attendance=SimpleNamespace(status=AttendanceStatus.CANCELED)),
            'Reserva cancelada',
        )
        # Outros status caem no dicionario de choices (sem get_status_display no stub).
        self.assertEqual(
            _format_attendance_status(attendance=SimpleNamespace(status=AttendanceStatus.BOOKED)),
            'Reservado',
        )


class CacheKeyTests(TestCase):
    def test_keys_carry_active_tenant_and_versioned_namespace(self):
        tenant = cache_keys.get_active_tenant_slug()
        self.assertEqual(
            cache_keys.build_student_rm_snapshot_cache_key(box_root_slug=None, student_id=7),
            f'student_app:rm:v1:{tenant}:student:7',
        )
        self.assertEqual(
            cache_keys.build_student_wod_snapshot_cache_key(
                box_root_slug=None, session_id=3, workout_version=2
            ),
            f'student_app:wod:v1:{tenant}:session:3:version:2',
        )

    def test_home_key_scope_switches_between_window_and_radar(self):
        tenant = cache_keys.get_active_tenant_slug()
        windowed = cache_keys.build_student_home_snapshot_cache_key(
            box_root_slug=None, student_id=1, start_date='2026-06-18', window_days=7, limit=None
        )
        radar = cache_keys.build_student_home_snapshot_cache_key(
            box_root_slug=None, student_id=1, start_date='2026-06-18', window_days=None, limit=5
        )
        radar_all = cache_keys.build_student_home_snapshot_cache_key(
            box_root_slug=None, student_id=1, start_date='2026-06-18', window_days=None, limit=None
        )
        self.assertEqual(windowed, f'student_app:home:v1:{tenant}:student:1:2026-06-18:window:7')
        self.assertEqual(radar, f'student_app:home:v1:{tenant}:student:1:2026-06-18:radar:5')
        self.assertEqual(radar_all, f'student_app:home:v1:{tenant}:student:1:2026-06-18:radar:all')

    def test_tenant_slug_falls_back_and_normalizes_when_in_public_schema(self):
        with mock.patch.object(cache_keys.connection, 'schema_name', 'public'):
            # Slug livre vira box_<slug-normalizado>.
            self.assertEqual(cache_keys.get_active_tenant_slug(fallback='Minha Box'), 'box_minha-box')
            # Slug ja prefixado e preservado.
            self.assertEqual(cache_keys.get_active_tenant_slug(fallback='box_endorfina'), 'box_endorfina')
            # control/public nunca viram discriminador de cache.
            self.assertEqual(cache_keys.get_active_tenant_slug(fallback='control'), 'public')
            self.assertEqual(cache_keys.get_active_tenant_slug(), 'public')


class TimezoneHelperTests(TestCase):
    def test_resolve_box_timezone_uses_settings_or_utc_fallback(self):
        resolved = resolve_box_timezone()
        self.assertIn(str(resolved), (settings.TIME_ZONE, 'UTC'))

    def test_localize_box_datetime_handles_none_and_aware_values(self):
        self.assertIsNone(localize_box_datetime(None))
        localized = localize_box_datetime(timezone.now())
        self.assertIsNotNone(localized)
        self.assertIsNotNone(localized.tzinfo)


class BrazilianHolidayTests(TestCase):
    def test_known_holidays_resolve_by_iso_date(self):
        self.assertEqual(get_brazilian_holiday_name(date(2026, 1, 1)), 'Ano Novo')
        self.assertEqual(get_brazilian_holiday_name(date(2026, 12, 25)), 'Natal')

    def test_non_holiday_and_missing_year_return_none(self):
        self.assertIsNone(get_brazilian_holiday_name(None))
        self.assertIsNone(get_brazilian_holiday_name(date(2026, 3, 10)))
        self.assertIsNone(get_brazilian_holiday_name(date(2099, 1, 1)))


class FormatRmValueTests(TestCase):
    def test_blank_values_render_dash(self):
        self.assertEqual(format_rm_value(None), '--')
        self.assertEqual(format_rm_value(''), '--')

    def test_integer_values_drop_decimals(self):
        self.assertEqual(format_rm_value(100), '100kg')
        self.assertEqual(format_rm_value(Decimal('100.00')), '100kg')

    def test_fractional_values_use_comma(self):
        self.assertEqual(format_rm_value(Decimal('12.5')), '12,5kg')
        self.assertEqual(format_rm_value(Decimal('102.50')), '102,5kg')

    def test_invalid_value_is_returned_as_string(self):
        self.assertEqual(format_rm_value('abc'), 'abc')
