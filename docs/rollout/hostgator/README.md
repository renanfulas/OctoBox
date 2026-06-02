<!--
ARQUIVO: indice consolidado de operacao do servidor de producao (HostGator VPS).

POR QUE ELE EXISTE:
- a producao roda em UMA VPS HostGator; os docs antigos `hostinger-vps-*` descrevem
  ESTE servidor com o nome do provedor trocado (Hostinger != HostGator) e em alguns
  pontos desatualizados (cron vs systemd, "storage externo" generico vs Cloudflare R2).
- esta pasta consolida os runbooks corrigidos, DERIVADOS DOS SCRIPTS REAIS (codigo vence doc).

FONTE DA VERDADE:
- os scripts em `scripts/linux/*` e `scripts/hostgator_*` sao a verdade operacional.
- estes runbooks apenas explicam como/quando rodar e o que validar.

PONTOS CRITICOS:
- runbook de emergencia tem que ser curto e de proposito unico: um arquivo por operacao.
- nunca rode restore contra o banco vivo do cliente.
-->

# Operacao — HostGator VPS (producao)

Producao roda em **uma VPS HostGator** (dominio `app.octoboxfit.com.br`). Estes runbooks
sao **derivados dos scripts reais** — não da prosa antiga. Em conflito, o **script vence**.

> **Nota de correcao:** os docs `docs/rollout/hostinger-vps-*` descrevem este mesmo servidor
> com o nome do provedor trocado. Estao sendo substituidos por esta pasta. Ver `scripts/hostgator_bootstrap_octobox.py`, `scripts/linux/bootstrap_hostgator_octobox.sh`, `infra/hostgator-vps/`.

## Layout do servidor (assumido pelos scripts)

| caminho | papel |
|---|---|
| `/srv/octobox/app` | código da aplicação |
| `/srv/octobox/shared/octobox.env` | ambiente (contém `DATABASE_URL`, vars de backup R2) |
| `/srv/octobox/backups` | dumps locais do PostgreSQL |
| `/srv/octobox/shared/deploy-state/` | estado (`last_backup_path`, `last_backup_remote_path`) |
| `infra/hostgator-vps/systemd/` | units systemd (backup timer, runtime-check) |

## Runbooks por operacao

| operacao | runbook | script real |
|---|---|---|
| Backup (diário + cópia externa R2) | [backup.md](backup.md) | `scripts/linux/backup_and_sync_postgres.sh`, `scripts/linux/setup_r2_backup.sh` |
| Restore (em banco isolado) | [restore.md](restore.md) | `scripts/restore_postgres.ps1`, `pg_restore` |
| Deploy | [deploy.md](deploy.md) | `scripts/linux/deploy_octobox.sh` |
| Rollback | [rollback.md](rollback.md) | `scripts/linux/rollback_octobox.sh` |
| Bootstrap (máquina do zero) | [bootstrap.md](bootstrap.md) | `scripts/linux/bootstrap_hostgator_octobox.sh` |
| Smoke & runtime check | [smoke.md](smoke.md) | `scripts/smoke_http.py`, `scripts/linux/check_octobox_runtime.sh` |

## Regra de ouro

1. **Código é a verdade.** Se um runbook divergir do script, corrija o runbook.
2. **Restore nunca toca o banco vivo.** Sempre banco isolado.
3. **Backup sem cópia externa (R2) não é backup.** É só um arquivo no mesmo disco que pode morrer junto.
