#!/usr/bin/env bash
# deploy/healthcheck.sh — Monitora o app e envia alerta por email se cair.
# Cron: */5 * * * * root /srv/octobox/deploy/healthcheck.sh
#
# Pré-requisito: apt-get install -y mailutils
# Configure ALERT_EMAIL abaixo com seu email real.

HEALTH_URL="https://octoboxfit.com.br/api/v1/health/"
ALERT_EMAIL="seu@email.com.br"
LOCK_FILE="/tmp/octobox_down.lock"

HTTP_STATUS=$(curl --silent --max-time 10 --output /dev/null \
    --write-out "%{http_code}" "$HEALTH_URL" || echo "000")

if [ "$HTTP_STATUS" != "200" ]; then
    # Só envia alerta uma vez por incidente (até o app voltar)
    if [ ! -f "$LOCK_FILE" ]; then
        touch "$LOCK_FILE"
        echo "OctoBox FORA DO AR — status HTTP $HTTP_STATUS em $(date)" \
            | mail -s "[ALERTA] OctoBox down" "$ALERT_EMAIL"
        echo "[$(date)] ALERTA enviado — status $HTTP_STATUS"
    fi
else
    # App voltou — remove lock e notifica recuperação
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        echo "OctoBox VOLTOU ao ar em $(date)" \
            | mail -s "[OK] OctoBox recuperado" "$ALERT_EMAIL"
        echo "[$(date)] App recuperado."
    fi
fi
