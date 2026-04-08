"""
ARQUIVO: comando para semear um box realista da zona sul de Sao Paulo.

POR QUE ELE EXISTE:
- Permite reconstruir rapidamente um ambiente de demonstracao com escala de box real.
- Cria um cenario coerente para validar recepcao, financeiro, grade, dashboard e comunicacao.

O QUE ESTE ARQUIVO FAZ:
1. Cria usuarios operacionais do box e vincula grupos.
2. Gera entre 100 e 200 alunos com mistura realista de status.
3. Monta planos, matriculas, cobrancas, aulas, presencas, intakes e WhatsApp.

PONTOS CRITICOS:
- O comando presume um banco vazio ou previamente descartavel.
- Os dados sao ficticios e nao devem ser misturados com operacao real.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from communications.models import (
    MessageDirection,
    MessageKind,
    StudentIntake,
    WhatsAppContact,
    WhatsAppContactStatus,
    WhatsAppMessageLog,
)
from finance.model_definitions import BillingCycle
from finance.models import Enrollment, EnrollmentStatus, MembershipPlan, Payment, PaymentMethod, PaymentStatus
from onboarding.models import IntakeSource, IntakeStatus
from operations.models import Attendance, AttendanceStatus, BehaviorCategory, BehaviorNote, ClassSession, SessionStatus
from students.models import Student, StudentGender, StudentStatus


SEED_TAG = '[seed-south-sp-box]'
DEFAULT_STUDENT_COUNT = 156
MIN_STUDENT_COUNT = 100
MAX_STUDENT_COUNT = 200
RNG_SEED = 20260407
SCENARIO_STABLE = 'stable'
SCENARIO_CHAOTIC = 'chaotic'

USER_BLUEPRINTS = [
    {
        'username': 'owner_morumbi',
        'email': 'owner@octobox-demo.local',
        'first_name': 'Fernando',
        'last_name': 'Azevedo',
        'group': 'Owner',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'username': 'manager_vila_andrade',
        'email': 'manager@octobox-demo.local',
        'first_name': 'Mayara',
        'last_name': 'Lima',
        'group': 'Manager',
    },
    {
        'username': 'recepcao_santo_amaro',
        'email': 'recepcao@octobox-demo.local',
        'first_name': 'Julia',
        'last_name': 'Santos',
        'group': 'Recepcao',
    },
    {
        'username': 'coach_brooklin',
        'email': 'coach1@octobox-demo.local',
        'first_name': 'Renan',
        'last_name': 'Costa',
        'group': 'Coach',
    },
    {
        'username': 'coach_campo_belo',
        'email': 'coach2@octobox-demo.local',
        'first_name': 'Bruna',
        'last_name': 'Moraes',
        'group': 'Coach',
    },
    {
        'username': 'coach_saude',
        'email': 'coach3@octobox-demo.local',
        'first_name': 'Diego',
        'last_name': 'Rocha',
        'group': 'Coach',
    },
]

FIRST_NAMES = [
    'Ana', 'Beatriz', 'Bruna', 'Camila', 'Carla', 'Carolina', 'Clara', 'Daniela', 'Debora', 'Eduarda',
    'Elaine', 'Fernanda', 'Gabriela', 'Helena', 'Isabela', 'Jaqueline', 'Juliana', 'Karen', 'Larissa',
    'Leticia', 'Luana', 'Mariana', 'Melissa', 'Nathalia', 'Nicole', 'Patricia', 'Priscila', 'Rafaela',
    'Renata', 'Sabrina', 'Sara', 'Tatiane', 'Valentina', 'Vanessa', 'Vitoria', 'Yasmin', 'Adriana',
    'Amanda', 'Bianca', 'Cecilia', 'Aline', 'Alice', 'Barbara', 'Cristina', 'Evelyn', 'Flavia', 'Giovana',
    'Heloisa', 'Ingrid', 'Jessica', 'Luciana', 'Marina', 'Michele', 'Monique', 'Pamela', 'Paula', 'Samira',
    'Thiago', 'Bruno', 'Caio', 'Carlos', 'Danilo', 'Diego', 'Eduardo', 'Felipe', 'Fernando', 'Gabriel',
    'Guilherme', 'Henrique', 'Igor', 'Joao', 'Jonathan', 'Kaique', 'Leonardo', 'Lucas', 'Marcelo', 'Marcos',
    'Matheus', 'Murilo', 'Nicolas', 'Otavio', 'Paulo', 'Pedro', 'Rafael', 'Ricardo', 'Rodrigo', 'Samuel',
    'Thierry', 'Tiago', 'Vinicius', 'Wesley', 'Yuri', 'Alexandre', 'Anderson', 'Arthur', 'Cesar', 'Douglas',
]

LAST_NAMES = [
    'Silva', 'Santos', 'Oliveira', 'Souza', 'Pereira', 'Costa', 'Rodrigues', 'Almeida', 'Nascimento', 'Lima',
    'Araujo', 'Fernandes', 'Carvalho', 'Gomes', 'Martins', 'Rocha', 'Ribeiro', 'Alves', 'Monteiro', 'Mendes',
    'Barbosa', 'Freitas', 'Teixeira', 'Correia', 'Cardoso', 'Moraes', 'Batista', 'Campos', 'Rezende', 'Vieira',
    'Cavalcanti', 'Moreira', 'Castro', 'Melo', 'Peixoto', 'Assis', 'Pinto', 'Leal', 'Borges', 'Dias',
]

NEIGHBORHOODS = [
    'Santo Amaro', 'Morumbi', 'Brooklin', 'Campo Belo', 'Saude', 'Vila Mariana', 'Vila Andrade',
    'Jabaquara', 'Moema', 'Ipiranga', 'Chacara Santo Antonio', 'Campo Grande',
]

PLAN_BLUEPRINTS = [
    {
        'name': 'Essencial 2x',
        'price': Decimal('229.90'),
        'billing_cycle': BillingCycle.MONTHLY,
        'sessions_per_week': 2,
        'description': f'{SEED_TAG} Plano de entrada para alunos com rotina enxuta.',
    },
    {
        'name': 'Performance 3x',
        'price': Decimal('259.90'),
        'billing_cycle': BillingCycle.MONTHLY,
        'sessions_per_week': 3,
        'description': f'{SEED_TAG} Plano principal da carteira com frequencia media.',
    },
    {
        'name': 'Unlimited',
        'price': Decimal('309.90'),
        'billing_cycle': BillingCycle.MONTHLY,
        'sessions_per_week': 7,
        'description': f'{SEED_TAG} Plano premium para alunos de alta frequencia.',
    },
    {
        'name': 'Kids 2x',
        'price': Decimal('199.90'),
        'billing_cycle': BillingCycle.MONTHLY,
        'sessions_per_week': 2,
        'description': f'{SEED_TAG} Oferta complementar para grade infantil.',
    },
]

SESSION_BLUEPRINTS = [
    ('Cross 06h', -1, 6, 0, 60, 18, SessionStatus.COMPLETED),
    ('Cross 07h', 0, 7, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Cross 09h', 0, 9, 0, 60, 16, SessionStatus.SCHEDULED),
    ('Mobility 12h30', 0, 12, 30, 45, 14, SessionStatus.SCHEDULED),
    ('Kids 17h', 0, 17, 0, 50, 14, SessionStatus.SCHEDULED),
    ('Cross 18h', 0, 18, 0, 60, 24, SessionStatus.SCHEDULED),
    ('Cross 19h15', 0, 19, 15, 60, 26, SessionStatus.SCHEDULED),
    ('Open Box 20h30', 0, 20, 30, 90, 20, SessionStatus.OPEN),
    ('Cross 06h', 1, 6, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Cross 07h', 1, 7, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Cross 12h', 1, 12, 0, 60, 16, SessionStatus.SCHEDULED),
    ('Cross 18h', 1, 18, 0, 60, 24, SessionStatus.SCHEDULED),
    ('Cross 19h15', 1, 19, 15, 60, 26, SessionStatus.SCHEDULED),
    ('Gymnastics 20h30', 1, 20, 30, 60, 16, SessionStatus.SCHEDULED),
    ('Cross 06h', 2, 6, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Cross 07h', 2, 7, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Cross 18h', 2, 18, 0, 60, 24, SessionStatus.SCHEDULED),
    ('Cross 19h15', 2, 19, 15, 60, 26, SessionStatus.SCHEDULED),
    ('Cross 07h', 3, 7, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Cross 18h', 3, 18, 0, 60, 24, SessionStatus.SCHEDULED),
    ('Cross 19h15', 3, 19, 15, 60, 26, SessionStatus.SCHEDULED),
    ('Cross 09h', 4, 9, 0, 60, 18, SessionStatus.SCHEDULED),
    ('Kids 10h30', 4, 10, 30, 50, 14, SessionStatus.SCHEDULED),
    ('Open Box 11h30', 4, 11, 30, 90, 20, SessionStatus.OPEN),
]


class Command(BaseCommand):
    help = 'Semeia um cenario realista de box da zona sul de Sao Paulo com 100 a 200 alunos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--students',
            type=int,
            default=DEFAULT_STUDENT_COUNT,
            help='Quantidade de alunos a gerar. Deve ficar entre 100 e 200.',
        )
        parser.add_argument(
            '--scenario',
            choices=[SCENARIO_STABLE, SCENARIO_CHAOTIC],
            default=SCENARIO_STABLE,
            help='Escolhe o perfil operacional do box simulado.',
        )

    def handle(self, *args, **options):
        total_students = options['students']
        scenario = options['scenario']
        if total_students < MIN_STUDENT_COUNT or total_students > MAX_STUDENT_COUNT:
            raise CommandError('Use uma quantidade entre 100 e 200 alunos para manter a simulacao coerente.')

        rng = random.Random(RNG_SEED)
        today = timezone.localdate()

        with transaction.atomic():
            users = self._seed_users()
            plans = self._seed_plans()
            students = self._seed_students(total_students=total_students, rng=rng, today=today, scenario=scenario)
            enrollments = self._seed_enrollments(students=students, plans=plans, today=today, scenario=scenario)
            payments = self._seed_payments(students=students, enrollments=enrollments, today=today, rng=rng, scenario=scenario)
            sessions = self._seed_sessions(today=today, coaches=users['coaches'], scenario=scenario)
            attendances = self._seed_attendances(students=students, sessions=sessions, rng=rng, scenario=scenario)
            intakes = self._seed_intakes(students=students, users=users, today=today, scenario=scenario)
            contacts, message_count = self._seed_whatsapp(students=students, rng=rng, scenario=scenario)
            behavior_notes = self._seed_behavior_notes(students=students, coaches=users['coaches'], today=today, rng=rng, scenario=scenario)

        self.stdout.write(self.style.SUCCESS('Cenario da zona sul de Sao Paulo preparado com sucesso.'))
        self.stdout.write(f'Usuarios: {get_user_model().objects.count()}')
        self.stdout.write(f'Alunos: {len(students)}')
        self.stdout.write(f'Planos: {len(plans)}')
        self.stdout.write(f'Matriculas: {len(enrollments)}')
        self.stdout.write(f'Pagamentos: {len(payments)}')
        self.stdout.write(f'Aulas: {len(sessions)}')
        self.stdout.write(f'Presencas: {len(attendances)}')
        self.stdout.write(f'Intakes: {len(intakes)}')
        self.stdout.write(f'Contatos WhatsApp: {len(contacts)}')
        self.stdout.write(f'Logs WhatsApp: {message_count}')
        self.stdout.write(f'Cenario: {scenario}')
        self.stdout.write('Credenciais demo: owner_morumbi / octobox123')

    def _seed_users(self):
        user_model = get_user_model()
        created_users = {}
        for blueprint in USER_BLUEPRINTS:
            group = Group.objects.get(name=blueprint['group'])
            defaults = {
                'email': blueprint['email'],
                'first_name': blueprint['first_name'],
                'last_name': blueprint['last_name'],
                'is_staff': blueprint.get('is_staff', False),
                'is_superuser': blueprint.get('is_superuser', False),
            }
            user, created = user_model.objects.get_or_create(username=blueprint['username'], defaults=defaults)
            if created:
                user.set_password('octobox123')
                user.save()
            else:
                changed = False
                for field, value in defaults.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        changed = True
                if changed:
                    user.save(update_fields=list(defaults.keys()))
                user.groups.clear()
            user.groups.add(group)
            created_users[blueprint['username']] = user

        return {
            'owner': created_users['owner_morumbi'],
            'manager': created_users['manager_vila_andrade'],
            'reception': created_users['recepcao_santo_amaro'],
            'coaches': [
                created_users['coach_brooklin'],
                created_users['coach_campo_belo'],
                created_users['coach_saude'],
            ],
        }

    def _seed_plans(self):
        plans = []
        for blueprint in PLAN_BLUEPRINTS:
            plan = MembershipPlan.objects.create(
                name=blueprint['name'],
                price=blueprint['price'],
                billing_cycle=blueprint['billing_cycle'],
                sessions_per_week=blueprint['sessions_per_week'],
                description=blueprint['description'],
                active=True,
            )
            plans.append(plan)
        return plans

    def _seed_students(self, *, total_students, rng, today, scenario):
        counts = self._build_status_distribution(total_students, scenario=scenario)
        students = []
        used_names = set()

        for index in range(total_students):
            status = self._status_for_index(index=index, counts=counts)
            gender = StudentGender.FEMALE if index % 2 == 0 else StudentGender.MALE
            full_name = self._build_unique_name(index=index, used_names=used_names, rng=rng)
            neighborhood = NEIGHBORHOODS[index % len(NEIGHBORHOODS)]
            birth_date = self._build_birth_date(index=index, rng=rng, today=today)
            student = Student.objects.create(
                full_name=full_name,
                phone=f'55119{91000000 + index:08d}',
                email=self._build_email(full_name=full_name),
                gender=gender,
                birth_date=birth_date,
                health_issue_status='no' if index % 9 else 'yes',
                cpf=f'{10000000000 + index:011d}',
                status=status,
                notes=(
                    f'{SEED_TAG} Aluno ficticio do box da zona sul. '
                    f'Bairro base: {neighborhood}. Objetivo principal: consistencia, condicionamento e rotina.'
                    if scenario == SCENARIO_STABLE else
                    f'Bairro base: {neighborhood}. Historico recente de faltas, atraso de pagamento ou retorno irregular.'
                ),
            )
            students.append(student)

        return students

    def _seed_enrollments(self, *, students, plans, today, scenario):
        enrollments = {}
        for index, student in enumerate(students):
            if student.status == StudentStatus.LEAD:
                continue

            plan = plans[index % len(plans)]
            if student.status == StudentStatus.ACTIVE:
                status = EnrollmentStatus.ACTIVE
                start_date = today - timedelta(days=90 - (index % 60))
                end_date = None
            elif student.status == StudentStatus.PAUSED:
                status = EnrollmentStatus.PENDING
                start_date = today - timedelta(days=70 - (index % 30))
                end_date = today + timedelta(days=10 + (index % 15))
            else:
                status = EnrollmentStatus.EXPIRED if index % 2 == 0 else EnrollmentStatus.CANCELED
                start_date = today - timedelta(days=180 - (index % 40))
                end_date = today - timedelta(days=15 + (index % 25))

            if scenario == SCENARIO_CHAOTIC and student.status == StudentStatus.ACTIVE and index % 4 == 0:
                status = EnrollmentStatus.PENDING
            if scenario == SCENARIO_CHAOTIC and student.status == StudentStatus.INACTIVE and index % 3 == 0:
                status = EnrollmentStatus.CANCELED
            if scenario == SCENARIO_CHAOTIC and student.status == StudentStatus.PAUSED and index % 2 == 0:
                status = EnrollmentStatus.EXPIRED

            enrollments[student.id] = Enrollment.objects.create(
                student=student,
                plan=plan,
                start_date=start_date,
                end_date=end_date,
                status=status,
                notes=f'{SEED_TAG} Matricula simulada para operacao de box real.',
            )

        return enrollments

    def _seed_payments(self, *, students, enrollments, today, rng, scenario):
        payments = []
        for index, student in enumerate(students):
            enrollment = enrollments.get(student.id)
            if enrollment is None:
                amount = Decimal('79.90')
                status = PaymentStatus.PENDING if scenario == SCENARIO_STABLE else PaymentStatus.OVERDUE
                method = PaymentMethod.PIX
                offsets = [-1] if scenario == SCENARIO_STABLE else [-5]
                labels = ['experimental']
            else:
                plan_price = enrollment.plan.price
                if student.status == StudentStatus.ACTIVE:
                    offsets = [-45, -12, 0]
                    labels = ['mes-retrasado', 'mes-passado', 'mes-atual']
                    if scenario == SCENARIO_STABLE:
                        status_sequence = [PaymentStatus.PAID, PaymentStatus.PAID, PaymentStatus.OVERDUE if index % 5 == 0 else PaymentStatus.PENDING]
                    else:
                        status_sequence = [
                            PaymentStatus.OVERDUE if index % 5 else PaymentStatus.PAID,
                            PaymentStatus.OVERDUE if index % 2 == 0 else PaymentStatus.PENDING,
                            PaymentStatus.OVERDUE if index % 3 != 0 else PaymentStatus.PENDING,
                        ]
                elif student.status == StudentStatus.PAUSED:
                    offsets = [-35, -5, 7]
                    labels = ['ultimo-ciclo', 'ponte', 'reactivacao']
                    status_sequence = [
                        PaymentStatus.PAID if scenario == SCENARIO_STABLE and index % 2 else PaymentStatus.OVERDUE,
                        PaymentStatus.PENDING if scenario == SCENARIO_STABLE else PaymentStatus.OVERDUE,
                        PaymentStatus.PENDING if scenario == SCENARIO_STABLE else PaymentStatus.OVERDUE,
                    ]
                else:
                    offsets = [-60, -18]
                    labels = ['fechamento', 'residual']
                    status_sequence = [
                        PaymentStatus.CANCELED if scenario == SCENARIO_STABLE and index % 2 else PaymentStatus.OVERDUE,
                        PaymentStatus.PAID if scenario == SCENARIO_STABLE else PaymentStatus.OVERDUE,
                    ]

                for payment_index, offset in enumerate(offsets):
                    due_date = today + timedelta(days=offset)
                    status = status_sequence[payment_index]
                    method = self._payment_method_for_index(index + payment_index)
                    amount = plan_price
                    paid_at = None
                    if status == PaymentStatus.PAID:
                        paid_at = timezone.make_aware(
                            datetime.combine(due_date + timedelta(days=1), time(hour=10 + (index % 7), minute=10)),
                            timezone.get_current_timezone(),
                        )
                    reference = f'SPBOX-{student.id}-{labels[payment_index]}-{due_date:%Y%m%d}'
                    payments.append(
                        Payment.objects.create(
                            student=student,
                            enrollment=enrollment,
                            due_date=due_date,
                            paid_at=paid_at,
                            amount=amount,
                            status=status,
                            method=method,
                            billing_group=f'spbox-{student.id}-{labels[payment_index]}',
                            installment_number=1,
                            installment_total=1,
                            reference=reference,
                            notes=f'{SEED_TAG} Cobranca simulada para fila real de recepcao e financeiro.',
                        )
                    )
                continue

            due_date = today + timedelta(days=offsets[0])
            payments.append(
                Payment.objects.create(
                    student=student,
                    enrollment=None,
                    due_date=due_date,
                    amount=amount,
                    status=status,
                    method=method,
                    billing_group=f'spbox-lead-{student.id}',
                    installment_number=1,
                    installment_total=1,
                    reference=f'SPBOX-LEAD-{student.id}-{due_date:%Y%m%d}',
                    notes=f'{SEED_TAG} Taxa experimental ficticia para lead aquecido.',
                )
            )

        rng.shuffle(payments)
        return payments

    def _seed_sessions(self, *, today, coaches, scenario):
        sessions = []
        tz = timezone.get_current_timezone()
        for index, (title, day_offset, hour, minute, duration, capacity, status) in enumerate(SESSION_BLUEPRINTS):
            scheduled_at = timezone.make_aware(
                datetime.combine(today + timedelta(days=day_offset), time(hour=hour, minute=minute)),
                tz,
            )
            adjusted_capacity = capacity if scenario == SCENARIO_STABLE else max(12, capacity - 4)
            sessions.append(
                ClassSession.objects.create(
                    title=title,
                    coach=coaches[index % len(coaches)],
                    scheduled_at=scheduled_at,
                    duration_minutes=duration,
                    capacity=adjusted_capacity,
                    status=status,
                    notes=(
                        f'{SEED_TAG} Grade simulada de um box ativo da zona sul.'
                        if scenario == SCENARIO_STABLE else
                        f'{SEED_TAG} Grade comprimida com horarios cheios, encaixes e pressao na recepcao.'
                    ),
                )
            )
        return sessions

    def _seed_attendances(self, *, students, sessions, rng, scenario):
        attendances = []
        active_students = [student for student in students if student.status == StudentStatus.ACTIVE]
        paused_students = [student for student in students if student.status == StudentStatus.PAUSED]

        for session_index, session in enumerate(sessions):
            pressure = 2 if scenario == SCENARIO_STABLE else 6
            base_sample_size = min(session.capacity + (0 if scenario == SCENARIO_STABLE else 3), 10 + (session_index % 8) * 2 + pressure)
            booked_students = active_students[session_index * 3: session_index * 3 + base_sample_size]
            if len(booked_students) < base_sample_size:
                remaining = base_sample_size - len(booked_students)
                booked_students.extend(active_students[:remaining])
            if session_index % 4 == 0:
                booked_students.extend(paused_students[:2] if scenario == SCENARIO_STABLE else paused_students[:4])

            limit = session.capacity if scenario == SCENARIO_STABLE else min(len(booked_students), session.capacity + 7)
            for slot_index, student in enumerate(booked_students[:limit]):
                status_roll = (session_index + slot_index) % 9
                if session.status == SessionStatus.COMPLETED:
                    attendance_status = AttendanceStatus.ABSENT if status_roll <= (1 if scenario == SCENARIO_CHAOTIC else 0) else AttendanceStatus.CHECKED_OUT
                elif status_roll <= (2 if scenario == SCENARIO_CHAOTIC else 0):
                    attendance_status = AttendanceStatus.ABSENT
                elif status_roll in ({3, 4, 5} if scenario == SCENARIO_CHAOTIC else {1, 2}):
                    attendance_status = AttendanceStatus.CHECKED_IN
                else:
                    attendance_status = AttendanceStatus.BOOKED

                check_in_at = None
                check_out_at = None
                if attendance_status in {AttendanceStatus.CHECKED_IN, AttendanceStatus.CHECKED_OUT}:
                    check_in_at = session.scheduled_at + timedelta(minutes=4 + (slot_index % 6))
                if attendance_status == AttendanceStatus.CHECKED_OUT:
                    check_out_at = session.scheduled_at + timedelta(minutes=session.duration_minutes)

                attendances.append(
                    Attendance.objects.create(
                        student=student,
                        session=session,
                        status=attendance_status,
                        reservation_source='seed-south-sp-box',
                        check_in_at=check_in_at,
                        check_out_at=check_out_at,
                        notes=(
                            f'{SEED_TAG} Presenca simulada para validar grade e recepcao.'
                            if scenario == SCENARIO_STABLE else
                            f'{SEED_TAG} Presenca simulada com encaixe, atraso e fila apertada na recepcao.'
                        ),
                    )
                )

        rng.shuffle(attendances)
        return attendances

    def _seed_intakes(self, *, students, users, today, scenario):
        leads = [student for student in students if student.status == StudentStatus.LEAD]
        actives = [student for student in students if student.status == StudentStatus.ACTIVE]
        intakes = []

        lead_batch = 8 if scenario == SCENARIO_STABLE else min(len(leads), 11)
        for index, lead in enumerate(leads[:lead_batch]):
            intake = StudentIntake.objects.create(
                full_name=lead.full_name,
                phone=lead.phone,
                email=lead.email,
                source=IntakeSource.WHATSAPP if index % 2 == 0 else IntakeSource.MANUAL,
                status=IntakeStatus.NEW if index < (4 if scenario == SCENARIO_STABLE else 8) else IntakeStatus.REVIEWING,
                assigned_to=users['reception'] if index < 5 else users['manager'],
                raw_payload={
                    'origin': 'instagram-zona-sul',
                    'bairro_interesse': NEIGHBORHOODS[index % len(NEIGHBORHOODS)],
                    'trial_requested_on': str(today - timedelta(days=index)),
                },
                notes=f'{SEED_TAG} Lead quente aguardando contato ou aula experimental.',
            )
            intakes.append(intake)

        matched_batch = 6 if scenario == SCENARIO_STABLE else 3
        for index, student in enumerate(actives[:matched_batch]):
            intake = StudentIntake.objects.create(
                full_name=student.full_name,
                phone=student.phone,
                email=student.email,
                source=IntakeSource.IMPORT if index % 2 == 0 else IntakeSource.CSV,
                status=IntakeStatus.MATCHED if index < (4 if scenario == SCENARIO_STABLE else 3) else IntakeStatus.APPROVED,
                linked_student=student,
                assigned_to=users['manager'],
                raw_payload={
                    'legacy_source': 'planilha-piloto',
                    'import_wave': index + 1,
                },
                notes=f'{SEED_TAG} Intake reconciliado com aluno ja convertido.',
            )
            intakes.append(intake)

        return intakes

    def _seed_whatsapp(self, *, students, rng, scenario):
        contacts = []
        message_count = 0
        selected_students = students[:36] if scenario == SCENARIO_STABLE else students[:72]
        tz = timezone.get_current_timezone()

        for index, student in enumerate(selected_students):
            last_inbound_at = timezone.make_aware(
                datetime.combine(timezone.localdate() - timedelta(days=index % 6), time(hour=8 + (index % 10), minute=15)),
                tz,
            )
            last_outbound_at = last_inbound_at + timedelta(minutes=12)
            contact = WhatsAppContact.objects.create(
                phone=student.phone,
                external_contact_id=f'wa-zs-{student.id}',
                display_name=student.full_name,
                linked_student=student if student.status != StudentStatus.LEAD else None,
                status=WhatsAppContactStatus.LINKED if student.status != StudentStatus.LEAD else WhatsAppContactStatus.NEW,
                last_inbound_at=last_inbound_at,
                last_outbound_at=last_outbound_at,
                notes=f'{SEED_TAG} Contato ficticio com historico de atendimento do box.',
            )
            contacts.append(contact)

            inbound_body = (
                'Oi, consigo remarcar minha aula de hoje?'
                if index % 4 == 0 else
                'Bom dia, queria saber sobre o plano 3x.'
                if index % 4 == 1 else
                'Consegue me mandar o link do PIX?'
                if index % 4 == 2 else
                'Chego 10 minutos atrasado para a aula das 19h.'
            )
            if scenario == SCENARIO_CHAOTIC and index % 5 == 0:
                inbound_body = 'Oi, meu nome nao apareceu na lista e meu pagamento caiu ontem.'
            if scenario == SCENARIO_CHAOTIC and index % 6 == 0:
                inbound_body = 'To chegando e a aula das 18h lotou. Consegue encaixe?'
            if scenario == SCENARIO_CHAOTIC and index % 7 == 0:
                inbound_body = 'Recebi cobranca duplicada no WhatsApp e no balcao me falaram outra coisa.'
            outbound_body = (
                'Claro. Ja deixei sua vaga ajustada na recepcao.'
                if index % 4 == 0 else
                'Consigo sim. Te explico o plano Performance 3x e a experimental.'
                if index % 4 == 1 else
                'Segue o link e qualquer coisa eu marco como pago assim que cair.'
                if index % 4 == 2 else
                'Tudo certo. Vou avisar o coach e manter sua reserva.'
            )

            WhatsAppMessageLog.objects.create(
                contact=contact,
                direction=MessageDirection.INBOUND,
                kind=MessageKind.TEXT,
                body=inbound_body,
                external_message_id=f'wa-in-{contact.id}',
                webhook_fingerprint=f'wa-fp-in-{contact.id}',
                delivered_at=last_inbound_at,
                raw_payload={'channel': 'whatsapp', 'seed': SEED_TAG},
            )
            WhatsAppMessageLog.objects.create(
                contact=contact,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT if index % 3 else MessageKind.TEMPLATE,
                body=outbound_body,
                external_message_id=f'wa-out-{contact.id}',
                webhook_fingerprint=f'wa-fp-out-{contact.id}',
                delivered_at=last_outbound_at,
                raw_payload={'channel': 'whatsapp', 'seed': SEED_TAG},
            )
            message_count += 2
            if scenario == SCENARIO_CHAOTIC and index % 3 == 0:
                WhatsAppMessageLog.objects.create(
                    contact=contact,
                    direction=MessageDirection.INBOUND,
                    kind=MessageKind.TEXT,
                    body='Ainda nao consegui resolver no balcao. Pode verificar agora?',
                    external_message_id=f'wa-chaos-{contact.id}',
                    webhook_fingerprint=f'wa-fp-chaos-{contact.id}',
                    delivered_at=last_outbound_at + timedelta(minutes=9),
                    raw_payload={'channel': 'whatsapp', 'seed': SEED_TAG, 'scenario': scenario},
                )
                message_count += 1
            if scenario == SCENARIO_CHAOTIC and index % 4 == 0:
                WhatsAppMessageLog.objects.create(
                    contact=contact,
                    direction=MessageDirection.OUTBOUND,
                    kind=MessageKind.SYSTEM,
                    body='Detectamos pendencia financeira e reserva acima da capacidade da turma. Confirmar no balcao.',
                    external_message_id=f'wa-chaos-system-{contact.id}',
                    webhook_fingerprint=f'wa-fp-chaos-system-{contact.id}',
                    delivered_at=last_outbound_at + timedelta(minutes=12),
                    raw_payload={'channel': 'whatsapp', 'seed': SEED_TAG, 'scenario': scenario, 'warning': 'double-conflict'},
                )
                message_count += 1

        rng.shuffle(contacts)
        return contacts, message_count

    def _seed_behavior_notes(self, *, students, coaches, today, rng, scenario):
        notes = []
        tracked_students = students[:18] if scenario == SCENARIO_STABLE else students[:34]
        categories = [
            BehaviorCategory.POSITIVE,
            BehaviorCategory.SUPPORT,
            BehaviorCategory.ATTENTION,
            BehaviorCategory.INJURY,
            BehaviorCategory.DISCIPLINE,
        ]
        for index, student in enumerate(tracked_students):
            happened_at = timezone.make_aware(
                datetime.combine(today - timedelta(days=index % 10), time(hour=7 + (index % 8), minute=20)),
                timezone.get_current_timezone(),
            )
            category = categories[index % len(categories)]
            notes.append(
                BehaviorNote.objects.create(
                    student=student,
                    author=coaches[index % len(coaches)],
                    category=category,
                    happened_at=happened_at,
                    description=(
                        f'{SEED_TAG} Observacao operacional para acompanhamento do aluno no box.'
                        if scenario == SCENARIO_STABLE else
                        f'{SEED_TAG} Observacao de operacao pressionada: atraso, lesao, conflito de agenda ou risco de evasao.'
                    ),
                    action_taken=(
                        'Recepcao e coach alinhados para acompanhamento leve.'
                        if scenario == SCENARIO_STABLE and category != BehaviorCategory.POSITIVE else
                        'Registrar reforco positivo na proxima aula.'
                        if scenario == SCENARIO_STABLE else
                        'Manager acionado para contato no mesmo dia e ajuste de agenda/cobranca.'
                    ),
                )
            )

        rng.shuffle(notes)
        return notes

    def _build_status_distribution(self, total_students, scenario):
        if scenario == SCENARIO_CHAOTIC:
            active = int(total_students * Decimal('0.60'))
            paused = int(total_students * Decimal('0.16'))
            inactive = int(total_students * Decimal('0.16'))
        else:
            active = int(total_students * Decimal('0.79'))
            paused = int(total_students * Decimal('0.09'))
            inactive = int(total_students * Decimal('0.07'))
        lead = total_students - active - paused - inactive
        return {
            StudentStatus.ACTIVE: active,
            StudentStatus.PAUSED: paused,
            StudentStatus.INACTIVE: inactive,
            StudentStatus.LEAD: lead,
        }

    def _status_for_index(self, *, index, counts):
        boundaries = []
        running = 0
        for status in (StudentStatus.ACTIVE, StudentStatus.PAUSED, StudentStatus.INACTIVE, StudentStatus.LEAD):
            running += counts[status]
            boundaries.append((running, status))
        for boundary, status in boundaries:
            if index < boundary:
                return status
        return StudentStatus.LEAD

    def _build_unique_name(self, *, index, used_names, rng):
        max_attempts = 200
        for _ in range(max_attempts):
            first_name = FIRST_NAMES[(index + rng.randint(0, len(FIRST_NAMES) - 1)) % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(index * 3 + rng.randint(0, len(LAST_NAMES) - 1)) % len(LAST_NAMES)]
            extra_last_name = LAST_NAMES[(index * 5 + rng.randint(0, len(LAST_NAMES) - 1)) % len(LAST_NAMES)]
            candidate = f'{first_name} {last_name} {extra_last_name}'
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
        raise CommandError('Nao foi possivel gerar nomes unicos para a seed.')

    def _build_email(self, *, full_name):
        slug = (
            full_name.lower()
            .replace(' ', '.')
            .replace('ã', 'a')
            .replace('á', 'a')
            .replace('â', 'a')
            .replace('é', 'e')
            .replace('ê', 'e')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ô', 'o')
            .replace('ú', 'u')
            .replace('ç', 'c')
        )
        return f'{slug}@sulbox.demo'

    def _build_birth_date(self, *, index, rng, today: date):
        age = 18 + ((index * 7 + rng.randint(0, 9)) % 28)
        day_offset = (index * 13 + rng.randint(0, 20)) % 365
        return today - timedelta(days=(age * 365) + day_offset)

    def _payment_method_for_index(self, index):
        methods = [
            PaymentMethod.PIX,
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.TRANSFER,
            PaymentMethod.BANK_SLIP,
            PaymentMethod.CASH,
        ]
        return methods[index % len(methods)]
