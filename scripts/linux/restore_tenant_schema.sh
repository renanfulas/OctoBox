#!/usr/bin/env bash

# Restore a tenant archive only into a newly-created isolated database whose
# shared/public rows come from a full archive of the same source database.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOST="127.0.0.1"
PORT="5432"
ADMIN_DATABASE="postgres"
TARGET_DATABASE=""
FORBID_DATABASE="octobox_control"
USER_NAME=""
SLUG=""
TENANT_BACKUP_FILE=""
TENANT_MANIFEST=""
BASE_BACKUP_FILE=""
BASE_MANIFEST=""

usage() {
  cat <<'USAGE'
Uso:
  PGPASSWORD='<senha>' bash scripts/linux/restore_tenant_schema.sh \
    --slug <box-slug> --user <role> \
    --backup-file backups/tenants/tenant-<slug>-AAAAmmdd-HHmmss.dump \
    --base-backup-file backups/octobox-AAAAmmdd-HHmmss.dump \
    [--tenant-manifest <tenant.dump.manifest.json>] \
    [--base-manifest <full.dump.manifest.json>] \
    [--target-database octobox_restore_<run-id>] [--host 127.0.0.1] [--port 5432]

O script exige um banco novo com prefixo octobox_restore_. Restaura primeiro o
backup full no laboratorio, substitui ali o schema-alvo e NUNCA escreve na origem.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --backup-file) TENANT_BACKUP_FILE="$2"; shift 2 ;;
    --tenant-manifest) TENANT_MANIFEST="$2"; shift 2 ;;
    --base-backup-file) BASE_BACKUP_FILE="$2"; shift 2 ;;
    --base-manifest) BASE_MANIFEST="$2"; shift 2 ;;
    --target-database) TARGET_DATABASE="$2"; shift 2 ;;
    --admin-database) ADMIN_DATABASE="$2"; shift 2 ;;
    --forbid-database) FORBID_DATABASE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "argumento desconhecido: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$USER_NAME" || -z "$SLUG" || -z "$TENANT_BACKUP_FILE" || -z "$BASE_BACKUP_FILE" ]]; then
  echo "erro: --slug, --user, --backup-file e --base-backup-file sao obrigatorios" >&2
  usage
  exit 2
fi
if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]{1,55}$ ]]; then
  echo "erro: --slug invalido" >&2
  exit 2
fi
if [[ -z "$TARGET_DATABASE" ]]; then
  echo "erro: informe --target-database com nome unico octobox_restore_<run-id>" >&2
  exit 2
fi
for database_name in "$TARGET_DATABASE" "$ADMIN_DATABASE" "$FORBID_DATABASE"; do
  if [[ ! "$database_name" =~ ^[a-z][a-z0-9_-]{0,62}$ ]]; then
    echo "erro: nome de banco de dados invalido" >&2
    exit 2
  fi
done
if [[ "$TARGET_DATABASE" != octobox_restore_* || "$TARGET_DATABASE" == "$FORBID_DATABASE" ]]; then
  echo "erro: destino deve ser um banco isolado com prefixo octobox_restore_" >&2
  exit 2
fi
if [[ ! -s "$TENANT_BACKUP_FILE" || ! -s "$BASE_BACKUP_FILE" ]]; then
  echo "erro: dump tenant ou base full ausente/vazio" >&2
  exit 3
fi

TENANT_MANIFEST="${TENANT_MANIFEST:-${TENANT_BACKUP_FILE}.manifest.json}"
BASE_MANIFEST="${BASE_MANIFEST:-${BASE_BACKUP_FILE}.manifest.json}"
SCHEMA="box_${SLUG}"
for binary in pg_restore psql createdb python3; do
  command -v "$binary" >/dev/null 2>&1 || { echo "erro: $binary nao encontrado no PATH" >&2; exit 3; }
done
if [[ ! -s "$TENANT_MANIFEST" || ! -s "$BASE_MANIFEST" ]]; then
  echo "erro: manifest tenant/full ausente; backup antigo nao pode ser usado por este fluxo" >&2
  exit 3
fi

target_server_version_num="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$ADMIN_DATABASE" -tAc 'SHOW server_version_num')"
pg_restore_version="$(pg_restore --version)"
python3 "$SCRIPT_DIR/tenant_backup_manifest.py" verify-restore \
  --tenant-dump "$TENANT_BACKUP_FILE" --tenant-manifest "$TENANT_MANIFEST" \
  --base-dump "$BASE_BACKUP_FILE" --base-manifest "$BASE_MANIFEST" \
  --schema "$SCHEMA" --target-database "$TARGET_DATABASE" \
  --target-server-version-num "$target_server_version_num" \
  --pg-restore-version "$pg_restore_version"

