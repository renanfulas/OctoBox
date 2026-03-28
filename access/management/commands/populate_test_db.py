from datetime import timedelta
from decimal import Decimal
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from students.models import Student


class Command(BaseCommand):
    help = 'Povoa o banco com massa de dados realista para testes de integridade e performance.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scale',
            type=str,
            default='test',
            choices=['test', 'load'],
            help='Escala da massa: test (rápida) ou load (mais pesada).',
        )
        parser.add_argument(
            '--records',
            type=int,
            default=None,
            help='Quantidade aproximada de alunos a gerar. Sobrescreve a escala quando informado.',
        )

    def handle(self, *args, **options):
        scale = options['scale']
        requested_records = options['records']

        counts = {
            'students': 80,
            'sessions': 18,
        }
        if scale == 'load':
            counts = {
                'students': 1000,
                'sessions': 120,
            }
        if requested_records:
            counts['students'] = max(requested_records, 1)
            counts['sessions'] = max(requested_records // 8, 12)

        self.stdout.write(self.style.SUCCESS(f"[OK] Iniciando massa de teste ({counts['students']} alunos / {counts['sessions']} aulas)."))

        with transaction.atomic():
            owner_group, _ = Group.objects.get_or_create(name='Owner')
            user_model = get_user_model()
            owner_user, created = user_model.objects.get_or_create(
                username='perf_owner',
                defaults={
                    'email': 'perf_owner@example.com',
                    'is_staff': True,
                    'is_superuser': True,
                },
            )
            if created:
                owner_user.set_password('password123')
                owner_user.save()
            owner_user.groups.add(owner_group)

            monthly_plan, _ = MembershipPlan.objects.get_or_create(
                name='Cross Prime',
                defaults={
                    'price': Decimal('289.90'),
                    'billing_cycle': 'monthly',
                    'sessions_per_week': 3,
                    'description': 'Plano base para massa de teste.',
                    'active': True,
                },
            )
            premium_plan, _ = MembershipPlan.objects.get_or_create(
                name='Cross Black',
                defaults={
                    'price': Decimal('349.90'),
                    'billing_cycle': 'monthly',
                    'sessions_per_week': 5,
                    'description': 'Plano premium para massa de teste.',
                    'active': True,
                },
            )
            plans = [monthly_plan, premium_plan]

            today = timezone.localdate()
            student_count = 0
            for index in range(counts['students']):
                student, created = Student.objects.get_or_create(
                    phone=f'55119{index:08d}',
                    defaults={
                        'full_name': f'Aluno Performance {index:04d}',
                        'email': f'perf-{index:04d}@example.com',
                        'status': 'active',
                    },
                )
                if not created:
                    continue

                plan = plans[index % len(plans)]
                enrollment = Enrollment.objects.create(
                    student=student,
                    plan=plan,
                    start_date=today - timedelta(days=index % 90),
                    status=EnrollmentStatus.ACTIVE,
                )
                Payment.objects.create(
                    student=student,
                    enrollment=enrollment,
                    due_date=today - timedelta(days=index % 15),
                    amount=plan.price,
                    status=PaymentStatus.PAID if index % 4 else PaymentStatus.OVERDUE,
                    method=PaymentMethod.PIX if index % 2 else PaymentMethod.CREDIT_CARD,
                    reference=f'PERF-{index:04d}',
                )
                student_count += 1

            all_students = list(Student.objects.order_by('id')[:counts['students']])
            session_count = 0
            for index in range(counts['sessions']):
                session = ClassSession.objects.create(
                    title=f'WOD Performance {index:03d}',
                    coach=owner_user,
                    scheduled_at=timezone.now() + timedelta(days=(index % 14) - 7, hours=index % 5),
                    duration_minutes=60,
                    capacity=20,
                    status=SessionStatus.SCHEDULED if index % 5 else SessionStatus.OPEN,
                )
                session_count += 1

                attendance_sample = all_students[index::max(counts['sessions'] // 6, 1)][: min(12, len(all_students))]
                Attendance.objects.bulk_create(
                    [
                        Attendance(
                            student=student,
                            session=session,
                            status=AttendanceStatus.CHECKED_IN if random.randint(0, 1) else AttendanceStatus.BOOKED,
                        )
                        for student in attendance_sample
                    ],
                    ignore_conflicts=True,
                )

        self.stdout.write(self.style.SUCCESS(f"[OK] Massa concluída: {student_count} alunos novos e {session_count} aulas novas."))
