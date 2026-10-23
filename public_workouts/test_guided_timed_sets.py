"""L2: isometria (prancha) no guiado é série por tempo, não carga."""

import json
import uuid
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from public_workouts.guided_prescription import expand_guided_prescription, validate_guided_prescription
from public_workouts.guided_workout import build_legacy_series
from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutSubscription, PublicWorkoutTrainingSet,
)
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.training_sessions import TrainingSessionInvalid, record_set, start_session
from public_workouts.training_set_decisions import correct_set
from student_identity.public_workout_session import (
    PUBLIC_WORKOUT_SESSION_COOKIE_NAME, build_public_workout_session_value,
)

_PLANK_STAGE = {
    'stage_id': 'prancha', 'role': 'top_set', 'min_sets': 2, 'max_sets': 3,
    'reps_min': None, 'reps_max': None, 'hold_seconds_min': 30, 'hold_seconds_max': 45,
    'rest_seconds': 45, 'load_rule': {'kind': 'manual'},
}


class TimedLegacyTextTest(SimpleTestCase):
    def _holds(self, spec):
        return [(row['role'], row['required'], row['hold_seconds'], row['hold_seconds_max'])
                for row in build_legacy_series({'reps_spec': spec})]

    def test_real_program_texts_become_timed_sets(self):
        # Formatos reais dos programas (arquivo da Juliana e o parser de HTML).
        self.assertEqual(self._holds('2 séries · 30-45 seg'), [('top_set', True, 30, 45)] * 2)
        self.assertEqual(self._holds('Top Set 2× 45-60s (prancha)'), [('top_set', True, 45, 60)] * 2)
        self.assertEqual(self._holds('3x45s'), [('top_set', True, 45, 45)] * 3)
        self.assertEqual(self._holds('3× 1 min'), [('top_set', True, 60, 60)] * 3)
        self.assertEqual(self._holds('2-3× 40 segundos'), [
            ('top_set', True, 40, 40), ('top_set', True, 40, 40), ('top_set', False, 40, 40),
        ])

    def test_reps_and_rest_notes_stay_untimed(self):
        for spec in ('3x8-10', '3× 10 · descanso 60s', '2× 45-60s → 2× 12-15'):
            with self.subTest(spec=spec):
                self.assertTrue(all(row.get('hold_seconds') is None for row in build_legacy_series({'reps_spec': spec})))


class TimedPrescriptionContractTest(SimpleTestCase):
    def test_timed_stage_expands_seconds_without_reps(self):
        prescription = {'version': 1, 'stages': [_PLANK_STAGE]}
        self.assertEqual(validate_guided_prescription(prescription), [])
        rows = expand_guided_prescription(prescription)
        self.assertEqual([(row['hold_seconds'], row['hold_seconds_max'], row['reps']) for row in rows], [(30, 45, None)] * 3)

    def test_invalid_timed_stages_are_rejected(self):
        cases = {
            'com repetições': {'reps_min': 8, 'hold_seconds_min': 30},
            'máximo sem mínimo': {'hold_seconds_min': None, 'hold_seconds_max': 30},
            'máximo menor': {'hold_seconds_min': 45, 'hold_seconds_max': 30},
            'acima de 1 h': {'hold_seconds_min': 3601, 'hold_seconds_max': None},
            'zero': {'hold_seconds_min': 0, 'hold_seconds_max': None},
        }
        for label, override in cases.items():
            with self.subTest(label):
                stage = {**_PLANK_STAGE, **override}
                self.assertTrue(validate_guided_prescription({'version': 1, 'stages': [stage]}))


