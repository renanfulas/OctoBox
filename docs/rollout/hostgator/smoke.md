<!--
ARQUIVO: runbook de SMOKE / runtime check — HostGator VPS.
FONTE DA VERDADE (codigo vence este doc):
- scripts/smoke_http.py                  (smoke HTTP manual, pos-deploy)
- scripts/linux/check_octobox_runtime.sh (check recorrente automatico)
-->

# Smoke & runtime check — HostGator VPS

Dois níveis: **manual pós-deploy** (você roda) e **recorrente automático** (systemd timer).

## 1. Smoke HTTP pós-deploy — `smoke_http.py`

Roda da sua máquina ou da VPS, contra o ambiente publicado.

```bash
python3 scripts/smoke_http.py --base-url https://app.octoboxfit.com.br
# autenticado (valida login + rota privada):
python3 scripts/smoke_http.py --base-url https://app.octoboxfit.com.br \
  --username <user> --password <senha>
```

Valida por padrão: público `/api/v1/health/`, `/login/` (aceita 200/301/302); autenticado `/dashboard/` após login real (pega `csrftoken`, faz POST). Sai `!= 0` se qualquer rota falhar. **Não** substitui a regressão dos corredores do aluno (`scripts/run_student_onboarding_real_smoke.py`).

## 2. Runtime check recorrente — `check_octobox_runtime.sh`

Roda sozinho via **`octobox-runtime-check.timer`** (instalado pelo `setup_r2_backup.sh`). Verifica:

1. serviços ativos: `octobox-gunicorn`, `nginx`, `postgresql`, `redis-server`;
2. healthcheck `https://app.octoboxfit.com.br/api/v1/health/`;
3. **disco** abaixo de `OCTOBOX_RUNTIME_DISK_THRESHOLD` (85%);
4. **último backup** existe e tem menos de `OCTOBOX_BACKUP_MAX_AGE_HOURS` (36h).

Falhou → sai `1` e dispara `OCTOBOX_ALERT_WEBHOOK_URL` (se configurado). Rodar na mão:

```bash
sudo bash /srv/octobox/app/scripts/linux/check_octobox_runtime.sh
```

## Quando usar qual

| momento | use |
|---|---|
| acabei de fazer deploy | `smoke_http.py` (1) |
| monitoramento contínuo | `check_octobox_runtime.sh` via timer (2) |
| "o site tá no ar?" rápido | `curl https://app.octoboxfit.com.br/api/v1/health/` |
