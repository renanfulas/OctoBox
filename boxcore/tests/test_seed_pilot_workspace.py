"""
ARQUIVO: testes da seed de workspace piloto.

POR QUE ELE EXISTE:
- Garante que a massa ficticia continue criando um cenario util sem duplicacao em reexecucoes.

O QUE ESTE ARQUIVO FAZ:
1. Prepara alunos e um usuario base.
2. Executa a seed do workspace piloto.
3. Confirma criacao de planos, cobrancas, aulas e presencas.
4. Confirma que nova execucao nao duplica os registros da propria seed.

PONTOS CRITICOS:
- Se esse teste falhar, a seed pode estar duplicando registros ou deixando de alimentar telas-chave.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from finance.models import Enrollment, MembershipPlan, Payment
from operations.models import Attendance, ClassSession
from students.models import Student, StudentStatus


class SeedPilotWorkspaceCommandTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(
            username='coach-demo',
            email='coach-demo@example.com',
            password='senha-forte-123',
        )
        student_specs = [
            ('Amanda Duarte', StudentStatus.ACTIVE),
            ('Bruna Costa', StudentStatus.ACTIVE),
            ('Bruno Nogueira', StudentStatus.ACTIVE),
            ('Caio Barros', StudentStatus.ACTIVE),
            ('Camila Moura', StudentStatus.ACTIVE),
            ('Daniel Freitas', StudentStatus.ACTIVE),
            ('Erika Prado', StudentStatus.PAUSED),
            ('Felipe Tavares', StudentStatus.PAUSED),
            ('Gabriela Rocha', StudentStatus.INACTIVE),
            ('Henrique Luz', StudentStatus.INACTIVE),
            ('Iara Monteiro', StudentStatus.LEAD),
            ('Joao Pedro', StudentStatus.LEAD),
        ]

        for index, (full_name, status) in enumerate(student_specs, start=1):
            Student.objects.create(
                full_name=full_name,
                phone=f'5511999000{index:03d}',
                status=status,
            )

    def test_seed_pilot_workspace_is_idempotent(self):
        call_command('seed_pilot_workspace')

        self.assertEqual(MembershipPlan.objects.filter(name__startswith='Piloto ').count(), 3)
        self.assertEqual(Enrollment.objects.filter(notes__contains='[seed-pilot-workspace]').count(), 10)
        self.assertEqual(Payment.objects.filter(reference__startswith='PILOTO-').count(), 16)
        self.assertEqual(ClassSession.objects.filter(notes__contains='[seed-pilot-workspace]').count(), 12)
        self.assertGreaterEqual(Attendance.objects.filter(notes__contains='[seed-pilot-workspace]').count(), 40)

        call_command('seed_pilot_workspace')

        self.assertEqual(MembershipPlan.objects.filter(name__startswith='Piloto ').count(), 3)
        self.assertEqual(Enrollment.objects.filter(notes__contains='[seed-pilot-workspace]').count(), 10)
        self.assertEqual(Payment.objects.filter(reference__startswith='PILOTO-').count(), 16)
        self.assertEqual(ClassSession.objects.filter(notes__contains='[seed-pilot-workspace]').count(), 12)