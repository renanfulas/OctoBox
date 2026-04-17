#!/usr/bin/env bash
set -euo pipefail

: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_ENV_FILE:=${OCTOBOX_APP_HOME}/shared/octobox.env}"
: "${OCTOBOX_APP_DIR:=${OCTOBOX_APP_HOME}/app}"
: "${OCTOBOX_VENV_PYTHON:=${OCTOBOX_APP_HOME}/venv/bin/python}"
: "${OCTOBOX_LEAD_IMPORT_NIGHT_SWEEP_LIMIT:=25}"

if [[ ! -d "${OCTOBOX_APP_DIR}" ]]; then
  echo "Diretorio da app nao encontrado em ${OCTOBOX_APP_DIR}." >&2
  exit 1
fi

if [[ ! -f "${OCTOBOX_ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${OCTOBOX_ENV_FILE}." >&2
  exit 1
fi

if [[ ! -x "${OCTOBOX_VENV_PYTHON}" ]]; then
  echo "Python da virtualenv nao encontrado em ${OCTOBOX_VENV_PYTHON}." >&2
  exit 1
fi

cd "${OCTOBOX_APP_DIR}"
set -a
source "${OCTOBOX_ENV_FILE}"
set +a

exec "${OCTOBOX_VENV_PYTHON}" manage.py run_due_nightly_lead_import_jobs --limit "${OCTOBOX_LEAD_IMPORT_NIGHT_SWEEP_LIMIT}"
