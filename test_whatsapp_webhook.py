"""
ARQUIVO: Teste Prático de Integração do WhatsApp Poll

Este script configura um aluno e uma aula de teste no banco de dados e
em seguida simula a chamada que o seu Robô do WhatsApp faria para o OctoBox.
"""

import os
import django
import json

# 1. CARREGAR AMBIENTE DO DJANGO
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.utils import timezone
from datetime import datetime, time

# Importar models
from students.model_definitions import Student
from operations.model_definitions import ClassSession, Attendance, AttendanceStatus


def rodar_teste_pratico():
    print("=== 🧪 INICIANDO TESTE PRÁTICO DO WEBHOOK ===\n")

    # --- PASSO 1: CONFIGURAR DADOS DE EXEMPLO ---
    telefone_teste = "5511999998888" # Telefone ficticio
    
    # 1.1 Criar ou buscar um Aluno para teste
    student, created = Student.objects.get_or_create(
        phone=telefone_teste,
        defaults={'full_name': "Pedro Whatsapp Teste"}
    )
    if not created:
         student.full_name = "Pedro Whatsapp Teste"
         student.save()
         
    print(f"✅ Aluno configurado: '{student.full_name}' - Tel: {student.phone}")

    # 1.2 Criar uma Aula para HOJE às 18h
    agora = timezone.now()
    horario_aula = timezone.make_aware(datetime.combine(agora.date(), time(hour=18, minute=0)))

    session, created = ClassSession.objects.get_or_create(
        scheduled_at=horario_aula,
        defaults={'title': "Crossfit WOD - Teste", 'capacity': 20}
    )
    print(f"✅ Aula configurada:  '{session.title}' às {session.scheduled_at.strftime('%H:%M')}\n")


    # --- PASSO 2: SIMULAR O ROBÕ ENVIANDO O VOTO ---
    client = Client()
    payload_do_robo = {
        "voter_phone": telefone_teste,
        "poll_name": "Check in - 23.MAR",
        "option_text": "18h" # <-- Horário votado 
    }

    print(f"📩 [ROBÔ] Enviando voto da enquete...")
    print(f"   Payload: {payload_do_robo}")
    
    # Dispara POST para o Webhook com um Host válido
    resposta = client.post(
        '/api/v1/integrations/whatsapp/webhook/poll-vote/',
        data=json.dumps(payload_do_robo),
        content_type='application/json',
        HTTP_HOST='localhost'
    )

    print(f"⬅️ [OCTOBOX] Resposta do Servidor: {resposta.status_code}")
    print(f"   Corpo: {resposta.content.decode('utf-8')}\n")


    # --- PASSO 3: VERIFICAR O RESULTADO NO BANCO ---
    presenca = Attendance.objects.filter(student=student, session=session).first()

    if presenca:
        print("📊 [BANCO] Resultado do Check-in:")
        print(f"   - Status: {presenca.status}")
        print(f"   - Origem: {presenca.reservation_source}")
        print(f"   - Aluno : {presenca.student.full_name}")
        print(f"   - Aula  : {presenca.session.title}")

        if presenca.status == AttendanceStatus.CHECKED_IN:
             print("\n🎉 SUCESSO! O aluno Pedro teve sua PRESENÇA MARCHADA automaticamente!\n")
             return

    print("\n❌ FALHA: A presença não foi registrada corretamente.")


if __name__ == "__main__":
    rodar_teste_pratico()
