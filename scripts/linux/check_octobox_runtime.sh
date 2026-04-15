#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_RUNTIME_DISK_THRESHOLD:=85}"
: "${OCTOBOX_BACKUP_MAX_AGE_HOURS:=36}"
: "${OCTOBOX_ALERT_WEBHOOK_URL:=}"

STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
LAST_BACKUP_FILE="${STATE_DIR}/last_backup_path"
HEALTH_URL="https://${OCTOBOX_DOMAIN}/api/v1/health/"
failures=()

notify_failure() {
  local message="$1"
  if [[ -n "${OCTOBOX_ALERT_WEBHOOK_URL}" ]]; then
    curl -fsS -X POST -H "Content-Type: application/json" \
      -d "{\"text\":\"${message//\"/\\\"}\"}" \
      "${OCTOBOX_ALERT_WEBHOOK_URL}" >/dev/null || true
  fi
}

check_service() {
  local service="$1"
  if ! systemctl is-active --quiet "${service}"; then
    failures+=("servico ${service} inativo")
  fi
}

check_service octobox-gunicorn
check_service nginx
check_service postgresql
check_service redis-server

if ! curl -fsS --max-time 10 "${HEALTH_URL}" >/dev/null; then
  failures+=("healthcheck falhou em ${HEALTH_URL}")
fi

disk_use="$(df -P "${OCTOBOX_APP_HOME}" | awk 'NR==2 {gsub("%","",$5); print $5}')"
if [[ -n "${disk_use}" && "${disk_use}" -ge "${OCTOBOX_RUNTIME_DISK_THRESHOLD}" ]]; then
  failures+=("uso de disco em ${OCTOBOX_APP_HOME} esta em ${disk_use}%")
fi

if [[ ! -f "${LAST_BACKUP_FILE}" ]]; then
  failures+=("ultimo backup nao registrado em ${LAST_BACKUP_FILE}")
else
  backup_path="$(tr -d '\r\n' < "${LAST_BACKUP_FILE}")"
  if [[ ! -f "${backup_path}" ]]; then
    failures+=("arquivo do ultimo backup nao existe: ${backup_path}")
  else
    backup_age_hours="$(( ( $(date +%s) - $(stat -c %Y "${backup_path}") ) / 3600 ))"
    if [[ "${backup_age_hours}" -gt "${OCTOBOX_BACKUP_MAX_AGE_HOURS}" ]]; then
      failures+=("ultimo backup tem ${backup_age_hours}h e passou do limite de ${OCTOBOX_BACKUP_MAX_AGE_HOURS}h")
    fi
  fi
fi

if (( ${#failures[@]} > 0 )); then
  echo "OctoBOX runtime check falhou:"
  for failure in "${failures[@]}"; do
    echo "- ${failure}"
  done
  notify_failure "OctoBOX runtime check falhou em ${OCTOBOX_DOMAIN}: ${failures[*]}"
  exit 1
fi

echo "OctoBOX runtime check OK"
echo "- dominio: ${OCTOBOX_DOMAIN}"
echo "- disco: ${disk_use}%"
if [[ -f "${LAST_BACKUP_FILE}" ]]; then
  echo "- ultimo backup: $(cat "${LAST_BACKUP_FILE}")"
fi
