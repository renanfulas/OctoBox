#!/usr/bin/env bash

# Create a tenant-only archive plus a PII-free inventory manifest.
# The archive is NOT self-contained: cross-schema FK dependencies remain in public.

set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOST="127.0.0.1"
PORT="5432"
DATABASE=""
USER_NAME=""
SLUG=""
OUTPUT_DIR="backups/tenants"
PYTHON_BIN="python3"

usage() {
  cat <<'USAGE'
Uso:
  PGPASSWORD='<senha>' bash scripts/linux/backup_tenant_schema.sh \
    --slug <box-slug> --database octobox_control --user octobox_app \
    [--host 127.0.0.1] [--port 5432] [--output-dir backups/tenants] [--python python3]

Gera um dump custom e <dump>.manifest.json. O manifesto lista dependencias,
migrations, grants e checksums sem copiar dados de linhas nem segredos.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --database) DATABASE="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --python) PYTHON_BIN="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "argumento desconhecido: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$DATABASE" || -z "$USER_NAME" || -z "$SLUG" ]]; then
  echo "erro: --slug, --database e --user sao obrigatorios" >&2
  usage
  exit 2
fi

if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]{1,55}$ ]]; then
  echo "erro: --slug deve ser um slug valido (letra inicial, letras minusculas, numeros e hifens)" >&2
  exit 2
fi

if [[ ! "$DATABASE" =~ ^[a-z][a-z0-9_-]{0,62}$ ]]; then
  echo "erro: --database invalido" >&2
  exit 2
fi

for binary in pg_dump pg_restore psql "$PYTHON_BIN" sha256sum; do
  command -v "$binary" >/dev/null 2>&1 || { echo "erro: $binary nao encontrado no PATH" >&2; exit 3; }
done

SCHEMA="box_${SLUG}"
schema_exists="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" -tAc \
  "SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA}'")"
if [[ "$schema_exists" != "1" ]]; then
  echo "erro: schema '${SCHEMA}' nao existe em ${DATABASE}" >&2
  exit 4
fi

mkdir -p "$OUTPUT_DIR"
timestamp="$(date -u +%Y%m%d-%H%M%S)"
destination="${OUTPUT_DIR}/tenant-${SLUG}-${timestamp}.dump"
partial_destination="${destination}.partial"
manifest="${destination}.manifest.json"
trap 'rm -f -- "$partial_destination"' EXIT

pg_dump --host "$HOST" --port "$PORT" --username "$USER_NAME" --dbname "$DATABASE" \
  --schema "$SCHEMA" --format c --file "$partial_destination"
if [[ ! -s "$partial_destination" ]]; then
  echo "erro: dump gerado com tamanho zero em ${partial_destination}" >&2
  exit 5
fi
mv -- "$partial_destination" "$destination"

server_version="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" -tAc 'SHOW server_version')"
server_version_num="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" -tAc 'SHOW server_version_num')"
pg_dump_version="$(pg_dump --version)"

