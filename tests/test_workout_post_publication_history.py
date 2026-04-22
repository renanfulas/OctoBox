from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from student_app.models import (
    SessionWorkout,
    SessionWorkoutFollowUpAction,
    SessionWorkoutOperationalMemory,
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
    StudentWorkoutView,
)
from tests.workout_test_support import WorkoutFlowBaseTestCase


class WorkoutPostPublicationHistoryTests(WorkoutFlowBaseTestCase):
    def test_approval_board_renders_post_publication_executive_history(self):
        first_published = SessionWorkout.objects.create(
            session=self.session,
            title='WOD publicado urgente',
            coach_notes='Saiu no curto prazo.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.manager,
            approved_at=timezone.now(),
            version=2,
        )
        SessionWorkoutRevision.objects.create(
            workout=first_published,
            version=2,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD publicado urgente',
                'coach_notes': 'Saiu no curto prazo.',
                'status': 'published',
                'version': 2,
                'approval_reason_category': 'operational_urgency',
                'approval_reason_label': 'Aprovado por urgencia operacional',
                'approval_reason_summary': 'Aprovado por urgencia operacional: Aula extra aberta no fim do dia.',
                'approved_with_sensitive_confirmation': True,
                'blocks': [],
            },
        )
        Attendance.objects.create(
            student=self.student_alpha,
            session=self.session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )
        Attendance.objects.create(
            student=self.student_beta,
            session=self.session,
            status=AttendanceStatus.CHECKED_IN,
            reservation_source='student_app',
        )
        StudentWorkoutView.objects.create(
            student=self.student_alpha,
            workout=first_published,
            first_viewed_at=timezone.now(),
            last_viewed_at=timezone.now(),
            view_count=2,
        )
        SessionWorkoutOperationalMemory.objects.create(
            workout=first_published,
            kind='reception_owned',
            note='Recepcao assumiu a turma com atraso curto.',
            created_by=self.manager,
        )
        SessionWorkoutOperationalMemory.objects.create(
            workout=first_published,
            kind='whatsapp_sent',
            note='WhatsApp disparado para relembrar abertura do WOD.',
            created_by=self.manager,
        )

        verbal_session = ClassSession.objects.create(
            title='Cross 09h',
            coach=self.coach,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=16,
        )
        second_published = SessionWorkout.objects.create(
            session=verbal_session,
            title='WOD com alinhamento',
            coach_notes='Saiu com ajuste verbal.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.manager,
            approved_at=timezone.now(),
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=second_published,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'WOD com alinhamento',
                'coach_notes': 'Saiu com ajuste verbal.',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'verbal_alignment',
                'approval_reason_label': 'Aprovado com alinhamento verbal',
                'approval_reason_summary': 'Aprovado com alinhamento verbal: Coach alinhou a troca do finisher.',
                'blocks': [],
            },
        )
        Attendance.objects.create(
            student=self.student_alpha,
            session=verbal_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )
        SessionWorkoutOperationalMemory.objects.create(
            workout=second_published,
            kind='coach_aligned',
            note='Coach alinhado para conduzir o bloco final.',
            created_by=self.manager,
        )

        plain_session = ClassSession.objects.create(
            title='Cross 11h',
            coach=self.coach,
            scheduled_at=timezone.now() + timedelta(days=2),
            duration_minutes=60,
            capacity=16,
        )
        third_published = SessionWorkout.objects.create(
            session=plain_session,
            title='WOD sem motivo extra',
            coach_notes='Fluxo padrao.',
            status=SessionWorkoutStatus.PUBLISHED,
            created_by=self.coach,
            approved_by=self.owner,
            approved_at=timezone.now(),
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=third_published,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.owner,
            snapshot={
                'title': 'WOD sem motivo extra',
                'coach_notes': 'Fluxo padrao.',
                'status': 'published',
                'version': 1,
                'blocks': [],
            },
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-publication-history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Historico executivo do que foi ao ar')
        self.assertContains(response, 'Aprovado por urgencia operacional')
        self.assertContains(response, 'Aprovado com alinhamento verbal')
        self.assertContains(response, 'Sem motivo extra')
        self.assertContains(response, 'Mudanca sensivel confirmada')
        self.assertContains(response, 'Aula extra aberta no fim do dia.')
        self.assertContains(response, 'Coach alinhou a troca do finisher.')
        self.assertContains(response, 'Publicado por manager-wod')
        self.assertContains(response, 'Abriram WOD 1')
        self.assertContains(response, 'Turma 2/16')
        self.assertContains(response, 'Check-in 1')
        self.assertContains(response, 'Memoria operacional agregada')
        self.assertContains(response, '1 casos que precisaram de recepcao')
        self.assertContains(response, '1 casos absorvidos com coach')
        self.assertContains(response, '1 casos que dependeram de whatsapp')
        self.assertContains(response, 'Alavanca x fechamento executivo')
        self.assertContains(response, 'Recepcao assumiu absorveu 0 de 1 caso(s) observados nesta janela.')
        self.assertContains(response, 'Coach alinhado absorveu 1 de 1 caso(s) observados nesta janela.')
        self.assertContains(response, 'WhatsApp disparado absorveu 0 de 1 caso(s) observados nesta janela.')
        self.assertContains(response, 'Boa alavanca de absorcao')
        self.assertContains(response, 'Taxa 100%')
        self.assertContains(response, 'Tendencia curta da alavanca')
        self.assertContains(response, 'Base curta')
        self.assertContains(response, 'Janela anterior')
        self.assertContains(response, 'Janela recente')

    def test_approval_board_filters_post_publication_history_by_reason(self):
        urgent_workout = SessionWorkout.objects.create(
            session=self.session,
            title='Urgente',
            status=SessionWorkoutStatus.PUBLISHED,
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=urgent_workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'Urgente',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'operational_urgency',
                'approval_reason_label': 'Aprovado por urgencia operacional',
                'blocks': [],
            },
        )
        aligned_session = ClassSession.objects.create(
            title='Cross 12h',
            coach=self.coach,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=12,
            status=SessionStatus.SCHEDULED,
        )
        aligned_workout = SessionWorkout.objects.create(
            session=aligned_session,
            title='Alinhado',
            status=SessionWorkoutStatus.PUBLISHED,
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=aligned_workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'Alinhado',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'verbal_alignment',
                'approval_reason_label': 'Aprovado com alinhamento verbal',
                'blocks': [],
            },
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-publication-history'), data={'published_reason': 'operational_urgency'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Urgente')
        self.assertNotContains(response, 'Alinhado')

    def test_approval_board_surfaces_post_publication_operational_alerts(self):
        urgent_session = ClassSession.objects.create(
            title='Cross 06h30',
            coach=self.coach,
            scheduled_at=timezone.now() + timedelta(minutes=40),
            duration_minutes=60,
            capacity=14,
            status=SessionStatus.SCHEDULED,
        )
        urgent_workout = SessionWorkout.objects.create(
            session=urgent_session,
            title='Urgente sem leitura',
            status=SessionWorkoutStatus.PUBLISHED,
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=urgent_workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'Urgente sem leitura',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'operational_urgency',
                'approval_reason_label': 'Aprovado por urgencia operacional',
                'blocks': [],
            },
        )
        Attendance.objects.create(
            student=self.student_alpha,
            session=urgent_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )
        Attendance.objects.create(
            student=self.student_beta,
            session=urgent_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )

        running_session = ClassSession.objects.create(
            title='Cross 07h15',
            coach=self.coach,
            scheduled_at=timezone.now() - timedelta(minutes=15),
            duration_minutes=60,
            capacity=14,
            status=SessionStatus.OPEN,
        )
        running_workout = SessionWorkout.objects.create(
            session=running_session,
            title='Aula rodando',
            status=SessionWorkoutStatus.PUBLISHED,
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=running_workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'Aula rodando',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'without_concerns',
                'approval_reason_label': 'Aprovado sem ressalvas',
                'blocks': [],
            },
        )
        Attendance.objects.create(
            student=self.student_alpha,
            session=running_session,
            status=AttendanceStatus.CHECKED_IN,
            reservation_source='student_app',
        )
        self.login_as_manager()

        response = self.client.get(reverse('workout-publication-history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pendencia real')
        self.assertContains(response, 'pendencia(s) real(is)')
        self.assertContains(response, 'escalonamento(s) curto(s)')
        self.assertContains(response, 'intervencao forte')
        self.assertContains(response, 'Intervencao forte')
        self.assertContains(response, 'Escalonar agora no chao da operacao')
        self.assertContains(response, 'alerta(s) critico(s)')
        self.assertContains(response, 'WOD urgente publicado sem nenhuma abertura no app do aluno')
        self.assertContains(response, 'Aula comeca em breve e poucos alunos abriram o WOD')
        self.assertContains(response, 'Ja ha aluno em aula sem leitura equivalente do WOD no app')
        self.assertContains(response, 'Alerta operacional')
        self.assertContains(response, 'Acao sugerida')
        self.assertContains(response, 'Reforcar chamada no WhatsApp')
        self.assertContains(response, 'Avisar coach')
        self.assertContains(response, 'Acompanhar operacao agora')

    def test_manager_can_register_follow_up_result_for_suggested_action(self):
        urgent_session = ClassSession.objects.create(
            title='Cross 06h45',
            coach=self.coach,
            scheduled_at=timezone.now() + timedelta(minutes=35),
            duration_minutes=60,
            capacity=14,
            status=SessionStatus.SCHEDULED,
        )
        urgent_workout = SessionWorkout.objects.create(
            session=urgent_session,
            title='Urgente com retorno operacional',
            status=SessionWorkoutStatus.PUBLISHED,
            version=1,
        )
        SessionWorkoutRevision.objects.create(
            workout=urgent_workout,
            version=1,
            event=SessionWorkoutRevisionEvent.PUBLISHED,
            created_by=self.manager,
            snapshot={
                'title': 'Urgente com retorno operacional',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'operational_urgency',
                'approval_reason_label': 'Aprovado por urgencia operacional',
                'blocks': [],
            },
        )
        Attendance.objects.create(
            student=self.student_alpha,
            session=urgent_session,
            status=AttendanceStatus.BOOKED,
            reservation_source='student_app',
        )
        self.login_as_manager()

        response = self.client.post(
            reverse('workout-follow-up-action', args=[urgent_workout.id]),
            data={
                'action_key': 'whatsapp-reinforce',
                'action_label': 'Reforcar chamada no WhatsApp',
                'result_status': 'completed',
                'outcome_note': 'Recepcao reforcou no grupo e a turma confirmou leitura.',
                'next': reverse('workout-publication-history'),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        follow_up = SessionWorkoutFollowUpAction.objects.get(workout=urgent_workout, action_key='whatsapp-reinforce')
        self.assertEqual(follow_up.status, 'completed')
        self.assertEqual(follow_up.resolved_by, self.manager)
        self.assertEqual(follow_up.outcome_note, 'Recepcao reforcou no grupo e a turma confirmou leitura.')
        self.assertEqual(follow_up.baseline_metrics.get('viewer_count'), 0)
        self.assertContains(response, 'acao(oes) com resultado')
        self.assertContains(response, 'Resolvido')
        self.assertContains(response, 'Recepcao reforcou no grupo e a turma confirmou leitura.')
        self.assertTrue(
            AuditEvent.objects.filter(action='session_workout_follow_up_registered', target_id=str(urgent_workout.id)).exists()
        )

        StudentWorkoutView.objects.create(
            student=self.student_alpha,
            workout=urgent_workout,
            first_viewed_at=timezone.now(),
            last_viewed_at=timezone.now(),
            view_count=1,
        )

        response = self.client.get(reverse('workout-publication-history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alerta(s) resolvido(s)')
        self.assertContains(response, 'Aberturas 0-&gt;1 | Check-in 0-&gt;0 | Turma 1-&gt;1')
        self.assertContains(response, 'Aberturas +1 | Check-in +0')

        response = self.client.post(
            reverse('workout-operational-memory-create', args=[urgent_workout.id]),
            data={
                'kind': 'coach_aligned',
                'note': 'Coach alinhado para reforcar a abertura do WOD no aquecimento.',
                'next': reverse('workout-publication-history'),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        memory = SessionWorkoutOperationalMemory.objects.get(workout=urgent_workout, kind='coach_aligned')
        self.assertEqual(memory.created_by, self.manager)
        self.assertEqual(memory.note, 'Coach alinhado para reforcar a abertura do WOD no aquecimento.')
        self.assertContains(response, 'Memoria operacional curta')
        self.assertContains(response, 'Coach alinhado')
        self.assertContains(response, 'Coach alinhado para reforcar a abertura do WOD no aquecimento.')
        self.assertTrue(
            AuditEvent.objects.filter(action='session_workout_operational_memory_created', target_id=str(urgent_workout.id)).exists()
        )
