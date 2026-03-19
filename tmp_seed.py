from django.utils import timezone
from datetime import timedelta
import random

from django.conf import settings
from access.models import Tenant, User, Role
from students.models import Student
from onboarding.models import Intake, IntakeStage
from finance.models import Payment, Plan, PaymentStatus
from operations.models import Session

def seed():
    print("Iniciando Seed Profundo no OctoBOX...")
    tenant, _ = Tenant.objects.get_or_create(name='OctoBOX Fictício')
    
    user = User.objects.filter(email='owner@octobox.com').first()
    if not user:
        user = User.objects.create_user(email='owner@octobox.com', password='password123', first_name='Oto', last_name='Owner')
    
    Role.objects.get_or_create(user=user, tenant=tenant, defaults={'role': 'OWNER'})

    print(f"Ambiente configurado: Box = {tenant.name}, Owner = {user.email}")
    now = timezone.now()

    # 1. Alunos Ativos
    print("Gerando Alunos...")
    students = []
    for i in range(1, 15):
        s, _ = Student.objects.get_or_create(tenant=tenant, email=f'aluno{i}@octobox.com', defaults={'first_name': f'Atleta {i}', 'last_name': 'Test'})
        students.append(s)

    # 2. Planos e Pagamentos (Financeiro)
    print("Gerando Financeiro (Pagamentos)...")
    plan, _ = Plan.objects.get_or_create(tenant=tenant, name="Plano Semestral Premium", defaults={'price': 299.90, 'frequency': 'MONTHLY'})
    
    # Criar alguns boletos atrasados (overdue) e pagos (paid)
    for i, s in enumerate(students[:5]):
        Payment.objects.get_or_create(
            tenant=tenant, student=s, description=f"Mensalidade {s.first_name}",
            defaults={
                'amount': 299.90, 'status': PaymentStatus.OVERDUE, 
                'due_date': now.date() - timedelta(days=5),
            }
        )
    for i, s in enumerate(students[5:10]):
        Payment.objects.get_or_create(
            tenant=tenant, student=s, description=f"Mensalidade {s.first_name}",
            defaults={
                'amount': 299.90, 'status': PaymentStatus.PAID, 
                'due_date': now.date() - timedelta(days=2),
                'paid_date': now.date() - timedelta(days=1),
                'paid_amount': 299.90
            }
        )

    # 3. Intakes (Comercial / Leads)
    print("Gerando Comercial (Leads)...")
    Intake.objects.get_or_create(tenant=tenant, name="Carlos Silva (Interessado)", defaults={'stage': IntakeStage.LEAD, 'created_at': now})
    Intake.objects.get_or_create(tenant=tenant, name="Marieta Pereira", defaults={'stage': IntakeStage.EVALUATION, 'created_at': now - timedelta(hours=5)})
    Intake.objects.get_or_create(tenant=tenant, name="Joao Augusto", defaults={'stage': IntakeStage.NEGOTIATION, 'created_at': now - timedelta(days=1)})
    Intake.objects.get_or_create(tenant=tenant, name="Ana Beatriz", defaults={'stage': IntakeStage.NEGOTIATION, 'created_at': now - timedelta(days=2)})

    # 4. Operations (Sessões para a Agenda)
    print("Gerando Agenda de Treinos (Sessões)...")
    Session.objects.get_or_create(tenant=tenant, name="Treino WOD Manha", start_time=now + timedelta(hours=1), defaults={'end_time': now + timedelta(hours=2)})
    Session.objects.get_or_create(tenant=tenant, name="CrossFit LPO", start_time=now + timedelta(hours=4), defaults={'end_time': now + timedelta(hours=5)})
    Session.objects.get_or_create(tenant=tenant, name="Treino Livre / Open Box", start_time=now + timedelta(hours=6), defaults={'end_time': now + timedelta(hours=7)})

    print("Seed Concluido com Sucesso! Volte ao painel e atualize a pagina.")

seed()
