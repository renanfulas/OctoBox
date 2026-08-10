#!/usr/bin/env bash
# backup_env_secrets.sh — cifra octobox.env com age e sobe pro R2.
#
# Por que existe: octobox.env nunca foi coberto por backup (so o Postgres era).
# Se a VPS falhar antes de um deploy fazer o `cp` local do env, a copia se
# perde de vez — foi exatamente o que aconteceu (ver incidente de perda total
# de env em 2026-08). Este script fecha esse gap com uma copia externa cifrada.
#
# Design: a VPS so tem a CHAVE PUBLICA (age recipient) — ela consegue cifrar
# e subir, mas nunca consegue decifrar o proprio backup. A chave privada fica
# so no cofre de senhas do time, gerada fora da VPS (ver setup_env_secrets_backup.sh
# e docs/rollout/hostgator/backup-env-secrets.md). Isso significa que mesmo se
# a VPS for comprometida ou apagada, os backups antigos continuam protegidos.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT:=}"
: "${OCTOBOX_BACKUP_REMOTE:=}"
: "${OCTOBOX_BACKUP_REMOTE_PREFIX:=octoboxfit-production}"
: "${OCTOBOX_ENV_BACKUP_RETENTION_DAYS:=180}"

ENV_FILE="${OCTOBOX_APP_HOME}/shared/octobox.env"
STATE_DIR="${OCTOBOX_APP_HOME}/shared/deploy-state"
BACKUP_DIR="${OCTOBOX_APP_HOME}/backups/env-secrets"
LAST_ENV_BACKUP_FILE="${STATE_DIR}/last_env_backup_path"
LAST_ENV_REMOTE_FILE="${STATE_DIR}/last_env_backup_remote_path"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo de ambiente nao encontrado em ${ENV_FILE}." >&2
  exit 1
fi

if [[ -z "${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT}" ]]; then
  echo "OCTOBOX_ENV_BACKUP_AGE_RECIPIENT nao definido. Rode setup_env_secrets_backup.sh primeiro." >&2
  exit 1
fi

if [[ -z "${OCTOBOX_BACKUP_REMOTE}" ]]; then
  echo "OCTOBOX_BACKUP_REMOTE nao definido. Exemplo: r2:octobox-backups" >&2
  exit 1
fi

if ! command -v age >/dev/null 2>&1; then
  echo "age nao encontrado. Instale com 'apt install age'." >&2
  exit 1
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone nao encontrado. Rode setup_r2_backup.sh primeiro." >&2
  exit 1
fi

mkdir -p "${STATE_DIR}" "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

timestamp="$(date -u +%Y%m%d-%H%M%S)"
backup_name="octobox-env-${timestamp}.age"
backup_path="${BACKUP_DIR}/${backup_name}"

age -r "${OCTOBOX_ENV_BACKUP_AGE_RECIPIENT}" -o "${backup_path}" "${ENV_FILE}"
chmod 600 "${backup_path}"
printf '%s\n' "${backup_path}" > "${LAST_ENV_BACKUP_FILE}"

remote_target="${OCTOBOX_BACKUP_REMOTE}/${OCTOBOX_BACKUP_REMOTE_PREFIX}/env-secrets/${backup_name}"

echo "== OctoBOX Env Secrets Backup =="
echo "Backup local (cifrado): ${backup_path}"
echo "Destino remoto: ${remote_target}"

rclone copyto "${backup_path}" "${remote_target}"
printf '%s\n' "${remote_target}" > "${LAST_ENV_REMOTE_FILE}"

find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'octobox-env-*.age' -mtime +"$((OCTOBOX_ENV_BACKUP_RETENTION_DAYS - 1))" -delete
rclone delete "${OCTOBOX_BACKUP_REMOTE}/${OCTOBOX_BACKUP_REMOTE_PREFIX}/env-secrets" --min-age "${OCTOBOX_ENV_BACKUP_RETENTION_DAYS}d"

echo
echo "Backup do env cifrado e sincronizado."
echo "Resumo final:"
echo "- backup local: ${backup_path}"
echo "- backup remoto: ${remote_target}"
echo "- retencao: ${OCTOBOX_ENV_BACKUP_RETENTION_DAYS} dias"
echo "- lembrete: a chave PRIVADA age para decifrar este arquivo NAO esta na VPS."
echo "  Ela deve estar no cofre de senhas do time (ver docs/rollout/hostgator/backup-env-secrets.md)."
