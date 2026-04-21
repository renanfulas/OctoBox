#!/usr/bin/env bash
# deploy/backup-setup.sh — Configura rclone + Google Drive e cron de backup.
# Roda UMA VEZ como root no VPS após o setup.sh.
set -euo pipefail

echo "==> Instalando rclone..."
curl https://rclone.org/install.sh | bash

echo ""
echo "==> Agora vamos conectar ao Google Drive."
echo "    Isso vai abrir um link — abra no seu navegador, autorize e cole o código aqui."
echo ""
rclone config create gdrive drive scope=drive

echo ""
echo "==> Criando pasta de backup no Google Drive..."
rclone mkdir gdrive:octobox-backups

echo "==> Criando diretório local de backups..."
mkdir -p /backups/octobox
chown octobox:octobox /backups/octobox

echo "==> Configurando cron de backup diário às 3h..."
cat > /etc/cron.d/octobox-backup << 'EOF'
# Backup diário do OctoBox — PostgreSQL -> Google Drive
0 3 * * * octobox /srv/octobox/deploy/backup.sh >> /var/log/octobox-backup.log 2>&1
EOF
chmod 644 /etc/cron.d/octobox-backup

echo "==> Rodando backup de teste agora..."
sudo -u octobox /srv/octobox/deploy/backup.sh

echo ""
echo "============================================================"
echo "Backup configurado. Verifique no Google Drive a pasta 'octobox-backups'."
echo "Logs em: tail -f /var/log/octobox-backup.log"
echo "============================================================"
