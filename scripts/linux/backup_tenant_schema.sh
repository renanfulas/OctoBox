#!/usr/bin/env bash

# ARQUIVO: script Linux de backup de UM tenant (schema box_<slug>) do PostgreSQL.
#
# POR QUE ELE EXISTE:
# - o backup full (backup_and_sync_postgres.sh) protege o cluster inteiro, mas recuperar
#   um box a partir dele obriga a voltar TODOS os boxes ao mesmo ponto no tempo.
# - a partir do segundo box pagante isso deixa de ser aceitavel: o erro de um cliente
#   nao pode custar o dia de trabalho dos outros.
#
# O QUE ESTE ARQUIVO FAZ:
# 1. valida que o schema box_<slug> existe antes de tentar qualquer coisa.
# 2. executa pg_dump restrito aquele schema, em formato custom.
# 3. grava o arquivo com slug e timestamp no nome, e confirma tamanho maior que zero.
#
# PONTOS CRITICOS:
# - este dump NAO inclui o schema public (control_box, control_domain, auth_user).
#   Restaurar so o schema de um box em um cluster onde o control plane perdeu a linha
#   daquele box devolve dados sem roteamento. Para desastre total do cluster, o dump
#   correto continua sendo o full.
# - exige pg_dump e psql instalados e PGPASSWORD no ambiente (ou .pgpass).
# - operacao de leitura apenas: nao altera nada no banco de origem.

set -euo pipefail

HOST="127.0.0.1"
PORT="5432"
DATABASE=""
USER_NAME=""
SLUG=""
OUTPUT_DIR="backups/tenants"

usage() {
  cat <<'USAGE'
Uso:
  PGPASSWORD='<senha>' bash scripts/linux/backup_tenant_schema.sh \
    --slug <box-slug> --database octobox_control --user octobox_app \
    [--host 127.0.0.1] [--port 5432] [--output-dir backups/tenants]

Gera: <output-dir>/tenant-<slug>-AAAAmmdd-HHmmss.dump (formato custom)
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
    -h|--help) usage; exit 0 ;;
    *) echo "argumento desconhecido: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$DATABASE" || -z "$USER_NAME" || -z "$SLUG" ]]; then
  echo "erro: --slug, --database e --user sao obrigatorios" >&2
  usage
  exit 2
fi

for binary in pg_dump psql; do
  command -v "$binary" >/dev/null 2>&1 || { echo "erro: $binary nao encontrado no PATH" >&2; exit 3; }
done

SCHEMA="box_${SLUG}"

# Falha cedo se o schema nao existir: um dump vazio de schema inexistente termina com
# exit 0 e produz um arquivo valido porem inutil — o pior tipo de backup.
schema_exists="$(
  psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$DATABASE" -tAc \
    "SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA}'"
)"

if [[ "$schema_exists" != "1" ]]; then
  echo "erro: schema '${SCHEMA}' nao existe em ${DATABASE}" >&2
  exit 4
fi

mkdir -p "$OUTPUT_DIR"
timestamp="$(date +%Y%m%d-%H%M%S)"
destination="${OUTPUT_DIR}/tenant-${SLUG}-${timestamp}.dump"

pg_dump \
  --host "$HOST" \
  --port "$PORT" \
  --username "$USER_NAME" \
  --dbname "$DATABASE" \
  --schema "$SCHEMA" \
  --format c \
  --file "$destination"

if [[ ! -s "$destination" ]]; then
  echo "erro: dump gerado com tamanho zero em ${destination}" >&2
  exit 5
fi

size="$(du -h "$destination" | cut -f1)"
echo "backup do tenant  : ${SLUG}"
echo "schema            : ${SCHEMA}"
echo "arquivo           : ${destination}"
echo "tamanho           : ${size}"
echo
echo "lembrete: este dump cobre apenas o schema do box. O schema public (control plane"
echo "e usuarios) continua coberto pelo backup full diario."