class TimedSetRecordingTest(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='prancha@example.test')
        PublicWorkoutSubscription.objects.create(account=self.account, plan_slug='prancha')
        payload = build_example_payload()
        movements = payload['days'][0]['blocks'][0]['movements']
        movements[0]['guided_prescription'] = {'version': 1, 'stages': [_PLANK_STAGE]}
        movements[0].update({'movement_slug': 'forearm-plank', 'load_type': 'free', 'load_value': None})
        self.program = publish_program(slug='prancha', payload=payload)
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(
            account_id=self.account.pk, identity_verified=True
        )
        self.url = reverse('public-workout-session', kwargs={'plan_slug': 'prancha'})

    def _record(self, session, **values):
        return record_set(
            account_id=self.account.pk, plan_slug='prancha', session_id=session.pk,
            movement_index=0, set_number=1, movement_slug='forearm-plank', role='top_set',
            weight=values.get('weight'), reps=values.get('reps'), rir=values.get('rir'),
            duration_seconds=values.get('duration_seconds'),
        )

    def test_timed_set_stores_seconds_and_creates_no_load_log(self):
        session = start_session(account_id=self.account.pk, plan_slug='prancha', day_id='seg')
        row, created = self._record(session, duration_seconds=45)
        self.assertTrue(created)
        self.assertEqual((row.duration_seconds, row.weight_kg, row.reps), (45, None, None))
        self.assertFalse(PublicWorkoutLoadLog.objects.filter(account=self.account).exists())
        # Reenvio idêntico (fila offline) não duplica; outro tempo é conflito.
        self.assertEqual(self._record(session, duration_seconds=45), (row, False))

    def test_timed_set_requires_seconds_and_untimed_rejects_them(self):
        session = start_session(account_id=self.account.pk, plan_slug='prancha', day_id='seg')
        with self.assertRaisesMessage(TrainingSessionInvalid, 'informe o tempo da série'):
            self._record(session, weight=Decimal('10.00'))
        publish_program(slug='agacha', payload=build_example_payload())
        squatter = PublicWorkoutAccount.objects.create(email='agacha@example.test')
        PublicWorkoutSubscription.objects.create(account=squatter, plan_slug='agacha')
        other = start_session(account_id=squatter.pk, plan_slug='agacha', day_id='seg')
        with self.assertRaisesMessage(TrainingSessionInvalid, 'esta série não é por tempo'):
            record_set(
                account_id=squatter.pk, plan_slug='agacha', session_id=other.pk,
                movement_index=0, set_number=1, movement_slug='agachamento-livre', role='top_set',
                weight=Decimal('50.00'), reps=8, rir=None, duration_seconds=30,
            )

    def test_api_records_seconds_and_returns_them_on_resume(self):
        started = self.client.post(self.url, data=json.dumps({
            'action': 'start', 'day_id': 'seg', 'start_key': str(uuid.uuid4()),
            'program_version': self.program.version,
        }), content_type='application/json')
        session_id = started.json()['session_id']
        body = {
            'action': 'set', 'session_id': session_id, 'movement_slug': 'forearm-plank',
            'movement_index': 0, 'set_number': 1, 'set_role': 'top_set',
            'weight_kg': '', 'reps': '', 'rir': '', 'duration_seconds': '45',
        }
        self.assertEqual(self.client.post(self.url, data=json.dumps({**body, 'duration_seconds': '0'}),
                                          content_type='application/json').status_code, 400)
        response = self.client.post(self.url, data=json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        recorded = self.client.get(self.url).json()['session']['recorded']
        self.assertEqual(recorded[0]['duration_seconds'], 45)
        self.assertEqual(PublicWorkoutTrainingSet.objects.get().duration_seconds, 45)

    def test_api_rejects_bad_seconds_and_missing_time_then_completes(self):
        started = self.client.post(self.url, data=json.dumps({
            'action': 'start', 'day_id': 'seg', 'start_key': str(uuid.uuid4()),
            'program_version': self.program.version,
        }), content_type='application/json')
        session_id = started.json()['session_id']
        base = {
            'action': 'set', 'session_id': session_id, 'movement_slug': 'forearm-plank',
            'movement_index': 0, 'set_number': 1, 'set_role': 'top_set',
            'weight_kg': '', 'reps': '', 'rir': '',
        }

        def post(body):
            return self.client.post(self.url, data=json.dumps(body), content_type='application/json')

        # Tempo booleano ou não numérico: payload inválido, nem chega na regra.
        for bad in (True, 'abc'):
            with self.subTest(duration=bad):
                response = post({**base, 'duration_seconds': bad})
                self.assertEqual((response.status_code, response.json()['error']), (400, 'serie invalida'))
        # Série por tempo sem o tempo: a regra do servidor recusa com a mensagem certa.
        response = post({**base, 'duration_seconds': ''})
        self.assertEqual((response.status_code, response.json()['error']), (400, 'informe o tempo da série'))
        self.assertEqual(post({**base, 'duration_seconds': 45}).status_code, 200)
        # A etapa pede 2 séries: com 1 feita, o treino encerra como parcial e devolve o tempo.
        completed = post({'action': 'partial', 'session_id': session_id})
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertEqual(completed.json()['recorded'][0]['duration_seconds'], 45)

    def test_timed_set_cannot_be_corrected_as_load(self):
        session = start_session(account_id=self.account.pk, plan_slug='prancha', day_id='seg')
        self._record(session, duration_seconds=45)
        with self.assertRaisesMessage(TrainingSessionInvalid, 'série por tempo'):
            correct_set(
                account_id=self.account.pk, plan_slug='prancha', session_id=session.pk,
                movement_index=0, set_number=1, command_key=uuid.uuid4(),
                weight=Decimal('10.00'), reps=None, rir=None,
            )
