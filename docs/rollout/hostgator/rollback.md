<!--
ARQUIVO: runbook de ROLLBACK — HostGator VPS de producao.
FONTE DA VERDADE (codigo vence este doc): scripts/linux/rollback_octobox.sh
-->

# Rollback — HostGator VPS

Volta o **código** pro commit anterior (registrado no último deploy). Rápido, sob estresse.

## Comando

```bash
sudo bash /srv/octobox/app/scripts/linux/rollback_octobox.sh
```

Usa `/srv/octobox/shared/deploy-state/previous_commit` como alvo. Faz `git checkout --force`, `pip install`, `collectstatic`, `check`, `restart octobox-gunicorn`, healthcheck — e troca `previous`/`current`.

## ⚠️ O que o rollback NÃO faz (o próprio script avisa)

> *"rollback rápido reposiciona o código. Não desfaz migrações de banco automaticamente."*

- Se o deploy ruim rodou uma **migração destrutiva** (dropou coluna/tabela, transformou dados), voltar só o código **não basta** — o schema novo continua lá e pode quebrar o código antigo.
- Nesse caso: **restore do banco** a partir do backup pré-deploy → [restore.md](restore.md) (o caminho está em `deploy-state/last_backup_path`).

## Decisão rápida

| sintoma | ação |
|---|---|
| bug de código, banco intacto | `rollback_octobox.sh` (basta) |
| migração mexeu/apagou dados | rollback **+** [restore.md](restore.md) |
| não sobe de jeito nenhum | rollback → se persistir, restore + investigar com `/master_debugger` |

## Validar

`systemctl is-active octobox-gunicorn` = `active` e healthcheck OK. Confira `current_commit` = o esperado.
