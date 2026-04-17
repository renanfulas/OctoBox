#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_REPO_DIR:=${OCTOBOX_APP_HOME}/app}"
: "${SYSTEMD_DIR:=/etc/systemd/system}"

SERVICE_SOURCE="${OCTOBOX_REPO_DIR}/infra/hostgator-vps/systemd/octobox-nightly-lead-imports.service"
TIMER_SOURCE="${OCTOBOX_REPO_DIR}/infra/hostgator-vps/systemd/octobox-nightly-lead-imports.timer"
RUNNER_SOURCE="${OCTOBOX_REPO_DIR}/scripts/linux/run_due_nightly_lead_import_jobs.sh"

if [[ ! -f "${SERVICE_SOURCE}" ]]; then
  echo "Service template nao encontrado em ${SERVICE_SOURCE}." >&2
  exit 1
fi

if [[ ! -f "${TIMER_SOURCE}" ]]; then
  echo "Timer template nao encontrado em ${TIMER_SOURCE}." >&2
  exit 1
fi

if [[ ! -f "${RUNNER_SOURCE}" ]]; then
  echo "Runner script nao encontrado em ${RUNNER_SOURCE}." >&2
  exit 1
fi

chmod +x "${RUNNER_SOURCE}"
cp "${SERVICE_SOURCE}" "${SYSTEMD_DIR}/octobox-nightly-lead-imports.service"
cp "${TIMER_SOURCE}" "${SYSTEMD_DIR}/octobox-nightly-lead-imports.timer"

systemctl daemon-reload
systemctl enable --now octobox-nightly-lead-imports.timer

echo "Timer instalado com sucesso."
systemctl list-timers octobox-nightly-lead-imports.timer --no-pager
