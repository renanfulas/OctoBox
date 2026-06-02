<!--
ARQUIVO: runbook de DEPLOY — HostGator VPS de producao.
FONTE DA VERDADE (codigo vence este doc): scripts/linux/deploy_octobox.sh
-->

# Deploy — HostGator VPS

Um comando faz tudo, com backup pré-deploy automático e healthcheck no fim.

## Comando

```bash
sudo OCTOBOX_BRANCH=main bash /srv/octobox/app/scripts/linux/deploy_octobox.sh
```

(Domínio padrão `app.octoboxfit.com.br`; sobrescreva com `OCTOBOX_DOMAIN=...` se preciso.)

## O que o script faz, em ordem

1. **Backup pré-deploy** do PostgreSQL (`pg_dump` via `backup_postgres.sh`) → grava o caminho em `/srv/octobox/shared/deploy-state/last_backup_path`.
2. `git fetch` + `checkout main` + **`pull --ff-only`** (não force-push; falha se houver divergência).
3. `pip install -r requirements.txt` na venv `/srv/octobox/venv`.
4. **`manage.py migrate` + `collectstatic --noinput` + `check`** (lendo `/srv/octobox/shared/octobox.env`).
5. Ajusta permissões de `staticfiles/`.
6. **`systemctl restart octobox-gunicorn`** + confirma `is-active`.
7. **Healthcheck:** `curl https://app.octoboxfit.com.br/api/v1/health/`.
8. Registra `previous_commit` e `current_commit` em `deploy-state/` (é isso que o rollback usa).

## Validar

1. saída final mostra `Current commit` novo e `Backup: ...`;
2. `systemctl is-active octobox-gunicorn` = `active`;
3. healthcheck respondeu OK;
4. smoke pós-deploy → [smoke.md](smoke.md).

## Se algo quebrar

Voltar o código pro commit anterior → [rollback.md](rollback.md). O backup pré-deploy desta execução está em `deploy-state/last_backup_path` se precisar de restore de dados ([restore.md](restore.md)).
