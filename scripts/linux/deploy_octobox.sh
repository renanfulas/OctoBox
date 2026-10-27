#!/usr/bin/env bash
set -euo pipefail

# Prepare an immutable release, then atomically switch `current` to it.
# This script is the single installation path used by the GitHub workflow.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_APP_GROUP:=octobox}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"

TARGET_SHA=""
DEPLOY_RUN_ID="manual"
while (($#)); do
  case "$1" in
    --sha)
      [[ $# -ge 2 ]] || { echo "--sha requer um SHA." >&2; exit 2; }
      TARGET_SHA="$2"
      shift 2
      ;;
    --run-id)
      [[ $# -ge 2 ]] || { echo "--run-id requer o ID da execução." >&2; exit 2; }
      DEPLOY_RUN_ID="$2"
      shift 2
      ;;
    *) echo "Argumento desconhecido: $1" >&2; exit 2 ;;
  esac
done
[[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "Informe --sha com SHA completo lowercase de 40 caracteres." >&2; exit 2; }
[[ "$DEPLOY_RUN_ID" =~ ^[a-zA-Z0-9._-]{1,80}$ ]] || { echo "ID da execução inválido." >&2; exit 2; }

APP_DIR="${OCTOBOX_APP_HOME}/app" # bare bootstrap checkout; never serves requests
RELEASES_DIR="${OCTOBOX_APP_HOME}/releases"
RELEASE_DIR="${RELEASES_DIR}/${TARGET_SHA}"
CURRENT_LINK="${OCTOBOX_APP_HOME}/current"
SHARED_DIR="${OCTOBOX_APP_HOME}/shared"
ENV_FILE="${SHARED_DIR}/octobox.env"
STATE_DIR="${SHARED_DIR}/deploy-state"
DEPLOYED_SHA_FILE="${STATE_DIR}/deployed_sha"
DEPLOY_RUN_FILE="${STATE_DIR}/deploy_run_id"
PREVIOUS_FILE="${STATE_DIR}/previous_commit"
CURRENT_FILE="${STATE_DIR}/current_commit"
LAST_BACKUP_FILE="${STATE_DIR}/last_backup_path"
STATIC_DIR="${SHARED_DIR}/staticfiles"
MEDIA_DIR="${SHARED_DIR}/media"
LOCK_FILE="${STATE_DIR}/deploy.lock"

[[ -e "${APP_DIR}/.git" ]] || { echo "Repositorio bootstrap ausente: ${APP_DIR}." >&2; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "Arquivo de ambiente ausente: ${ENV_FILE}." >&2; exit 1; }
install -d -m 0750 -o root -g "${OCTOBOX_APP_GROUP}" "${STATE_DIR}"
install -d -m 0750 -o "${OCTOBOX_APP_USER}" -g "${OCTOBOX_APP_GROUP}" "${RELEASES_DIR}"
install -d -m 0755 -o "${OCTOBOX_APP_USER}" -g "${OCTOBOX_APP_GROUP}" \
  "${STATIC_DIR}" "${MEDIA_DIR}" "${OCTOBOX_APP_HOME}/backups"
exec 9>"${LOCK_FILE}"
flock -n 9 || { echo "Outro deploy/rollback já está em andamento." >&2; exit 1; }

git_as_app() { sudo -u "${OCTOBOX_APP_USER}" git -C "${APP_DIR}" "$@"; }
run_as_app() { sudo -u "${OCTOBOX_APP_USER}" "$@"; }
run_django() {
  local release="$1"; shift
  sudo -u "${OCTOBOX_APP_USER}" bash -c '
    set -euo pipefail
    set -a
    source "$1"
    source "$2/.release.env"
    set +a
    cd "$2"
    "$2/venv/bin/python" manage.py "${@:3}"
  ' bash "${ENV_FILE}" "${release}" "$@"
}
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
try:
    body = json.loads(os.environ['RESPONSE'])
except (KeyError, json.JSONDecodeError):
    sys.exit(1)
expected = os.environ['EXPECTED_SHA']
if not body.get('healthy') or body.get('deployed_sha') != expected:
    sys.exit(1)
if body.get('loaded_sha') != expected or body.get('release_consistent') is not True:
    sys.exit(1)
PY
}
guard_existing_release() {
  # Never prepare in-place over an active, sealed or interrupted release.
  # A healthy active SHA is a no-op; every other existing destination requires
  # explicit operator recovery (or the rollback command for a sealed release).
  if [[ ! -e "${RELEASE_DIR}" && ! -L "${RELEASE_DIR}" ]]; then return 0; fi
  if [[ -L "${RELEASE_DIR}" || -z "${current_release}" || "${current_sha}" != "${TARGET_SHA}" ||
        "${current_release}" != "$(readlink -f "${RELEASE_DIR}")" ]]; then
    echo "Destino de release já existe e não é o SHA ativo; preparação bloqueada para preservar o artefato." >&2
    exit 1
  fi
  if [[ ! -e "${RELEASE_DIR}/.git" || ! -x "${RELEASE_DIR}/venv/bin/python" ||
        ! -f "${RELEASE_DIR}/.release-manifest" || ! -f "${RELEASE_DIR}/staticfiles/staticfiles.json" ]]; then
    echo "Release ativa incompleta; repetição não pode repará-la em uso." >&2
    exit 1
  fi
  local manifest_sha assets_sha actual_assets_sha
  manifest_sha="$(sed -n 's/^release_sha=//p' "${RELEASE_DIR}/.release-manifest")"
  assets_sha="$(sed -n 's/^asset_manifest_sha256=//p' "${RELEASE_DIR}/.release-manifest")"
  actual_assets_sha="$(sha256sum "${RELEASE_DIR}/staticfiles/staticfiles.json" | awk '{print $1}')"
  if [[ "${manifest_sha}" != "${TARGET_SHA}" || ! "${assets_sha}" =~ ^[0-9a-f]{64}$ ||
        "${assets_sha}" != "${actual_assets_sha}" ]] || ! health_matches "${TARGET_SHA}"; then
    echo "Release ativa não confirmou manifesto/health; nenhuma dependência ou ponteiro foi alterado." >&2
    exit 1
  fi
  echo "Release ${TARGET_SHA} já está ativa e saudável; repetição concluída sem preparar ou ativar novamente."
  exit 0
}

restore_previous_release() {
  # Activation overwrote previous_commit with the release being replaced.
  # A failed activation must restore the original rollback chain as well.
  if [[ "${previous_commit_present}" == 1 ]]; then
    write_atomic "${PREVIOUS_FILE}" "${previous_commit}"
  else
    rm -f "${PREVIOUS_FILE}"
  fi
  if [[ -n "${current_release}" && -d "${current_release}" ]]; then
    atomic_symlink "${current_release}"
    write_atomic "${DEPLOYED_SHA_FILE}" "${current_sha}"
    write_atomic "${DEPLOY_RUN_FILE}" "${current_run_id}"
    write_atomic "${CURRENT_FILE}" "${current_sha}"
    systemctl restart octobox-gunicorn || true
    if systemctl cat octobox-public-workout-rest-alerts.service >/dev/null 2>&1; then
      systemctl restart octobox-public-workout-rest-alerts || echo "ALERTA: rest-alert worker não reiniciou na release restaurada." >&2
    fi
    health_matches "${current_sha}" || echo "ALERTA: release anterior também não confirmou health." >&2
  else
    rm -f "${CURRENT_LINK}" "${DEPLOYED_SHA_FILE}" "${DEPLOY_RUN_FILE}" "${CURRENT_FILE}"
    systemctl stop octobox-gunicorn || true
    if systemctl cat octobox-public-workout-rest-alerts.service >/dev/null 2>&1; then
      systemctl stop octobox-public-workout-rest-alerts || echo "ALERTA: rest-alert worker não parou após falha da primeira ativação." >&2
    fi
  fi
}

previous_commit_present=0
previous_commit=""
if [[ -f "${PREVIOUS_FILE}" ]]; then
  previous_commit="$(cat "${PREVIOUS_FILE}")"
  previous_commit_present=1
fi

current_release=""
current_sha=""
current_run_id="manual"
if [[ -L "${CURRENT_LINK}" ]]; then
  current_release="$(readlink -f "${CURRENT_LINK}")"
  [[ -f "${current_release}/.release.env" ]] || { echo "Release current inválida: ${current_release}." >&2; exit 1; }
  current_sha="$(sed -n 's/^OCTOBOX_RELEASE_SHA=//p' "${current_release}/.release.env" | head -n 1)"
  current_run_id="$(sed -n 's/^github_run_id=//p' "${current_release}/.release-manifest" | head -n 1)"
  current_run_id="${current_run_id:-manual}"
fi

echo "== OctoBOX Release Deploy =="
echo "Target SHA: ${TARGET_SHA}"
echo "Current SHA: ${current_sha:-none}"

git_as_app fetch --no-tags origin "${TARGET_SHA}"
resolved_sha="$(git_as_app rev-parse "${TARGET_SHA}^{commit}")"
[[ "${resolved_sha}" == "${TARGET_SHA}" ]] || { echo "SHA resolvido não corresponde ao alvo." >&2; exit 1; }
main_sha="$(git_as_app ls-remote origin refs/heads/main | awk 'NR == 1 {print $1}')"
[[ "${main_sha}" == "${TARGET_SHA}" ]] || { echo "Release obsoleta: origin/main=${main_sha}, alvo=${TARGET_SHA}." >&2; exit 1; }

guard_existing_release

if [[ ! -e "${RELEASE_DIR}/.git" ]]; then
  [[ ! -e "${RELEASE_DIR}" ]] || { echo "Destino de release existe sem metadados Git: ${RELEASE_DIR}." >&2; exit 1; }
  git_as_app worktree add --detach "${RELEASE_DIR}" "${TARGET_SHA}"
fi
[[ -e "${RELEASE_DIR}/.git" ]] || { echo "Metadados da release ausentes." >&2; exit 1; }
[[ "$(sudo -u "${OCTOBOX_APP_USER}" git -C "${RELEASE_DIR}" rev-parse HEAD)" == "${TARGET_SHA}" ]] || { echo "Worktree imutável da release não confere." >&2; exit 1; }

# Per-release Python environment; a failed dependency install cannot alter the live one.
if [[ ! -x "${RELEASE_DIR}/venv/bin/python" ]]; then
  run_as_app python3 -m venv "${RELEASE_DIR}/venv"
fi
run_as_app "${RELEASE_DIR}/venv/bin/python" -m pip install --disable-pip-version-check -r "${RELEASE_DIR}/requirements.txt"
run_as_app "${RELEASE_DIR}/venv/bin/python" -m pip check

cat > "${RELEASE_DIR}/.release.env" <<EOF
OCTOBOX_RELEASE_SHA=${TARGET_SHA}
OCTOBOX_STATIC_ROOT=${RELEASE_DIR}/staticfiles
OCTOBOX_MEDIA_ROOT=${MEDIA_DIR}
EOF
chown "${OCTOBOX_APP_USER}:${OCTOBOX_APP_GROUP}" "${RELEASE_DIR}/.release.env"
chmod 0640 "${RELEASE_DIR}/.release.env"
cat > "${RELEASE_DIR}/.release-manifest" <<EOF
release_sha=${TARGET_SHA}
github_run_id=${DEPLOY_RUN_ID}
EOF
chown "${OCTOBOX_APP_USER}:${OCTOBOX_APP_GROUP}" "${RELEASE_DIR}/.release-manifest"
chmod 0640 "${RELEASE_DIR}/.release-manifest"

# Keep the existing operational PostgreSQL backup behavior before any migration.
if [[ ! -x "${RELEASE_DIR}/scripts/linux/backup_postgres.sh" ]]; then
  echo "Backup PostgreSQL indisponível nesta release; abortando." >&2
  exit 1
fi
backup_path="$(sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${RELEASE_DIR}' && set -a && source '${ENV_FILE}' && set +a && python3 - <<'PY'
import os, subprocess
from pathlib import Path
from urllib.parse import urlparse
database_url = urlparse(os.environ['DATABASE_URL'])
if database_url.scheme not in {'postgres', 'postgresql'}:
    raise SystemExit('DATABASE_URL nao aponta para PostgreSQL.')
backup_dir = Path('${OCTOBOX_APP_HOME}/backups')
before = set(backup_dir.glob('octobox-*.dump'))
env = os.environ.copy()
env['PGPASSWORD'] = database_url.password or ''
subprocess.run(['${RELEASE_DIR}/scripts/linux/backup_postgres.sh', '--host', database_url.hostname or '127.0.0.1', '--port', str(database_url.port or 5432), '--database', (database_url.path or '/').lstrip('/'), '--user', database_url.username or '', '--output-dir', str(backup_dir)], check=True, env=env)
created = sorted(set(backup_dir.glob('octobox-*.dump')) - before, key=lambda path: path.stat().st_mtime)
if not created:
    raise SystemExit('Backup novo nao foi identificado.')
print(created[-1])
PY" | tail -n 1)"
write_atomic "${LAST_BACKUP_FILE}" "${backup_path}"

echo "== Validate/prep release =="
mkdir -p "${RELEASE_DIR}/staticfiles"
chown -R "${OCTOBOX_APP_USER}:${OCTOBOX_APP_GROUP}" "${RELEASE_DIR}/staticfiles"
run_django "${RELEASE_DIR}" check
run_django "${RELEASE_DIR}" collectstatic --noinput
# Keep every hashed file for assets already referenced in open clients, while
# each release retains its own WhiteNoise manifest for rendering/rollback.
cp -a "${RELEASE_DIR}/staticfiles/." "${STATIC_DIR}/"
find "${STATIC_DIR}" -type d -exec chmod 755 {} +
find "${STATIC_DIR}" -type f -exec chmod 644 {} +
asset_manifest_sha256="$(sha256sum "${RELEASE_DIR}/staticfiles/staticfiles.json" | awk '{print $1}')"
printf 'asset_manifest_sha256=%s\n' "${asset_manifest_sha256}" >> "${RELEASE_DIR}/.release-manifest"
chown "${OCTOBOX_APP_USER}:${OCTOBOX_APP_GROUP}" "${RELEASE_DIR}/.release-manifest"
chmod 0640 "${RELEASE_DIR}/.release-manifest"

# Database changes are intentionally applied before activation. Releases must use
# expand/contract migrations so the still-running prior process remains compatible.
run_django "${RELEASE_DIR}" bootstrap_control
run_django "${RELEASE_DIR}" migrate --noinput
run_django "${RELEASE_DIR}" bootstrap_roles

# Application code and release metadata become read-only to the runtime account.
find "${RELEASE_DIR}" -path "${RELEASE_DIR}/venv" -prune -o -type d -exec chown root:"${OCTOBOX_APP_GROUP}" {} + -exec chmod 0755 {} +
find "${RELEASE_DIR}" -path "${RELEASE_DIR}/venv" -prune -o -type f -exec chown root:"${OCTOBOX_APP_GROUP}" {} + -exec chmod a-w {} +

echo "== Activate =="
if [[ -n "${current_sha}" ]]; then write_atomic "${PREVIOUS_FILE}" "${current_sha}"; fi
atomic_symlink "${RELEASE_DIR}"
write_atomic "${DEPLOYED_SHA_FILE}" "${TARGET_SHA}"
write_atomic "${DEPLOY_RUN_FILE}" "${DEPLOY_RUN_ID}"
write_atomic "${CURRENT_FILE}" "${TARGET_SHA}"
if ! systemctl restart octobox-gunicorn || ! systemctl is-active --quiet octobox-gunicorn; then
  echo "Gunicorn não iniciou a nova release; restaurando o ponteiro anterior." >&2
  restore_previous_release
  exit 1
fi

if systemctl cat octobox-public-workout-rest-alerts.service >/dev/null 2>&1; then
  systemctl restart octobox-public-workout-rest-alerts || echo "AVISO: rest-alert worker não reiniciou." >&2
  systemctl is-active octobox-public-workout-rest-alerts || echo "AVISO: rest-alert worker nao ficou ativo."
fi

if ! health_matches "${TARGET_SHA}"; then
  echo "Health não confirmou release ${TARGET_SHA}; restaurando ponteiro anterior." >&2
  restore_previous_release
  exit 1
fi

echo "Deploy concluído: ${TARGET_SHA}"
echo "Backup: ${backup_path}"
