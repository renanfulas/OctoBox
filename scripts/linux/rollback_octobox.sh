#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_APP_GROUP:=octobox}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"

STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
CURRENT_LINK="${OCTOBOX_APP_HOME}/current"
PREVIOUS_FILE="${STATE_DIR}/previous_commit"
CURRENT_FILE="${STATE_DIR}/current_commit"
DEPLOYED_SHA_FILE="${STATE_DIR}/deployed_sha"
[[ -f "${PREVIOUS_FILE}" ]] || { echo "Nenhum SHA anterior registrado." >&2; exit 1; }
[[ -L "${CURRENT_LINK}" ]] || { echo "Ponteiro current não é um symlink gerenciado." >&2; exit 1; }

exec 9>"${STATE_DIR}/deploy.lock"
flock -n 9 || { echo "Outro deploy/rollback já está em andamento." >&2; exit 1; }

current_release="$(readlink -f "${CURRENT_LINK}")"
current_sha="$(sed -n 's/^OCTOBOX_RELEASE_SHA=//p' "${current_release}/.release.env" | head -n 1)"
current_run_id="$(sed -n 's/^github_run_id=//p' "${current_release}/.release-manifest" | head -n 1)"
current_run_id="${current_run_id:-manual}"
target_sha="$(tr -d '\r\n' < "${PREVIOUS_FILE}")"
[[ "${current_sha}" =~ ^[0-9a-f]{40}$ && "${target_sha}" =~ ^[0-9a-f]{40}$ ]] || { echo "SHA de release inválido." >&2; exit 1; }
target_release="${OCTOBOX_APP_HOME}/releases/${target_sha}"
[[ -e "${target_release}/.git" && -x "${target_release}/venv/bin/python" ]] || { echo "Release anterior não está completa: ${target_release}." >&2; exit 1; }
[[ -f "${target_release}/staticfiles/staticfiles.json" ]] || { echo "Manifesto de estáticos da release anterior ausente." >&2; exit 1; }
[[ "$(sed -n 's/^OCTOBOX_RELEASE_SHA=//p' "${target_release}/.release.env" | head -n 1)" == "${target_sha}" ]] || { echo "Manifesto da release anterior não confere." >&2; exit 1; }
[[ "$(sed -n 's/^release_sha=//p' "${target_release}/.release-manifest" | head -n 1)" == "${target_sha}" ]] || { echo "Manifesto operacional da release anterior não confere." >&2; exit 1; }
expected_assets_sha="$(sed -n 's/^asset_manifest_sha256=//p' "${target_release}/.release-manifest" | head -n 1)"
actual_assets_sha="$(sha256sum "${target_release}/staticfiles/staticfiles.json" | awk '{print $1}')"
[[ "${expected_assets_sha}" =~ ^[0-9a-f]{64}$ && "${expected_assets_sha}" == "${actual_assets_sha}" ]] || { echo "Hash do manifesto de estáticos da release anterior não confere." >&2; exit 1; }

atomic_symlink() {
  local target="$1" tmp="${CURRENT_LINK}.next.$$"
  ln -sfn "$target" "$tmp"
  mv -Tf "$tmp" "${CURRENT_LINK}"
}
write_atomic() {
  local path="$1" value="$2" tmp
  tmp="${path}.tmp.$$"
  printf '%s\n' "$value" > "$tmp"
  chmod 0640 "$tmp"
  chown root:"${OCTOBOX_APP_GROUP}" "$tmp"
  mv -f "$tmp" "$path"
}
health_matches() {
  local expected="$1" response
  response="$(curl --fail --silent --show-error --max-time 15 "https://${OCTOBOX_DOMAIN}/api/v1/health/")" || return 1
  RESPONSE="$response" EXPECTED_SHA="$expected" python3 - <<'PY'
import json, os, sys
try: body = json.loads(os.environ['RESPONSE'])
except (KeyError, json.JSONDecodeError): sys.exit(1)
expected = os.environ['EXPECTED_SHA']
sys.exit(0 if body.get('healthy') and body.get('deployed_sha') == expected and body.get('loaded_sha') == expected and body.get('release_consistent') is True else 1)
PY
}
restore_current_release() {
  atomic_symlink "${current_release}"
  write_atomic "${PREVIOUS_FILE}" "${target_sha}"
  write_atomic "${CURRENT_FILE}" "${current_sha}"
  write_atomic "${DEPLOYED_SHA_FILE}" "${current_sha}"
  write_atomic "${OCTOBOX_APP_HOME}/shared/deploy-state/deploy_run_id" "${current_run_id}"
  systemctl restart octobox-gunicorn || true
  if systemctl cat octobox-public-workout-rest-alerts.service >/dev/null 2>&1; then
    systemctl restart octobox-public-workout-rest-alerts || echo "ALERTA: rest-alert worker não reiniciou na release restaurada." >&2
  fi
  health_matches "${current_sha}" || echo "ALERTA: health da release anterior também falhou." >&2
}

echo "== OctoBOX Release Rollback =="
echo "Current: ${current_sha}"
echo "Target: ${target_sha}"
echo "Aviso: migrations já aplicadas não são revertidas automaticamente; releases devem manter compatibilidade expand/contract."

sudo -u "${OCTOBOX_APP_USER}" "${target_release}/venv/bin/python" -m pip check
sudo -u "${OCTOBOX_APP_USER}" bash -c 'set -a; source "$1"; source "$2/.release.env"; set +a; cd "$2"; "$2/venv/bin/python" manage.py check' bash "${OCTOBOX_APP_HOME}/shared/octobox.env" "${target_release}"

atomic_symlink "${target_release}"
write_atomic "${PREVIOUS_FILE}" "${current_sha}"
write_atomic "${CURRENT_FILE}" "${target_sha}"
write_atomic "${DEPLOYED_SHA_FILE}" "${target_sha}"
target_run_id="$(sed -n 's/^github_run_id=//p' "${target_release}/.release-manifest" | head -n 1)"
write_atomic "${OCTOBOX_APP_HOME}/shared/deploy-state/deploy_run_id" "${target_run_id:-manual}"
if ! systemctl restart octobox-gunicorn || ! systemctl is-active --quiet octobox-gunicorn; then
  echo "Gunicorn não iniciou a release de rollback; restaurando o ponteiro original." >&2
  restore_current_release
  exit 1
fi
if systemctl cat octobox-public-workout-rest-alerts.service >/dev/null 2>&1; then
  systemctl restart octobox-public-workout-rest-alerts || echo "AVISO: rest-alert worker não reiniciou." >&2
fi

if ! health_matches "${target_sha}"; then
  echo "Health não confirmou rollback; restaurando release que estava ativa." >&2
  restore_current_release
  exit 1
fi

echo "Rollback concluído: ${target_sha}"
