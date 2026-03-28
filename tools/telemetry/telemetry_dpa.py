import os
import sys
import django
from django.test import Client
from django.urls import reverse
from django.db import connection, reset_queries

# Força o PYTHONPATH
sys.path.insert(0, os.getcwd())

# Monkeypatch settings before setup to disable DJDT
from django.conf import settings
import config.settings.development as dev_settings

# Copia as configurações de desenvolvimento
new_settings = {k: v for k, v in dev_settings.__dict__.items() if k.isupper()}

# Remove DJDT do MIDDLEWARE e INSTALLED_APPS
new_settings['MIDDLEWARE'] = [m for m in new_settings.get('MIDDLEWARE', []) if 'debug_toolbar' not in m]
new_settings['INSTALLED_APPS'] = [a for a in new_settings.get('INSTALLED_APPS', []) if 'debug_toolbar' not in a]

# Garante DEBUG True para contagem de queries
new_settings['DEBUG'] = True
new_settings['SECRET_KEY'] = 'telemetry-secret'
new_settings['ALLOWED_HOSTS'] = ['*', 'testserver']

# Força banco de dados se necessário (aqui já deve estar vindo do development.py)

if not settings.configured:
    settings.configure(**new_settings)
    
import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

def run_telemetry():
    print("\n--- OCTOBOX DPA TELEMETRY ---")
    
    # Usa o banco fisico para garantir que os apps e modelos existam
    print("📋 Usando banco fisico para telemetria...")
    
    # Setup User (Garantir um Owner para o dashboard)
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    User = get_user_model()
    
    user, created = User.objects.get_or_create(username='perf_telemetry')
    if created:
        user.set_password('pass')
        group, _ = Group.objects.get_or_create(name='Owner')
        user.groups.add(group)
        user.save()
    
    # Setup User
    user, _ = User.objects.get_or_create(username='perf_telemetry')
    user.set_password('pass')
    group, _ = Group.objects.get_or_create(name='Owner')
    user.groups.add(group)
    user.save()
    
    client = Client()
    if not client.login(username='perf_telemetry', password='pass'):
        print("❌ Falha no login da telemetria")
        return
    
    results = {}

    # 1. Dashboard Telemetry
    try:
        url = reverse('dashboard')
        reset_queries()
        client.get(url)
        results['dashboard'] = len(connection.queries)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"⚠️ Erro Dashboard: {e}")
        results['dashboard'] = "ERRO"

    # 2. Student Directory Telemetry
    try:
        url = reverse('student-directory')
        reset_queries()
        client.get(url)
        results['student-directory'] = len(connection.queries)
    except Exception as e:
        print(f"⚠️ Erro Alunos: {e}")
        results['student-directory'] = "ERRO"

    print("\n--- RESULTADOS REAIS (BASELINE) ---")
    for view, count in results.items():
        print(f"📍 {view}: {count} queries")
    print("-----------------------------------\n")

if __name__ == "__main__":
    run_telemetry()
