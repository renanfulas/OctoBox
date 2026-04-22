import os
import json
import subprocess
import datetime
import sys

STATE_FILE = os.path.join(os.path.dirname(__file__), '..', 'trava_state.json')
LABELS = {1: "VERDE", 2: "ÂMBAR", 3: "VERMELHA"}

def get_state():
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    msg = f"TRAVA3_BACKUP_{timestamp}"
    print(f"📸 Iniciando backup preventivo: {msg}")
    res = run_cmd(f"git stash push -m {msg}")
    if res.returncode == 0:
        print("✅ Backup (Git Stash) concluído com sucesso.")
        return msg
    else:
        print(f"⚠️ Falha ao criar backup Git: {res.stderr}")
        return None

def status():
    state = get_state()
    level = state['level']
    print(f"\n--- STATUS PROTOCOLO RENANFULAS ---")
    print(f"Nível Atual: {level} ({state['label']})")
    print(f"Ativado em: {state['activated_at']}")
    print(f"Backup Ref: {state['backup_ref'] or 'Nenhum'}")
    print(f"------------------------------------\n")
    
    if level == 1:
        print("🟢 PERMISSÃO: Visual, CSS, Docs, Testes.")
    elif level == 2:
        print("🟡 PERMISSÃO: + Views, Queries, URLs, Forms.")
    elif level == 3:
        print("🔴 PERMISSÃO: BYPASS TOTAL (Elite Mode).")

def unlock(level):
    if level not in [1, 2, 3]:
        print("❌ Nível inválido. Use 1, 2 ou 3.")
        return

    state = get_state()
    if level == 3:
        print("🚨 ATENÇÃO: Nível 3 (VERMELHA) exige bypass total e backup.")
        confirm = input("Confirmar ativação do Protocolo Renanfulas Bypass? (S/N): ")
        if confirm.lower() != 's':
            print("❌ Operação cancelada.")
            return
        
        backup_ref = backup()
        state['backup_ref'] = backup_ref

    state['level'] = level
    state['label'] = LABELS[level]
    state['activated_at'] = datetime.datetime.now().isoformat()
    save_state(state)
    print(f"✅ Protocolo atualizado para Nível {level} ({LABELS[level]})")

def lock():
    state = get_state()
    state['level'] = 1
    state['label'] = "VERDE"
    state['activated_at'] = datetime.datetime.now().isoformat()
    state['backup_ref'] = None
    save_state(state)
    print("🟢 Sistema RETORNADO ao Nível 1 (VERDE). Segurança máxima restabelecida.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        status()
    else:
        cmd = sys.argv[1]
        if cmd == "status": status()
        elif cmd == "unlock" and len(sys.argv) == 3: unlock(int(sys.argv[2]))
        elif cmd == "lock": lock()
        elif cmd == "backup": backup()
        else: print("Comando desconhecido.")
