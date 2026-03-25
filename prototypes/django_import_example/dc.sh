#!/usr/bin/env bash
set -euo pipefail

CMD=""
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    CMD="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    CMD="docker-compose"
  fi
fi

if [ -z "$CMD" ]; then
  echo "Nenhum 'docker compose' ou 'docker-compose' encontrado no PATH." >&2
  exit 1
fi

exec $CMD "$@"
