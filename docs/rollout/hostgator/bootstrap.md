<!--
ARQUIVO: runbook de BOOTSTRAP (provisionar a maquina do zero) — HostGator VPS.
FONTE DA VERDADE (codigo vence este doc): scripts/linux/bootstrap_hostgator_octobox.sh
-->

# Bootstrap — HostGator VPS (do zero)

Provisiona uma VPS Ubuntu nova até produção rodando com HTTPS. **Um comando.** Use ao montar a máquina, ou ao reconstruir após desastre.

## Pré-requisitos (env obrigatórias)

```bash
sudo OCTOBOX_DB_PASSWORD='<senha-postgres>' \
     OCTOBOX_ADMIN_PATH='<path-secreto-do-admin>' \
     OCTOBOX_SECRET_KEY='<django-secret>' \
     OCTOBOX_PHONE_BLIND_INDEX_KEY='<blind-index-key>' \
     bash /srv/octobox/app/scripts/linux/bootstrap_hostgator_octobox.sh
```

Defaults: domínio `app.octoboxfit.com.br`, repo `github.com/renanfulas/OctoBox`, branch `main`, DB `octobox_control`/`octobox_app`, slug `octoboxfit-production`.

## O que o script provisiona

1. **apt:** git, python3-venv, build-essential, libpq-dev, **nginx, postgresql, redis-server, certbot**.
2. usuário `octobox`, árvore `/srv/octobox/{app,shared,backups}`, clone do repo, **venv + pip install**.
3. **PostgreSQL:** cria role `octobox_app` + banco `octobox_control`.
4. escreve `/srv/octobox/shared/octobox.env` (config de produção completa: `DJANGO_ENV=production`, `DATABASE_URL`, `REDIS_URL`, HSTS/SSL, admin path, throttles).
5. **systemd:** unit `octobox-gunicorn.service` (gunicorn em socket unix, 2 workers).
6. **nginx:** site HTTP→HTTPS + bloco SSL; **certbot** emite o Let's Encrypt.
7. `migrate` + `collectstatic` + **`bootstrap_roles`** + `check`.

## Depois do bootstrap

1. **superusuário** (o script imprime o comando exato):
   `sudo -u octobox bash -lc 'cd /srv/octobox/app && set -a && source /srv/octobox/shared/octobox.env && set +a && /srv/octobox/venv/bin/python manage.py createsuperuser'`
2. **backup externo R2** → [backup.md](backup.md) (`setup_r2_backup.sh`).
3. **smoke** → [smoke.md](smoke.md).
4. provisionar boxes → `provision_box` (ver memória/skill de tenant).
