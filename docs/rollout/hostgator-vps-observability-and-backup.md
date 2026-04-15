<!--
ARQUIVO: guia enxuto de observabilidade e backup externo para HostGator VPS.

TIPO DE DOCUMENTO:
- runbook operacional

AUTORIDADE:
- alta para a rota atual de producao em VPS unica

DOCUMENTOS IRMAOS:
- [hostinger-vps-production-deploy.md](hostinger-vps-production-deploy.md)
- [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)
-->

# Observabilidade e backup externo na HostGator VPS

## Objetivo

Aplicar o maior retorno com o menor custo operacional agora:

1. backup diario automatico
2. copia externa automatica
3. retencao simples de 30 dias
4. check recorrente de runtime, disco e frescor do ultimo backup
5. webhook de alerta opcional

Em linguagem simples:

1. o backup e a copia da chave
2. o storage externo e a casa do vizinho confiavel
3. o runtime check e o porteiro que passa de hora em hora olhando se esta tudo de pe

## Recomendacao de baixo custo

Use `rclone` com um bucket S3-compatível barato.

Rota recomendada hoje:

1. Cloudflare R2

Motivo:

1. custo baixo
2. S3-compatible
3. boa aderencia ao stack que ja usa Cloudflare na borda

## Variaveis de ambiente novas

Adicionar em `/srv/octobox/shared/octobox.env`:

```env
OCTOBOX_BACKUP_REMOTE=r2:octobox-backups
OCTOBOX_BACKUP_REMOTE_PREFIX=octoboxfit-production
OCTOBOX_BACKUP_RETENTION_DAYS=30
OCTOBOX_BACKUP_MAX_AGE_HOURS=36
OCTOBOX_RUNTIME_DISK_THRESHOLD=85
OCTOBOX_ALERT_WEBHOOK_URL=
```

## Scripts novos

1. [../../scripts/linux/backup_and_sync_postgres.sh](../../scripts/linux/backup_and_sync_postgres.sh)
2. [../../scripts/linux/check_octobox_runtime.sh](../../scripts/linux/check_octobox_runtime.sh)

## Units novas

1. [../../infra/hostgator-vps/systemd/octobox-backup.service](../../infra/hostgator-vps/systemd/octobox-backup.service)
2. [../../infra/hostgator-vps/systemd/octobox-backup.timer](../../infra/hostgator-vps/systemd/octobox-backup.timer)
3. [../../infra/hostgator-vps/systemd/octobox-runtime-check.service](../../infra/hostgator-vps/systemd/octobox-runtime-check.service)
4. [../../infra/hostgator-vps/systemd/octobox-runtime-check.timer](../../infra/hostgator-vps/systemd/octobox-runtime-check.timer)

## Instalacao sugerida na VPS

```bash
sudo apt update
sudo apt install -y rclone
sudo cp /srv/octobox/app/infra/hostgator-vps/systemd/octobox-backup.service /etc/systemd/system/
sudo cp /srv/octobox/app/infra/hostgator-vps/systemd/octobox-backup.timer /etc/systemd/system/
sudo cp /srv/octobox/app/infra/hostgator-vps/systemd/octobox-runtime-check.service /etc/systemd/system/
sudo cp /srv/octobox/app/infra/hostgator-vps/systemd/octobox-runtime-check.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now octobox-backup.timer
sudo systemctl enable --now octobox-runtime-check.timer
```

## Configurar o remote do rclone

Exemplo conceitual:

```bash
rclone config
```

Criar um remote com nome:

1. `r2`

Depois apontar:

1. bucket: `octobox-backups`

## Politica recomendada

1. timer diario de backup as `03:15`
2. retencao de `30 dias`
3. runtime check a cada `5 minutos`
4. alerta via webhook apenas quando houver falha

## O que o runtime check valida

1. `octobox-gunicorn` ativo
2. `nginx` ativo
3. `postgresql` ativo
4. `redis-server` ativo
5. `https://app.octoboxfit.com.br/api/v1/health/` respondendo
6. disco abaixo do limite
7. ultimo backup ainda fresco

## Comandos de validacao

```bash
sudo systemctl status octobox-backup.timer --no-pager -l
sudo systemctl status octobox-runtime-check.timer --no-pager -l
sudo systemctl start octobox-backup.service
sudo systemctl start octobox-runtime-check.service
sudo journalctl -u octobox-backup.service -n 50 --no-pager
sudo journalctl -u octobox-runtime-check.service -n 50 --no-pager
```
