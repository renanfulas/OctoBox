#!/usr/bin/env bash
# setup_env_secrets_backup.sh — liga o backup cifrado do octobox.env (setup unico).
#
# Pre-requisito (rodar FORA da VPS, na sua maquina, uma vez):
#   age-keygen -o octobox-env-backup-key.txt
# Isso imprime "Public key: age1...". Guarde o ARQUIVO INTEIRO (chave privada)
# no cofre de senhas do time (1Password/Bitwarden) — nunca em disco na VPS,
# nunca no repositorio. Passe so a chave PUBLICA (age1...) para este script.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT:=}"
: "${OCTOBOX_ENV_BACKUP_RETENTION_DAYS:=180}"

ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"
APP_DIR="${OCTOBOX_APP_HOME}/app"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

if [[ -z "${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT}" ]]; then
  cat >&2 <<'EOF'
OCTOBOX_ENV_BACKUP_AGE_RECIPIENT nao definido.

Gere o par de chaves FORA da VPS primeiro (na sua maquina):
    age-keygen -o octobox-env-backup-key.txt

Guarde o arquivo inteiro no cofre de senhas do time. Depois rode este script:
    sudo OCTOBOX_ENV_BACKUP_AGE_RECIPIENT='age1...' \
         bash setup_env_secrets_backup.sh
EOF
  exit 1
fi

if [[ "${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT}" != age1* ]]; then
  echo "OCTOBOX_ENV_BACKUP_AGE_RECIPIENT nao parece uma chave publica age (deve comecar com 'age1')." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y age

OCTOBOX_ENV_BACKUP_AGE_RECIPIENT="${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT}" \
OCTOBOX_ENV_BACKUP_RETENTION_DAYS="${OCTOBOX_ENV_BACKUP_RETENTION_DAYS}" \
ENV_FILE_PATH="${ENV_FILE}" python3 <<'PY'
from pathlib import Path
import os

env_file = Path(os.environ["ENV_FILE_PATH"])
updates = {
    "OCTOBOX_ENV_BACKUP_AGE_RECIPIENT": os.environ["OCTOBOX_ENV_BACKUP_AGE_RECIPIENT"],
    "OCTOBOX_ENV_BACKUP_RETENTION_DAYS": os.environ["OCTOBOX_ENV_BACKUP_RETENTION_DAYS"],
}

lines = env_file.read_text(encoding="utf-8").splitlines()
positions = {}
for index, raw_line in enumerate(lines):
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key = stripped.split("=", 1)[0].strip()
    positions[key] = index

for key, value in updates.items():
    entry = f"{key}={value}"
    if key in positions:
        lines[positions[key]] = entry
    else:
        lines.append(entry)

env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

chmod 600 "${ENV_FILE}"

install -m 755 "${APP_DIR}/scripts/linux/backup_env_secrets.sh" /usr/local/bin/backup_env_secrets.sh
install -m 644 "${APP_DIR}/infra/hostgator-vps/systemd/octobox-env-backup.service" /etc/systemd/system/octobox-env-backup.service
install -m 644 "${APP_DIR}/infra/hostgator-vps/systemd/octobox-env-backup.timer" /etc/systemd/system/octobox-env-backup.timer

systemctl daemon-reload
systemctl enable --now octobox-env-backup.timer
systemctl start octobox-env-backup.service

echo
echo "Backup cifrado do env configurado."
echo "Resumo final:"
echo "- chave publica (recipient): ${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT}"
echo "- retencao: ${OCTOBOX_ENV_BACKUP_RETENTION_DAYS} dias"
echo "- timer: octobox-env-backup.timer"
echo "- LEMBRETE CRITICO: a chave PRIVADA precisa estar no cofre de senhas do time."
echo "  Sem ela, os backups cifrados sao inuteis. Confirme isso agora antes de seguir."
