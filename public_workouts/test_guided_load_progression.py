"""L2: a carga que o aluno registra no guiado vira a sugestão das semanas seguintes.

Cenário do produto: na semana 1 o aluno faz 100 kg no supino pelo treino
guiado. Nas semanas seguintes da periodização, a página já precisa trazer a
carga da Top calculada (e o aquecimento derivado dela), sem o aluno digitar.

Regra (periodization.suggest_progressive_load_kg): última Top real do mesmo
programa x (%RM-meio da fase atual / %RM-meio da fase em que foi feita),
limitada pelo teto da fase contra o 1RM estimado, arredondada a 2,5 kg. Na
mesma fase do registro, repete a última carga sem o teto.
"""

import json
import re
import uuid
from decimal import Decimal
from html import unescape

from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time

from public_workouts.guided_prescription import expand_guided_prescription
from public_workouts.models import PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutSubscription
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME, build_public_workout_session_value,
)

_SLUG = 'progressao'
_BENCH = 'supino-reto'
_PROGRAM_ID = 'progressao-2026'

# Semana 1 começa na segunda 05/01/2026; cada semana tem uma fase canônica.
_WEEKS = [
    {'week_number': 1, 'phase_type': 'volume'},                 # 62-72 %RM, meio 67
    {'week_number': 2, 'phase_type': 'strength_hypertrophy'},   # 72-80 %RM, meio 76
    {'week_number': 3, 'phase_type': 'intensity'},              # 80-90 %RM, meio 85
    {'week_number': 4, 'phase_type': 'deload'},                 # 50-65 %RM, meio 57,5
]
_WEEK_1, _WEEK_2, _WEEK_3, _WEEK_4, _WEEK_5 = (
    '2026-01-06 12:00', '2026-01-13 12:00', '2026-01-20 12:00', '2026-01-27 12:00', '2026-02-03 12:00',
)

_PRESCRIPTION = {
    'version': 1, 'stages': [
        {'stage_id': 'aquecimento', 'role': 'warmup', 'min_sets': 2, 'max_sets': 2,
         'reps_min': 8, 'reps_max': 8, 'rest_seconds': 60,
         'load_rule': {'kind': 'percent_of_top', 'start_percent': 40, 'end_percent': 55}},
        {'stage_id': 'top', 'role': 'top_set', 'min_sets': 1, 'max_sets': 1,
         'reps_min': 6, 'reps_max': 8, 'rest_seconds': 120,
         'load_rule': {'kind': 'suggested_top'}},
    ],
}
_TOP_SET_NUMBER = 3


def _program_payload(*, load_type='free', load_value=None, periodization=True):
    payload = build_example_payload()
    payload['program_id'] = _PROGRAM_ID
    payload['started_on'] = '2026-01-05'
    if periodization:
        payload['periodization'] = {'weeks': _WEEKS, 'volume_table': [], 'note': ''}
    movement = payload['days'][0]['blocks'][0]['movements'][0]
    movement.update({
        'movement_slug': _BENCH, 'reps_spec': '2x8 aquecimento + 1x6-8 Top', 'rir_spec': 'RIR 2',
        'load_type': load_type, 'load_value': load_value, 'guided_prescription': _PRESCRIPTION,
    })
    return payload


