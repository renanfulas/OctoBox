#!/usr/bin/env bash
# deploy/setup.sh — Roda UMA VEZ no VPS virgem para configurar tudo.
# Uso: bash setup.sh
set -euo pipefail

APP_USER="octobox"
APP_DIR="/srv/octobox"
REPO_URL="https://github.com/renanfulas/OctoBox.git"
PYTHON_VERSION="3.12"

echo "==> Atualizando pacotes..."
apt-get update -y
apt-get upgrade -y

echo "==> Instalando dependências do sistema..."
apt-get install -y \
    python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl ufw fail2ban

echo "==> Criando usuário da aplicação..."
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --shell /bin/bash "$APP_USER"

echo "==> Clonando repositório..."
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
fi

echo "==> Criando virtualenv e instalando dependências Python..."
sudo -u "$APP_USER" python${PYTHON_VERSION} -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Configurando PostgreSQL..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = 'octobox'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER octobox WITH PASSWORD 'TROQUE_ESTA_SENHA';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'octobox'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE octobox OWNER octobox;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE octobox TO octobox;"

echo "==> Configurando Redis (bind localhost apenas)..."
sed -i 's/^bind .*/bind 127.0.0.1 -::1/' /etc/redis/redis.conf
systemctl enable redis-server
systemctl restart redis-server

echo "==> Copiando arquivos de serviço systemd..."
cp "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/octobox.service
systemctl daemon-reload
systemctl enable octobox

echo "==> Copiando configuração do Nginx..."
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/octobox
ln -sf /etc/nginx/sites-available/octobox /etc/nginx/sites-enabled/octobox
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx

echo "==> Configurando firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo ""
echo "============================================================"
echo "PROXIMO PASSO: crie o arquivo de variáveis de ambiente:"
echo "  sudo nano /etc/octobox.env"
echo ""
echo "Conteúdo mínimo do .env (veja deploy/env.example):"
echo "  DJANGO_ENV=production"
echo "  DJANGO_SECRET_KEY=..."
echo "  DATABASE_URL=postgresql://octobox:SENHA@localhost/octobox"
echo "  REDIS_URL=redis://127.0.0.1:6379/0"
echo "  DJANGO_ALLOWED_HOSTS=seudominio.com.br"
echo ""
echo "Depois rode:"
echo "  sudo -u octobox /srv/octobox/.venv/bin/python manage.py migrate"
echo "  sudo -u octobox /srv/octobox/.venv/bin/python manage.py bootstrap_roles"
echo "  sudo -u octobox /srv/octobox/.venv/bin/python manage.py createsuperuser"
echo "  sudo systemctl start octobox"
echo "  sudo certbot --nginx -d seudominio.com.br"
echo "============================================================"
