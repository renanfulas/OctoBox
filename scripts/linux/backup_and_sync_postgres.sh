#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_BACKUP_RETENTION_DAYS:=30}"
: "${OCTOBOX_BACKUP_REMOTE:=}"
: "${OCTOBOX_BACKUP_REMOTE_PREFIX:=octobox-production}"

APP_DIR="${OCTOBOX_APP_HOME}/app"
ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"
STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
LAST_BACKUP_FILE="${STATE_DIR}/last_backup_path"
LAST_REMOTE_FILE="${STATE_DIR}/last_backup_remote_path"
BACKUP_DIR="${OCTOBOX_APP_HOME}/backups"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

if [[ -z "${OCTOBOX_BACKUP_REMOTE}" ]]; then
  echo "OCTOBOX_BACKUP_REMOTE nao definido. Exemplo: r2:octobox-backups" >&2
  exit 1
fi

mkdir -p "${STATE_DIR}" "${BACKUP_DIR}"

backup_path="$(
  sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && python3 - <<'PY'
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

database_url = os.environ['DATABASE_URL']
parsed = urlparse(database_url)
if parsed.scheme not in {'postgres', 'postgresql'}:
    raise SystemExit('DATABASE_URL nao aponta para PostgreSQL.')

host = parsed.hostname or '127.0.0.1'
port = str(parsed.port or 5432)
database = (parsed.path or '/').lstrip('/')
username = parsed.username or ''
password = parsed.password or ''

if not password:
    raise SystemExit('Senha PostgreSQL ausente no DATABASE_URL.')

env = os.environ.copy()
env['PGPASSWORD'] = password
cmd = [
    'bash',
    '${APP_DIR}/scripts/linux/backup_postgres.sh',
    '--host', host,
    '--port', port,
    '--database', database,
    '--user', username,
    '--output-dir', '${BACKUP_DIR}',
]
subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)

created = sorted(Path('${BACKUP_DIR}').glob('octobox-*.dump'))
if not created:
    raise SystemExit('Backup nao foi criado.')
print(created[-1])
PY"
)"

printf '%s\n' "${backup_path}" > "${LAST_BACKUP_FILE}"

backup_name="$(basename "${backup_path}")"
remote_target="${OCTOBOX_BACKUP_REMOTE}/${OCTOBOX_BACKUP_REMOTE_PREFIX}/${backup_name}"

echo "== OctoBOX Backup Sync =="
echo "Backup local: ${backup_path}"
echo "Destino remoto: ${remote_target}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone nao encontrado. Instale e configure um remote antes de usar sync externo." >&2
  exit 1
fi

rclone copyto "${backup_path}" "${remote_target}"
printf '%s\n' "${remote_target}" > "${LAST_REMOTE_FILE}"

find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'octobox-*.dump' -mtime +"$((OCTOBOX_BACKUP_RETENTION_DAYS - 1))" -delete
rclone delete "${OCTOBOX_BACKUP_REMOTE}/${OCTOBOX_BACKUP_REMOTE_PREFIX}" --min-age "${OCTOBOX_BACKUP_RETENTION_DAYS}d"
rclone rmdirs "${OCTOBOX_BACKUP_REMOTE}/${OCTOBOX_BACKUP_REMOTE_PREFIX}" --leave-root

echo
echo "Backup sincronizado."
echo "Resumo final:"
echo "- backup local: ${backup_path}"
echo "- backup remoto: ${remote_target}"
echo "- retencao: ${OCTOBOX_BACKUP_RETENTION_DAYS} dias"
