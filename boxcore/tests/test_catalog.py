"""
ARQUIVO: testes das paginas visuais de catalogo.

POR QUE ELE EXISTE:
- Protege a camada leve de alunos, grade e operacao comercial contra regressao.

O QUE ESTE ARQUIVO FAZ:
1. Testa renderizacao da pagina de alunos e da grade de aulas.
2. Testa criacao e edicao de aluno pelo fluxo leve.
3. Testa conversao de intake, geracao de cobranca e mudanca de plano.
4. Testa acoes diretas de pagamento e matricula.
5. Testa exportacoes de alunos e o registro operacional de comunicacao por WhatsApp.

PONTOS CRITICOS:
- Se estes testes quebrarem, a operacao diaria perde o fluxo principal fora do admin.
"""

from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auditing.models import AuditEvent
from catalog.forms import ClassScheduleRecurringForm, StudentQuickForm
from communications.models import StudentIntake, WhatsAppContact, WhatsAppMessageLog
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, ClassSession, SessionStatus
from operations.session_snapshots import serialize_class_session
from students.models import Student


class CatalogViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_superuser(
            username='catalog-owner',
            email='catalog-owner@example.com',
            password='senha-forte-123',
        )
        self.valid_cpf = '052.484.340-68'
        self.student = Student.objects.create(full_name='Bruna Costa', phone='5511988888888')
        self.plan = MembershipPlan.objects.create(name='Cross Prime', price='289.90')
        self.plan_plus = MembershipPlan.objects.create(name='Cross Black', price='349.90')
        self.enrollment = Enrollment.objects.create(student=self.student, plan=self.plan)
        Payment.objects.create(student=self.student, enrollment=self.enrollment, due_date=timezone.localdate(), amount='289.90')
        self.intake = StudentIntake.objects.create(full_name='Lead Bruna', phone='5511970000000', email='lead@example.com')
        ClassSession.objects.create(title='WOD 18h', scheduled_at=timezone.now())
        self.coach = self.user

    def _student_quick_form_data(self, **overrides):
        data = {
            'full_name': 'Mateus Oliveira',
            'phone': '5511966666666',
            'status': 'active',
            'email': '',
            'gender': '',
            'birth_date': '',
            'health_issue_status': '',
            'cpf': '',
            'acquisition_source': 'instagram',
            'acquisition_source_detail': '',
            'notes': '',
            'selected_plan': '',
            'enrollment_status': 'pending',
            'payment_method': PaymentMethod.PIX,
            'confirm_payment_now': 'False',
            'payment_due_date': '',
            'payment_reference': '',
            'initial_payment_amount': '',
            'billing_strategy': 'single',
            'installment_total': 1,
            'recurrence_cycles': 3,
            'intake_record': '',
        }
        data.update(overrides)
        return data

    def test_student_directory_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alunos')
        self.assertContains(response, 'Bruna Costa')
        self.assertContains(response, 'Novo aluno')
        self.assertContains(response, '1 alunos')
        self.assertNotContains(response, 'fonts.googleapis.com')
        self.assertNotContains(response, 'fonts.gstatic.com')
        self.assertContains(response, 'js/core/search-loader.js')
        self.assertNotContains(response, 'js/core/search.js')
        self.assertContains(response, 'js/core/dynamic-visuals-loader.js')
        self.assertNotContains(response, 'js/core/dynamic-visuals.js')
        self.assertContains(response, 'js/core/shell.js')
        self.assertContains(response, 'js/core/shell-interactions.js')
        self.assertContains(response, 'js/core/shell-effects-loader.js')
        self.assertNotContains(response, 'js/core/shell-effects.js')
        self.assertIn('css/catalog/students/scene.css', response.context['current_page_assets']['css'])
        self.assertIn('css/catalog/students/intake-directory.css', response.context['current_page_assets']['css'])
        self.assertEqual(response.context['current_page_assets']['deferred_css'], ['bundle:css/catalog/students-deferred.css'])
        self.assertEqual(response.context['current_page_assets']['enhancement_css'], ['bundle:css/catalog/students-enhancement.css'])
        self.assertEqual(response.context['current_page_assets']['deferred_css_runtime'], ['css/catalog/students-deferred.css'])
        self.assertEqual(response.context['current_page_assets']['enhancement_css_runtime'], ['css/catalog/students-enhancement.css'])
        self.assertNotIn('css/catalog/shared.css', response.context['current_page_assets']['css'])
        self.assertNotIn('css/catalog/students.css', response.context['current_page_assets']['css'])

    def test_student_directory_treats_expired_pending_payment_as_overdue(self):
        overdue_student = Student.objects.create(full_name='Aline Atrasada', phone='5511977777777')
        overdue_enrollment = Enrollment.objects.create(student=overdue_student, plan=self.plan)
        Payment.objects.create(
            student=overdue_student,
            enrollment=overdue_enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=1),
            amount='289.90',
            status=PaymentStatus.PENDING,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory'))
        page = response.context['student_directory_page']
        overdue_kpi = next(
            card
            for card in page['data']['interactive_kpis']
            if card['student_filter'] == 'overdue'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(overdue_kpi['display_value'], 1)
        self.assertContains(response, 'data-student-name="Aline Atrasada"')
        self.assertContains(response, 'data-payment-status="overdue"')
        self.assertContains(response, 'Atrasado')

        filtered_response = self.client.get(reverse('student-directory'), data={'payment_status': PaymentStatus.OVERDUE})
        self.assertEqual(filtered_response.status_code, 200)
        self.assertContains(filtered_response, 'Aline Atrasada')
        self.assertNotContains(filtered_response, 'Bruna Costa')
        self.assertEqual(filtered_response.context['student_directory_page']['data']['total_students'], 1)

    def test_student_directory_pills_and_kpis_redirect_when_full_index_is_missing(self):
        script = (
            Path(__file__).resolve().parents[2]
            / 'static'
            / 'js'
            / 'pages'
            / 'students'
            / 'student-directory.js'
        ).read_text(encoding='utf-8')

        self.assertIn("nextParams.set('payment_status', 'overdue');", script)
        self.assertIn("nextParams.set('created_window', '30d');", script)
        self.assertIn('if (hasServerScopedFilters() || !hasFullDirectorySearchIndex)', script)
        self.assertIn('if (!hasFullDirectorySearchIndex) {', script)
        self.assertIn('window.location.assign(buildDirectoryFilterUrl(nextFilter));', script)

    def test_class_grid_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('class-grid'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Grade de aulas')
        self.assertContains(response, 'WOD 18h')
        self.assertContains(response, 'Calendário das próximas duas semanas')
        self.assertContains(response, 'Expandir mês')
        self.assertContains(response, 'Agenda de Hoje')
        self.assertContains(response, 'Planejador recorrente')

    def test_class_grid_can_create_recurring_schedule(self):
        self.client.force_login(self.user)
        days_ahead = (7 - timezone.localdate().weekday()) % 7 or 7
        start_date = timezone.localdate() + timezone.timedelta(days=days_ahead)
        end_date = start_date + timezone.timedelta(days=13)

        response = self.client.post(
            reverse('class-grid'),
            data={
                'title': 'WOD 07h',
                'coach': '',
                'start_date': str(start_date),
                'end_date': str(end_date),
                'weekdays': ['0', '2'],
                'start_time': '07:00',
                'sequence_count': 0,
                'duration_minutes': 60,
                'capacity': 18,
                'status': 'scheduled',
                'notes': 'Abrir check-in 15 minutos antes.',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        created_sessions = ClassSession.objects.filter(title='WOD 07h').order_by('scheduled_at')
        self.assertEqual(created_sessions.count(), 4)
        self.assertEqual(created_sessions.first().capacity, 18)
        self.assertTrue(AuditEvent.objects.filter(action='class_schedule_recurring_created').exists())

    def test_class_grid_can_create_recurring_schedule_with_sequence(self):
        self.client.force_login(self.user)
        days_ahead = (7 - timezone.localdate().weekday()) % 7 or 7
        start_date = timezone.localdate() + timezone.timedelta(days=days_ahead)

        response = self.client.post(
            reverse('class-grid'),
            data={
                'title': 'WOD Sequencia 07h',
                'coach': '',
                'start_date': start_date.strftime('%d/%m/%y'),
                'end_date': start_date.strftime('%d/%m/%y'),
                'weekdays': [str(start_date.weekday())],
                'start_time': '07:00',
                'sequence_count': 3,
                'duration_minutes': 60,
                'capacity': 18,
                'status': 'scheduled',
                'notes': 'Teste de sequencia.',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        created_sessions = list(ClassSession.objects.filter(title='WOD Sequencia 07h').order_by('scheduled_at'))
        self.assertEqual(len(created_sessions), 4)
        self.assertEqual([timezone.localtime(item.scheduled_at).strftime('%H:%M') for item in created_sessions], ['07:00', '08:00', '09:00', '10:00'])

    def test_class_grid_can_create_weekend_rotation_inside_monthly_window(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'planner',
                'title': 'Rodizio Weekend',
                'coach': self.coach.id,
                'start_date': '2026-04-01',
                'end_date': '2026-04-30',
                'anchor_date': '2026-04-11',
                'interval_days': '14',
                'weekdays': ['5', '6'],
                'start_time': '09:00',
                'sequence_count': 0,
                'duration_minutes': 60,
                'capacity': 18,
                'status': 'scheduled',
                'notes': '',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        created_sessions = list(ClassSession.objects.filter(title='Rodizio Weekend').order_by('scheduled_at'))
        self.assertEqual(len(created_sessions), 4)
        self.assertEqual(
            [timezone.localtime(item.scheduled_at).date() for item in created_sessions],
            [
                timezone.datetime(2026, 4, 11).date(),
                timezone.datetime(2026, 4, 12).date(),
                timezone.datetime(2026, 4, 25).date(),
                timezone.datetime(2026, 4, 26).date(),
            ],
        )
        self.assertTrue(all(item.coach_id == self.coach.id for item in created_sessions))

    def test_class_schedule_form_normalizes_single_digit_hour(self):
        start_date = timezone.localdate() + timezone.timedelta(days=1)
        form = ClassScheduleRecurringForm(
            data={
                'title': 'WOD 08h',
                'coach': '',
                'start_date': start_date.strftime('%d/%m/%y'),
                'end_date': start_date.strftime('%d/%m/%y'),
                'weekdays': [str(start_date.weekday())],
                'start_time': '8',
                'sequence_count': 0,
                'duration_minutes': 60,
                'capacity': 18,
                'status': SessionStatus.SCHEDULED,
                'notes': '',
                'skip_existing': 'on',
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['start_time'].strftime('%H:%M'), '08:00')

    def test_class_session_snapshot_uses_second_name_when_first_is_generic_coach_title(self):
        titled_coach = get_user_model().objects.create_user(
            username='coach.ana',
            first_name='Coach',
            last_name='Ana',
            password='senha-forte-123',
        )
        session = ClassSession.objects.create(
            title='Open 09h',
            coach=titled_coach,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            duration_minutes=60,
            capacity=18,
            status=SessionStatus.SCHEDULED,
        )
        session.occupied_slots = 0

        snapshot = serialize_class_session(session, now=timezone.localtime())

        self.assertEqual(snapshot['coach_display_name'], 'Ana')

    def test_class_grid_allows_exact_daily_limit_in_single_batch(self):
        self.client.force_login(self.user)
        days_ahead = (7 - timezone.localdate().weekday()) % 7 or 7
        start_date = timezone.localdate() + timezone.timedelta(days=days_ahead)

        for index in range(6):
            ClassSession.objects.create(
                title=f'Base diaria {index}',
                scheduled_at=timezone.make_aware(
                    timezone.datetime.combine(start_date, timezone.datetime.strptime(f'{6 + index:02d}:00', '%H:%M').time()),
                    timezone.get_current_timezone(),
                ),
                duration_minutes=60,
                capacity=18,
                status=SessionStatus.SCHEDULED,
            )

        response = self.client.post(
            reverse('class-grid'),
            data={
                'title': 'WOD Limite Diario Exato',
                'coach': '',
                'start_date': start_date.strftime('%d/%m/%y'),
                'end_date': start_date.strftime('%d/%m/%y'),
                'weekdays': [str(start_date.weekday())],
                'start_time': '12:00',
                'sequence_count': 5,
                'duration_minutes': 60,
                'capacity': 18,
                'status': 'scheduled',
                'notes': 'Teste do limite diario exato.',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ClassSession.objects.filter(title='WOD Limite Diario Exato').count(), 6)
        self.assertEqual(ClassSession.objects.filter(scheduled_at__date=start_date).count(), 12)

    def test_class_grid_allows_large_weekly_batch_below_limit(self):
        self.client.force_login(self.user)
        days_ahead = (7 - timezone.localdate().weekday()) % 7 or 7
        start_date = timezone.localdate() + timezone.timedelta(days=days_ahead)
        end_date = start_date + timezone.timedelta(days=6)

        response = self.client.post(
            reverse('class-grid'),
            data={
                'title': 'WOD Limite Semanal Exato',
                'coach': '',
                'start_date': start_date.strftime('%d/%m/%y'),
                'end_date': end_date.strftime('%d/%m/%y'),
                'weekdays': [str(index) for index in range(7)],
                'start_time': '06:00',
                'sequence_count': 5,
                'duration_minutes': 60,
                'capacity': 18,
                'status': 'scheduled',
                'notes': 'Teste de lote semanal sem bloqueio precoce.',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ClassSession.objects.filter(title='WOD Limite Semanal Exato').count(), 42)

    def test_class_grid_allows_exact_monthly_limit_in_single_batch(self):
        self.client.force_login(self.user)
        start_date = timezone.datetime(2026, 4, 1).date()
        end_date = timezone.datetime(2026, 4, 30).date()

        response = self.client.post(
            reverse('class-grid'),
            data={
                'title': 'WOD Limite Mensal Exato',
                'coach': '',
                'start_date': start_date.strftime('%d/%m/%y'),
                'end_date': end_date.strftime('%d/%m/%y'),
                'weekdays': [str(index) for index in range(7)],
                'start_time': '06:00',
                'sequence_count': 4,
                'duration_minutes': 60,
                'capacity': 18,
                'status': 'scheduled',
                'notes': 'Teste do limite mensal exato.',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClassSession.objects.filter(title='WOD Limite Mensal Exato').count(), 0)
        self.assertContains(response, 'Limite mensal atingido')

    def test_class_grid_can_filter_by_coach_and_status(self):
        self.client.force_login(self.user)
        target_month = timezone.localdate().strftime('%Y-%m')
        ClassSession.objects.create(
            title='Funcional 06h',
            coach=self.coach,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            status=SessionStatus.OPEN,
        )
        ClassSession.objects.create(
            title='Yoga 20h',
            scheduled_at=timezone.now() + timezone.timedelta(days=2),
            status=SessionStatus.CANCELED,
        )

        response = self.client.get(
            reverse('class-grid'),
            data={
                'reference_month': target_month,
                'coach': self.coach.id,
                'status': SessionStatus.OPEN,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Funcional 06h')
        self.assertNotContains(response, 'Yoga 20h')

    def test_class_grid_can_update_and_delete_session(self):
        self.client.force_login(self.user)
        session = ClassSession.objects.get(title='WOD 18h')
        secondary_session = ClassSession.objects.create(
            title='Funcional 06h',
            coach=self.coach,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            status=SessionStatus.OPEN,
        )

        update_response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': session.id,
                'return_query': '',
                'title': 'WOD 19h',
                'coach': self.coach.id,
                'start_time': '19:00',
                'duration_minutes': 75,
                'capacity': 22,
                'status': SessionStatus.SCHEDULED,
                'notes': 'Turma ajustada para horario nobre.',
            },
        )

        self.assertEqual(update_response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.title, 'WOD 19h')
        self.assertEqual(session.status, SessionStatus.SCHEDULED)
        self.assertEqual(timezone.localtime(session.scheduled_at).time().strftime('%H:%M'), '19:00')

        delete_response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-action',
                'action': 'delete-session',
                'session_id': secondary_session.id,
                'return_query': '',
            },
        )

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(ClassSession.objects.filter(pk=secondary_session.id).exists())
        self.assertTrue(AuditEvent.objects.filter(action='class_session_quick_updated').exists())
        self.assertTrue(AuditEvent.objects.filter(action='class_session_quick_deleted').exists())

    def test_class_grid_quick_edit_renders_start_time_without_seconds(self):
        self.client.force_login(self.user)
        session = ClassSession.objects.create(
            title='Cross 06h',
            coach=self.coach,
            scheduled_at=timezone.make_aware(datetime(2026, 3, 20, 6, 0), timezone.get_current_timezone()),
            status=SessionStatus.SCHEDULED,
        )

        response = self.client.get(reverse('class-grid'), data={'edit_session': session.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="start_time" value="06:00"', html=False)
        self.assertNotContains(response, 'name="start_time" value="06:00:00"', html=False)

    def test_class_grid_can_update_completed_session_without_reopening_it(self):
        self.client.force_login(self.user)
        session = ClassSession.objects.create(
            title='Cross 06h',
            coach=self.coach,
            scheduled_at=timezone.make_aware(datetime(2026, 3, 20, 6, 0), timezone.get_current_timezone()),
            status=SessionStatus.COMPLETED,
            notes='Sessao concluida seed.',
        )

        response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': session.id,
                'return_query': '',
                'title': 'Cross 06h',
                'coach': self.coach.id,
                'start_time': '06:00',
                'duration_minutes': 60,
                'capacity': 14,
                'status': SessionStatus.COMPLETED,
                'notes': 'Sessao concluida ajustada sem reabrir status.',
            },
        )

        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(session.notes, 'Sessao concluida ajustada sem reabrir status.')

    def test_class_grid_quick_edit_allows_notes_roundtrip_on_completed_session(self):
        self.client.force_login(self.user)
        session = ClassSession.objects.create(
            title='Mobility 08h',
            coach=self.coach,
            scheduled_at=timezone.make_aware(datetime(2026, 3, 21, 8, 0), timezone.get_current_timezone()),
            status=SessionStatus.COMPLETED,
            notes='',
        )

        update_response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': session.id,
                'return_query': '',
                'title': 'Mobility 08h',
                'coach': self.coach.id,
                'start_time': '08:00',
                'duration_minutes': 60,
                'capacity': 14,
                'status': SessionStatus.COMPLETED,
                'notes': 'Observacao QA ida e volta.',
            },
        )

        self.assertEqual(update_response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(session.notes, 'Observacao QA ida e volta.')

        clear_response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': session.id,
                'return_query': '',
                'title': 'Mobility 08h',
                'coach': self.coach.id,
                'start_time': '08:00',
                'duration_minutes': 60,
                'capacity': 14,
                'status': SessionStatus.COMPLETED,
                'notes': '',
            },
        )

        self.assertEqual(clear_response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(session.notes, '')

    def test_class_grid_quick_edit_allows_schedule_roundtrip_on_completed_session(self):
        self.client.force_login(self.user)
        session = ClassSession.objects.create(
            title='Engine 18h',
            coach=self.coach,
            scheduled_at=timezone.make_aware(datetime(2026, 3, 21, 18, 0), timezone.get_current_timezone()),
            duration_minutes=60,
            capacity=16,
            status=SessionStatus.COMPLETED,
        )

        update_response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': session.id,
                'return_query': '',
                'title': 'Engine 18h reforcada',
                'coach': self.coach.id,
                'start_time': '18:30',
                'duration_minutes': 45,
                'capacity': 12,
                'status': SessionStatus.COMPLETED,
                'notes': 'Ajuste operacional temporario.',
            },
        )

        self.assertEqual(update_response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(timezone.localtime(session.scheduled_at).strftime('%H:%M'), '18:30')
        self.assertEqual(session.duration_minutes, 45)
        self.assertEqual(session.capacity, 12)
        self.assertEqual(session.title, 'Engine 18h reforcada')

        restore_response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': session.id,
                'return_query': '',
                'title': 'Engine 18h',
                'coach': self.coach.id,
                'start_time': '18:00',
                'duration_minutes': 60,
                'capacity': 16,
                'status': SessionStatus.COMPLETED,
                'notes': '',
            },
        )

        self.assertEqual(restore_response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)
        self.assertEqual(timezone.localtime(session.scheduled_at).strftime('%H:%M'), '18:00')
        self.assertEqual(session.duration_minutes, 60)
        self.assertEqual(session.capacity, 16)
        self.assertEqual(session.title, 'Engine 18h')
        self.assertEqual(session.notes, '')

    def test_class_grid_blocks_delete_when_session_has_attendance(self):
        self.client.force_login(self.user)
        protected_session = ClassSession.objects.create(
            title='Funcional 07h',
            coach=self.coach,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            status=SessionStatus.OPEN,
        )
        Attendance.objects.create(student=self.student, session=protected_session)

        response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-action',
                'action': 'delete-session',
                'session_id': protected_session.id,
                'return_query': '',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ClassSession.objects.filter(pk=protected_session.id).exists())
        self.assertContains(response, 'Nao exclua uma aula que ja tenha reservas ou presencas.')

    def test_class_grid_blocks_reopening_completed_session_in_quick_edit(self):
        self.client.force_login(self.user)
        completed_session = ClassSession.objects.create(
            title='Recovery 21h',
            coach=self.coach,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            status=SessionStatus.COMPLETED,
        )

        response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'session-edit',
                'session_id': completed_session.id,
                'return_query': '',
                'title': 'Recovery 21h ajustada',
                'coach': self.coach.id,
                'start_time': '21:00',
                'duration_minutes': 60,
                'capacity': 20,
                'status': SessionStatus.SCHEDULED,
                'notes': 'Tentativa de reabrir aula concluida.',
            },
        )

        self.assertEqual(response.status_code, 200)
        completed_session.refresh_from_db()
        self.assertEqual(completed_session.status, SessionStatus.COMPLETED)
        self.assertContains(response, 'Aulas concluidas nao podem voltar para agendada por esta edicao rapida.')

    def test_class_grid_marks_today_session_as_in_progress_during_runtime(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        session = ClassSession.objects.create(
            title='WOD 10h',
            coach=self.coach,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('10:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            status=SessionStatus.SCHEDULED,
        )
        original_localtime = timezone.localtime
        simulated_now = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.strptime('10:00', '%H:%M').time()),
            timezone.get_current_timezone(),
        )

        with patch(
            'boxcore.catalog.class_grid_queries.timezone.localtime',
            side_effect=lambda value=None, *args, **kwargs: simulated_now if value is None else original_localtime(value, *args, **kwargs),
        ):
            response = self.client.get(reverse('class-grid'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Em andamento')
        self.assertContains(response, 'Entradas encerradas enquanto a aula estiver em andamento.')
        self.assertContains(response, 'Fechado')
        self.assertContains(response, 'class-occupancy-closed')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.SCHEDULED)

    def test_class_grid_uses_occupancy_threshold_colors_and_lotada_label(self):
        self.client.force_login(self.user)
        full_session = ClassSession.objects.create(
            title='WOD Lotado 18h',
            coach=self.coach,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            duration_minutes=60,
            capacity=10,
            status=SessionStatus.SCHEDULED,
        )

        for index in range(10):
            student = Student.objects.create(full_name=f'Aluno Lotado {index}', phone=f'5511977700{index:03d}')
            Attendance.objects.create(student=student, session=full_session)

        response = self.client.get(reverse('class-grid'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lotada')
        self.assertContains(response, 'class-occupancy-critical')

    def test_class_grid_auto_completes_today_session_after_end_time(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        session = ClassSession.objects.create(
            title='WOD 10h final',
            coach=self.coach,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(today, timezone.datetime.strptime('10:00', '%H:%M').time()),
                timezone.get_current_timezone(),
            ),
            duration_minutes=60,
            status=SessionStatus.SCHEDULED,
        )
        original_localtime = timezone.localtime
        simulated_now = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.strptime('11:01', '%H:%M').time()),
            timezone.get_current_timezone(),
        )

        with patch(
            'boxcore.catalog.class_grid_queries.timezone.localtime',
            side_effect=lambda value=None, *args, **kwargs: simulated_now if value is None else original_localtime(value, *args, **kwargs),
        ):
            response = self.client.get(reverse('class-grid'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Finalizada')
        self.assertContains(response, 'Fechado')
        self.assertContains(response, 'Entradas encerradas porque a aula ja foi finalizada.')
        session.refresh_from_db()
        self.assertEqual(session.status, SessionStatus.COMPLETED)

    def test_class_grid_blocks_daily_limit(self):
        self.client.force_login(self.user)
        days_ahead = (7 - timezone.localdate().weekday()) % 7 or 7
        start_date = timezone.localdate() + timezone.timedelta(days=days_ahead)
        for index in range(12):
            ClassSession.objects.create(
                title=f'Extra {index}',
                scheduled_at=timezone.make_aware(
                    timezone.datetime.combine(start_date, timezone.datetime.strptime(f'{6 + index % 12:02d}:00', '%H:%M').time()),
                    timezone.get_current_timezone(),
                ),
            )

        response = self.client.post(
            reverse('class-grid'),
            data={
                'form_kind': 'planner',
                'return_query': '',
                'title': 'WOD limite',
                'coach': '',
                'start_date': str(start_date),
                'end_date': str(start_date),
                'weekdays': [str(start_date.weekday())],
                'start_time': '21:00',
                'sequence_count': 0,
                'duration_minutes': 60,
                'capacity': 18,
                'status': SessionStatus.SCHEDULED,
                'notes': '',
                'skip_existing': 'on',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClassSession.objects.filter(title='WOD limite').exists())
        self.assertContains(response, 'Limite diario atingido')

    def test_student_quick_create_flow_creates_student(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('student-quick-create'),
            data={
                'full_name': 'Mateus Oliveira',
                'phone': '5511977777777',
                'status': 'active',
                'email': 'mateus@example.com',
                'gender': 'male',
                'birth_date': '',
                'health_issue_status': 'no',
                'cpf': self.valid_cpf,
                'acquisition_source': 'instagram',
                'acquisition_source_detail': 'story da unidade',
                'notes': '',
                'selected_plan': self.plan.id,
                'enrollment_status': 'active',
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': 'True',
                'payment_due_date': str(timezone.localdate()),
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 3,
                'intake_record': self.intake.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Student.objects.filter(full_name='Mateus Oliveira').exists())
        created_student = Student.objects.get(full_name='Mateus Oliveira')
        self.assertEqual(created_student.cpf, self.valid_cpf)
        self.assertEqual(created_student.acquisition_source, 'instagram')
        self.assertEqual(created_student.acquisition_source_detail, 'story da unidade')
        self.assertEqual(created_student.resolved_acquisition_source, 'instagram')
        self.assertEqual(created_student.source_resolution_method, 'intake_auto')
        self.assertEqual(created_student.source_resolution_reason, 'operational_only')
        self.assertEqual(created_student.source_confidence, 'high')
        self.assertFalse(created_student.source_conflict_flag)
        self.assertIsNotNone(created_student.source_captured_at)
        self.assertEqual(created_student.source_captured_by_id, self.user.id)
        self.assertTrue(created_student.enrollments.filter(plan=self.plan, status='active').exists())
        created_payment = created_student.payments.latest('created_at')
        self.assertEqual(created_payment.method, PaymentMethod.PIX)
        self.assertEqual(created_payment.status, PaymentStatus.PAID)
        self.intake.refresh_from_db()
        self.assertEqual(self.intake.linked_student, created_student)
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_created').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_payment_created').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_intake_converted').exists())

    def test_student_quick_form_normalizes_phone_and_cpf(self):
        form = StudentQuickForm(
            data={
                'full_name': 'Mateus Oliveira',
                'phone': '(11) 97777-7777',
                'status': 'active',
                'email': '',
                'gender': '',
                'birth_date': '',
                'health_issue_status': '',
                'cpf': self.valid_cpf,
                'acquisition_source': 'instagram',
                'acquisition_source_detail': '',
                'notes': '',
                'selected_plan': '',
                'enrollment_status': 'pending',
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': 'False',
                'payment_due_date': '',
                'payment_reference': '',
                'initial_payment_amount': '',
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 3,
                'intake_record': '',
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['phone'], '11977777777')
        self.assertEqual(form.cleaned_data['cpf'], self.valid_cpf)

    def test_student_quick_form_accepts_compact_birth_date(self):
        form = StudentQuickForm(data=self._student_quick_form_data(birth_date='21111995'))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['birth_date'], date(1995, 11, 21))

    def test_student_quick_form_rejects_invalid_birth_month(self):
        form = StudentQuickForm(data=self._student_quick_form_data(birth_date='21171995'))

        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)

    def test_student_quick_form_rejects_implausible_birth_year(self):
        form = StudentQuickForm(data=self._student_quick_form_data(birth_date='21111800'))

        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)

    def test_student_quick_form_rejects_future_birth_date(self):
        future_birth_date = timezone.localdate() + timezone.timedelta(days=1)
        form = StudentQuickForm(data=self._student_quick_form_data(birth_date=future_birth_date.strftime('%d/%m/%Y')))

        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)

    def test_student_quick_form_blocks_duplicate_phone_after_normalization(self):
        form = StudentQuickForm(
            data={
                'full_name': 'Bruna Costa Duplicada',
                'phone': '(11) 98888-8888',
                'status': 'active',
                'email': '',
                'gender': '',
                'birth_date': '',
                'health_issue_status': '',
                'cpf': '',
                'acquisition_source': 'instagram',
                'acquisition_source_detail': '',
                'notes': '',
                'selected_plan': '',
                'enrollment_status': 'pending',
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': 'False',
                'payment_due_date': '',
                'payment_reference': '',
                'initial_payment_amount': '',
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 3,
                'intake_record': '',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        self.assertIn('WhatsApp', form.errors['phone'][0])

    def test_student_quick_create_flow_returns_form_error_when_phone_already_exists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('student-quick-create'),
            data={
                'full_name': 'Bruna Costa Duplicada',
                'phone': '(11) 98888-8888',
                'status': 'active',
                'email': '',
                'gender': '',
                'birth_date': '',
                'health_issue_status': '',
                'cpf': '',
                'acquisition_source': 'instagram',
                'acquisition_source_detail': '',
                'notes': '',
                'selected_plan': '',
                'enrollment_status': 'pending',
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': 'False',
                'payment_due_date': '',
                'payment_reference': '',
                'initial_payment_amount': '',
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 3,
                'intake_record': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Já existe um aluno cadastrado com este WhatsApp.')
        self.assertEqual(Student.objects.filter(full_name='Bruna Costa Duplicada').count(), 0)

    def test_student_quick_create_flow_shows_conversational_recovery_guide_when_invalid(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('student-quick-create'),
            data={
                'full_name': 'Mateus Oliveira',
                'phone': '5511977777777',
                'status': 'lead',
                'email': '',
                'gender': '',
                'birth_date': '',
                'health_issue_status': '',
                'cpf': '',
                'acquisition_source': 'instagram',
                'acquisition_source_detail': '',
                'notes': '',
                'selected_plan': self.plan.id,
                'enrollment_status': 'active',
                'payment_method': PaymentMethod.PIX,
                'confirm_payment_now': 'False',
                'payment_due_date': str(timezone.localdate()),
                'billing_strategy': 'single',
                'installment_total': 1,
                'recurrence_cycles': 3,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vamos destravar isso por etapa')
        self.assertContains(response, 'O box separou onde travou para voce corrigir sem cacar erro no formulario inteiro.')
        self.assertContains(response, 'Passo 2: perfil do aluno')
        self.assertContains(response, 'Lead nao pode sair com matricula ativa.')

    def test_student_quick_update_flow_updates_student(self):
        self.client.force_login(self.user)
        student = Student.objects.get(full_name='Bruna Costa')

        response = self.client.post(
            reverse('student-quick-update', args=[student.id]),
            data={
                'full_name': 'Bruna Costa Lima',
                'phone': '5511988888888',
                'email': 'bruna@example.com',
                'status': 'active',
                'gender': 'female',
                'birth_date': '',
                'health_issue_status': 'yes',
                'cpf': '987.654.321-00',
                'notes': 'Lesao antiga no ombro esquerdo.',
                'selected_plan': self.plan_plus.id,
                'enrollment_status': 'active',
                'payment_method': PaymentMethod.CREDIT_CARD,
                'confirm_payment_now': 'False',
                'payment_due_date': str(timezone.localdate()),
                'billing_strategy': 'installments',
                'installment_total': 3,
                'recurrence_cycles': 1,
            },
        )

        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.full_name, 'Bruna Costa Lima')
        self.assertEqual(student.gender, 'female')
        self.assertEqual(student.health_issue_status, 'yes')
        self.assertTrue(student.enrollments.filter(plan=self.plan_plus, status='active').exists())
        self.assertTrue(student.enrollments.filter(plan=self.plan, status='expired').exists())
        self.assertEqual(student.payments.filter(enrollment__plan=self.plan_plus).count(), 3)
        latest_payment = student.payments.filter(enrollment__plan=self.plan_plus).order_by('created_at').first()
        self.assertEqual(latest_payment.method, PaymentMethod.CREDIT_CARD)
        self.assertEqual(latest_payment.status, PaymentStatus.PENDING)
        self.assertTrue(AuditEvent.objects.filter(action='student_quick_updated').exists())
        self.assertTrue(AuditEvent.objects.filter(action='student_plan_changed').exists())

    def test_student_payment_action_marks_payment_as_paid(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()

        response = self.client.post(
            reverse('student-payment-action', args=[self.student.id]),
            data={
                'payment_id': payment.id,
                'amount': payment.amount,
                'due_date': str(payment.due_date),
                'method': payment.method,
                'reference': '',
                'notes': '',
                'action': 'mark-paid',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('#student-financial-overview'))
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)

    def test_student_payment_action_returns_fragments_for_ajax(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()

        response = self.client.post(
            reverse('student-payment-action', args=[self.student.id]),
            data={
                'payment_id': payment.id,
                'amount': payment.amount,
                'due_date': str(payment.due_date),
                'method': payment.method,
                'reference': '',
                'notes': '',
                'action': 'mark-paid',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['selected_payment_id'], payment.id)
        self.assertIn('fragments', body)
        self.assertIn('student-payment-checkout-form', body['fragments']['checkout'])
        self.assertIn('student-financial-kpi-card', body['fragments']['kpis'])
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)

    def test_student_payment_drawer_returns_selected_payment_fragment(self):
        self.client.force_login(self.user)
        newer_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() + timezone.timedelta(days=10),
            amount='319.90',
            status=PaymentStatus.PENDING,
            method=PaymentMethod.CREDIT_CARD,
            reference='ABR-319',
        )

        response = self.client.get(
            reverse('student-payment-drawer', args=[self.student.id, newer_payment.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['selected_payment_id'], newer_payment.id)
        self.assertIn('ABR-319', body['fragments']['checkout'])
        self.assertIn('319', body['fragments']['checkout'])
        self.assertIn('value="{}"'.format(newer_payment.id), body['fragments']['checkout'])

    def test_student_form_financial_ledger_buttons_bind_to_specific_payment_ids(self):
        self.client.force_login(self.user)
        overdue_payment = Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() - timezone.timedelta(days=5),
            amount='309.90',
            status=PaymentStatus.OVERDUE,
            method=PaymentMethod.CASH,
            reference='MAR-309',
        )

        response = self.client.get(reverse('student-quick-update', args=[self.student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-payment-id="{overdue_payment.id}"', html=False)
        self.assertContains(response, 'data-action="edit-payment"', html=False)

    def test_student_payment_action_rejects_invalid_action(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()

        response = self.client.post(
            reverse('student-payment-action', args=[self.student.id]),
            data={
                'payment_id': payment.id,
                'action': 'escalar-invalido',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('#student-financial-overview'))
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PENDING)

    def test_student_enrollment_action_rejects_invalid_action(self):
        self.client.force_login(self.user)
        initial_status = self.enrollment.status

        response = self.client.post(
            reverse('student-enrollment-action', args=[self.student.id]),
            data={
                'enrollment_id': self.enrollment.id,
                'action_date': str(timezone.localdate()),
                'reason': 'Tentativa invalida.',
                'action': 'hack-enrollment',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, initial_status)

    def test_student_directory_uses_operational_payment_status_with_overdue_priority(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()
        payment.status = PaymentStatus.OVERDUE
        payment.save(update_fields=['status', 'updated_at'])
        Payment.objects.create(
            student=self.student,
            enrollment=self.enrollment,
            due_date=timezone.localdate() + timezone.timedelta(days=5),
            amount='289.90',
            status=PaymentStatus.PAID,
        )

        response = self.client.get(reverse('student-directory'))

        self.assertEqual(response.status_code, 200)
        student_row = next(item for item in response.context['students'] if item.id == self.student.id)
        self.assertEqual(student_row.operational_payment_status, PaymentStatus.OVERDUE)

    def test_student_enrollment_action_can_cancel_and_reactivate(self):
        self.client.force_login(self.user)

        cancel_response = self.client.post(
            reverse('student-enrollment-action', args=[self.student.id]),
            data={
                'enrollment_id': self.enrollment.id,
                'action_date': str(timezone.localdate()),
                'reason': 'Mudanca de rotina.',
                'action': 'cancel-enrollment',
            },
        )
        self.assertEqual(cancel_response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.CANCELED)

        reactivate_response = self.client.post(
            reverse('student-enrollment-action', args=[self.student.id]),
            data={
                'enrollment_id': self.enrollment.id,
                'action_date': str(timezone.localdate()),
                'reason': 'Retorno ao box.',
                'action': 'reactivate-enrollment',
            },
        )
        self.assertEqual(reactivate_response.status_code, 302)
        self.assertEqual(self.student.enrollments.filter(status=EnrollmentStatus.ACTIVE).count(), 1)

    def test_student_enrollment_action_returns_fragments_for_ajax(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('student-enrollment-action', args=[self.student.id]),
            data={
                'enrollment_id': self.enrollment.id,
                'action_date': str(timezone.localdate()),
                'reason': 'Mudanca de rotina.',
                'action': 'cancel-enrollment',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'success')
        self.assertIn('fragments', body)
        self.assertIn('student-enrollment-management', body['fragments']['enrollment'])
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.CANCELED)

    def test_student_update_page_shows_financial_overview(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-quick-update', args=[self.student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cobrar agora')
        self.assertContains(response, 'Plano atual')
        self.assertContains(response, 'Dados cadastrais')
        self.assertContains(response, 'Historico de pagamentos')
        self.assertContains(response, 'Salvar perfil')

    def test_student_update_page_renders_date_inputs_in_iso_format(self):
        self.client.force_login(self.user)
        student = Student.objects.get(full_name='Bruna Costa')
        student.birth_date = timezone.datetime(2000, 1, 8).date()
        student.save(update_fields=['birth_date', 'updated_at'])
        enrollment = student.enrollments.select_related('plan').first()
        payment = enrollment.payments.order_by('-due_date', '-created_at').first()

        response = self.client.get(reverse('student-quick-update', args=[student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="birth_date" value="08/01/2000"', html=False)
        self.assertContains(response, f'name="due_date" value="{payment.due_date:%d/%m/%Y}"', html=False)
        self.assertContains(response, f'name="action_date" value="{timezone.localdate():%Y-%m-%d}"', html=False)

    def test_student_directory_can_export_csv(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory-export', args=['csv']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('Bruna Costa', response.content.decode())

    def test_student_directory_can_export_pdf(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('student-directory-export', args=['pdf']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_finance_communication_action_registers_whatsapp_log(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()

        response = self.client.post(
            reverse('finance-communication-action'),
            data={
                'action_kind': 'overdue',
                'student_id': self.student.id,
                'payment_id': payment.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        # Verifica persistência via vínculo direto
        contact = WhatsAppContact.objects.filter(linked_student=self.student).first()
        self.assertIsNotNone(contact)
        self.assertTrue(WhatsAppMessageLog.objects.filter(contact=contact, direction='outbound').exists())
        self.assertTrue(AuditEvent.objects.filter(action='operational_whatsapp_touch_registered').exists())

    def test_finance_communication_action_can_register_and_redirect_to_whatsapp(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()
        response = self.client.post(
            reverse('finance-communication-action'),
            data={
                'action_kind': 'overdue',
                'student_id': self.student.id,
                'payment_id': payment.id,
                'open_in_whatsapp': '1',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('wa.me', response.url)
        # Verifica log via vínculo direto
        self.assertTrue(WhatsAppMessageLog.objects.filter(contact__linked_student=self.student, direction='outbound').exists())
        self.assertTrue(AuditEvent.objects.filter(action='operational_whatsapp_touch_registered').exists())

    def test_finance_communication_action_blocks_same_whatsapp_touch_twice_in_a_day(self):
        self.client.force_login(self.user)
        payment = self.student.payments.first()

        first_response = self.client.post(
            reverse('finance-communication-action'),
            data={
                'action_kind': 'overdue',
                'student_id': self.student.id,
                'payment_id': payment.id,
                'open_in_whatsapp': '1',
            },
        )
        second_response = self.client.post(
            reverse('finance-communication-action'),
            data={
                'action_kind': 'overdue',
                'student_id': self.student.id,
                'payment_id': payment.id,
            },
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        
        # Verifica auditoria de bloqueio (admite qualquer evento de bloqueio no sistema durante o teste)
        self.assertTrue(AuditEvent.objects.filter(action='operational_whatsapp_touch_blocked').exists())
        self.assertEqual(WhatsAppContact.objects.filter(linked_student=self.student).count(), 1)
        self.assertEqual(WhatsAppMessageLog.objects.filter(contact__linked_student=self.student, direction='outbound').count(), 1)
