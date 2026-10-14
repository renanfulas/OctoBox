"""L2: prescrição publicada, sessão e séries no PostgreSQL real."""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from decimal import Decimal
import uuid
import json

from public_workouts.models import (
    PublicWorkoutAccount, PublicWorkoutLoadLog, PublicWorkoutStaffCredential,
    PublicWorkoutSubscription, PublicWorkoutTrainingSet, PublicWorkoutTrainingSetRevision,
)
from student_identity.public_workout_session import PUBLIC_WORKOUT_SESSION_COOKIE_NAME, build_public_workout_session_value
from public_workouts.schema import build_example_payload
from public_workouts.services import publish_program
from public_workouts.training_sessions import TrainingSessionConflict, finish_session, record_set, start_session
from public_workouts.training_set_decisions import cancel_session, correct_set, skip_set, unskip_set
from public_workouts.training_analytics import recent_training_sessions, training_summary


class GuidedTrainingSessionIntegrationTest(TestCase):
    def setUp(self):
        self.account = PublicWorkoutAccount.objects.create(email='guiado@example.com')
        payload = build_example_payload()
        payload['days'][0]['blocks'][0]['movements'][0]['guided_prescription'] = {
            'version': 1, 'stages': [
                {'stage_id': 'top', 'role': 'top_set', 'min_sets': 2, 'max_sets': 3,
                 'reps_min': 6, 'reps_max': 8, 'rest_seconds': 120,
                 'load_rule': {'kind': 'suggested_top'}},
            ],
        }
        self.program = publish_program(slug='guiado', payload=payload)

    def test_minimum_sets_complete_optional_set_can_remain_open(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        for number in (1, 2):
            record_set(
                account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
                movement_index=0, set_number=number, movement_slug='agachamento-livre',
                role='top_set', weight=Decimal('50.00'), reps=7, rir=Decimal('2.0'),
            )
        completed, created = finish_session(
            account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
        )
        self.assertTrue(created)
        self.assertEqual(completed.outcome, 'completed')
        self.assertEqual(PublicWorkoutTrainingSet.objects.filter(session=session).count(), 2)

    def test_cannot_complete_before_minimum(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        with self.assertRaises(TrainingSessionConflict):
            finish_session(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk)

    def test_offline_start_rejects_new_program_version_without_rewriting_old_session(self):
        start_key = str(uuid.uuid4())
        first = start_session(
            account_id=self.account.pk, plan_slug='guiado', day_id='seg',
            start_key=start_key, expected_program_version=self.program.version,
        )
        payload = build_example_payload()
        payload['program_id'] = self.program.program_id
        publish_program(slug='guiado', payload=payload)
        replay = start_session(
            account_id=self.account.pk, plan_slug='guiado', day_id='seg',
            start_key=start_key, expected_program_version=self.program.version,
        )
        self.assertEqual(replay.pk, first.pk)
        with self.assertRaises(TrainingSessionConflict):
            start_session(
                account_id=self.account.pk, plan_slug='guiado', day_id='seg',
                start_key=str(uuid.uuid4()), expected_program_version=self.program.version,
            )

    def test_skip_required_is_visible_but_only_partial_can_finish(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        skipped, created = skip_set(
            account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
            movement_index=0, set_number=1, movement_slug='agachamento-livre', role='top_set',
        )
        self.assertTrue(created)
        self.assertEqual(skipped.status, 'skipped')
        self.assertFalse(PublicWorkoutLoadLog.objects.exists())
        with self.assertRaises(TrainingSessionConflict):
            finish_session(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk)
        ended, _ = finish_session(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk, partial=True)
        self.assertEqual(ended.completed_set_count, 0)
        self.assertEqual(training_summary(window_days=7)['sessions_partial'], 1)

    def test_unskip_restores_slot_before_end(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        address = dict(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
                       movement_index=0, set_number=1)
        skip_set(**address, movement_slug='agachamento-livre', role='top_set')
        self.assertTrue(unskip_set(**address))
        self.assertFalse(PublicWorkoutTrainingSet.objects.filter(session=session).exists())

    def test_correct_top_supersedes_load_log_once_and_keeps_audit(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        row, _ = record_set(
            account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
            movement_index=0, set_number=1, movement_slug='agachamento-livre',
            role='top_set', weight=Decimal('50.00'), reps=7, rir=Decimal('2.0'),
        )
        original_log = row.load_log
        command_key = uuid.uuid4()
        corrected, changed = correct_set(
            account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
            movement_index=0, set_number=1, command_key=command_key,
            weight=Decimal('55.00'), reps=7, rir=Decimal('1.0'),
        )
        self.assertTrue(changed)
        self.assertEqual(corrected.weight_kg, Decimal('55.00'))
        original_log.refresh_from_db()
        self.assertFalse(original_log.is_active)
        self.assertEqual(PublicWorkoutLoadLog.objects.filter(account=self.account, is_active=True).count(), 1)
        self.assertEqual(PublicWorkoutTrainingSetRevision.objects.filter(training_set=row).count(), 1)
        _, replay_changed = correct_set(
            account_id=self.account.pk, plan_slug='guiado', session_id=session.pk,
            movement_index=0, set_number=1, command_key=command_key,
            weight=Decimal('55.00'), reps=7, rir=Decimal('1.0'),
        )
        self.assertFalse(replay_changed)
        self.assertEqual(PublicWorkoutLoadLog.objects.filter(account=self.account).count(), 2)

    def test_cancel_is_idempotent_and_reported_separately(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        _, created = cancel_session(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk)
        self.assertTrue(created)
        _, created = cancel_session(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk)
        self.assertFalse(created)
        with self.assertRaises(TrainingSessionConflict):
            finish_session(account_id=self.account.pk, plan_slug='guiado', session_id=session.pk)
        self.assertEqual(training_summary(window_days=7)['sessions_cancelled'], 1)
        self.assertEqual(recent_training_sessions(window_days=7)[0]['status'], 'Cancelado')

    def test_session_api_persists_skip_and_unskip_for_same_account(self):
        PublicWorkoutSubscription.objects.create(account=self.account, plan_slug='guiado')
        self.client.cookies[PUBLIC_WORKOUT_SESSION_COOKIE_NAME] = build_public_workout_session_value(account_id=self.account.pk)
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        url = reverse('public-workout-session', kwargs={'plan_slug': 'guiado'})
        body = {'action': 'skip', 'session_id': str(session.pk), 'movement_index': 0,
                'set_number': 1, 'movement_slug': 'agachamento-livre', 'set_role': 'top_set'}
        response = self.client.post(url, data=json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.json()['session']['skipped'], ['0:1'])
        body['action'] = 'unskip'
        response = self.client.post(url, data=json.dumps(body), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(url).json()['session']['skipped'], [])

    def test_analytics_detail_requires_staff_session_and_lists_student(self):
        session = start_session(account_id=self.account.pk, plan_slug='guiado', day_id='seg')
        url = reverse('public-workout-training-session-detail', kwargs={'session_id': session.pk})
        anonymous = self.client.get(url)
        self.assertEqual(anonymous.status_code, 302)
        credential, _ = PublicWorkoutStaffCredential.objects.update_or_create(
            username='guided-analytics', defaults={'password_hash': make_password('test-only'), 'is_active': True},
        )
        auth_session = self.client.session
        auth_session['public_workout_analytics_username'] = credential.username
        auth_session.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.account.email)
        self.assertContains(response, str(session.pk))
