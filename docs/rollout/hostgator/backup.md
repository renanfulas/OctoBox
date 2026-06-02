<!--
ARQUIVO: runbook de BACKUP do PostgreSQL — HostGator VPS de producao.

POR QUE ELE EXISTE:
- consolida o backup real (derivado dos scripts) num runbook curto e correto.

FONTE DA VERDADE (codigo vence este doc):
- scripts/linux/setup_r2_backup.sh        (setup unico: rclone + R2 + systemd timer)
- scripts/linux/backup_and_sync_postgres.sh (dump + sync R2 + retencao)
- scripts/linux/backup_postgres.sh        (pg_dump cru, baixo nivel)

CORRECAO vs docs antigos:
- automacao real e systemd timer (octobox-backup.timer), NAO cron.
- copia externa real e Cloudflare R2 via rclone, nao "storage externo" generico.
-->

# Backup — HostGator VPS

Banco: PostgreSQL local na própria VPS. Backup = **dump custom + cópia externa no Cloudflare R2**,
automatizado por **systemd timer**. Tudo já está nos scripts; este runbook é o como/quando/validar.

## 1. Setup (uma vez por máquina) — `setup_r2_backup.sh`

Configura rclone→R2, grava as vars de backup no `octobox.env` e instala+liga o timer systemd.

```bash
sudo OCTOBOX_R2_ACCOUNT_ID='<account>' \
     OCTOBOX_R2_ACCESS_KEY_ID='<key>' \
     OCTOBOX_R2_SECRET_ACCESS_KEY='<secret>' \
     OCTOBOX_BACKUP_REMOTE='r2:octobox-backups' \
     bash /srv/octobox/app/scripts/linux/setup_r2_backup.sh
```

Defaults embutidos: bucket `octobox-backups`, prefixo `octoboxfit-production`, retenção **30 dias**,
idade máx. aceitável **36h**, alerta de disco em **85%**. O script:
1. instala `rclone` e cria o remote `r2` (endpoint Cloudflare S3-compat);
2. escreve `OCTOBOX_BACKUP_REMOTE*` e retenção no `octobox.env`;
3. instala as units de `infra/hostgator-vps/systemd/` e dá `enable --now` em `octobox-backup.timer` e `octobox-runtime-check.timer`.

→ A partir daqui o backup roda sozinho. Confira: `systemctl status octobox-backup.timer`.

## 2. Backup manual (sob demanda) — `backup_and_sync_postgres.sh`

Antes de mudança grande, ou pra forçar uma cópia agora. Lê `DATABASE_URL` do `octobox.env`,
dumpa, sobe pro R2 e aplica retenção (local + remoto).

```bash
sudo bash /srv/octobox/app/scripts/linux/backup_and_sync_postgres.sh
```

Saída esperada (no fim): `backup local`, `backup remoto` e `retencao`. O caminho do último
backup fica em `/srv/octobox/shared/deploy-state/last_backup_path` e `last_backup_remote_path`.

> Pré-requisitos que o script exige (falha cedo se faltar): rodar como root, `octobox.env`
> presente, `OCTOBOX_BACKUP_REMOTE` definido, `rclone` instalado/configurado.

## 3. Dump cru (baixo nível / fora da VPS) — `backup_postgres.sh`

Só o `pg_dump` (sem R2). Útil para um dump pontual ou em outra máquina.

```bash
PGPASSWORD='<senha>' bash scripts/linux/backup_postgres.sh \
  --host 127.0.0.1 --port 5432 \
  --database octobox_control --user octobox_app \
  --output-dir /srv/octobox/backups
# -> octobox-AAAAmmdd-HHmmss.dump (formato custom)
```

## Validar depois de CADA backup

1. arquivo `octobox-*.dump` criado e **tamanho > 0**;
2. timestamp coerente com agora;
3. **cópia remota confirmada** (`last_backup_remote_path` aponta pro R2);
4. `rclone lsf r2:octobox-backups/octoboxfit-production/ | tail` mostra o dump novo.

## Failure checks — PARE e investigue se:

- backup com arquivo **zero**;
- último backup **muito antigo** (> `OCTOBOX_BACKUP_MAX_AGE_HOURS`, padrão 36h);
- backup **só local**, sem cópia no R2 (disco da VPS morre = perde tudo junto);
- timer `octobox-backup.timer` **inativo** (`systemctl status`).

## Restore

Backup só vale se o restore foi ensaiado → ver [restore.md](restore.md). Faça um restore de prova
**quinzenal/mensal** em banco isolado.
