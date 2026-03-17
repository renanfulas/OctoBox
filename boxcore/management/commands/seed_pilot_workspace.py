"""
ARQUIVO: comando interno para semear um workspace piloto com massa ficticia coerente.

POR QUE ELE EXISTE:
- Prepara um cenario realista para validar Recepcao, Financeiro, Dashboard e grade de aulas sem depender de dados reais.

O QUE ESTE ARQUIVO FAZ:
1. Cria ou atualiza planos ficticios padronizados.
2. Vincula matriculas e cobrancas a alunos ja existentes.
3. Gera grade ficticia de aulas com presencas coerentes.
4. Mantem a seed idempotente para permitir reexecucao sem duplicar registros.

PONTOS CRITICOS:
- A seed reaproveita alunos existentes; ela nao deve sobrescrever dados estruturais fora do proprio escopo ficticio.
- Referencias, nomes e notas foram desenhados para permitir nova execucao sem duplicacao.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from finance.model_definitions import BillingCycle
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from students.models import Student, StudentStatus


DEMO_TAG = '[seed-pilot-workspace]'
PLAN_PREFIX = 'Piloto '
PAYMENT_REFERENCE_PREFIX = 'PILOTO-'


class Command(BaseCommand):
    help = 'Gera planos, matriculas, pagamentos, aulas e presencas ficticias para validar o workspace piloto.'

    def handle(self, *args, **options):
        students = list(Student.objects.order_by('full_name', 'id'))
        if len(students) < 8:
            raise CommandError('A seed precisa de pelo menos 8 alunos cadastrados para montar um cenario util.')

        today = timezone.localdate()
        coach_pool = list(get_user_model().objects.order_by('id')[:3])

        with transaction.atomic():
            plans = self._seed_plans()
            selected_students = self._select_students(students)
            enrollments = self._seed_enrollments(selected_students, plans, today)
            payments = self._seed_payments(selected_students, enrollments, today)
            sessions = self._seed_sessions(today, coach_pool)
            attendances = self._seed_attendances(selected_students, sessions, today)

        self.stdout.write(self.style.SUCCESS('Workspace piloto ficticio preparado com sucesso.'))
        self.stdout.write(f'Planos preparados: {len(plans)}')
        self.stdout.write(f'Matriculas preparadas: {len(enrollments)}')
        self.stdout.write(f'Pagamentos preparados: {len(payments)}')
        self.stdout.write(f'Aulas preparadas: {len(sessions)}')
        self.stdout.write(f'Presencas preparadas: {len(attendances)}')

    def _select_students(self, students):
        # Prioriza ativos e pausados para a operacao parecer natural, mas ainda reaproveita a base ja carregada.
        prioritized = sorted(
            students,
            key=lambda student: (
                student.status not in {StudentStatus.ACTIVE, StudentStatus.PAUSED},
                student.full_name,
                student.id,
            ),
        )
        return prioritized[:12]

    def _seed_plans(self):
        plan_blueprints = [
            {
                'name': f'{PLAN_PREFIX}Mensal 3x',
                'price': Decimal('239.90'),
                'billing_cycle': BillingCycle.MONTHLY,
                'sessions_per_week': 3,
                'description': 'Plano ficticio para validar venda, matricula e cobranca recorrente no fluxo piloto.',
                'active': True,
            },
            {
                'name': f'{PLAN_PREFIX}Unlimited',
                'price': Decimal('289.90'),
                'billing_cycle': BillingCycle.MONTHLY,
                'sessions_per_week': 7,
                'description': 'Plano ficticio para carteira premium e comparacao de mix comercial.',
                'active': True,
            },
            {
                'name': f'{PLAN_PREFIX}Kids 2x',
                'price': Decimal('199.90'),
                'billing_cycle': BillingCycle.MONTHLY,
                'sessions_per_week': 2,
                'description': 'Plano ficticio para reforcar leitura de portfolio com oferta complementar.',
                'active': True,
            },
        ]

        plans = []
        for blueprint in plan_blueprints:
            plan, _ = MembershipPlan.objects.update_or_create(
                name=blueprint['name'],
                defaults=blueprint,
            )
            plans.append(plan)
        return plans

    def _seed_enrollments(self, students, plans, today):
        enrollments = {}
        for index, student in enumerate(students[:10]):
            plan = plans[index % len(plans)]
            if index < 6:
                status = EnrollmentStatus.ACTIVE
                start_date = today - timedelta(days=45 - (index * 3))
                end_date = None
            elif index < 8:
                status = EnrollmentStatus.PENDING
                start_date = today - timedelta(days=12 - index)
                end_date = None
            elif index == 8:
                status = EnrollmentStatus.EXPIRED
                start_date = today - timedelta(days=95)
                end_date = today - timedelta(days=5)
            else:
                status = EnrollmentStatus.CANCELED
                start_date = today - timedelta(days=120)
                end_date = today - timedelta(days=18)

            enrollment, _ = Enrollment.objects.update_or_create(
                student=student,
                plan=plan,
                notes=f'{DEMO_TAG} Matricula ficticia preparada para validar carteira e cobranca do piloto.',
                defaults={
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': status,
                },
            )
            enrollments[student.id] = enrollment
        return enrollments

    def _seed_payments(self, students, enrollments, today):
        payment_blueprints = [
            {'student_index': 0, 'offset_days': -18, 'status': PaymentStatus.PAID, 'method': PaymentMethod.PIX, 'amount': Decimal('239.90'), 'label': 'fev'},
            {'student_index': 0, 'offset_days': -3, 'status': PaymentStatus.OVERDUE, 'method': PaymentMethod.PIX, 'amount': Decimal('239.90'), 'label': 'mar'},
            {'student_index': 1, 'offset_days': -14, 'status': PaymentStatus.PAID, 'method': PaymentMethod.CREDIT_CARD, 'amount': Decimal('289.90'), 'label': 'fev'},
            {'student_index': 1, 'offset_days': 0, 'status': PaymentStatus.PENDING, 'method': PaymentMethod.CREDIT_CARD, 'amount': Decimal('289.90'), 'label': 'mar'},
            {'student_index': 2, 'offset_days': -7, 'status': PaymentStatus.OVERDUE, 'method': PaymentMethod.DEBIT_CARD, 'amount': Decimal('199.90'), 'label': 'mar'},
            {'student_index': 2, 'offset_days': 12, 'status': PaymentStatus.PENDING, 'method': PaymentMethod.DEBIT_CARD, 'amount': Decimal('199.90'), 'label': 'abr'},
            {'student_index': 3, 'offset_days': -1, 'status': PaymentStatus.OVERDUE, 'method': PaymentMethod.PIX, 'amount': Decimal('239.90'), 'label': 'mar'},
            {'student_index': 4, 'offset_days': 2, 'status': PaymentStatus.PENDING, 'method': PaymentMethod.TRANSFER, 'amount': Decimal('289.90'), 'label': 'mar'},
            {'student_index': 5, 'offset_days': 5, 'status': PaymentStatus.PENDING, 'method': PaymentMethod.PIX, 'amount': Decimal('239.90'), 'label': 'mar'},
            {'student_index': 6, 'offset_days': -22, 'status': PaymentStatus.PAID, 'method': PaymentMethod.CASH, 'amount': Decimal('199.90'), 'label': 'fev'},
            {'student_index': 6, 'offset_days': -4, 'status': PaymentStatus.OVERDUE, 'method': PaymentMethod.CASH, 'amount': Decimal('199.90'), 'label': 'mar'},
            {'student_index': 7, 'offset_days': 8, 'status': PaymentStatus.PENDING, 'method': PaymentMethod.BANK_SLIP, 'amount': Decimal('289.90'), 'label': 'abr'},
            {'student_index': 8, 'offset_days': -35, 'status': PaymentStatus.PAID, 'method': PaymentMethod.PIX, 'amount': Decimal('239.90'), 'label': 'jan'},
            {'student_index': 9, 'offset_days': -10, 'status': PaymentStatus.CANCELED, 'method': PaymentMethod.PIX, 'amount': Decimal('289.90'), 'label': 'mar'},
            {'student_index': 10, 'offset_days': -6, 'status': PaymentStatus.OVERDUE, 'method': PaymentMethod.OTHER, 'amount': Decimal('149.90'), 'label': 'avulso'},
            {'student_index': 11, 'offset_days': -2, 'status': PaymentStatus.PENDING, 'method': PaymentMethod.PIX, 'amount': Decimal('119.90'), 'label': 'experimental'},
        ]

        payments = []
        for blueprint in payment_blueprints:
            student = students[blueprint['student_index']]
            due_date = today + timedelta(days=blueprint['offset_days'])
            enrollment = enrollments.get(student.id) if blueprint['student_index'] < 10 else None
            reference = f"{PAYMENT_REFERENCE_PREFIX}{student.id}-{blueprint['label']}-{due_date.strftime('%Y%m%d')}"
            billing_group = f'piloto-{student.id}-{blueprint["label"]}'
            paid_at = None
            if blueprint['status'] == PaymentStatus.PAID:
                paid_at = timezone.make_aware(
                    datetime.combine(due_date + timedelta(days=1), time(hour=10, minute=15)),
                    timezone.get_current_timezone(),
                )

            payment, _ = Payment.objects.update_or_create(
                reference=reference,
                defaults={
                    'student': student,
                    'enrollment': enrollment,
                    'due_date': due_date,
                    'paid_at': paid_at,
                    'amount': blueprint['amount'],
                    'status': blueprint['status'],
                    'method': blueprint['method'],
                    'billing_group': billing_group,
                    'installment_number': 1,
                    'installment_total': 1,
                    'notes': f'{DEMO_TAG} Cobranca ficticia para validar fila curta da Recepcao e leitura do Financeiro.',
                },
            )
            payments.append(payment)
        return payments

    def _seed_sessions(self, today, coach_pool):
        session_blueprints = [
            {'title': 'Cross 06h', 'day_offset': -2, 'time': time(hour=6), 'duration': 60, 'capacity': 14, 'status': SessionStatus.COMPLETED},
            {'title': 'Cross 18h30', 'day_offset': -1, 'time': time(hour=18, minute=30), 'duration': 60, 'capacity': 18, 'status': SessionStatus.COMPLETED},
            {'title': 'Cross 07h', 'day_offset': 0, 'time': time(hour=7), 'duration': 60, 'capacity': 16, 'status': SessionStatus.SCHEDULED},
            {'title': 'Mobility 12h30', 'day_offset': 0, 'time': time(hour=12, minute=30), 'duration': 45, 'capacity': 10, 'status': SessionStatus.SCHEDULED},
            {'title': 'Cross 18h', 'day_offset': 0, 'time': time(hour=18), 'duration': 60, 'capacity': 20, 'status': SessionStatus.SCHEDULED},
            {'title': 'Cross 19h15', 'day_offset': 1, 'time': time(hour=19, minute=15), 'duration': 60, 'capacity': 20, 'status': SessionStatus.SCHEDULED},
            {'title': 'Gymnastics 07h', 'day_offset': 2, 'time': time(hour=7), 'duration': 60, 'capacity': 12, 'status': SessionStatus.SCHEDULED},
            {'title': 'Cross 18h', 'day_offset': 2, 'time': time(hour=18), 'duration': 60, 'capacity': 20, 'status': SessionStatus.SCHEDULED},
            {'title': 'Kids 17h', 'day_offset': 3, 'time': time(hour=17), 'duration': 50, 'capacity': 12, 'status': SessionStatus.SCHEDULED},
            {'title': 'Open Box 20h', 'day_offset': 4, 'time': time(hour=20), 'duration': 90, 'capacity': 16, 'status': SessionStatus.OPEN},
            {'title': 'Cross 09h', 'day_offset': 5, 'time': time(hour=9), 'duration': 60, 'capacity': 18, 'status': SessionStatus.SCHEDULED},
            {'title': 'Cross 10h30', 'day_offset': 6, 'time': time(hour=10, minute=30), 'duration': 60, 'capacity': 18, 'status': SessionStatus.SCHEDULED},
        ]

        sessions = []
        for index, blueprint in enumerate(session_blueprints):
            scheduled_date = today + timedelta(days=blueprint['day_offset'])
            scheduled_at = timezone.make_aware(
                datetime.combine(scheduled_date, blueprint['time']),
                timezone.get_current_timezone(),
            )
            coach = coach_pool[index % len(coach_pool)] if coach_pool else None
            session, _ = ClassSession.objects.update_or_create(
                title=blueprint['title'],
                scheduled_at=scheduled_at,
                defaults={
                    'coach': coach,
                    'duration_minutes': blueprint['duration'],
                    'capacity': blueprint['capacity'],
                    'status': blueprint['status'],
                    'notes': f'{DEMO_TAG} Aula ficticia criada para validar leitura de grade e rotina do coach.',
                },
            )
            sessions.append(session)
        return sessions

    def _seed_attendances(self, students, sessions, today):
        attendance_blueprints = {
            0: [(0, AttendanceStatus.CHECKED_OUT), (1, AttendanceStatus.CHECKED_OUT), (2, AttendanceStatus.ABSENT), (3, AttendanceStatus.CHECKED_OUT), (4, AttendanceStatus.CHECKED_OUT)],
            1: [(0, AttendanceStatus.CHECKED_OUT), (2, AttendanceStatus.CHECKED_OUT), (5, AttendanceStatus.ABSENT), (6, AttendanceStatus.CHECKED_OUT), (7, AttendanceStatus.CHECKED_OUT), (8, AttendanceStatus.CHECKED_OUT)],
            2: [(0, AttendanceStatus.CHECKED_OUT), (1, AttendanceStatus.CHECKED_OUT), (3, AttendanceStatus.CHECKED_OUT), (4, AttendanceStatus.BOOKED), (9, AttendanceStatus.BOOKED)],
            3: [(2, AttendanceStatus.BOOKED), (5, AttendanceStatus.BOOKED), (10, AttendanceStatus.BOOKED)],
            4: [(0, AttendanceStatus.BOOKED), (1, AttendanceStatus.BOOKED), (2, AttendanceStatus.BOOKED), (6, AttendanceStatus.BOOKED), (7, AttendanceStatus.BOOKED), (11, AttendanceStatus.BOOKED)],
            5: [(3, AttendanceStatus.BOOKED), (4, AttendanceStatus.BOOKED), (8, AttendanceStatus.BOOKED), (9, AttendanceStatus.BOOKED)],
            6: [(0, AttendanceStatus.BOOKED), (5, AttendanceStatus.BOOKED), (6, AttendanceStatus.BOOKED)],
            7: [(1, AttendanceStatus.BOOKED), (2, AttendanceStatus.BOOKED), (7, AttendanceStatus.BOOKED), (10, AttendanceStatus.BOOKED)],
            8: [(8, AttendanceStatus.BOOKED), (9, AttendanceStatus.BOOKED), (11, AttendanceStatus.BOOKED)],
            9: [(0, AttendanceStatus.BOOKED), (3, AttendanceStatus.BOOKED), (5, AttendanceStatus.BOOKED), (6, AttendanceStatus.BOOKED), (7, AttendanceStatus.BOOKED)],
            10: [(1, AttendanceStatus.BOOKED), (4, AttendanceStatus.BOOKED), (8, AttendanceStatus.BOOKED), (10, AttendanceStatus.BOOKED)],
            11: [(2, AttendanceStatus.BOOKED), (6, AttendanceStatus.BOOKED), (9, AttendanceStatus.BOOKED)],
        }

        attendances = []
        for session_index, slots in attendance_blueprints.items():
            session = sessions[session_index]
            for student_index, status in slots:
                student = students[student_index]
                check_in_at = None
                check_out_at = None
                if status in {AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT}:
                    check_in_at = session.scheduled_at + timedelta(minutes=5)
                if status == AttendanceStatus.CHECKED_OUT:
                    check_out_at = session.scheduled_at + timedelta(minutes=session.duration_minutes)

                attendance, _ = Attendance.objects.update_or_create(
                    student=student,
                    session=session,
                    defaults={
                        'status': status,
                        'reservation_source': 'seed-pilot-workspace',
                        'check_in_at': check_in_at,
                        'check_out_at': check_out_at,
                        'notes': (
                            f'{DEMO_TAG} Falta simulada para leitura de risco e retencao.'
                            if status == AttendanceStatus.ABSENT else
                            f'{DEMO_TAG} Presenca ficticia para dar volume real a grade do piloto.'
                        ),
                    },
                )
                attendances.append(attendance)
        return attendances