from datetime import timedelta
from decimal import Decimal
import random
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from operations.models import Attendance, AttendanceStatus, ClassSession, SessionStatus
from students.models import Student


@contextmanager
def _tenant_population_context(*, schema_name, box_created, connection, call_command, schema_context):
    from django.core.management.base import CommandError
    from control.tenant_write_fence import (
        TenantFenceTargetMissing,
        TenantWritesFrozen,
        tenant_write_guard,
    )

    try:
        with tenant_write_guard(schema_name):
            quoted_schema = connection.ops.quote_name(schema_name)
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS {quoted_schema}')
            if box_created:
                call_command('migrate_schemas', schema=schema_name, verbosity=0, interactive=False)
            with schema_context(schema_name):
                yield
    except TenantWritesFrozen as exc:
        raise CommandError(
            f'Box {schema_name} está congelado; a população de dados foi recusada.'
        ) from exc
    except TenantFenceTargetMissing as exc:
        raise CommandError(str(exc)) from exc


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

        # Sprint 2: provisionar tenant de teste antes de popular dados.
        # Modelos manipulados aqui (Student, ClassSession, Enrollment, Payment,
        # MembershipPlan, Attendance) sao TENANT_APPS — so existem em schemas
        # box_xxx, nunca em public. Usa o mesmo slug 'test' do conftest.py para
        # que a suite pytest encontre os dados no schema esperado.
        from django.conf import settings
        if 'django_tenants' in settings.INSTALLED_APPS:
            from django.core.management import call_command
            from django.db import connection
            from django_tenants.utils import schema_context
            from control.models import Box

            test_slug = 'test'
            test_schema = f'box_{test_slug}'

            box = Box.objects.filter(slug=test_slug).first()
            box_created = box is None
            if box_created:
                tenant_owner, _ = get_user_model().objects.get_or_create(
                    username='__perf_tenant_owner__',
                    defaults={'email': '__perf_tenant__@example.test'},
                )
                box, box_created = Box.objects.get_or_create(
                    slug=test_slug,
                    defaults={
                        'schema_name': test_schema,
                        'display_name': 'Performance Test Tenant',
                        'status': Box.Status.ACTIVE,
                        'owner_user': tenant_owner,
                    },
                )
            if box.schema_name != test_schema:
                raise CommandError(
                    f'O box de performance deve usar {test_schema}; encontrado {box.schema_name}.'
                )

            context_manager = _tenant_population_context(
                schema_name=test_schema,
                box_created=box_created,
                connection=connection,
                call_command=call_command,
                schema_context=schema_context,
            )
        else:
            # SQLite fallback (test.py removeu django_tenants). Roda em public.
            import contextlib
            context_manager = contextlib.nullcontext()

        with context_manager, transaction.atomic():
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
                            status=AttendanceStatus.CHECKED_IN if random.randint(0, 1) else AttendanceStatus.BOOKED,  # nosec B311 - fixture randomness only
                        )
                        for student in attendance_sample
                    ],
                    ignore_conflicts=True,
                )

        self.stdout.write(self.style.SUCCESS(f"[OK] Massa concluída: {student_count} alunos novos e {session_count} aulas novas."))
