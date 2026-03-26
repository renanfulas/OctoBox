import requests
import time
import sys

# Força output seguro
sys.stdout.reconfigure(encoding='utf-8')

URL = "http://127.0.0.1:8000/login/"
print("=== INICIANDO ATAQUE SIMULADO AO LOGIN (TESTE 3) ===")
print("Alvo: " + URL)
print("Disparando 15 requisicoes de POST em rajada...\n")

success_count = 0
blocked_count = 0

for i in range(1, 16):
    try:
        resp = requests.post(URL, data={"username": "hacker", "password": "123"}, timeout=5)
        
        if resp.status_code == 429:
            print(f"Req #{i:02d}: BLOQUEADO! (Status 429 - {resp.text})")
            blocked_count += 1
        elif resp.status_code == 200:
            print(f"Req #{i:02d}: Falhou Login, mas PASSOU a guardia (Status 200)")
            success_count += 1
        else:
            print(f"Req #{i:02d}: Status inesperado {resp.status_code}")
    except Exception as e:
        print(f"Req #{i:02d}: ERRO DE CONEXAO - O servidor esta rodando? ({str(e)})")
        break
    
    time.sleep(0.05)

print("\n=== RESUMO DO ATAQUE ===")
print(f"Requisicoes que passaram (esperado ~8): {success_count}")
print(f"Requisicoes bloqueadas pelo Guardiao: {blocked_count}")
if blocked_count > 0:
    print("[SUCESSO] O Rate Limiting esta ativo e esmagou o bot!")
else:
    print("[FALHA] O Rate Limiting nao defendeu.")
