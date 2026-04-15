#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"
: "${OCTOBOX_RCLONE_REMOTE_NAME:=r2}"
: "${OCTOBOX_R2_ACCOUNT_ID:=}"
: "${OCTOBOX_R2_ACCESS_KEY_ID:=}"
: "${OCTOBOX_R2_SECRET_ACCESS_KEY:=}"
: "${OCTOBOX_R2_BUCKET:=octobox-backups}"
: "${OCTOBOX_BACKUP_REMOTE_PREFIX:=octoboxfit-production}"
: "${OCTOBOX_BACKUP_RETENTION_DAYS:=30}"
: "${OCTOBOX_BACKUP_MAX_AGE_HOURS:=36}"
: "${OCTOBOX_RUNTIME_DISK_THRESHOLD:=85}"
: "${OCTOBOX_ALERT_WEBHOOK_URL:=}"

ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"
APP_DIR="${OCTOBOX_APP_HOME}/app"
STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
LAST_BACKUP_FILE="${STATE_DIR}/last_backup_path"
LAST_REMOTE_FILE="${STATE_DIR}/last_backup_remote_path"
RCLONE_CONFIG_DIR="/root/.config/rclone"
RCLONE_CONFIG_FILE="${RCLONE_CONFIG_DIR}/rclone.conf"

if [[ ! -d "${APP_DIR}" ]]; then
  echo "Aplicacao nao encontrada em ${APP_DIR}." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

if [[ -z "${OCTOBOX_R2_ACCOUNT_ID}" || -z "${OCTOBOX_R2_ACCESS_KEY_ID}" || -z "${OCTOBOX_R2_SECRET_ACCESS_KEY}" ]]; then
  echo "Defina OCTOBOX_R2_ACCOUNT_ID, OCTOBOX_R2_ACCESS_KEY_ID e OCTOBOX_R2_SECRET_ACCESS_KEY." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt update
apt install -y rclone

mkdir -p "${RCLONE_CONFIG_DIR}" "${STATE_DIR}"
chmod 700 "${RCLONE_CONFIG_DIR}"

rclone config create "${OCTOBOX_RCLONE_REMOTE_NAME}" s3 \
  provider Cloudflare \
  access_key_id "${OCTOBOX_R2_ACCESS_KEY_ID}" \
  secret_access_key "${OCTOBOX_R2_SECRET_ACCESS_KEY}" \
  endpoint "https://${OCTOBOX_R2_ACCOUNT_ID}.r2.cloudflarestorage.com" \
  acl private \
  no_check_bucket true \
  --non-interactive >/dev/null

chmod 600 "${RCLONE_CONFIG_FILE}"

ENV_FILE_PATH="${ENV_FILE}" python3 <<'PY'
from pathlib import Path
import os

env_file = Path(os.environ["ENV_FILE_PATH"])
updates = {
    "OCTOBOX_BACKUP_REMOTE": os.environ["OCTOBOX_BACKUP_REMOTE"],
    "OCTOBOX_BACKUP_REMOTE_PREFIX": os.environ["OCTOBOX_BACKUP_REMOTE_PREFIX"],
    "OCTOBOX_BACKUP_RETENTION_DAYS": os.environ["OCTOBOX_BACKUP_RETENTION_DAYS"],
    "OCTOBOX_BACKUP_MAX_AGE_HOURS": os.environ["OCTOBOX_BACKUP_MAX_AGE_HOURS"],
    "OCTOBOX_RUNTIME_DISK_THRESHOLD": os.environ["OCTOBOX_RUNTIME_DISK_THRESHOLD"],
    "OCTOBOX_ALERT_WEBHOOK_URL": os.environ.get("OCTOBOX_ALERT_WEBHOOK_URL", ""),
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

install -m 755 "${APP_DIR}/scripts/linux/backup_and_sync_postgres.sh" /usr/local/bin/backup_and_sync_postgres.sh
install -m 755 "${APP_DIR}/scripts/linux/check_octobox_runtime.sh" /usr/local/bin/check_octobox_runtime.sh
install -m 644 "${APP_DIR}/infra/hostgator-vps/systemd/octobox-backup.service" /etc/systemd/system/octobox-backup.service
install -m 644 "${APP_DIR}/infra/hostgator-vps/systemd/octobox-backup.timer" /etc/systemd/system/octobox-backup.timer
install -m 644 "${APP_DIR}/infra/hostgator-vps/systemd/octobox-runtime-check.service" /etc/systemd/system/octobox-runtime-check.service
install -m 644 "${APP_DIR}/infra/hostgator-vps/systemd/octobox-runtime-check.timer" /etc/systemd/system/octobox-runtime-check.timer

systemctl daemon-reload
systemctl enable --now octobox-backup.timer
systemctl enable --now octobox-runtime-check.timer
systemctl start octobox-backup.service
systemctl start octobox-runtime-check.service

echo
echo "Configuracao de backup externo concluida."
echo "Resumo final:"
echo "- remote rclone: ${OCTOBOX_RCLONE_REMOTE_NAME}"
echo "- bucket remoto: ${OCTOBOX_R2_BUCKET}"
echo "- caminho remoto base: ${OCTOBOX_BACKUP_REMOTE}"
if [[ -f "${LAST_BACKUP_FILE}" ]]; then
  echo "- ultimo backup local: $(cat "${LAST_BACKUP_FILE}")"
fi
if [[ -f "${LAST_REMOTE_FILE}" ]]; then
  echo "- ultimo backup remoto: $(cat "${LAST_REMOTE_FILE}")"
fi
echo "- timer backup: octobox-backup.timer"
echo "- timer runtime check: octobox-runtime-check.timer"
