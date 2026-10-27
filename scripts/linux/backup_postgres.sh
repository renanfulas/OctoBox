#!/usr/bin/env bash

# Full PostgreSQL archive with a PII-free integrity/version manifest.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOST="127.0.0.1"
PORT="5432"
DATABASE=""
USER_NAME=""
OUTPUT_DIR="backups"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --database) DATABASE="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Uso: PGPASSWORD='<senha>' bash $0 --database <db> --user <role> [--host host] [--port 5432] [--output-dir backups]"
      exit 0
      ;;
    *) echo "Argumento desconhecido: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$DATABASE" || -z "$USER_NAME" ]]; then
  echo "--database e --user sao obrigatorios" >&2
  exit 1
fi
if [[ ! "$DATABASE" =~ ^[a-z][a-z0-9_-]{0,62}$ ]]; then
  echo "--database invalido" >&2
  exit 1
fi
if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "PGPASSWORD nao definido. Exporte a senha ou configure .pgpass." >&2
  exit 1
fi
for binary in pg_dump psql python3; do
  command -v "$binary" >/dev/null 2>&1 || { echo "${binary} nao encontrado no PATH" >&2; exit 3; }
done

mkdir -p "$OUTPUT_DIR"
timestamp="$(date -u +%Y%m%d-%H%M%S)"
destination="${OUTPUT_DIR}/octobox-${timestamp}.dump"
partial_destination="${destination}.partial"
manifest="${destination}.manifest.json"
trap 'rm -f -- "$partial_destination"' EXIT

pg_dump --host "$HOST" --port "$PORT" --username "$USER_NAME" --dbname "$DATABASE" \
  --format custom --file "$partial_destination"
if [[ ! -s "$partial_destination" ]]; then
  echo "Dump PostgreSQL ausente ou vazio." >&2
  exit 1
fi
mv -- "$partial_destination" "$destination"

server_version="$(psql --host "$HOST" --port "$PORT" --username "$USER_NAME" \
  --dbname "$DATABASE" --tuples-only --no-align --command 'SHOW server_version')"
server_version_num="$(psql --host "$HOST" --port "$PORT" --username "$USER_NAME" \
  --dbname "$DATABASE" --tuples-only --no-align --command 'SHOW server_version_num')"
pg_dump_version="$(pg_dump --version)"
python3 "$SCRIPT_DIR/tenant_backup_manifest.py" create-full \
  --dump "$destination" --manifest "$manifest" --database "$DATABASE" \
  --server-version "$server_version" --server-version-num "$server_version_num" \
  --pg-dump-version "$pg_dump_version"
trap - EXIT

echo "Backup PostgreSQL criado em ${destination}"
echo "Manifesto PostgreSQL criado em ${manifest}"
