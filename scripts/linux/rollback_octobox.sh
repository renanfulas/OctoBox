#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"

APP_DIR="${OCTOBOX_APP_HOME}/app"
VENV_PYTHON="${OCTOBOX_APP_HOME}/venv/bin/python"
ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"
STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
CURRENT_FILE="${STATE_DIR}/current_commit"
PREVIOUS_FILE="${STATE_DIR}/previous_commit"
LAST_BACKUP_FILE="${STATE_DIR}/last_backup_path"

if [[ ! -f "${PREVIOUS_FILE}" ]]; then
  echo "Nenhum commit anterior registrado para rollback." >&2
  exit 1
fi

target_commit="$(tr -d '\r\n' < "${PREVIOUS_FILE}")"
current_commit="$(sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" rev-parse HEAD)"

if [[ -z "${target_commit}" ]]; then
  echo "Commit anterior vazio." >&2
  exit 1
fi

echo "== OctoBOX Rollback =="
echo "Current commit: ${current_commit}"
echo "Target commit: ${target_commit}"
if [[ -f "${LAST_BACKUP_FILE}" ]]; then
  echo "Ultimo backup conhecido: $(cat "${LAST_BACKUP_FILE}")"
fi
echo "Aviso: rollback rapido reposiciona o codigo. Nao desfaz migracoes de banco automaticamente."

sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" fetch --all --tags
sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" checkout --force "${target_commit}"
sudo -u "${OCTOBOX_APP_USER}" "${OCTOBOX_APP_HOME}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && '${VENV_PYTHON}' manage.py collectstatic --noinput"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${APP_DIR}' && set -a && source '${ENV_FILE}' && set +a && '${VENV_PYTHON}' manage.py check"

chmod 751 "${OCTOBOX_APP_HOME}"
chmod 755 "${APP_DIR}"
find "${APP_DIR}/staticfiles" -type d -exec chmod 755 {} \;
find "${APP_DIR}/staticfiles" -type f -exec chmod 644 {} \;

systemctl restart octobox-gunicorn
systemctl is-active octobox-gunicorn
curl -sk "https://${OCTOBOX_DOMAIN}/api/v1/health/"

printf '%s\n' "${current_commit}" > "${PREVIOUS_FILE}"
printf '%s\n' "${target_commit}" > "${CURRENT_FILE}"

echo
echo "Rollback concluido para ${target_commit}."