class GuidedLoadProgressionTest(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='supino@example.test')
        PublicWorkoutSubscription.objects.create(account=self.account, plan_slug=_SLUG)
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk, identity_verified=True
        )

    def _publish(self, **kwargs):
        self.program = publish_program(slug=_SLUG, payload=_program_payload(**kwargs))

    def _page(self):
        return self.client.get(f'/renan/{_SLUG}').content.decode()

    def _bench_card(self, html=None):
        """O que a página entrega ao guiado: kg por série e a origem da sugestão."""
        series, _anchor, kind = self._bench_card_with_anchor(html)
        return series, kind

    def _bench_card_with_anchor(self, html=None):
        match = re.search(
            r'data-guided-series="([^"]*)" data-load-anchor="([^"]*)" data-movement-slug="' + _BENCH
            + r'"[^>]*data-load-kind="([^"]*)"',
            html or self._page(),
        )
        self.assertIsNotNone(match, 'cartão do supino não encontrado na página do aluno')
        return json.loads(unescape(match.group(1))), json.loads(unescape(match.group(2))), match.group(3)

    def _top_kg(self):
        series, kind = self._bench_card()
        top = series[_TOP_SET_NUMBER - 1]
        self.assertEqual(top['role'], 'top_set')
        return top['weight_kg'], kind

    def _record_top_through_guided(self, *, weight, reps, rir):
        """Mesmo caminho do celular: inicia a sessão guiada e registra a Top pela API."""
        url = reverse('public-workout-session', kwargs={'plan_slug': _SLUG})
        local_id = str(uuid.uuid4())
        started = self.client.post(url, data=json.dumps({
            'action': 'start', 'day_id': 'seg', 'start_key': local_id,
            'program_version': self.program.version, 'local_session_id': local_id,
        }), content_type='application/json')
        self.assertEqual(started.status_code, 200, started.content)
        session_id = started.json()['session_id']
        recorded = self.client.post(url, data=json.dumps({
            'action': 'set', 'session_id': str(session_id), 'movement_slug': _BENCH,
            'movement_index': 0, 'set_number': _TOP_SET_NUMBER, 'set_role': 'top_set',
            'weight_kg': str(weight), 'reps': str(reps), 'rir': str(rir),
        }), content_type='application/json')
        self.assertEqual(recorded.status_code, 200, recorded.content)
        completed = self.client.post(url, data=json.dumps({
            'action': 'complete', 'session_id': str(session_id),
        }), content_type='application/json')
        self.assertIn(completed.status_code, (200, 409), completed.content)

    def test_100kg_in_week_1_becomes_the_suggestion_of_the_next_weeks(self):
        self._publish()

        with freeze_time(_WEEK_1):
            # Primeira vez neste programa: não há base, então não inventa kg.
            top_kg, kind = self._top_kg()
            self.assertIsNone(top_kg)
            self.assertNotEqual(kind, 'phase_progressive')
            self._record_top_through_guided(weight=100, reps=8, rir=2)
            log = PublicWorkoutLoadLog.objects.get(account=self.account, movement_slug=_BENCH)
            self.assertEqual(log.weight_kg, Decimal('100.00'))
            self.assertEqual(log.program_id, _PROGRAM_ID)

        # 100 x 8 com RIR 2 estima 1RM ~133,3 kg, que define o teto de cada fase.
        expected = {
            # 100 x 76/67 = 113,4, teto 80% de 133,3 = 106,7 -> 107,5
            _WEEK_2: 107.5,
            # 100 x 85/67 = 126,9, teto 90% de 133,3 = 120 -> 120
            _WEEK_3: 120.0,
            # deload: 100 x 57,5/67 = 85,8 (abaixo do teto de 86,7) -> 85
            _WEEK_4: 85.0,
            # o mesociclo recomeça em Volume, a fase do registro: repete os 100 kg
            _WEEK_5: 100.0,
        }
        for moment, kg in expected.items():
            with self.subTest(semana=moment), freeze_time(moment):
                series, kind = self._bench_card()
                self.assertEqual(kind, 'phase_progressive')
                self.assertEqual(series[_TOP_SET_NUMBER - 1]['weight_kg'], kg)
                # O aquecimento sai da Top sugerida (40% e 55%), também sem digitar.
                ramp = expand_guided_prescription(_PRESCRIPTION, top_weight_kg=kg)
                self.assertEqual(
                    [row['weight_kg'] for row in series[:2]], [row['weight_kg'] for row in ramp[:2]],
                )
                self.assertTrue(all(row['weight_kg'] for row in series))

    def test_same_phase_repeats_the_last_load_without_the_ceiling(self):
        self._publish()
        with freeze_time(_WEEK_1):
            self._record_top_through_guided(weight=100, reps=8, rir=2)
        # Quinta da mesma semana (mesma fase): repete os 100 kg que o aluno fez. O teto
        # de Volume (72% do 1RM estimado de 133,3 = 96) não corta para 95.
        with freeze_time('2026-01-08 12:00'):
            self.assertEqual(self._top_kg(), (100.0, 'phase_progressive'))

    def test_page_hands_the_guided_screen_last_week_load_and_this_week_phase(self):
        """Dados do quadro "Semana passada 100 kg → Hoje 107,5 kg" e da linha da fase."""
        self._publish()
        with freeze_time(_WEEK_1):
            _series, anchor, _kind = self._bench_card_with_anchor()
            self.assertEqual(anchor, {})  # sem carga real ainda: nenhuma âncora
            self._record_top_through_guided(weight=100, reps=8, rir=2)
        with freeze_time(_WEEK_2):
            html = self._page()
            series, anchor, kind = self._bench_card_with_anchor(html)
            self.assertEqual(anchor, {'kg': 100.0, 'on': '2026-01-06'})
            self.assertEqual((series[_TOP_SET_NUMBER - 1]['weight_kg'], kind), (107.5, 'phase_progressive'))
            self.assertIn('data-period-week="2" data-period-total="4" data-period-phase="Força-Hipertrofia"', html)

    def test_newest_guided_load_is_the_anchor_for_the_following_week(self):
        self._publish()
        with freeze_time(_WEEK_1):
            self._record_top_through_guided(weight=100, reps=8, rir=2)
        with freeze_time(_WEEK_2):
            self.assertEqual(self._top_kg(), (107.5, 'phase_progressive'))
            # O aluno foi além da sugestão: 112,5 x 8 com RIR 2 (1RM estimado 150).
            self._record_top_through_guided(weight=Decimal('112.5'), reps=8, rir=2)
        with freeze_time(_WEEK_3):
            # Âncora nova: 112,5 x 85/76 = 125,8 (teto 90% de 150 = 135) -> 125.
            self.assertEqual(self._top_kg(), (125.0, 'phase_progressive'))

    def test_coach_percentage_of_rm_uses_the_1rm_estimated_from_the_guided_load(self):
        # Treinador prescreveu 75% do RM: a prescrição dele vence a progressão por fase.
        self._publish(load_type='percentage_of_rm', load_value=75.0)
        with freeze_time(_WEEK_1):
            self.assertIsNone(self._top_kg()[0])
            self._record_top_through_guided(weight=100, reps=8, rir=2)
        with freeze_time(_WEEK_2):
            # 75% de 133,3 = 100 kg.
            self.assertEqual(self._top_kg(), (100.0, 'percentage'))

    def test_without_periodization_the_last_load_is_offered_as_reference(self):
        self._publish(periodization=False)
        with freeze_time(_WEEK_1):
            self._record_top_through_guided(weight=100, reps=8, rir=2)
        with freeze_time(_WEEK_2):
            top_kg, kind = self._top_kg()
            # Sem fase, a estimativa por reps/RIR do próprio exercício entra (1x6-8, RIR 2
            # sobre 1RM 133,3 = 100); nunca fica vazio depois de um registro.
            self.assertIsNotNone(top_kg)
            self.assertIn(kind, ('rir_estimate', 'last_observed'))
