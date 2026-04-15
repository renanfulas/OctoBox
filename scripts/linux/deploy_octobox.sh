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

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "Repositorio nao encontrado em ${APP_DIR}." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

echo "== OctoBOX Deploy =="
echo "App dir: ${APP_DIR}"
echo "Branch: ${OCTOBOX_BRANCH}"

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

echo
echo "Deploy concluido."
