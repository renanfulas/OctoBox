#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root." >&2
  exit 1
fi

: "${OCTOBOX_DOMAIN:=app.octoboxfit.com.br}"
: "${OCTOBOX_APP_USER:=octobox}"
: "${OCTOBOX_APP_GROUP:=octobox}"
: "${OCTOBOX_APP_HOME:=/srv/octobox}"
: "${OCTOBOX_REPO:=https://github.com/renanfulas/OctoBox.git}"
: "${OCTOBOX_BRANCH:=main}"
: "${OCTOBOX_DB_NAME:=octobox_control}"
: "${OCTOBOX_DB_USER:=octobox_app}"
: "${OCTOBOX_DB_PASSWORD:=}"
: "${OCTOBOX_RUNTIME_SLUG:=octoboxfit-production}"
: "${OCTOBOX_MANAGER_ENABLED:=True}"
: "${OCTOBOX_ADMIN_PATH:=}"
: "${OCTOBOX_SECRET_KEY:=}"
: "${OCTOBOX_PHONE_BLIND_INDEX_KEY:=}"

if [[ -z "${OCTOBOX_DB_PASSWORD}" || -z "${OCTOBOX_ADMIN_PATH}" || -z "${OCTOBOX_SECRET_KEY}" || -z "${OCTOBOX_PHONE_BLIND_INDEX_KEY}" ]]; then
  echo "Defina OCTOBOX_DB_PASSWORD, OCTOBOX_ADMIN_PATH, OCTOBOX_SECRET_KEY e OCTOBOX_PHONE_BLIND_INDEX_KEY." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt update
apt install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  libpq-dev \
  pkg-config \
  nginx \
  postgresql \
  postgresql-contrib \
  redis-server \
  certbot \
  python3-certbot-nginx

systemctl enable --now postgresql redis-server nginx

if ! id "${OCTOBOX_APP_USER}" >/dev/null 2>&1; then
  adduser --system --group --home "${OCTOBOX_APP_HOME}" "${OCTOBOX_APP_USER}"
fi

mkdir -p "${OCTOBOX_APP_HOME}/app" "${OCTOBOX_APP_HOME}/shared" "${OCTOBOX_APP_HOME}/backups" /run/octobox /var/www/certbot
chown -R "${OCTOBOX_APP_USER}:${OCTOBOX_APP_GROUP}" "${OCTOBOX_APP_HOME}" /run/octobox

if [[ ! -d "${OCTOBOX_APP_HOME}/app/.git" ]]; then
  sudo -u "${OCTOBOX_APP_USER}" git clone --branch "${OCTOBOX_BRANCH}" "${OCTOBOX_REPO}" "${OCTOBOX_APP_HOME}/app"
else
  sudo -u "${OCTOBOX_APP_USER}" git -C "${OCTOBOX_APP_HOME}/app" fetch origin
  sudo -u "${OCTOBOX_APP_USER}" git -C "${OCTOBOX_APP_HOME}/app" checkout "${OCTOBOX_BRANCH}"
  sudo -u "${OCTOBOX_APP_USER}" git -C "${OCTOBOX_APP_HOME}/app" pull --ff-only origin "${OCTOBOX_BRANCH}"
fi

sudo -u "${OCTOBOX_APP_USER}" python3 -m venv "${OCTOBOX_APP_HOME}/venv"
sudo -u "${OCTOBOX_APP_USER}" "${OCTOBOX_APP_HOME}/venv/bin/pip" install --upgrade pip
sudo -u "${OCTOBOX_APP_USER}" "${OCTOBOX_APP_HOME}/venv/bin/pip" install -r "${OCTOBOX_APP_HOME}/app/requirements.txt"

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${OCTOBOX_DB_USER}') THEN
      CREATE ROLE ${OCTOBOX_DB_USER} LOGIN PASSWORD '${OCTOBOX_DB_PASSWORD}';
   ELSE
      ALTER ROLE ${OCTOBOX_DB_USER} WITH LOGIN PASSWORD '${OCTOBOX_DB_PASSWORD}';
   END IF;
END
\$\$;
SQL

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${OCTOBOX_DB_NAME}'" | grep -q 1; then
  sudo -u postgres createdb -O "${OCTOBOX_DB_USER}" "${OCTOBOX_DB_NAME}"
fi

