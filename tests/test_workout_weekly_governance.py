from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from student_app.models import (
    SessionWorkout,
    SessionWorkoutOperationalMemory,
    SessionWorkoutRevision,
    SessionWorkoutRevisionEvent,
    SessionWorkoutStatus,
    WorkoutWeeklyManagementCheckpoint,
)
from tests.workout_test_support import WorkoutFlowBaseTestCase


class WorkoutWeeklyGovernanceTests(WorkoutFlowBaseTestCase):
    def test_approval_board_surfaces_light_management_alert_for_consistent_improvement(self):
        sessions = [
            ClassSession.objects.create(
                title=f'Cross trend {index}',
                coach=self.coach,
                scheduled_at=timezone.now() + timedelta(days=index + 1),
                duration_minutes=60,
                capacity=12,
                status=SessionStatus.SCHEDULED,
            )
            for index in range(4)
        ]

        for index, session in enumerate(sessions):
            workout = SessionWorkout.objects.create(
                session=session,
                title=f'Coach trend {index}',
                status=SessionWorkoutStatus.PUBLISHED,
                version=1,
            )
            snapshot = {
                'title': f'Coach trend {index}',
                'status': 'published',
                'version': 1,
                'approval_reason_category': 'no_reason',
                'blocks': [],
            }
            if index < 2:
                snapshot['approval_reason_category'] = 'operational_urgency'
                snapshot['approval_reason_label'] = 'Aprovado por urgencia operacional'
                Attendance.objects.create(
                    student=self.student_alpha,
                    session=session,
                    status=AttendanceStatus.BOOKED,
                    reservation_source='student_app',
                )
                Attendance.objects.create(
                    student=self.student_beta,
                    session=session,
                    status=AttendanceStatus.BOOKED,
                    reservation_source='student_app',
                )
            SessionWorkoutRevision.objects.create(
                workout=workout,
                version=1,
                event=SessionWorkoutRevisionEvent.PUBLISHED,
                created_by=self.manager,
                snapshot=snapshot,
            )
            SessionWorkoutOperationalMemory.objects.create(
                workout=workout,
                kind='coach_aligned',
                note=f'Coach alinhado caso {index}.',
                created_by=self.manager,
            )

        self.login_as_manager()

        response = self.client.get(reverse('workout-approval-board'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alerta leve de gestao')
        self.assertContains(response, 'Coach alinhado em melhora consistente')
        self.assertContains(response, 'Prioridade executiva')
        self.assertContains(response, 'Olhar em seguida')
        self.assertContains(response, 'Recomendacao executiva curta')
        self.assertContains(response, 'Formalizar coach alinhado como boa pratica do box')
        self.assertContains(response, 'Consolidar nos proximos 7 dias')
        self.assertContains(response, 'Resumo executivo semanal do box')
        self.assertContains(response, 'O melhor sinal de melhora veio de coach alinhado.')
        self.assertContains(response, 'Vale consolidar esse corredor como boa pratica curta do box enquanto o sinal continua forte.')

    def test_manager_can_register_weekly_management_checkpoint(self):
        self.login_as_manager()

        response = self.client.post(
            reverse('workout-weekly-checkpoint-update'),
            data={
                'execution_status': 'in_progress',
                'responsible_role': 'manager',
                'closure_status': 'partial',
                'governance_commitment_status': 'assumed',
                'governance_commitment_note': 'Owner assumiu a decisao e vai cobrar fechamento na proxima semana.',
                'summary_note': 'Manager puxando o ritual semanal e fechando parcialmente a recomendacao.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        checkpoint = WorkoutWeeklyManagementCheckpoint.objects.get()
        self.assertEqual(checkpoint.execution_status, 'in_progress')
        self.assertEqual(checkpoint.responsible_role, 'manager')
        self.assertEqual(checkpoint.closure_status, 'partial')
        self.assertEqual(checkpoint.governance_commitment_status, 'assumed')
        self.assertEqual(checkpoint.updated_by, self.manager)
        self.assertContains(response, 'Checkpoint de gestao da semana')
        self.assertContains(response, 'Historico leve dos checkpoints')
        self.assertContains(response, 'Semana de')
        self.assertContains(response, 'Em andamento')
        self.assertContains(response, 'Parcial')
        self.assertContains(response, 'Assumido')
        self.assertContains(response, 'Manager')
        self.assertTrue(AuditEvent.objects.filter(action='session_workout_weekly_checkpoint_updated').exists())

    def test_weekly_checkpoint_history_surfaces_rhythm_changes(self):
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        WorkoutWeeklyManagementCheckpoint.objects.create(
            week_start=monday,
            execution_status='completed',
            responsible_role='manager',
            closure_status='partial',
            governance_commitment_status='executed',
            governance_commitment_note='Compromisso da governanca foi executado na semana atual.',
            summary_note='Semana atual fechou parcial.',
            updated_by=self.manager,
        )
        WorkoutWeeklyManagementCheckpoint.objects.create(
            week_start=monday - timedelta(days=7),
            execution_status='not_started',
            responsible_role='manager',
            closure_status='partial',
            governance_commitment_status='assumed',
            summary_note='Semana anterior ficou travada no parcial.',
            updated_by=self.manager,
        )
        WorkoutWeeklyManagementCheckpoint.objects.create(
            week_start=monday - timedelta(days=14),
            execution_status='in_progress',
            responsible_role='owner',
            closure_status='partial',
            governance_commitment_status='not_assumed',
            summary_note='Duas semanas atras tambem fechou parcial.',
            updated_by=self.owner,
        )

        self.login_as_manager()

        response = self.client.get(reverse('workout-approval-board'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Maturidade operacional')
        self.assertContains(response, 'Instavel')
        self.assertContains(response, 'Acao de governanca')
        self.assertContains(response, 'Rodar ajuste curto antes de formalizar')
        self.assertContains(response, 'Virada de execucao')
        self.assertContains(response, 'Sequencia parcial')
        self.assertContains(response, 'O checkpoint saiu de nao iniciado para concluido')
        self.assertContains(response, 'Executado')
