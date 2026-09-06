#!/usr/bin/env bash
# setup_gdrive_backup.sh — ativa o Google Drive como destino SECUNDARIO de
# backup (Postgres diario + octobox.env cifrado a cada 7 dias), em paralelo
# com o R2 ja configurado por setup_r2_backup.sh. Nao remove nem substitui o R2.
#
# Pre-requisito (rodar ANTES deste script, na propria VPS, via SSH):
#   rclone config
# Escolha "n" (new remote), nome "gdrive" (ou o que passar em
# OCTOBOX_GDRIVE_REMOTE_NAME), tipo "drive". Na pergunta "Use auto config?"
# responda "n" (VPS sem navegador) — o rclone imprime um link para abrir em
# QUALQUER dispositivo com navegador; autorize a conta Google e cole o codigo
# de volta no terminal da VPS. Isso e OAuth de verdade contra sua conta
# Google — so voce pode autorizar, por isso este script nao automatiza esse
# passo.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_GDRIVE_REMOTE_NAME:=gdrive}"
: "${OCTOBOX_GDRIVE_FOLDER:=octobox-backups}"

ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

if ! command -v rclone >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt update
  apt install -y rclone
fi

if ! rclone listremotes | grep -qx "${OCTOBOX_GDRIVE_REMOTE_NAME}:"; then
  cat >&2 <<EOF
Remote rclone '${OCTOBOX_GDRIVE_REMOTE_NAME}' ainda nao existe.

Rode primeiro, interativo (precisa autorizar no navegador):
    rclone config

Escolha "n" (new remote), nome "${OCTOBOX_GDRIVE_REMOTE_NAME}", tipo "drive".
Em "Use auto config?" responda "n" e siga o link em outro dispositivo,
colando o codigo de volta aqui.

Depois rode este script de novo:
    sudo bash ${OCTOBOX_APP_HOME}/app/scripts/linux/setup_gdrive_backup.sh
EOF
  exit 1
fi

rclone mkdir "${OCTOBOX_GDRIVE_REMOTE_NAME}:${OCTOBOX_GDRIVE_FOLDER}"

OCTOBOX_BACKUP_REMOTE_SECONDARY="${OCTOBOX_GDRIVE_REMOTE_NAME}:${OCTOBOX_GDRIVE_FOLDER}" \
ENV_FILE_PATH="${ENV_FILE}" python3 <<'PY'
from pathlib import Path
import os

env_file = Path(os.environ["ENV_FILE_PATH"])
updates = {
    "OCTOBOX_BACKUP_REMOTE_SECONDARY": os.environ["OCTOBOX_BACKUP_REMOTE_SECONDARY"],
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

systemctl daemon-reload
if systemctl list-unit-files | grep -q '^octobox-backup.timer'; then
  systemctl restart octobox-backup.timer
fi
if systemctl list-unit-files | grep -q '^octobox-env-backup.timer'; then
  systemctl restart octobox-env-backup.timer
fi

echo
echo "Google Drive configurado como destino secundario de backup."
echo "Resumo final:"
echo "- remote: ${OCTOBOX_GDRIVE_REMOTE_NAME}:${OCTOBOX_GDRIVE_FOLDER}"
echo "- proximo backup do Postgres (diario, 03:15) tambem vai sincronizar pro Drive."
echo "- proximo backup do octobox.env (a cada 7 dias) tambem."
echo "- R2 continua ativo sem alteracao — este e um destino ADICIONAL, nao substitui."
