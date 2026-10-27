from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django_tenants.utils import schema_context
from django.utils import timezone
from datetime import timedelta
import random

from control.models import Box
from control.tenant_write_fence import tenant_write_guarded_command
from students.models import Student
from finance.models import Payment, PaymentStatus
from operations.models import ClassSession

class Command(BaseCommand):
    help = 'Popula banco de dados com valores ficticios para testar UI do Dashboard'

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='Schema box_<slug> ativo para receber os dados fictícios.')

    @tenant_write_guarded_command(write_option=None)
    def handle(self, *args, **kwargs):
        schema_name = kwargs['schema']
        box = Box.objects.filter(schema_name=schema_name, status=Box.Status.ACTIVE).first()
        if box is None:
            raise CommandError(f'Box ativo não encontrado para schema {schema_name!r}.')
        with schema_context(box.schema_name):
            return self._seed_dashboard()

    def _seed_dashboard(self):
        self.stdout.write("Iniciando Seed Profundo no OctoBOX...")

        now = timezone.now()

        self.stdout.write("Gerando Alunos...")
        students = []
        for i in range(1, 15):
            phone = f"55119{random.randint(10000000, 99999999)}"
            s, _ = Student.objects.get_or_create(email=f'aluno{i}@octobox.com', defaults={'full_name': f'Atleta {i} Test', 'phone': phone})
            students.append(s)

        self.stdout.write("Gerando Pagamentos (Financeiro)...")
        for i, s in enumerate(students[:5]):
            Payment.objects.get_or_create(
                student=s,
                defaults={
                    'amount': 299.90, 'status': PaymentStatus.OVERDUE,
                    'due_date': now.date() - timedelta(days=5),
                }
            )

        for i, s in enumerate(students[5:10]):
            Payment.objects.get_or_create(
                student=s,
                defaults={
                    'amount': 299.90, 'status': PaymentStatus.PAID,
                    'due_date': now.date() - timedelta(days=2),
                    'paid_at': now,
                }
            )

        self.stdout.write("Gerando Agenda de Treinos (Sessões)...")
        ClassSession.objects.get_or_create(title="Treino WOD Manha", scheduled_at=now + timedelta(hours=1), defaults={'duration_minutes': 60})
        ClassSession.objects.get_or_create(title="CrossFit LPO", scheduled_at=now + timedelta(hours=4), defaults={'duration_minutes': 60})
        ClassSession.objects.get_or_create(title="Treino Livre / Open Box", scheduled_at=now + timedelta(hours=6), defaults={'duration_minutes': 60})

        # Gerar sessões passadas para constar no gráfico de presença
        ClassSession.objects.get_or_create(title="WOD Matinal Ontem", scheduled_at=now - timedelta(days=1, hours=2), defaults={'duration_minutes': 60})

        self.stdout.write(self.style.SUCCESS("Seed Concluido com Sucesso! Volte ao painel e atualize a pagina."))
