#!/usr/bin/env bash

# ARQUIVO: script Linux de backup do PostgreSQL para VPS.
#
# POR QUE ELE EXISTE:
# - permite backup repetivel do PostgreSQL em ambientes Linux como Hostinger VPS.
#
# O QUE ESTE ARQUIVO FAZ:
# 1. recebe host, porta, banco e usuario por argumento.
# 2. cria a pasta de destino se necessario.
# 3. executa pg_dump em formato custom.
# 4. falha cedo se faltar argumento essencial.
#
# PONTOS CRITICOS:
# - exige pg_dump instalado.
# - exige PGPASSWORD no ambiente ou .pgpass configurado.
# - nao envia o backup para storage externo; isso deve ser tratado pelo operador.

set -euo pipefail

HOST="127.0.0.1"
PORT="5432"
DATABASE=""
USER_NAME=""
OUTPUT_DIR="backups"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --database)
      DATABASE="$2"
      shift 2
      ;;
    --user)
      USER_NAME="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Argumento desconhecido: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${DATABASE}" ]]; then
  echo "--database e obrigatorio" >&2
  exit 1
fi

if [[ -z "${USER_NAME}" ]]; then
  echo "--user e obrigatorio" >&2
  exit 1
fi

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "PGPASSWORD nao definido. Exporte a senha no ambiente ou configure .pgpass." >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
DESTINATION="${OUTPUT_DIR}/octobox-${TIMESTAMP}.dump"

pg_dump \
  --host "${HOST}" \
  --port "${PORT}" \
  --username "${USER_NAME}" \
  --dbname "${DATABASE}" \
  --format custom \
  --file "${DESTINATION}"

echo "Backup PostgreSQL criado em ${DESTINATION}"