# Recheck archive readability before allocating the isolated database.
pg_restore --list "$BASE_BACKUP_FILE" >/dev/null
pg_restore --list "$TENANT_BACKUP_FILE" >/dev/null

db_exists="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$ADMIN_DATABASE" -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DATABASE}'")"
if [[ "$db_exists" == "1" ]]; then
  echo "erro: banco destino ja existe; use nome novo e nao reutilize estado de outra rodada" >&2
  exit 4
fi

echo "criando banco isolado ${TARGET_DATABASE} a partir de template0"
createdb --host "$HOST" --port "$PORT" --username "$USER_NAME" \
  --maintenance-db "$ADMIN_DATABASE" --template template0 --owner "$USER_NAME" "$TARGET_DATABASE"

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "restaurando base full (dados public compartilhados e schemas)"
pg_restore --host "$HOST" --port "$PORT" --username "$USER_NAME" --dbname "$TARGET_DATABASE" \
  --exit-on-error --no-owner --no-acl --no-tablespaces "$BASE_BACKUP_FILE"

# A tenant-only dump cannot recreate FKs or views owned by another schema.
# Inspect the restored full snapshot too: it can differ from the tenant manifest.
external_dependencies="$(psql -qAt -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" \
  -v ON_ERROR_STOP=1 -v tenant_schema="$SCHEMA" \
  -f "$SCRIPT_DIR/tenant_restore_external_dependencies.sql")"
if [[ ! "$external_dependencies" =~ ^[0-9]+$ || "$external_dependencies" != "0" ]]; then
  echo "erro: FKs ou views externas dependem do tenant; substituicao seletiva bloqueada antes do DROP" >&2
  exit 5
fi

# This drop is constrained to the newly-created isolated destination above. It
# replaces the target schema with the selected tenant archive exactly; it never
# executes against the source/live database.
schema_present="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -tAc \
  "SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA}'")"
if [[ "$schema_present" == "1" ]]; then
  psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -v ON_ERROR_STOP=1 \
    -c "DROP SCHEMA \"${SCHEMA}\" CASCADE"
fi

# The selective pg_dump archive contains the tenant objects but, as exercised
# against PostgreSQL 15, does not recreate the namespace after the full dump's
# schema is dropped. Create the empty namespace only in the isolated target.
psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -v ON_ERROR_STOP=1 \
  -c "CREATE SCHEMA \"${SCHEMA}\""

echo "restaurando tenant ${SCHEMA} sobre a base compartilhada isolada"
pg_restore --host "$HOST" --port "$PORT" --username "$USER_NAME" --dbname "$TARGET_DATABASE" \
  --schema "$SCHEMA" --exit-on-error --no-owner --no-acl --no-tablespaces "$TENANT_BACKUP_FILE"

table_count="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -tAc \
  "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='${SCHEMA}' AND c.relkind IN ('r','p')")"
invalid_fk_count="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -tAc \
  "SELECT count(*) FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='${SCHEMA}' AND c.contype='f' AND NOT c.convalidated")"
finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo
echo "tenant restaurado : ${SLUG}"
echo "schema            : ${SCHEMA}"
echo "banco isolado     : ${TARGET_DATABASE}"
echo "base full         : ${BASE_BACKUP_FILE}"
echo "dump tenant       : ${TENANT_BACKUP_FILE}"
echo "inicio / fim UTC  : ${started_at} -> ${finished_at}"
echo "tabelas tenant    : ${table_count}"
echo "FK nao validadas  : ${invalid_fk_count}"
if [[ "$table_count" == "0" || "$invalid_fk_count" != "0" ]]; then
  echo "ATENCAO: restore reprovado. Mantenha o laboratorio isolado para diagnostico." >&2
  exit 5
fi
echo "proximos gates obrigatorios, com DATABASE_URL apontando para ${TARGET_DATABASE}:"
echo "  python manage.py migrate_schemas --schema=${SCHEMA} --check --noinput"
echo "  python manage.py smoke_test_tenant --slug ${SLUG} --schema-only --restore-semantic"
echo "  conferir Box/Domain/Membership e StudentBoxMembership no snapshot compartilhado"
