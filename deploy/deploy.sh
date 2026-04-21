#!/usr/bin/env bash
# deploy/deploy.sh — Deploy manual no VPS. Rode como usuário octobox.
# Uso: bash deploy/deploy.sh
set -euo pipefail

APP_DIR="/srv/octobox"
cd "$APP_DIR"

echo "==> Pull origin/main..."
git fetch origin main
git reset --hard origin/main

echo "==> Dependências Python..."
.venv/bin/pip install --quiet -r requirements.txt

echo "==> Static files..."
.venv/bin/python manage.py collectstatic --noinput

echo "==> Migrations..."
.venv/bin/python manage.py migrate --noinput

echo "==> Roles..."
.venv/bin/python manage.py bootstrap_roles

echo "==> Reiniciando Gunicorn..."
sudo systemctl reload octobox || sudo systemctl restart octobox

echo "==> Pronto. Status:"
systemctl status octobox --no-pager -l
