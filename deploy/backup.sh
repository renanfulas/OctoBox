#!/usr/bin/env bash
# deploy/backup.sh — Backup diário do PostgreSQL + envio para Google Drive via rclone.
# Cron: 0 3 * * * octobox /srv/octobox/deploy/backup.sh >> /var/log/octobox-backup.log 2>&1
set -euo pipefail

BACKUP_DIR="/backups/octobox"
DB_NAME="octobox"
RETENTION_DAYS=30
RCLONE_REMOTE="gdrive:octobox-backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="octobox_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Iniciando backup..."

# Dump comprimido
pg_dump "$DB_NAME" | gzip > "$BACKUP_DIR/$FILENAME"

SIZE=$(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1)
echo "[$(date)] Dump gerado: $FILENAME ($SIZE)"

# Envia para Google Drive
if command -v rclone &>/dev/null; then
    rclone copy "$BACKUP_DIR/$FILENAME" "$RCLONE_REMOTE" --log-level INFO
    echo "[$(date)] Backup enviado para $RCLONE_REMOTE/$FILENAME"
else
    echo "[$(date)] AVISO: rclone nao encontrado. Backup salvo apenas localmente."
fi

# Remove backups locais antigos
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
echo "[$(date)] Backups locais com mais de 7 dias removidos."

# Verifica se rclone tem mais de RETENTION_DAYS arquivos e remove os mais antigos
if command -v rclone &>/dev/null; then
    rclone delete "$RCLONE_REMOTE" \
        --min-age "${RETENTION_DAYS}d" \
        --log-level INFO || true
    echo "[$(date)] Backups remotos com mais de ${RETENTION_DAYS} dias removidos."
fi

echo "[$(date)] Backup concluido."
