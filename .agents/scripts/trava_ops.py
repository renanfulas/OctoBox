import os
import json
import subprocess
import datetime
import sys

# Console do Windows costuma nao ser UTF-8 (cp1252/cp1250) — os prints deste
# script usam emoji, que quebram com UnicodeEncodeError nesse caso. Acontece
# tambem quando outro processo chama este script via subprocess com
# capture_output=True (o stdout deixa de ser um console de verdade). Forcar
# UTF-8 aqui evita o crash nos dois cenarios.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, 'encoding', '').lower() != 'utf-8':
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

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
    """Tira um snapshot do worktree atual SEM alterar a working tree e SEM
    tocar a pilha de stash do usuário.

    ANTES: usava `git stash push`, que REMOVE as mudanças atuais da working
    tree (era simultaneamente backup E desfazimento do trabalho em curso) e
    empilhava sobre stashes pré-existentes do usuário — um deles já achado
    no repo (`stash@{0}: wip: uncommitted wod changes...`), que seria
    atingido por um `stash pop` cego em revert().

    AGORA: `git stash create` grava o estado (index + worktree) num
    commit-object e devolve o hash — NADA muda na working tree. `git stash
    store` registra esse commit-object em refs/stash (para não ser coletado
    pelo `git gc`), sem remover nem reordenar entradas existentes. O hash
    retornado é o único identificador salvo em trava_state.json — nunca um
    índice de stash (`stash@{N}`), que desloca a cada novo `git stash`.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    msg = f"TRAVA3_BACKUP_{timestamp}"
    print(f"📸 Iniciando backup preventivo: {msg}")

    create_res = run_cmd("git stash create")
    if create_res.returncode != 0:
        print(f"⚠️ Falha ao criar snapshot Git: {create_res.stderr}")
        return None

    stash_hash = (create_res.stdout or "").strip()
    if not stash_hash:
        # Worktree limpo no momento do backup — nao ha o que reverter depois,
        # mas isso NAO e erro (ex.: nivel 3 ativado antes de qualquer edicao).
        print("ℹ️ Worktree sem mudanças pendentes — backup vazio (nada a reverter depois).")
        return "EMPTY"

    store_res = run_cmd(f'git stash store -m "{msg}" {stash_hash}')
    if store_res.returncode != 0:
        print(f"⚠️ Snapshot criado ({stash_hash[:10]}) mas falhou ao registrar em refs/stash "
              f"(pode ser coletado pelo git gc): {store_res.stderr}")
        # Ainda assim retorna o hash: aplicavel enquanto nao for coletado.
        return stash_hash

    print(f"✅ Backup concluído — snapshot {stash_hash[:10]}, worktree intocado.")
    return stash_hash


def revert():
    """Desfaz mudanças atuais e restaura o snapshot de trava_state.json['backup_ref'].

    LIMITAÇÃO CONHECIDA: `git stash create` não captura arquivos NÃO
    rastreados (novos). `git checkout -- .` também só descarta tracked.
    Arquivos novos criados depois do backup sobrevivem ao revert — rode
    `git status` depois e confira à mão. Não usamos `git clean` aqui de
    propósito: apagaria arquivos não relacionados à sessão sem confirmação.
    """
    state = get_state()
    ref = state.get('backup_ref')

    if not ref:
        print("❌ Nenhum backup_ref registrado em trava_state.json — nada para reverter.")
        return False

    # "EMPTY" significa "worktree ja estava limpo no momento do backup" — nao
    # significa "nao ha o que descartar agora". Se o agente editou algo DEPOIS
    # desse backup, o revert ainda precisa descartar essas edicoes e voltar
    # para HEAD; so nao ha stash pra reaplicar por cima (nao existia mudanca
    # nenhuma pra guardar). Pular o discard aqui era um bug: deixava a edicao
    # ruim intacta sempre que o backup tivesse sido tirado com worktree limpo.
    discard = run_cmd("git checkout -- .")
    if discard.returncode != 0:
        print(f"⚠️ Falha ao descartar mudanças atuais: {discard.stderr}")
        return False

    if ref == "EMPTY":
        print("✅ Worktree descartado e restaurado para HEAD (backup era de um estado limpo).")
        return True

    apply_res = run_cmd(f"git stash apply {ref}")
    if apply_res.returncode != 0:
        print(f"⚠️ Falha ao reaplicar snapshot {ref[:10]}: {apply_res.stderr}")
        return False

    print(f"✅ Worktree revertido para o snapshot {ref[:10]}.")
    print("   Verifique `git status` — arquivos NOVOS criados após o backup não são revertidos.")
    return True

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
        elif cmd == "revert": sys.exit(0 if revert() else 1)
        else: print("Comando desconhecido.")
