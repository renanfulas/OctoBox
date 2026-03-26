import os
import django
import sys
import time
import random

# Força output seguro sem unicode problemático no shell
sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from operations.services.contact_importer import import_contacts_from_list

print("=== INICIANDO TESTE DA BALEIA (TESTE 2) ===")
print("Gerando 50.000 contatos ficticios em memoria...")
start_gen = time.time()
contact_list = []
for i in range(50000):
    contact_list.append({
        "Nome": f"Aluno Mega Teste {i}",
        "Telefone": f"55119{random.randint(10000000, 99999999)}",
        "Email": f"aluno.teste{i}@octobox.test"
    })
print(f"Gerados em {time.time() - start_gen:.2f} segundos.")

print("\nAcionando o Motor de Ingestao (Bulk Create O(1))...")
start_import = time.time()

report = import_contacts_from_list(contact_list, source_platform='whatsapp', actor=None)

duration = time.time() - start_import

print("\n=== RESUMO DA INGESTAO ===")
print(f"Tempo total: {duration:.2f} segundos")
print(f"Velocidade: {50000 / duration:.2f} contatos por segundo")
print(f"Inseridos: {report['success']}")
print(f"Duplicados Ignorados: {report['duplicates']}")
print(f"Erros Fatais: {report['errors']}")

if duration < 45:
    print("\n[SUCESSO] Desempenho absurdo! Titulo Enterprise conquistado.")
else:
    print("\n[FALHA] Levou mais de 45s, a performance nao atingiu o alvo elitista.")
