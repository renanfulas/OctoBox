import os
import django
import sys

# Força output seguro
sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from operations.services.contact_importer import import_contacts_from_list
from onboarding.models import StudentIntake

print("=== TESTE DE PROTECAO CONTRA INJECAO (VIRUS CSV) ===")

# 1. Simula um contato com nome que tenta rodar uma fórmula (Ex: Soma ou Link malicioso)
malicious_contacts = [
    {"Nome": "=SUM(1,1)", "Telefone": "5511988887777", "Email": "hacker@test.com"},
    {"Nome": "+55-1234", "Telefone": "5511966665555", "Email": "atack@test.com"},
    {"Nome": "@Link", "Telefone": "5511911112222", "Email": "meta@test.com"}
]

print("Importando contatos 'maliciosos'...")
import_contacts_from_list(malicious_contacts, source_platform='whatsapp', actor=None)

# 2. Verifica como ficou no banco de dados
print("\nVerificando persistencia no Banco de Dados:")
for contact in malicious_contacts:
    saved = StudentIntake.objects.filter(phone=contact['Telefone']).first()
    if saved:
        print(f"Original: {contact['Nome']} -> Salvo: {saved.full_name}")
        if saved.full_name.startswith("'"):
            print("  [OK] Neutralizado com aspa simples.")
        else:
            print("  [ERRO] O valor esta desprotegido!")
    else:
        print(f"  [ERRO] Contato {contact['Nome']} nao encontrado.")

print("\n=== FIM DO TESTE ===")
