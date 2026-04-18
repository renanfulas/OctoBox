"""
ARQUIVO: comando interno para reconstruir a base ficticia de demo do box.

POR QUE ELE EXISTE:
- Permite apagar a base operacional/comercial atual ligada a alunos e recriar um cenario ficticio coerente para revisao visual e testes manuais.

O QUE ESTE ARQUIVO FAZ:
1. Limpa alunos e todos os dados dependentes que alimentam dashboard, financeiro, entradas, grade e WhatsApp.
2. Recria uma carteira ficticia de alunos com perfis variados.
3. Reaproveita a seed piloto para gerar planos, matriculas, cobrancas, aulas e presencas.
4. Complementa o cenario com intakes, contatos/logs de WhatsApp e notas comportamentais.

PONTOS CRITICOS:
- Este comando e destrutivo para a base comercial/operacional ligada a alunos.
- Usuarios e permissoes nao sao apagados; apenas dados de negocio usados na demonstracao.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from boxcore.management.commands.seed_pilot_workspace import Command as SeedPilotWorkspaceCommand
from communications.models import MessageDirection, MessageKind, StudentIntake, WhatsAppContact, WhatsAppContactStatus, WhatsAppMessageLog
from finance.models import Enrollment, MembershipPlan, Payment
from onboarding.models import IntakeSource, IntakeStatus
from operations.models import Attendance, BehaviorCategory, BehaviorNote, ClassSession
from students.models import Student, StudentStatus


DEMO_TAG = '[reset-demo-workspace]'
SCENARIO_BALANCED = 'balanced'
SCENARIO_RECEPTION_CONVERSION = 'reception-conversion'

STUDENT_BLUEPRINTS = [
    {
        'full_name': 'Alice Braga',
        'phone': '5511999100001',
        'email': 'alice.braga.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluna consistente da rotina matinal, boa para testar base ativa.',
    },
    {
        'full_name': 'Bianca Torres',
        'phone': '5511999100002',
        'email': 'bianca.torres.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluna premium usada para validar carteira e cobranca em dia.',
    },
    {
        'full_name': 'Caio Menezes',
        'phone': '5511999100003',
        'email': 'caio.menezes.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluno com historico util para leitura de presenca e risco.',
    },
    {
        'full_name': 'Diana Prado',
        'phone': '5511999100004',
        'email': 'diana.prado.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluna da faixa da noite, boa para testar ocupacao das turmas.',
    },
    {
        'full_name': 'Enzo Salles',
        'phone': '5511999100005',
        'email': 'enzo.salles.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluno usado para risco financeiro curto e fila comercial.',
    },
    {
        'full_name': 'Fernanda Luz',
        'phone': '5511999100006',
        'email': 'fernanda.luz.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluna com rotina regular para validar filtros do catalogo.',
    },
    {
        'full_name': 'Gustavo Pires',
        'phone': '5511999100007',
        'email': 'gustavo.pires.demo@example.com',
        'status': StudentStatus.PAUSED,
        'notes': f'{DEMO_TAG} Aluno pausado para validar mistura da carteira e retomada.',
    },
    {
        'full_name': 'Helena Castro',
        'phone': '5511999100008',
        'email': 'helena.castro.demo@example.com',
        'status': StudentStatus.PAUSED,
        'notes': f'{DEMO_TAG} Aluna pausada para leitura de follow-up e reativacao.',
    },
    {
        'full_name': 'Igor Nunes',
        'phone': '5511999100009',
        'email': 'igor.nunes.demo@example.com',
        'status': StudentStatus.INACTIVE,
        'notes': f'{DEMO_TAG} Aluno inativo para testar historico e carteira perdida.',
    },
    {
        'full_name': 'Julia Ramos',
        'phone': '5511999100010',
        'email': 'julia.ramos.demo@example.com',
        'status': StudentStatus.INACTIVE,
        'notes': f'{DEMO_TAG} Aluna inativa para validar conversao de churn.',
    },
    {
        'full_name': 'Kaique Lima',
        'phone': '5511999100011',
        'email': 'kaique.lima.demo@example.com',
        'status': StudentStatus.LEAD,
        'notes': f'{DEMO_TAG} Lead quente para revisar fila de entradas e alunos.',
    },
    {
        'full_name': 'Larissa Freire',
        'phone': '5511999100012',
        'email': 'larissa.freire.demo@example.com',
        'status': StudentStatus.LEAD,
        'notes': f'{DEMO_TAG} Lead em avaliacao para dashboard e central de intake.',
    },
    {
        'full_name': 'Mateus Arantes',
        'phone': '5511999100013',
        'email': 'mateus.arantes.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluno adicional para dar densidade real ao diretorio.',
    },
    {
        'full_name': 'Nina Queiroz',
        'phone': '5511999100014',
        'email': 'nina.queiroz.demo@example.com',
        'status': StudentStatus.ACTIVE,
        'notes': f'{DEMO_TAG} Aluna adicional para reforcar agenda e cobranca.',
    },
]


class Command(BaseCommand):
    help = 'Limpa a base ligada a alunos e recria um cenario ficticio coerente para demo do box.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scenario',
            choices=[SCENARIO_BALANCED, SCENARIO_RECEPTION_CONVERSION],
            default=SCENARIO_BALANCED,
            help='Escolhe o perfil da demo ficticia a ser reconstruida.',
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        scenario = options['scenario']

        with transaction.atomic():
            self._clear_business_data()
            coach_pool = self._resolve_coach_pool()
            students = self._seed_students()
            self._seed_core_workspace(students=students, coach_pool=coach_pool, today=today)
            self._seed_intakes(students=students, scenario=scenario)
            self._seed_whatsapp(students=students, scenario=scenario)
            self._seed_behavior_notes(students=students, coach_pool=coach_pool)

        self.stdout.write(self.style.SUCCESS('Base ficticia do box reconstruida com sucesso.'))
        self.stdout.write(f'Cenario aplicado: {scenario}')
        self.stdout.write(f'Alunos: {Student.objects.count()}')
        self.stdout.write(f'Planos: {MembershipPlan.objects.count()}')
        self.stdout.write(f'Matriculas: {Enrollment.objects.count()}')
        self.stdout.write(f'Pagamentos: {Payment.objects.count()}')
        self.stdout.write(f'Aulas: {ClassSession.objects.count()}')
        self.stdout.write(f'Presencas: {Attendance.objects.count()}')
        self.stdout.write(f'Intakes: {StudentIntake.objects.count()}')
        self.stdout.write(f'Contatos WhatsApp: {WhatsAppContact.objects.count()}')
        self.stdout.write(f'Logs WhatsApp: {WhatsAppMessageLog.objects.count()}')

    def _clear_business_data(self):
        WhatsAppMessageLog.objects.all().delete()
        WhatsAppContact.objects.all().delete()
        StudentIntake.objects.all().delete()
        Attendance.objects.all().delete()
        BehaviorNote.objects.all().delete()
        Payment.objects.all().delete()
        Enrollment.objects.all().delete()
        ClassSession.objects.all().delete()
        MembershipPlan.objects.all().delete()
        Student.objects.all().delete()

    def _resolve_coach_pool(self):
        user_model = get_user_model()
        preferred_specs = [
            ('qa_coach', 'qa_coach@example.com'),
            ('copilot-demo-coach', 'copilot-demo-coach@example.com'),
            ('qa_owner_browser', 'qa_owner_browser@example.com'),
        ]
        selected = []
        used_ids = set()

        for username, email in preferred_specs:
            user = user_model.objects.filter(username=username).first()
            if user is None:
                user = user_model.objects.create_user(
                    username=username,
                    email=email,
                    password='test',
                )
            if user.id not in used_ids:
                selected.append(user)
                used_ids.add(user.id)

        if len(selected) < 3:
            for user in user_model.objects.order_by('id'):
                if user.id in used_ids:
                    continue
                selected.append(user)
                used_ids.add(user.id)
                if len(selected) == 3:
                    break

        while len(selected) < 3:
            username = f'coach-demo-{len(selected) + 1}'
            user = user_model.objects.create_user(
                username=username,
                email=f'{username}@example.com',
                password='test',
            )
            selected.append(user)

        return selected[:3]

    def _seed_students(self):
        students = []
        for blueprint in STUDENT_BLUEPRINTS:
            students.append(Student.objects.create(**blueprint))
        return students

    def _seed_core_workspace(self, *, students, coach_pool, today):
        seed_command = SeedPilotWorkspaceCommand()
        plans = seed_command._seed_plans()
        selected_students = seed_command._select_students(students)
        enrollments = seed_command._seed_enrollments(selected_students, plans, today)
        seed_command._seed_payments(selected_students, enrollments, today)
        sessions = seed_command._seed_sessions(today, coach_pool)
        seed_command._seed_attendances(selected_students, sessions, today)

    def _seed_intakes(self, *, students, scenario):
        student_map = {student.full_name: student for student in students}
        intake_blueprints = [
            {
                'full_name': 'Olivia Serra',
                'phone': '5511999101010',
                'email': 'olivia.serra.demo@example.com',
                'source': IntakeSource.WHATSAPP,
                'status': IntakeStatus.NEW,
                'notes': f'{DEMO_TAG} Lead novo pedindo primeiro contato comercial.',
            },
            {
                'full_name': 'Pedro Vidal',
                'phone': '5511999101011',
                'email': 'pedro.vidal.demo@example.com',
                'source': IntakeSource.MANUAL,
                'status': IntakeStatus.REVIEWING,
                'notes': f'{DEMO_TAG} Intake em revisao pela recepcao para conversao rapida.',
            },
            {
                'full_name': 'Kaique Lima',
                'phone': '5511999100011',
                'email': 'kaique.lima.demo@example.com',
                'source': IntakeSource.WHATSAPP,
                'status': IntakeStatus.APPROVED,
                'linked_student': student_map['Kaique Lima'],
                'notes': f'{DEMO_TAG} Intake ja vinculado a lead interno para manter o fluxo visivel.',
            },
            {
                'full_name': 'Nina Queiroz',
                'phone': '5511999100014',
                'email': 'nina.queiroz.demo@example.com',
                'source': IntakeSource.IMPORT,
                'status': IntakeStatus.APPROVED,
                'linked_student': student_map['Nina Queiroz'],
                'notes': f'{DEMO_TAG} Intake historico aprovado para dar contraste na central.',
            },
        ]

        if scenario == SCENARIO_RECEPTION_CONVERSION:
            intake_blueprints.extend(
                [
                    {
                        'full_name': 'Sofia Mello',
                        'phone': '5511999101012',
                        'email': 'sofia.mello.demo@example.com',
                        'source': IntakeSource.WHATSAPP,
                        'status': IntakeStatus.NEW,
                        'notes': f'{DEMO_TAG} Lead quente pedindo experimental para aumentar pressao da recepcao.',
                    },
                    {
                        'full_name': 'Thiago Viana',
                        'phone': '5511999101013',
                        'email': 'thiago.viana.demo@example.com',
                        'source': IntakeSource.MANUAL,
                        'status': IntakeStatus.REVIEWING,
                        'notes': f'{DEMO_TAG} Intake com documentacao parcial aguardando decisao da recepcao.',
                    },
                    {
                        'full_name': 'Valentina Cruz',
                        'phone': '5511999101014',
                        'email': 'valentina.cruz.demo@example.com',
                        'source': IntakeSource.WHATSAPP,
                        'status': IntakeStatus.APPROVED,
                        'linked_student': student_map['Larissa Freire'],
                        'notes': f'{DEMO_TAG} Intake ja reconciliado com lead interno para acelerar conversao.',
                    },
                ]
            )

        for blueprint in intake_blueprints:
            StudentIntake.objects.create(**blueprint)

    def _seed_whatsapp(self, *, students, scenario):
        student_map = {student.full_name: student for student in students}
        contact_blueprints = [
            {
                'phone': '5511999100003',
                'display_name': 'Caio Menezes',
                'linked_student': student_map['Caio Menezes'],
                'status': WhatsAppContactStatus.LINKED,
                'notes': f'{DEMO_TAG} Contato ativo para validar historico de conversa.',
                'messages': [
                    ('inbound', 'Chego 10 min atrasado hoje, tudo bem?'),
                    ('outbound', 'Tudo certo. Sua reserva segue ativa para a aula.'),
                ],
            },
            {
                'phone': '5511999100005',
                'display_name': 'Enzo Salles',
                'linked_student': student_map['Enzo Salles'],
                'status': WhatsAppContactStatus.LINKED,
                'notes': f'{DEMO_TAG} Contato usado para validar cobranca curta e retorno comercial.',
                'messages': [
                    ('outbound', 'Seu vencimento ficou para hoje. Se precisar, posso te mandar o PIX por aqui.'),
                ],
            },
            {
                'phone': '5511999101010',
                'display_name': 'Olivia Serra',
                'linked_student': None,
                'status': WhatsAppContactStatus.NEW,
                'notes': f'{DEMO_TAG} Contato ainda sem vinculo para sustentar a central de entradas.',
                'messages': [
                    ('inbound', 'Oi, quero fazer uma aula experimental ainda esta semana.'),
                ],
            },
            {
                'phone': '5511999100014',
                'display_name': 'Nina Queiroz',
                'linked_student': student_map['Nina Queiroz'],
                'status': WhatsAppContactStatus.LINKED,
                'notes': f'{DEMO_TAG} Contato ativo de aluna recorrente com historico recente.',
                'messages': [
                    ('inbound', 'Consegue me confirmar a aula das 19h15 de amanha?'),
                    ('outbound', 'Confirmada. Sua vaga ja esta reservada.'),
                ],
            },
        ]

        if scenario == SCENARIO_RECEPTION_CONVERSION:
            contact_blueprints.extend(
                [
                    {
                        'phone': '5511999101011',
                        'display_name': 'Pedro Vidal',
                        'linked_student': None,
                        'status': WhatsAppContactStatus.NEW,
                        'notes': f'{DEMO_TAG} Conversa de intake em qualificacao para manter a recepcao ativa.',
                        'messages': [
                            ('inbound', 'Quero entender valores e se posso treinar a noite.'),
                            ('outbound', 'Consigo te passar as opcoes e reservar uma visita hoje.'),
                        ],
                    },
                    {
                        'phone': '5511999101012',
                        'display_name': 'Sofia Mello',
                        'linked_student': None,
                        'status': WhatsAppContactStatus.NEW,
                        'notes': f'{DEMO_TAG} Lead novo puxando a fila de primeiro contato da recepcao.',
                        'messages': [
                            ('inbound', 'Oi, voces ainda tem aula experimental hoje?'),
                            ('outbound', 'Temos sim. Posso te encaixar na turma das 19h15.'),
                        ],
                    },
                    {
                        'phone': '5511999101014',
                        'display_name': 'Valentina Cruz',
                        'linked_student': student_map['Larissa Freire'],
                        'status': WhatsAppContactStatus.LINKED,
                        'notes': f'{DEMO_TAG} Contato conciliado com lead interno para validar handoff de conversao.',
                        'messages': [
                            ('inbound', 'Consegui separar meus horarios, qual plano encaixa melhor?'),
                            ('outbound', 'Pelo seu ritmo, o mensal 3x faz sentido para comecar.'),
                        ],
                    },
                ]
            )

        for blueprint in contact_blueprints:
            messages = blueprint.pop('messages')
            contact = WhatsAppContact.objects.create(**blueprint)
            for direction, body in messages:
                WhatsAppMessageLog.objects.create(
                    contact=contact,
                    direction=MessageDirection.INBOUND if direction == 'inbound' else MessageDirection.OUTBOUND,
                    kind=MessageKind.TEXT,
                    body=body,
                    raw_payload={'seed': 'reset_demo_workspace'},
                )

    def _seed_behavior_notes(self, *, students, coach_pool):
        student_map = {student.full_name: student for student in students}
        BehaviorNote.objects.create(
            student=student_map['Caio Menezes'],
            author=coach_pool[0],
            category=BehaviorCategory.ATTENTION,
            description=f'{DEMO_TAG} Caiu uma frequencia nas ultimas duas semanas e vale acolhimento antes de esfriar.',
            action_taken='Recepcao orientada a checar rotina e preferencia de horario.',
        )
        BehaviorNote.objects.create(
            student=student_map['Fernanda Luz'],
            author=coach_pool[1],
            category=BehaviorCategory.POSITIVE,
            description=f'{DEMO_TAG} Boa evolucao tecnica e alta recorrencia recente.',
            action_taken='Usar como exemplo positivo na leitura do coach.',
        )
        BehaviorNote.objects.create(
            student=student_map['Gustavo Pires'],
            author=coach_pool[2],
            category=BehaviorCategory.SUPPORT,
            description=f'{DEMO_TAG} Aluno pausado por agenda de trabalho, mas com chance real de retorno.',
            action_taken='Sinalizado para retomada comercial na proxima semana.',
        )
