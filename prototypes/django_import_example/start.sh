#!/usr/bin/env bash
set -euo pipefail

echo "Building and starting services..."
docker-compose up -d --build

echo "Running migrations..."
docker-compose run --rm web python manage.py migrate

read -p "Start Celery worker? (y/N) " yn
if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
  docker-compose up -d worker
fi

echo "Ambiente rodando em http://localhost:8000"
