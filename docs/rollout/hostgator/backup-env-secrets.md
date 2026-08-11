<!--
ARQUIVO: runbook de BACKUP CIFRADO do octobox.env — HostGator VPS de producao.
FONTE DA VERDADE (codigo vence este doc):
- scripts/linux/backup_env_secrets.sh
- scripts/linux/setup_env_secrets_backup.sh

POR QUE ELE EXISTE:
- ate 2026-08, so o Postgres tinha backup automatizado. O octobox.env so
  existia em disco na propria VPS (e em copias .bak- feitas a cada deploy,
  tambem na mesma VPS). Quando a VPS falhou antes de um backup local
  sobreviver, TODO o env se perdeu de uma vez — incluindo DJANGO_SECRET_KEY,
  que tambem e a chave de criptografia de PII (ver shared_support/crypto_fields.py).
  Isso fecha esse gap com uma copia externa, cifrada, fora da VPS.
-->

# Backup cifrado do `octobox.env` — HostGator VPS

O `octobox.env` nunca deve depender só do disco da própria VPS. Este backup
cifra o arquivo com [`age`](https://github.com/FiloSottile/age) e sobe pro
mesmo bucket R2 usado pelo Postgres, num prefixo separado (`env-secrets/`).

## Por que `age` e não só jogar no R2 direto

A VPS só recebe a **chave pública** (o "recipient", começa com `age1...`).
Com ela, o script consegue **cifrar e subir**, mas **nunca consegue decifrar**
os próprios backups. Isso é proposital: se a VPS for comprometida, sofrer
outro rebuild descontrolado, ou for acessada por alguém sem autorização, os
backups antigos continuam protegidos — a chave privada nunca esteve lá.

## 1. Setup (uma vez, e a chave privada nasce FORA da VPS)

Na sua máquina (não na VPS):
```bash
age-keygen -o octobox-env-backup-key.txt
# imprime algo como: Public key: age1qy3z9...
```
1. Guarde o **arquivo inteiro** (`octobox-env-backup-key.txt`, com a chave
   privada) num item do cofre de senhas do time (1Password/Bitwarden) — nunca
   no repositório, nunca em disco na VPS.
2. Copie só a **chave pública** (`age1...`) e rode na VPS:
```bash
sudo OCTOBOX_ENV_BACKUP_AGE_RECIPIENT='age1qy3z9...' \
     bash /srv/octobox/app/scripts/linux/setup_env_secrets_backup.sh
```
Isso instala `age`, grava a chave pública no próprio `octobox.env` (ela é
pública, não é segredo), instala o timer `octobox-env-backup.timer` (roda
a cada 10 dias — `octobox.env` muda muito menos que o banco, não precisa de
cadência diária) e dispara o primeiro
backup na hora.

> Pré-requisito: `setup_r2_backup.sh` já deve ter sido rodado antes (usa o
> mesmo remote `rclone` e o mesmo `OCTOBOX_BACKUP_REMOTE`).

## 2. Backup manual (sob demanda)

```bash
sudo bash /srv/octobox/app/scripts/linux/backup_env_secrets.sh
```

## 3. Restaurar (quando precisar de verdade)

Na sua máquina, com o arquivo de chave privada do cofre de senhas em mãos:
```bash
# baixe o .age mais recente do R2 (rclone já está configurado na VPS,
# ou use o painel/CLI do Cloudflare R2 direto)
rclone copy r2:octobox-backups/octoboxfit-production/env-secrets/ ./ --max-age 11d

age -d -i octobox-env-backup-key.txt octobox-env-<timestamp>.age > octobox.env.restaurado
```
Confira o conteúdo antes de sobrescrever `/srv/octobox/shared/octobox.env` —
principalmente `DJANGO_ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, que o
`deploy-vps.yml` reescreve a cada deploy e podem estar desatualizados no
backup mais antigo.

## Validar depois de CADA setup/mudança

1. `systemctl status octobox-env-backup.timer` → `active`;
2. `cat /srv/octobox/shared/deploy-state/last_env_backup_remote_path` aponta
   pro R2;
3. **Ensaie um restore de verdade** (baixar + decifrar num ambiente isolado,
   nunca sobrescrevendo produção) — quinzenal/mensal, junto do ensaio de
   restore do Postgres em [restore.md](restore.md). Backup nunca testado não
   é backup, é uma esperança.

## Failure checks — PARE e investigue se

- `OCTOBOX_ENV_BACKUP_AGE_RECIPIENT` vazio ou não começa com `age1`;
- timer inativo;
- `last_env_backup_remote_path` mais antigo que 11 dias (janela de 10 dias + folga);
- a chave privada não está confirmada no cofre de senhas do time — sem ela,
  todo esse backup é decorativo.
