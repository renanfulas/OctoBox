<!--
ARQUIVO: runbook de preservacao local antes de formatar a maquina.

TIPO DE DOCUMENTO:
- runbook operacional local

AUTORIDADE:
- alta para recuperacao do ambiente de desenvolvimento local

DOCUMENTOS IRMAOS:
- [backup-guide.md](backup-guide.md)
- [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)

QUANDO USAR:
- antes de formatar o computador de desenvolvimento
- ao restaurar um checkout local do OctoBOX depois da formatacao
- quando houver duvida sobre o que deve ir para Git e o que deve ficar fora

PONTOS CRITICOS:
- segredos e bancos locais nao devem ser commitados no Git
- backup sem teste de restauracao nao e protecao real
-->

# Runbook de formatacao e restore local

Este runbook preserva o ambiente local sem transformar o GitHub em cofre de segredo.

Pense em duas caixas:

1. GitHub guarda o codigo, historico, branches e docs.
2. Backup local seguro guarda segredos, banco local e arquivos privados.

## O que deve ir para o GitHub

1. codigo fonte
2. templates
3. CSS e JavaScript versionados
4. testes
5. docs e runbooks
6. scripts reutilizaveis sem segredo

## O que nao deve ir para o GitHub

1. `.env`
2. `.env.*`, exceto `.env.example`
3. `db.sqlite3`
4. `media/`
5. `backups/`
6. `.venv/`
7. `staticfiles/`
8. logs, caches e arquivos temporarios

## Backup minimo antes de formatar

Crie uma pasta fora do checkout do repo, de preferencia em um local sincronizado e privado, como OneDrive pessoal ou HD externo.

Exemplo:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = "$env:USERPROFILE\OneDrive\Documents\OctoBOX-local-backup-$stamp"
New-Item -ItemType Directory -Path $backupRoot
Copy-Item .env -Destination $backupRoot -ErrorAction SilentlyContinue
Copy-Item .env.homolog.local -Destination $backupRoot -ErrorAction SilentlyContinue
Copy-Item db.sqlite3 -Destination $backupRoot -ErrorAction SilentlyContinue
Copy-Item backups -Destination $backupRoot -Recurse -ErrorAction SilentlyContinue
git bundle create "$backupRoot\octobox-all-branches.bundle" --all
git status --short --branch > "$backupRoot\git-status.txt"
git branch -vv > "$backupRoot\git-branches.txt"
```

Se o backup for para nuvem, proteja a pasta ou compacte com senha antes de compartilhar qualquer arquivo.

## O que nao precisa salvar

1. `.venv/`: recrie com Python e `requirements.txt`
2. `staticfiles/`: recrie com `collectstatic` ou `sync_runtime_assets`
3. caches de teste e Python
4. logs temporarios
5. worktrees descartaveis de agentes, salvo se houver branch unica ainda nao publicada

## Restore depois da formatacao

Clone o repo:

```powershell
git clone https://github.com/renanfulas/OctoBox.git
cd OctoBox
```

Restaure arquivos privados do backup:

```powershell
Copy-Item "CAMINHO_DO_BACKUP\.env" . -ErrorAction SilentlyContinue
Copy-Item "CAMINHO_DO_BACKUP\.env.homolog.local" . -ErrorAction SilentlyContinue
Copy-Item "CAMINHO_DO_BACKUP\db.sqlite3" . -ErrorAction SilentlyContinue
Copy-Item "CAMINHO_DO_BACKUP\backups" . -Recurse -ErrorAction SilentlyContinue
```

Se alguma branch local nao tiver sido publicada por algum motivo, restaure pelo bundle:

```powershell
git fetch "CAMINHO_DO_BACKUP\octobox-all-branches.bundle" "refs/heads/*:refs/remotes/local-backup/*"
git branch -a
```

Recrie o ambiente:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Se assets locais parecerem desatualizados:

```powershell
.\.venv\Scripts\python.exe manage.py sync_runtime_assets --collectstatic
```

## Checklist de seguranca

1. confirme que `.env` nao aparece em `git status`
2. confirme que `db.sqlite3` nao aparece em `git status`
3. rode `git branch -vv` e confira se as branches importantes existem
4. rode os testes do escopo antes de continuar desenvolvimento
5. apague qualquer zip ou pasta de backup que tenha sido criada sem senha em local compartilhado
