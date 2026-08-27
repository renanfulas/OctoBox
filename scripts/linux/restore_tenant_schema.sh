#!/usr/bin/env bash

# ARQUIVO: script Linux de restore NAO DESTRUTIVO de um tenant em banco isolado.
#
# POR QUE ELE EXISTE:
# - separa a parte segura do restore por tenant (restaurar e conferir num banco de teste)
#   da parte perigosa (promover para o banco vivo).
# - a promocao NAO esta automatizada de proposito: ela troca dados de um cliente pagante
#   e deve ser executada passo a passo, com a rede de seguranca do ALTER SCHEMA RENAME.
#   O roteiro esta em docs/rollout/restore-and-rollback-drill.md, Parte C.
#
# O QUE ESTE ARQUIVO FAZ:
# 1. valida o arquivo de dump e as ferramentas necessarias.
# 2. cria o banco isolado de restore se ele nao existir.
# 3. recusa continuar se o schema alvo ja existir no banco isolado (evita mistura de rodadas).
# 4. restaura o schema do tenant e conta as tabelas restauradas como conferencia minima.
#
# PONTOS CRITICOS:
# - o parametro --target-database NUNCA deve apontar para o banco vivo. O script recusa
#   explicitamente o nome do banco de producao informado em --forbid-database.
# - restore nao valida regra de negocio: depois dele, rode
#   `python manage.py smoke_test_tenant --slug <slug>` apontando para o banco isolado.

set -euo pipefail

HOST="127.0.0.1"
PORT="5432"
ADMIN_DATABASE="postgres"
TARGET_DATABASE="octobox_restore_test"
FORBID_DATABASE="octobox_control"
USER_NAME=""
SLUG=""
BACKUP_FILE=""

usage() {
  cat <<'USAGE'
Uso:
  PGPASSWORD='<senha>' bash scripts/linux/restore_tenant_schema.sh \
    --slug <box-slug> --backup-file backups/tenants/tenant-<slug>-AAAAmmdd-HHmmss.dump \
    --user octobox_app \
    [--target-database octobox_restore_test] [--host 127.0.0.1] [--port 5432] \
    [--admin-database postgres] [--forbid-database octobox_control]

Restaura o schema box_<slug> num banco ISOLADO. Nunca aponte --target-database
para o banco vivo.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --backup-file) BACKUP_FILE="$2"; shift 2 ;;
    --target-database) TARGET_DATABASE="$2"; shift 2 ;;
    --admin-database) ADMIN_DATABASE="$2"; shift 2 ;;
    --forbid-database) FORBID_DATABASE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "argumento desconhecido: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$USER_NAME" || -z "$SLUG" || -z "$BACKUP_FILE" ]]; then
  echo "erro: --slug, --backup-file e --user sao obrigatorios" >&2
  usage
  exit 2
fi

if [[ "$TARGET_DATABASE" == "$FORBID_DATABASE" ]]; then
  echo "erro: --target-database aponta para o banco vivo ('${FORBID_DATABASE}')." >&2
  echo "      restore por tenant sempre roda em banco isolado." >&2
  exit 2
fi

if [[ ! -s "$BACKUP_FILE" ]]; then
  echo "erro: arquivo de backup ausente ou vazio: ${BACKUP_FILE}" >&2
  exit 3
fi

for binary in pg_restore psql createdb; do
  command -v "$binary" >/dev/null 2>&1 || { echo "erro: $binary nao encontrado no PATH" >&2; exit 3; }
done

SCHEMA="box_${SLUG}"

db_exists="$(
  psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$ADMIN_DATABASE" -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DATABASE}'"
)"

if [[ "$db_exists" != "1" ]]; then
  echo "banco isolado '${TARGET_DATABASE}' nao existe — criando"
  createdb -h "$HOST" -p "$PORT" -U "$USER_NAME" "$TARGET_DATABASE"
fi

# Uma rodada anterior deixada para tras faria o pg_restore sobrepor objetos e mascarar
# divergencia entre o dump e o que ja estava la. Melhor recusar e obrigar a limpeza.
schema_present="$(
  psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -tAc \
    "SELECT 1 FROM information_schema.schemata WHERE schema_name = '${SCHEMA}'"
)"

if [[ "$schema_present" == "1" ]]; then
  echo "erro: schema '${SCHEMA}' ja existe em '${TARGET_DATABASE}' (rodada anterior?)." >&2
  echo "      limpe antes:  DROP SCHEMA ${SCHEMA} CASCADE;" >&2
  exit 4
fi

started_at="$(date +%H:%M:%S)"

pg_restore \
  --host "$HOST" \
  --port "$PORT" \
  --username "$USER_NAME" \
  --dbname "$TARGET_DATABASE" \
  --schema "$SCHEMA" \
  --no-owner \
  "$BACKUP_FILE"

finished_at="$(date +%H:%M:%S)"

table_count="$(
  psql -h "$HOST" -p "$PORT" -U "$USER_NAME" -d "$TARGET_DATABASE" -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = '${SCHEMA}'"
)"

echo
echo "tenant restaurado : ${SLUG}"
echo "schema            : ${SCHEMA}"
echo "banco isolado     : ${TARGET_DATABASE}"
echo "arquivo           : ${BACKUP_FILE}"
echo "inicio / fim      : ${started_at} -> ${finished_at}"
echo "tabelas no schema : ${table_count}"
echo
if [[ "$table_count" == "0" ]]; then
  echo "ATENCAO: nenhuma tabela restaurada. Trate o restore como REPROVADO." >&2
  exit 5
fi
echo "proximo passo obrigatorio:"
echo "  python manage.py smoke_test_tenant --slug ${SLUG}   # com DATABASE_URL apontando para ${TARGET_DATABASE}"
