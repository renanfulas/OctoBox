"""Limites do registro de série no treino guiado: carga até 999 kg, reps até 300.

A tela (guided-format.js MAX_WEIGHT_KG/MAX_REPS, tests/js/curva_guided_focus_units.test.js)
e o servidor usam os mesmos tetos; aqui, o servidor recusa o que passa deles.
"""

import json
import uuid

from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time

from public_workouts.models import PublicWorkoutTrainingSet
from public_workouts.test_guided_load_progression import (
    _BENCH, _SLUG, _TOP_SET_NUMBER, _WEEK_1, GuidedLoadProgressionTest,
)
from student_app.views.public_workout_session_commands import MAX_SET_REPS, MAX_SET_WEIGHT_KG


class GuidedSetLimitsTest(TestCase):
    # Mesmo aluno e programa do teste de progressão, sem herdar os testes dele.
    setUp = GuidedLoadProgressionTest.setUp
    _publish = GuidedLoadProgressionTest._publish

    def _start(self):
        self.url = reverse('public-workout-session', kwargs={'plan_slug': _SLUG})
        local_id = str(uuid.uuid4())
        started = self.client.post(self.url, data=json.dumps({
            'action': 'start', 'day_id': 'seg', 'start_key': local_id,
            'program_version': self.program.version, 'local_session_id': local_id,
        }), content_type='application/json')
        self.assertEqual(started.status_code, 200, started.content)
        return started.json()['session_id']

    def _post(self, body):
        return self.client.post(self.url, data=json.dumps(body), content_type='application/json')

    def test_limits_are_three_digit_load_and_300_reps(self):
        self.assertEqual((MAX_SET_WEIGHT_KG, MAX_SET_REPS), (999, 300))

    def test_set_above_999_kg_or_300_reps_is_refused_and_the_limit_itself_is_kept(self):
        self._publish()
        with freeze_time(_WEEK_1):
            session_id = self._start()
            base = {
                'action': 'set', 'session_id': str(session_id), 'movement_slug': _BENCH,
                'movement_index': 0, 'set_number': _TOP_SET_NUMBER, 'set_role': 'top_set',
                'weight_kg': '100', 'reps': '8', 'rir': '2',
            }
            for field, value in (('weight_kg', '999.01'), ('weight_kg', '1000'), ('reps', '301'), ('reps', '1000')):
                with self.subTest(**{field: value}):
                    response = self._post({**base, field: value})
                    self.assertEqual((response.status_code, response.json()['error']), (400, 'serie invalida'))
            self.assertFalse(PublicWorkoutTrainingSet.objects.exists())
            response = self._post({**base, 'weight_kg': '999', 'reps': '300'})
            self.assertEqual(response.status_code, 200, response.content)
            # Correção passa pelos mesmos tetos.
            correction = self._post({**base, 'action': 'correct', 'command_key': str(uuid.uuid4()), 'reps': '301'})
            self.assertEqual(correction.status_code, 400, correction.content)
