import concurrent.futures
import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

URL = "http://127.0.0.1:8000/login/"

print("=== INICIANDO O INCENDIO NA RECEPCAO (TESTE 1) ===")
print("Simulando 20 recepcionistas clicando no sistema ao mesmo tempo (Stress Test)...")

def fetch_url(url):
    try:
        # Acesso agressivo tentando derrubar as threads do servidor
        r = requests.get(url, timeout=5)
        return r.status_code
    except Exception as e:
        return 'ERR'

TOTAL_REQUESTS = 300
WORKERS = 20
success_ok = 0
dropped = 0

start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = [executor.submit(fetch_url, URL) for _ in range(TOTAL_REQUESTS)]
    for f in concurrent.futures.as_completed(futures):
        res = f.result()
        # Aceitamos 200 OK ou 429 Too Many Requests (se o Guardião segurar a onda)
        if type(res) == int and res in [200, 429]:
            success_ok += 1
        elif res == 'ERR':
            dropped += 1
        else:
            dropped += 1

duration = time.time() - start

print(f"\n=== RESUMO DO INCENDIO ===")
print(f"Disparos simultaneos: {TOTAL_REQUESTS}")
print(f"Tempo total para esvaziar a fila: {duration:.2f}s")
print(f"Conexoes Vivas (Toleradas ou Bloqueadas Seguramente): {success_ok}")
print(f"Conexoes Mortas (Timout/Queda): {dropped}")

if dropped == 0:
    print("\n[SUCESSO INTEGRAL] A Fortaleza brilhou. Nem um unico bit perdido sob fogo cruzado!")
else:
    print(f"\n[FALHA ACEITAVEL] Perdemos {dropped} requisicoes no servidor de desenvolvimento local (Single Node).")
