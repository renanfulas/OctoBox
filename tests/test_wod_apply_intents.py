"""Gate A4 no tenant: programa, prévia, replay e confirmação semanal."""

import json
from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from operations.models import ClassSession, ClassType, SessionStatus, WorkoutProgram, WorkoutTemplate, WorkoutTemplateBlock
from operations.services.wod_preview_contracts import issue_projection_token, read_projection_token
from operations.services.wod_projection import build_projection_preview, project_plan_to_sessions
from operations.services.wod_drafts import (
    DRAFT_TTL, MAX_ACTIVE_DRAFTS, MAX_SOURCE_LENGTH, DraftQuota,
    DraftTooLarge, resolve_draft_scope, save_draft,
)
from operations.workout_draft_views import (
    DRAFT_SAVE_RATE_LIMIT_MAX, _too_many_saves,
)
from student_app.application.wod_snapshots import get_published_student_workout_snapshot
from student_app.models import ReplicationBatch, SessionWorkout, SessionWorkoutStatus, WeeklyWodPlan, WodInputDraft
from tests.workout_test_support import WorkoutFlowBaseTestCase


class WodApplyIntentTests(WorkoutFlowBaseTestCase):
    def setUp(self):
        super().setUp()
        self.program = WorkoutProgram.objects.create(slug='a4-cross-a', name='Cross A')
        self.other_program = WorkoutProgram.objects.create(slug='a4-cross-b', name='Cross B')
        self.session.class_type = ClassType.CROSS
        self.session.workout_program = self.program
        self.session.save(update_fields=['class_type', 'workout_program'])
        self.template = WorkoutTemplate.objects.create(name='Base A4', created_by=self.coach)
        WorkoutTemplateBlock.objects.create(template=self.template, title='Força', kind='strength', sort_order=1)

    def _new_session(self, *, program, status=SessionStatus.SCHEDULED):
        return ClassSession.objects.create(
            title=f'Aula {program.name}', class_type=ClassType.CROSS,
            workout_program=program, coach=self.coach,
            scheduled_at=self.session.scheduled_at + timedelta(hours=1),
            duration_minutes=60, capacity=12, status=status,
        )

    def _daily_preview(self):
        return self.client.post(reverse('wod-day-program-preview'), {
            'target_date': timezone.localdate().isoformat(),
            'template_id': self.template.pk, 'workout_program_id': self.program.pk,
            'mode': 'replace_empty',
        })

    def _daily_confirm(self, preview):
        return self.client.post(reverse('wod-day-program-confirm'), {
            'intent_id': preview['intent_id'], 'fingerprint': preview['fingerprint'],
        })

    def test_daily_targets_one_program_preserves_completed_and_replays(self):
        other = self._new_session(program=self.other_program)
        completed = self._new_session(program=self.program, status=SessionStatus.COMPLETED)
        canceled = self._new_session(program=self.program, status=SessionStatus.CANCELED)
        response = self._daily_preview()
        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(preview['ready_count'], 1)
        self.assertEqual(preview['completed_count'], 1)
        entry_by_session = {row['session_id']: row for row in preview['entries']}
        self.assertEqual(set(entry_by_session), {self.session.pk, completed.pk, canceled.pk})
        self.assertEqual(entry_by_session[canceled.pk]['status'], 'skipped_canceled')

        confirmation = self._daily_confirm(preview)
        self.assertEqual(confirmation.status_code, 200)
        self.assertEqual(confirmation.json()['applied_count'], 1)
        self.assertEqual(confirmation.json()['skipped_completed'], 1)
        self.assertIn('skipped_canceled', {item['code'] for item in confirmation.json()['skipped_reasons']})
        self.assertTrue(SessionWorkout.objects.filter(session=self.session).exists())
        self.assertFalse(SessionWorkout.objects.filter(session__in=[other, completed, canceled]).exists())

        replay = self._daily_confirm(preview)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()['idempotent_replay'])
        self.template.refresh_from_db()
        self.assertEqual(self.template.usage_count, 1)
        reused = self.client.post(reverse('wod-day-program-confirm'), {
            'intent_id': preview['intent_id'], 'fingerprint': '0' * 64,
        })
        self.assertEqual(reused.status_code, 409)
        self.assertEqual(reused.json()['code'], 'idempotency_key_reused')

    def test_daily_change_after_preview_blocks_entire_batch(self):
        preview = self._daily_preview().json()
        self.session.status = SessionStatus.COMPLETED
        self.session.save(update_fields=['status'])
        response = self._daily_confirm(preview)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'stale_preview')
        self.assertFalse(SessionWorkout.objects.exists())

    def test_daily_cancellation_after_preview_blocks_entire_batch(self):
        preview = self._daily_preview().json()
        self.session.status = SessionStatus.CANCELED
        self.session.save(update_fields=['status'])

        response = self._daily_confirm(preview)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'stale_preview')
        self.assertFalse(SessionWorkout.objects.exists())

    def test_inactive_program_after_preview_blocks_confirmation_without_mutation(self):
        preview = self._daily_preview().json()
        self.program.is_active = False
        self.program.save(update_fields=['is_active'])

        response = self._daily_confirm(preview)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'stale_preview')
        self.assertFalse(SessionWorkout.objects.exists())

    def test_archived_template_after_preview_blocks_confirmation_without_mutation(self):
        preview = self._daily_preview().json()
        self.template.archived_at = timezone.now()
        self.template.save(update_fields=['archived_at'])

        response = self._daily_confirm(preview)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'stale_preview')
        self.assertFalse(SessionWorkout.objects.exists())

    def test_daily_policy_change_after_preview_blocks_entire_batch(self):
        with override_settings(WOD_APPROVAL_POLICY='strict'):
            preview = self._daily_preview().json()

        with override_settings(WOD_APPROVAL_POLICY='coach_autonomy'):
            response = self._daily_confirm(preview)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'stale_preview')
        self.assertFalse(SessionWorkout.objects.exists())

    def test_draft_and_applied_wod_stay_invisible_until_publication(self):
        scope = resolve_draft_scope(actor=self.coach, scope_kind='daily', session_id=self.session.pk)
        save_draft(actor=self.coach, scope=scope, source_text='Texto privado do coach', request_id=uuid4())
        self.assertIsNone(get_published_student_workout_snapshot(session_id=self.session.pk, box_root_slug=None))

        preview = self._daily_preview().json()
        self.assertEqual(self._daily_confirm(preview).status_code, 200)
        self.assertIsNone(get_published_student_workout_snapshot(session_id=self.session.pk, box_root_slug=None))

        workout = SessionWorkout.objects.get(session=self.session)
        workout.status = SessionWorkoutStatus.PUBLISHED
        workout.version += 1
        workout.save(update_fields=['status', 'version'])
        published = get_published_student_workout_snapshot(session_id=self.session.pk, box_root_slug=None)
        self.assertEqual(published['workout_title'], 'Base A4')
        self.assertNotIn('Texto privado do coach', str(published))

        workout.title = 'Base A4 revisada'
        workout.version += 1
        workout.save(update_fields=['title', 'version'])
        revised = get_published_student_workout_snapshot(session_id=self.session.pk, box_root_slug=None)
        self.assertEqual(revised['workout_title'], 'Base A4 revisada')

    def test_manager_keeps_weekly_draft_access_without_daily_editor_access(self):
        self.login_as_manager()
        daily = self.client.get(reverse('wod-input-draft'), {
            'scope_kind': 'daily', 'session_id': self.session.pk,
        })
        self.assertEqual(daily.status_code, 403)
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        weekly = self.client.get(reverse('wod-input-draft'), {
            'scope_kind': 'weekly', 'week_start': week_start.isoformat(),
            'workout_program_id': self.program.pk,
        })
        self.assertEqual(weekly.status_code, 200)
        self.assertIsNone(weekly.json()['draft'])

    def test_manager_cannot_read_or_update_coachs_weekly_draft(self):
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        coach_scope = resolve_draft_scope(
            actor=self.coach, scope_kind='weekly', week_start=week_start.isoformat(),
            workout_program_id=self.program.pk,
        )
        draft = save_draft(
            actor=self.coach, scope=coach_scope, source_text='Texto privado do Coach',
            request_id=uuid4(),
        )
        self.login_as_manager()

        read = self.client.get(reverse('wod-input-draft'), {
            'scope_kind': 'weekly', 'week_start': week_start.isoformat(),
            'workout_program_id': self.program.pk,
        })
        self.assertEqual(read.status_code, 200)
        self.assertIsNone(read.json()['draft'])
        self.assertNotContains(read, 'Texto privado do Coach')

        update = self.client.post(reverse('wod-input-draft'), data=json.dumps({
            'scope_kind': 'weekly', 'week_start': week_start.isoformat(),
            'workout_program_id': self.program.pk, 'action': 'save',
            'source_text': 'Tentativa de alteração', 'request_id': str(uuid4()),
            'draft_id': str(draft.pk), 'expected_version': draft.version,
        }), content_type='application/json')
        self.assertEqual(update.status_code, 409)
        self.assertEqual(update.json()['code'], 'draft_missing')
        draft.refresh_from_db()
        self.assertEqual(draft.source_text, 'Texto privado do Coach')
        self.assertEqual(draft.version, 1)

    def test_expired_draft_is_not_recovered_and_is_marked_expired(self):
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        scope = resolve_draft_scope(
            actor=self.coach, scope_kind='weekly', week_start=monday.isoformat(),
            workout_program_id=self.program.pk,
        )
        draft = save_draft(actor=self.coach, scope=scope, source_text='Rascunho vencido', request_id=uuid4())
        WodInputDraft.objects.filter(pk=draft.pk).update(expires_at=timezone.now() - timedelta(seconds=1))

        response = self.client.get(reverse('wod-input-draft'), {
            'scope_kind': 'weekly', 'week_start': monday.isoformat(),
            'workout_program_id': self.program.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['draft'])
        draft.refresh_from_db()
        self.assertEqual(draft.state, WodInputDraft.State.EXPIRED)

    def test_draft_size_boundary_and_http_status(self):
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        scope = resolve_draft_scope(
            actor=self.coach, scope_kind='weekly', week_start=monday.isoformat(),
            workout_program_id=self.program.pk,
        )
        accepted = save_draft(
            actor=self.coach, scope=scope, source_text='x' * MAX_SOURCE_LENGTH,
            request_id=uuid4(),
        )
        self.assertEqual(len(accepted.source_text), MAX_SOURCE_LENGTH)

        with self.assertRaises(DraftTooLarge):
            save_draft(
                actor=self.coach, scope=scope, source_text='x' * (MAX_SOURCE_LENGTH + 1),
                request_id=uuid4(),
            )

        response = self.client.post(
            reverse('wod-input-draft'),
            data=json.dumps({
                'scope_kind': 'weekly', 'week_start': monday.isoformat(),
                'workout_program_id': self.program.pk, 'action': 'save',
                'source_text': 'x' * (MAX_SOURCE_LENGTH + 1), 'request_id': str(uuid4()),
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()['code'], 'draft_too_large')

    def test_draft_expiration_is_sliding_for_thirty_days(self):
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        scope = resolve_draft_scope(
            actor=self.coach, scope_kind='weekly', week_start=monday.isoformat(),
            workout_program_id=self.program.pk,
        )
        created_at = timezone.now()
        with patch('operations.services.wod_drafts.timezone.now', return_value=created_at):
            draft = save_draft(
                actor=self.coach, scope=scope, source_text='WOD original', request_id=uuid4(),
            )
        self.assertEqual(draft.expires_at, created_at + DRAFT_TTL)
        self.assertEqual(DRAFT_TTL, timedelta(days=30))

        updated_at = created_at + timedelta(days=10)
        with patch('operations.services.wod_drafts.timezone.now', return_value=updated_at):
            updated = save_draft(
                actor=self.coach, scope=scope, source_text='WOD revisado', request_id=uuid4(),
                expected_version=draft.version, draft_id=draft.pk,
            )
        self.assertEqual(updated.version, draft.version + 1)
        self.assertEqual(updated.expires_at, updated_at + timedelta(days=30))

    def test_save_rate_limit_has_exact_window_and_retry_after(self):
        key = f'wod-draft-save:{self.coach.pk}'
        cache.delete(key)
        try:
            for _ in range(DRAFT_SAVE_RATE_LIMIT_MAX):
                self.assertFalse(_too_many_saves(self.coach))
            self.assertTrue(_too_many_saves(self.coach))
        finally:
            cache.delete(key)

        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        response = self.client.post(
            reverse('wod-input-draft'),
            data=json.dumps({
                'scope_kind': 'weekly', 'week_start': monday.isoformat(),
                'workout_program_id': self.program.pk, 'action': 'save',
                'source_text': 'WOD', 'request_id': str(uuid4()),
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        with patch('operations.workout_draft_views._too_many_saves', return_value=True):
            limited = self.client.post(
                reverse('wod-input-draft'),
                data=json.dumps({
                    'scope_kind': 'weekly', 'week_start': monday.isoformat(),
                    'workout_program_id': self.program.pk, 'action': 'save',
                    'source_text': 'WOD revisado', 'request_id': str(uuid4()),
                    'draft_id': response.json()['draft']['draft_id'], 'expected_version': 1,
                }),
                content_type='application/json',
            )
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()['code'], 'rate_limited')
        self.assertEqual(limited['Retry-After'], '300')

    def test_discard_remains_available_when_save_rate_limit_is_exhausted(self):
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        scope = resolve_draft_scope(
            actor=self.coach, scope_kind='weekly', week_start=monday.isoformat(),
            workout_program_id=self.program.pk,
        )
        draft = save_draft(
            actor=self.coach, scope=scope, source_text='WOD para descartar', request_id=uuid4(),
        )
        with patch('operations.workout_draft_views._too_many_saves', return_value=True) as limiter:
            response = self.client.post(
                reverse('wod-input-draft'),
                data=json.dumps({
                    'scope_kind': 'weekly', 'week_start': monday.isoformat(),
                    'workout_program_id': self.program.pk, 'action': 'discard',
                    'draft_id': str(draft.pk), 'expected_version': draft.version,
                }),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(limiter.called)
        draft.refresh_from_db()
        self.assertEqual(draft.state, WodInputDraft.State.DISCARDED)

    def test_active_draft_quota_is_per_author_and_box(self):
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        for index in range(MAX_ACTIVE_DRAFTS):
            week_start = monday + timedelta(days=index * 7)
            scope = resolve_draft_scope(
                actor=self.coach, scope_kind='weekly', week_start=week_start.isoformat(),
                workout_program_id=self.program.pk,
            )
            save_draft(actor=self.coach, scope=scope, source_text=f'WOD {index}', request_id=uuid4())

        twenty_first_scope = resolve_draft_scope(
            actor=self.coach, scope_kind='weekly',
            week_start=(monday + timedelta(days=MAX_ACTIVE_DRAFTS * 7)).isoformat(),
            workout_program_id=self.program.pk,
        )
        with self.assertRaises(DraftQuota):
            save_draft(
                actor=self.coach, scope=twenty_first_scope,
                source_text='WOD excedente', request_id=uuid4(),
            )
        self.assertEqual(
            WodInputDraft.objects.filter(author=self.coach, state='active').count(),
            MAX_ACTIVE_DRAFTS,
        )

    def _weekly_plan(self):
        weekday = timezone.localtime(self.session.scheduled_at).weekday()
        week_start = timezone.localdate() - timedelta(days=weekday)
        plan = WeeklyWodPlan.objects.create(
            week_start=week_start, workout_program=self.program,
            label='Semana A4', source_text='Treino da semana',
            status='confirmed', created_by=self.coach,
            parsed_payload={'days': [{
                'weekday': weekday,
                'blocks': [{'kind': 'strength', 'title': 'Força', 'movements': []}],
            }]},
        )
        return plan, week_start

    def test_weekly_token_targets_program_and_replays_batch(self):
        other = self._new_session(program=self.other_program)
        completed = self._new_session(program=self.program, status=SessionStatus.COMPLETED)
        plan, week_start = self._weekly_plan()
        classes = [ClassType.CROSS]
        preview = build_projection_preview(
            weekly_plan=plan, target_week_start=week_start,
            class_types=classes, exclude_completed=True,
        )
        self.assertEqual(preview['totals']['sessions_creatable'], 1)
        self.assertEqual(preview['totals']['sessions_completed_skipped'], 1)
        key = uuid4()
        token = issue_projection_token(
            weekly_plan=plan, target_week_start=week_start, class_types=classes,
            actor=self.coach, preview=preview, intent_id=key,
        )
        digest = read_projection_token(token)['fingerprint']
        kwargs = dict(
            weekly_plan=plan, target_week_start=week_start,
            class_types=classes, actor=self.coach, idempotency_key=key,
            expected_preview_fingerprint=digest, exclude_completed=True,
        )
        batch, result = project_plan_to_sessions(**kwargs)
        self.assertEqual(batch.sessions_created, 1)
        self.assertFalse(result.get('idempotent_replay', False))
        self.assertFalse(SessionWorkout.objects.filter(session__in=[other, completed]).exists())
        replay, replay_preview = project_plan_to_sessions(**kwargs)
        self.assertEqual(replay.pk, batch.pk)
        self.assertTrue(replay_preview['idempotent_replay'])
        self.assertEqual(ReplicationBatch.objects.filter(weekly_plan=plan).count(), 1)

    def test_weekly_changed_destination_rejects_preview_before_write(self):
        plan, week_start = self._weekly_plan()
        classes = [ClassType.CROSS]
        preview = build_projection_preview(
            weekly_plan=plan, target_week_start=week_start,
            class_types=classes, exclude_completed=True,
        )
        digest = read_projection_token(issue_projection_token(
            weekly_plan=plan, target_week_start=week_start, class_types=classes,
            actor=self.coach, preview=preview, intent_id=uuid4(),
        ))['fingerprint']
        self.session.status = SessionStatus.COMPLETED
        self.session.save(update_fields=['status'])
        with self.assertRaisesMessage(ValidationError, 'mudaram depois da prévia'):
            project_plan_to_sessions(
                weekly_plan=plan, target_week_start=week_start,
                class_types=classes, actor=self.coach, idempotency_key=uuid4(),
                expected_preview_fingerprint=digest, exclude_completed=True,
            )
        self.assertFalse(ReplicationBatch.objects.exists())
        self.assertFalse(SessionWorkout.objects.exists())

    def test_weekly_cancellation_after_preview_rejects_stale_fingerprint(self):
        plan, week_start = self._weekly_plan()
        classes = [ClassType.CROSS]
        preview = build_projection_preview(
            weekly_plan=plan, target_week_start=week_start,
            class_types=classes, exclude_completed=True,
        )
        intent_id = uuid4()
        digest = read_projection_token(issue_projection_token(
            weekly_plan=plan, target_week_start=week_start, class_types=classes,
            actor=self.coach, preview=preview, intent_id=intent_id,
        ))['fingerprint']
        self.session.status = SessionStatus.CANCELED
        self.session.save(update_fields=['status'])

        with self.assertRaisesMessage(ValidationError, 'mudaram depois da prévia'):
            project_plan_to_sessions(
                weekly_plan=plan, target_week_start=week_start,
                class_types=classes, actor=self.coach, idempotency_key=intent_id,
                expected_preview_fingerprint=digest, exclude_completed=True,
            )

        self.assertFalse(ReplicationBatch.objects.exists())
        self.assertFalse(SessionWorkout.objects.exists())

    def test_weekly_new_workout_after_preview_rejects_stale_fingerprint(self):
        other_destination = self._new_session(program=self.program)
        plan, week_start = self._weekly_plan()
        classes = [ClassType.CROSS]
        preview = build_projection_preview(
            weekly_plan=plan, target_week_start=week_start,
            class_types=classes, exclude_completed=True,
        )
        intent_id = uuid4()
        digest = read_projection_token(issue_projection_token(
            weekly_plan=plan, target_week_start=week_start, class_types=classes,
            actor=self.coach, preview=preview, intent_id=intent_id,
        ))['fingerprint']
        concurrent_workout = SessionWorkout.objects.create(
            session=self.session, title='WOD concorrente',
            status=SessionWorkoutStatus.DRAFT, created_by=self.coach,
        )

        with self.assertRaisesMessage(ValidationError, 'mudaram depois da prévia'):
            project_plan_to_sessions(
                weekly_plan=plan, target_week_start=week_start,
                class_types=classes, actor=self.coach, idempotency_key=intent_id,
                expected_preview_fingerprint=digest, exclude_completed=True,
            )

        self.assertEqual(SessionWorkout.objects.get(session=self.session).pk, concurrent_workout.pk)
        self.assertFalse(SessionWorkout.objects.filter(session=other_destination).exists())
        self.assertFalse(ReplicationBatch.objects.exists())

    def test_weekly_program_change_after_preview_rejects_stale_fingerprint(self):
        other_destination = self._new_session(program=self.program)
        plan, week_start = self._weekly_plan()
        classes = [ClassType.CROSS]
        preview = build_projection_preview(
            weekly_plan=plan, target_week_start=week_start,
            class_types=classes, exclude_completed=True,
        )
        intent_id = uuid4()
        digest = read_projection_token(issue_projection_token(
            weekly_plan=plan, target_week_start=week_start, class_types=classes,
            actor=self.coach, preview=preview, intent_id=intent_id,
        ))['fingerprint']

        self.session.workout_program = self.other_program
        self.session.save(update_fields=['workout_program'])

        with self.assertRaisesMessage(ValidationError, 'mudaram depois da prévia'):
            project_plan_to_sessions(
                weekly_plan=plan, target_week_start=week_start,
                class_types=classes, actor=self.coach, idempotency_key=intent_id,
                expected_preview_fingerprint=digest, exclude_completed=True,
            )

        self.assertEqual(self.session.workout_program_id, self.other_program.pk)
        self.assertFalse(ReplicationBatch.objects.exists())
        self.assertFalse(SessionWorkout.objects.filter(session__in=[self.session, other_destination]).exists())
