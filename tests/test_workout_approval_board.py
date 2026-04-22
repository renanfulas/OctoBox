from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from access.roles import ROLE_COACH
from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession
from student_app.models import (
    SessionWorkout,
    SessionWorkoutBlock,
    SessionWorkoutMovement,
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
    SessionWorkoutRmGapAction,
    SessionWorkoutStatus,
    StudentExerciseMax,
    StudentWorkoutView,
    WorkoutLoadType,
    WorkoutRmGapActionStatus,
)
from tests.workout_test_support import WorkoutFlowBaseTestCase


class WorkoutApprovalBoardTests(WorkoutFlowBaseTestCase):
    def test_manager_can_approve_pending_workout(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD pendente',
            coach_notes='Submeter para aprovacao.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
        )
        self.login_as_manager()

        response = self.client.post(reverse('workout-approval-action', args=[workout.id, 'approve']), follow=True)

        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.status, SessionWorkoutStatus.PUBLISHED)
        self.assertEqual(workout.approved_by, self.manager)
        self.assertTrue(
            SessionWorkoutRevision.objects.filter(
                workout=workout,
                event=SessionWorkoutRevisionEvent.PUBLISHED,
                version=workout.version,
            ).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action='session_workout_published', target_id=str(workout.id)).exists())

    def test_manager_can_approve_with_optional_decision_reason(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD com trilha de decisao',
            coach_notes='Submeter para aprovacao.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
        )
        self.login_as_manager()

        response = self.client.post(
            reverse('workout-approval-action', args=[workout.id, 'approve']),
            data={
                'approval_reason_category': 'verbal_alignment',
                'approval_reason_note': 'Coach alinhou ajuste final no aquecimento.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.status, SessionWorkoutStatus.PUBLISHED)
        revision = SessionWorkoutRevision.objects.get(
            workout=workout,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            version=workout.version,
        )
        self.assertEqual(revision.snapshot.get('approval_reason_label'), 'Aprovado com alinhamento verbal')
        self.assertEqual(
            revision.snapshot.get('approval_reason_summary'),
            'Aprovado com alinhamento verbal: Coach alinhou ajuste final no aquecimento.',
        )
        audit = AuditEvent.objects.get(action='session_workout_published', target_id=str(workout.id))
        self.assertEqual(audit.metadata.get('approval_reason_category'), 'verbal_alignment')
        self.assertEqual(audit.metadata.get('approval_reason_label'), 'Aprovado com alinhamento verbal')

    def test_manager_must_confirm_sensitive_changes_before_approving(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD sensivel',
            coach_notes='Ajuste de carga importante.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
            version=2,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Forca',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=5,
            load_type=WorkoutLoadType.FIXED_KG,
            load_value=Decimal('90.00'),
            sort_order=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD sensivel',
                'coach_notes': 'Versao anterior',
                'status': 'published',
                'version': 1,
                'blocks': [
                    {
                        'sort_order': 1,
                        'title': 'Forca',
                        'kind': 'strength',
                        'kind_label': 'Forca',
                        'notes': '',
                        'movements': [
                            {
                                'sort_order': 1,
                                'movement_slug': 'deadlift',
                                'movement_label': 'Deadlift',
                                'sets': 5,
                                'reps': 5,
                                'load_type': WorkoutLoadType.PERCENTAGE_OF_RM,
                                'load_value': '70.00',
                                'notes': '',
                            }
                        ],
                    }
                ],
            },
        )
        self.login_as_manager()

        response = self.client.post(reverse('workout-approval-action', args=[workout.id, 'approve']), follow=True)

        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.status, SessionWorkoutStatus.PENDING_APPROVAL)
        self.assertContains(response, 'Confirme que revisou as mudancas sensiveis antes de publicar.')

        response = self.client.post(
            reverse('workout-approval-action', args=[workout.id, 'approve']),
            data={'confirm_sensitive_changes': '1'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.status, SessionWorkoutStatus.PUBLISHED)

    def test_owner_can_reject_pending_workout_with_reason(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD pendente',
            coach_notes='Submeter para aprovacao.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
        )
        self.login_as_owner()

        response = self.client.post(
            reverse('workout-approval-action', args=[workout.id, 'reject']),
            data={
                'rejection_category': 'adjust_notes',
                'rejection_reason': 'Ajuste a progressao do bloco principal.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.status, SessionWorkoutStatus.REJECTED)
        self.assertEqual(workout.rejected_by, self.owner)
        self.assertEqual(workout.rejection_reason, 'Ajustar notas: Ajuste a progressao do bloco principal.')
        self.assertTrue(
            SessionWorkoutRevision.objects.filter(
                workout=workout,
                event=SessionWorkoutRevisionEvent.REJECTED,
                version=workout.version,
            ).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action='session_workout_rejected', target_id=str(workout.id)).exists())

    def test_approval_board_renders_richer_review_summary(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD pendente rico',
            coach_notes='Treino com aquecimento e forca.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
            version=3,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Aquecimento',
            kind='warmup',
            notes='Subir temperatura.',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='bike',
            movement_label='Bike',
            sets=1,
            reps=10,
            load_type=WorkoutLoadType.FREE,
            sort_order=1,
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-approval-board'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Leitura rapida da revisao')
        self.assertContains(response, 'Preview: Bike')
        self.assertContains(response, 'Versao 3 aguardando leitura final')
        self.assertContains(response, 'Preview do impacto no aluno')
        self.assertContains(response, 'Aluno vera assim')

    def test_approval_board_renders_diff_against_last_published_revision(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD revisado',
            coach_notes='Agora com bloco extra.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
            version=5,
        )
        warmup = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Warmup',
            kind='warmup',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=warmup,
            movement_slug='bike',
            movement_label='Bike',
            sets=1,
            reps=10,
            load_type=WorkoutLoadType.FREE,
            sort_order=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=workout,
            version=4,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD revisado',
                'coach_notes': 'Versao anterior',
                'status': 'published',
                'version': 4,
                'blocks': [
                    {
                        'sort_order': 1,
                        'title': 'Warmup',
                        'kind': 'warmup',
                        'kind_label': 'Aquecimento',
                        'notes': '',
                        'movements': [
                            {
                                'sort_order': 1,
                                'movement_slug': 'bike',
                                'movement_label': 'Bike',
                                'sets': 1,
                                'reps': 8,
                                'load_type': WorkoutLoadType.FREE,
                                'load_value': '',
                                'notes': '',
                            }
                        ],
                    }
                ],
            },
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-approval-board'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Diff contra a ultima publicacao')
        self.assertContains(response, 'Notas alteradas')
        self.assertContains(response, 'Timeline leve de auditoria')
        self.assertContains(response, 'Preview anterior')
        self.assertContains(response, 'Preview apos aprovacao')
        self.assertContains(response, 'Alto impacto')
        self.assertContains(response, 'Radar da fila')

    def test_approval_board_renders_decision_trail_in_timeline(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD com historico de decisao',
            coach_notes='Treino com aprovacao anterior.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
            version=3,
        )
        SessionWorkoutRevision.objects.create(
            workout=workout,
            version=2,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD com historico de decisao',
                'coach_notes': 'Versao publicada',
                'status': 'published',
                'version': 2,
                'blocks': [],
                'approval_reason_summary': 'Aprovado por urgencia operacional: Aula extra aberta no mesmo dia.',
            },
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-approval-board'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aprovado por urgencia operacional: Aula extra aberta no mesmo dia.')

    def test_approval_board_filters_sensitive_today_and_coach(self):
        sensitive_workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD sensivel filtrado',
            coach_notes='Tem carga fixa.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=self.coach,
            submitted_by=self.coach,
            submitted_at=timezone.now(),
            version=2,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=sensitive_workout,
            title='Forca',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=4,
            reps=4,
            load_type=WorkoutLoadType.FIXED_KG,
            load_value=Decimal('85.00'),
            sort_order=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=sensitive_workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD sensivel filtrado',
                'coach_notes': 'Versao anterior',
                'status': 'published',
                'version': 1,
                'blocks': [
                    {
                        'sort_order': 1,
                        'title': 'Forca',
                        'kind': 'strength',
                        'kind_label': 'Forca',
                        'notes': '',
                        'movements': [
                            {
                                'sort_order': 1,
                                'movement_slug': 'deadlift',
                                'movement_label': 'Deadlift',
                                'sets': 4,
                                'reps': 4,
                                'load_type': WorkoutLoadType.PERCENTAGE_OF_RM,
                                'load_value': '75.00',
                                'notes': '',
                            }
                        ],
                    }
                ],
            },
        )
        other_coach = get_user_model().objects.create_user(
            username='coach-outro',
            email='coach-outro@example.com',
            password='senha-forte-123',
        )
        other_coach.groups.add(Group.objects.get(name=ROLE_COACH))
        other_session = ClassSession.objects.create(
            title='Cross 20h',
            coach=other_coach,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        SessionWorkout.objects.create(
            session=other_session,
            title='WOD comum',
            coach_notes='Sem sensibilidade.',
            status=SessionWorkoutStatus.PENDING_APPROVAL,
            created_by=other_coach,
            submitted_by=other_coach,
            submitted_at=timezone.now(),
        )
        self.login_as_manager()

        response = self.client.get(
            reverse('workout-approval-board'),
            data={
                'coach': self.coach.username,
                'sensitive_only': '1',
                'today_only': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WOD sensivel filtrado')
        self.assertNotContains(response, 'WOD comum')
        self.assertContains(response, 'Somente mudancas sensiveis')

    def test_approval_board_renders_rm_readiness_against_real_consumption(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD com RM publicado',
            coach_notes='Treino de forca guiado por percentual.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.manager,
            approved_at=timezone.now(),
            version=2,
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Forca principal',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('70.00'),
            sort_order=1,
        )
        Attendance.objects.create(student=self.student_alpha, session=self.session, status=AttendanceStatus.BOOKED)
        Attendance.objects.create(student=self.student_beta, session=self.session, status=AttendanceStatus.CHECKED_IN)
        StudentExerciseMax.objects.create(
            student=self.student_alpha,
            exercise_slug='deadlift',
            exercise_label='Deadlift',
            one_rep_max_kg=Decimal('100.00'),
        )
        StudentWorkoutView.objects.create(
            student=self.student_alpha,
            workout=workout,
            first_viewed_at=timezone.now(),
            last_viewed_at=timezone.now(),
            view_count=1,
        )
        StudentWorkoutView.objects.create(
            student=self.student_beta,
            workout=workout,
            first_viewed_at=timezone.now(),
            last_viewed_at=timezone.now(),
            view_count=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=workout,
            version=2,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD com RM publicado',
                'coach_notes': 'Treino de forca guiado por percentual.',
                'status': 'published',
                'version': 2,
                'approval_reason_summary': 'Aprovado sem ressalvas',
                'blocks': [
                    {
                        'sort_order': 1,
                        'title': 'Forca principal',
                        'kind': 'strength',
                        'kind_label': 'Forca',
                        'notes': '',
                        'movements': [
                            {
                                'sort_order': 1,
                                'movement_slug': 'deadlift',
                                'movement_label': 'Deadlift',
                                'sets': 5,
                                'reps': 3,
                                'load_type': WorkoutLoadType.PERCENTAGE_OF_RM,
                                'load_value': '70.00',
                                'notes': '',
                            }
                        ],
                    }
                ],
            },
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-publication-history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Prontidao de RM x consumo real')
        self.assertContains(response, 'RM pronto 1/2 (50%)')
        self.assertContains(response, 'Aberturas prontas 1/2 (50%)')
        self.assertContains(response, 'Movimentos dependentes de RM: Deadlift')
        self.assertContains(response, 'Sem RM completo: Aluno Beta.')
        self.assertContains(response, 'Gap de RM nas aberturas 1')
        self.assertContains(response, 'Coletar RM antes da proxima aula semelhante')
        self.assertContains(
            response,
            'O sinal mostra que o treino pediu uma chave que parte da turma ainda nao tinha; melhor medir antes ou simplificar a prescricao.',
        )
        self.assertContains(response, 'href="#rm-gap-queue"')
        self.assertContains(response, 'Alunos sem RM para movimentos criticos')
        self.assertContains(response, 'Aluno Beta')
        self.assertContains(response, 'Deadlift')
        self.assertContains(
            response,
            reverse('workout-student-rm-quick-edit', args=[workout.id, self.student_beta.id, 'deadlift']),
        )

    def test_manager_can_mark_rm_gap_as_requested(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD com gap de RM',
            coach_notes='Treino de forca guiado por percentual.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.manager,
            approved_at=timezone.now(),
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Forca principal',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('75.00'),
            sort_order=1,
        )
        Attendance.objects.create(student=self.student_beta, session=self.session, status=AttendanceStatus.BOOKED)
        self.login_as_manager()

        response = self.client.post(
            reverse('workout-rm-gap-action', args=[workout.id]),
            data={
                'student_id': self.student_beta.id,
                'exercise_slug': 'deadlift',
                'exercise_label': 'Deadlift',
                'status': 'requested',
                'note': 'Recepcao vai pedir o RM antes da aula das 18h.',
                'next': reverse('workout-publication-history'),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        action = SessionWorkoutRmGapAction.objects.get(workout=workout, student=self.student_beta, exercise_slug='deadlift')
        self.assertEqual(action.status, WorkoutRmGapActionStatus.REQUESTED)
        self.assertEqual(action.note, 'Recepcao vai pedir o RM antes da aula das 18h.')
        self.assertContains(response, 'RM solicitado registrado para Aluno Beta.')

    def test_manager_cannot_mark_rm_as_collected_without_registered_rm(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD com gap de RM',
            coach_notes='Treino de forca guiado por percentual.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.manager,
            approved_at=timezone.now(),
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Forca principal',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('75.00'),
            sort_order=1,
        )
        Attendance.objects.create(student=self.student_beta, session=self.session, status=AttendanceStatus.BOOKED)
        self.login_as_manager()

        response = self.client.post(
            reverse('workout-rm-gap-action', args=[workout.id]),
            data={
                'student_id': self.student_beta.id,
                'exercise_slug': 'deadlift',
                'exercise_label': 'Deadlift',
                'status': 'collected',
                'note': 'Coach disse que ja mediu.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            SessionWorkoutRmGapAction.objects.filter(workout=workout, student=self.student_beta, exercise_slug='deadlift').exists()
        )
        self.assertContains(response, 'Nao marque RM coletado sem registrar o RM real do aluno primeiro.')

    def test_manager_can_open_quick_rm_edit_and_save_rm(self):
        workout = SessionWorkout.objects.create(
            session=self.session,
            title='WOD com atalho de RM',
            coach_notes='Treino de forca guiado por percentual.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.manager,
            approved_at=timezone.now(),
        )
        block = SessionWorkoutBlock.objects.create(
            workout=workout,
            title='Forca principal',
            kind='strength',
            sort_order=1,
        )
        SessionWorkoutMovement.objects.create(
            block=block,
            movement_slug='deadlift',
            movement_label='Deadlift',
            sets=5,
            reps=3,
            load_type=WorkoutLoadType.PERCENTAGE_OF_RM,
            load_value=Decimal('75.00'),
            sort_order=1,
        )
        Attendance.objects.create(student=self.student_beta, session=self.session, status=AttendanceStatus.BOOKED)
        self.login_as_manager()
        url = reverse('workout-student-rm-quick-edit', args=[workout.id, self.student_beta.id, 'deadlift'])

        response = self.client.get(f'{url}?label=Deadlift')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aluno Beta')
        self.assertContains(response, 'Deadlift')
        self.assertContains(response, 'Salvar RM e fechar gap')

        response = self.client.post(
            url,
            data={
                'exercise_label': 'Deadlift',
                'one_rep_max_kg': '105.00',
                'notes': 'Medido na janela operacional da board.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        rm_record = StudentExerciseMax.objects.get(student=self.student_beta, exercise_slug='deadlift')
        self.assertEqual(rm_record.one_rep_max_kg, Decimal('105.00'))
        self.assertEqual(rm_record.notes, 'Medido na janela operacional da board.')
        gap_action = SessionWorkoutRmGapAction.objects.get(workout=workout, student=self.student_beta, exercise_slug='deadlift')
        self.assertEqual(gap_action.status, WorkoutRmGapActionStatus.COLLECTED)
        self.assertContains(response, 'RM de Deadlift salvo para Aluno Beta.')
