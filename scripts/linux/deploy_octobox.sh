#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_APP_GROUP:=octobox}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_BRANCH:=main}"
: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"

APP_DIR="${OCTOBOX_APP_HOME}/app"
VENV_PYTHON="${OCTOBOX_APP_HOME}/venv/bin/python"
ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"
STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
CURRENT_FILE="${STATE_DIR}/current_commit"
PREVIOUS_FILE="${STATE_DIR}/previous_commit"
LAST_BACKUP_FILE="${STATE_DIR}/last_backup_path"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "Repositorio nao encontrado em ${APP_DIR}." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

mkdir -p "${STATE_DIR}" "${OCTOBOX_APP_HOME}/backups"

current_commit="$(sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" rev-parse HEAD)"
echo "== OctoBOX Deploy =="
echo "App dir: ${APP_DIR}"
echo "Branch: ${OCTOBOX_BRANCH}"
echo "Current commit: ${current_commit}"

echo "== Pre-deploy backup =="
backup_path="$(sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && python3 - <<'PY'
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

database_url = os.environ['DATABASE_URL']
parsed = urlparse(database_url)
if parsed.scheme not in {'postgres', 'postgresql'}:
    raise SystemExit('DATABASE_URL nao aponta para PostgreSQL.')

host = parsed.hostname or '127.0.0.1'
port = str(parsed.port or 5432)
database = (parsed.path or '/').lstrip('/')
username = parsed.username or ''
password = parsed.password or ''

timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
destination = Path('${OCTOBOX_APP_HOME}/backups') / f'predeploy-{timestamp}.dump'
env = os.environ.copy()
env['PGPASSWORD'] = password

cmd = [
    'bash',
    '${APP_DIR}/scripts/linux/backup_postgres.sh',
    '--host', host,
    '--port', port,
    '--database', database,
    '--user', username,
    '--output-dir', '${OCTOBOX_APP_HOME}/backups',
]
subprocess.run(cmd, check=True, env=env)

created = sorted(Path('${OCTOBOX_APP_HOME}/backups').glob('octobox-*.dump'))
if not created:
    raise SystemExit('Backup nao foi criado.')
print(created[-1])
PY" | tail -n 1)"
echo "Backup criado em: ${backup_path}"
printf '%s\n' "${backup_path}" > "${LAST_BACKUP_FILE}"

echo "== Git sync =="
sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" fetch origin
sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" checkout "${OCTOBOX_BRANCH}"
sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" pull --ff-only origin "${OCTOBOX_BRANCH}"

echo "== Python deps =="
sudo -u "${OCTOBOX_APP_USER}" "${OCTOBOX_APP_HOME}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "== Django migrate/check/static =="
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && '${VENV_PYTHON}' manage.py migrate"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && '${VENV_PYTHON}' manage.py collectstatic --noinput"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && '${VENV_PYTHON}' manage.py check"

echo "== Static permissions =="
chmod 751 "${OCTOBOX_APP_HOME}"
chmod 755 "${APP_DIR}"
find "${APP_DIR}/staticfiles" -type d -exec chmod 755 {} \;
find "${APP_DIR}/staticfiles" -type f -exec chmod 644 {} \;

echo "== Restart services =="
systemctl restart octobox-gunicorn
systemctl is-active octobox-gunicorn

echo "== Healthcheck =="
curl -sk "https://${OCTOBOX_DOMAIN}/api/v1/health/"

new_commit="$(sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" rev-parse HEAD)"
printf '%s\n' "${current_commit}" > "${PREVIOUS_FILE}"
printf '%s\n' "${new_commit}" > "${CURRENT_FILE}"

echo
echo "Deploy concluido."
echo "Previous commit: ${current_commit}"
echo "Current commit: ${new_commit}"
echo "Backup: ${backup_path}"
