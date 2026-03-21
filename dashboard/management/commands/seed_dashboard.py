from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from django.contrib.auth import get_user_model
User = get_user_model()

from students.models import Student
from finance.models import Payment, PaymentStatus
from operations.models import ClassSession

class Command(BaseCommand):
    help = 'Popula banco de dados com valores ficticios para testar UI do Dashboard'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando Seed Profundo no OctoBOX...")

        user = User.objects.first()
        if not user:
            user = User.objects.create_user('admin', email='admin@octobox.com', password='password123', first_name='Oto', last_name='Owner')
            self.stdout.write(f"Usuario criado: {user.email}")

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