cat >"${OCTOBOX_APP_HOME}/shared/octobox.env" <<EOF
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=${OCTOBOX_SECRET_KEY}
PHONE_BLIND_INDEX_KEY=${OCTOBOX_PHONE_BLIND_INDEX_KEY}
DJANGO_ALLOWED_HOSTS=${OCTOBOX_DOMAIN}
DJANGO_CSRF_TRUSTED_ORIGINS=https://${OCTOBOX_DOMAIN}
DATABASE_URL=postgresql://${OCTOBOX_DB_USER}:${OCTOBOX_DB_PASSWORD}@127.0.0.1:5432/${OCTOBOX_DB_NAME}
DB_CONN_MAX_AGE=60
REDIS_URL=redis://127.0.0.1:6379/0
BOX_RUNTIME_SLUG=${OCTOBOX_RUNTIME_SLUG}
OPERATIONS_MANAGER_WORKSPACE_ENABLED=${OCTOBOX_MANAGER_ENABLED}
CACHE_IGNORE_EXCEPTIONS=True
CACHE_KEY_PREFIX=octobox
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
DJANGO_ADMIN_URL_PATH=${OCTOBOX_ADMIN_PATH}
SECURITY_TRUSTED_PROXY_IPS=
SECURITY_BLOCKED_IPS=
SECURITY_BLOCKED_IP_RANGES=
SECURITY_LOG_LEVEL=WARNING
LOGIN_RATE_LIMIT_MAX_REQUESTS=8
LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
ADMIN_RATE_LIMIT_MAX_REQUESTS=12
ADMIN_RATE_LIMIT_WINDOW_SECONDS=300
WRITE_RATE_LIMIT_MAX_REQUESTS=30
WRITE_RATE_LIMIT_WINDOW_SECONDS=60
EXPORT_RATE_LIMIT_MAX_REQUESTS=6
EXPORT_RATE_LIMIT_WINDOW_SECONDS=300
DASHBOARD_RATE_LIMIT_MAX_REQUESTS=30
DASHBOARD_RATE_LIMIT_WINDOW_SECONDS=60
HEAVY_READ_RATE_LIMIT_MAX_REQUESTS=30
HEAVY_READ_RATE_LIMIT_WINDOW_SECONDS=60
AUTOCOMPLETE_RATE_LIMIT_MAX_REQUESTS=60
AUTOCOMPLETE_RATE_LIMIT_WINDOW_SECONDS=60
EOF

chown "${OCTOBOX_APP_USER}:${OCTOBOX_APP_GROUP}" "${OCTOBOX_APP_HOME}/shared/octobox.env"
chmod 600 "${OCTOBOX_APP_HOME}/shared/octobox.env"

cat >/etc/systemd/system/octobox-gunicorn.service <<EOF
[Unit]
Description=OctoBOX Gunicorn service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=${OCTOBOX_APP_USER}
Group=${OCTOBOX_APP_GROUP}
WorkingDirectory=${OCTOBOX_APP_HOME}/app
EnvironmentFile=${OCTOBOX_APP_HOME}/shared/octobox.env
RuntimeDirectory=octobox
RuntimeDirectoryMode=0755
ExecStart=${OCTOBOX_APP_HOME}/venv/bin/gunicorn \\
  --workers 2 \\
  --bind unix:/run/octobox/gunicorn.sock \\
  --access-logfile - \\
  --error-logfile - \\
  --capture-output \\
  config.wsgi
Restart=always
RestartSec=5
TimeoutStopSec=30
KillMode=mixed
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/nginx/sites-available/octobox.http.conf <<EOF
upstream octobox_app {
    server unix:/run/octobox/gunicorn.sock;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${OCTOBOX_DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias ${OCTOBOX_APP_HOME}/app/staticfiles/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_redirect off;
        proxy_pass http://octobox_app;
    }
}
EOF

cat >/etc/nginx/sites-available/octobox.conf <<EOF
upstream octobox_app {
    server unix:/run/octobox/gunicorn.sock;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${OCTOBOX_DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${OCTOBOX_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${OCTOBOX_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${OCTOBOX_DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    client_max_body_size 20M;

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy strict-origin-when-cross-origin;

    location /static/ {
        alias ${OCTOBOX_APP_HOME}/app/staticfiles/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_redirect off;
        proxy_pass http://octobox_app;
    }
}
EOF

ln -sfn /etc/nginx/sites-available/octobox.http.conf /etc/nginx/sites-enabled/octobox.conf
rm -f /etc/nginx/sites-enabled/default

sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${OCTOBOX_APP_HOME}/app' && set -a && source '${OCTOBOX_APP_HOME}/shared/octobox.env' && set +a && '${OCTOBOX_APP_HOME}/venv/bin/python' manage.py migrate"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${OCTOBOX_APP_HOME}/app' && set -a && source '${OCTOBOX_APP_HOME}/shared/octobox.env' && set +a && '${OCTOBOX_APP_HOME}/venv/bin/python' manage.py collectstatic --noinput"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${OCTOBOX_APP_HOME}/app' && set -a && source '${OCTOBOX_APP_HOME}/shared/octobox.env' && set +a && '${OCTOBOX_APP_HOME}/venv/bin/python' manage.py bootstrap_roles"
sudo -u "${OCTOBOX_APP_USER}" bash -lc "cd '${OCTOBOX_APP_HOME}/app' && set -a && source '${OCTOBOX_APP_HOME}/shared/octobox.env' && set +a && '${OCTOBOX_APP_HOME}/venv/bin/python' manage.py check"

systemctl daemon-reload
systemctl enable --now octobox-gunicorn
nginx -t
systemctl restart nginx

if [[ ! -d "/etc/letsencrypt/live/${OCTOBOX_DOMAIN}" ]]; then
  certbot --nginx -d "${OCTOBOX_DOMAIN}" --non-interactive --agree-tos -m "infra@${OCTOBOX_DOMAIN#*.}" --redirect
fi

ln -sfn /etc/nginx/sites-available/octobox.conf /etc/nginx/sites-enabled/octobox.conf

systemctl restart nginx
systemctl restart octobox-gunicorn

echo "Bootstrap concluido."
echo "Crie o superusuario com:"
echo "sudo -u ${OCTOBOX_APP_USER} bash -lc 'cd ${OCTOBOX_APP_HOME}/app && set -a && source ${OCTOBOX_APP_HOME}/shared/octobox.env && set +a && ${OCTOBOX_APP_HOME}/venv/bin/python manage.py createsuperuser'"
