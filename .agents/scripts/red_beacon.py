import os
import sys
import json
import subprocess
import time

# Reutiliza o scanner de rotas limpo
SCANNER_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'scan_routes.py')
TRAVA_OPS = os.path.join(os.path.dirname(__file__), 'trava_ops.py')

def get_health():
    print("📡 Red Beacon: Escaneando rotas críticas...")
    subprocess.run(f"python {SCANNER_PATH} > $null 2>&1", shell=True)
    
    if not os.path.exists('scan_output.json'):
        return None
        
    with open('scan_output.json', 'r') as f:
        data = json.load(f)
        
    errors = [d for d in data if d['status'] != 200 and d['status'] != 302 and d['status'] != 403]
    return errors

def trigger_skybeam():
    print("\n" + "!"*60)
    print("☢️ VERTICAL SKYBEAM ATIVADO! ☢️")
    print("Muitos erros detectados pós-alteração. Infortúnio iminente.")
    print("Revertendo alterações via Git Stash e bloqueando sistema...")
    print("!"*60 + "\n")
    
    subprocess.run("git stash pop > $null 2>&1", shell=True)
    subprocess.run(f"python {TRAVA_OPS} lock", shell=True)
    sys.exit(1)

def main():
    errors = get_health()
    
    if errors is None:
        print("❌ Falha ao obter dados de saúde.")
        return

    error_count = len(errors)
    
    if error_count == 0:
        print("✅ Red Beacon: Sistema SAUDÁVEL. Nenhuma anomalia detectada.")
    elif error_count < 3:
        print(f"🟡 Red Beacon ATIVO: {error_count} erro(s) 500 detectado(s)!")
        for e in errors:
            print(f"  - {e['route']}: {e['detail']}")
        print("⚠️ Recomendado: Revisar alterações imediatamente.")
    else:
        trigger_skybeam()

if __name__ == "__main__":
    main()