# Catalog metadata contains identifiers and schema structure only; no row contents.
catalog_json="$(psql -qAt -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" -v tenant_schema="$SCHEMA" <<'SQL'
SELECT json_build_object(
  'object_counts', (
    SELECT json_build_object(
      'tables', count(*) FILTER (WHERE c.relkind IN ('r', 'p')),
      'views', count(*) FILTER (WHERE c.relkind IN ('v', 'm')),
      'sequences', count(*) FILTER (WHERE c.relkind = 'S'),
      'owned_sequences', count(*) FILTER (WHERE c.relkind = 'S' AND EXISTS (
        SELECT 1 FROM pg_depend d
        WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid
          AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
      ))
    )
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = :'tenant_schema'
  ),
  'cross_schema_foreign_keys', coalesce((
    SELECT json_agg(json_build_object(
      'direction', CASE WHEN sn.nspname = :'tenant_schema' THEN 'tenant_to_shared' ELSE 'shared_to_tenant' END,
      'source_schema', sn.nspname,
      'source_table', sc.relname,
      'source_columns', ARRAY(
        SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(attnum, ord)
        JOIN pg_attribute a ON a.attrelid = sc.oid AND a.attnum = k.attnum ORDER BY k.ord
      ),
      'target_schema', tn.nspname,
      'target_table', tc.relname,
      'target_columns', ARRAY(
        SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(attnum, ord)
        JOIN pg_attribute a ON a.attrelid = tc.oid AND a.attnum = k.attnum ORDER BY k.ord
      ),
      'delete_rule', CASE c.confdeltype WHEN 'a' THEN 'no_action' WHEN 'r' THEN 'restrict'
                       WHEN 'c' THEN 'cascade' WHEN 'n' THEN 'set_null' WHEN 'd' THEN 'set_default' END,
      'constraint_validated', c.convalidated
    ) ORDER BY sn.nspname, sc.relname, c.conname)
    FROM pg_constraint c
    JOIN pg_class sc ON sc.oid = c.conrelid JOIN pg_namespace sn ON sn.oid = sc.relnamespace
    JOIN pg_class tc ON tc.oid = c.confrelid JOIN pg_namespace tn ON tn.oid = tc.relnamespace
    WHERE c.contype = 'f' AND sn.nspname <> tn.nspname
      AND (sn.nspname = :'tenant_schema' OR tn.nspname = :'tenant_schema')
  ), '[]'::json),
  'extensions', coalesce((
    SELECT json_agg(json_build_object('name', e.extname, 'version', e.extversion, 'schema', en.nspname)
                    ORDER BY e.extname)
    FROM pg_extension e JOIN pg_namespace en ON en.oid = e.extnamespace
  ), '[]'::json),
  'grants', coalesce((
    SELECT json_agg(json_build_object(
      'object_type', CASE c.relkind WHEN 'S' THEN 'sequence' ELSE 'relation' END,
      'object_name', c.relname,
      'grantee', CASE acl.grantee WHEN 0 THEN 'PUBLIC' ELSE grantee.rolname END,
      'privilege', acl.privilege_type,
      'grantable', acl.is_grantable
    ) ORDER BY c.relname, grantee.rolname, acl.privilege_type)
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    CROSS JOIN LATERAL aclexplode(coalesce(c.relacl, acldefault(
      CASE WHEN c.relkind = 'S' THEN 'S'::"char" ELSE 'r'::"char" END, c.relowner
    ))) acl
    LEFT JOIN pg_roles grantee ON grantee.oid = acl.grantee
    WHERE n.nspname = :'tenant_schema' AND c.relkind IN ('r', 'p', 'v', 'm', 'S')
  ), '[]'::json),
  'schema_grants', coalesce((
    SELECT json_agg(json_build_object(
      'grantee', CASE acl.grantee WHEN 0 THEN 'PUBLIC' ELSE grantee.rolname END,
      'privilege', acl.privilege_type,
      'grantable', acl.is_grantable
    ) ORDER BY grantee.rolname, acl.privilege_type)
    FROM pg_namespace n
    CROSS JOIN LATERAL aclexplode(coalesce(n.nspacl, acldefault('n'::"char", n.nspowner))) acl
    LEFT JOIN pg_roles grantee ON grantee.oid = acl.grantee
    WHERE n.nspname = :'tenant_schema'
  ), '[]'::json)
)::text;
SQL
)"

migrations_json='{}'
migrations_exist="$(psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" -tAc \
  "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='${SCHEMA}' AND table_name='django_migrations')")"
if [[ "$migrations_exist" == "t" ]]; then
  migrations_json="$(psql -qAt -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" <<SQL
SELECT coalesce(json_object_agg(app, name), '{}'::json)::text
FROM (
  SELECT DISTINCT ON (app) app, name
  FROM "${SCHEMA}".django_migrations
  ORDER BY app, applied DESC, id DESC
) latest;
SQL
)"
fi

metadata_json="$("$PYTHON_BIN" -c 'import json,sys; m=json.loads(sys.argv[1]); m["latest_django_migrations"]=json.loads(sys.argv[2]); print(json.dumps(m,separators=(",",":")))' "$catalog_json" "$migrations_json")"
"$PYTHON_BIN" "$SCRIPT_DIR/tenant_backup_manifest.py" create-tenant \
  --dump "$destination" --manifest "$manifest" --schema "$SCHEMA" --database "$DATABASE" \
  --server-version "$server_version" --server-version-num "$server_version_num" \
  --pg-dump-version "$pg_dump_version" --metadata-json "$metadata_json"

trap - EXIT
size="$(du -h "$destination" | cut -f1)"
echo "backup do tenant  : ${SLUG}"
echo "schema            : ${SCHEMA}"
echo "arquivo           : ${destination}"
echo "manifesto         : ${manifest}"
echo "tamanho           : ${size}"
echo
echo "o dump nao inclui as linhas de public apontadas pelas FKs; use um full backup"
echo "compativel para restauracao isolada e valide todas as dependencias antes de uso."
