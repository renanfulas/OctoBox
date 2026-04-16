<!--
ARQUIVO: runbook de scheduler explicito para o corredor de retries da Signal Mesh.

POR QUE ELE EXISTE:
- liga o codigo novo a operacao real em Render, cron local e VPS com systemd.
- evita configuracao oral ou dependente de memoria humana.
-->

# Runbook: scheduler explicito da Signal Mesh

## Comando institucional unico

O comando recomendado para o ambiente atual e:

```powershell
python manage.py run_signal_mesh_retry_sweep
```

Ele aciona:

1. retries vencidos de `AsyncJob`
2. retries vencidos de `WebhookEvent`

Arquivos centrais:

1. [../../shared_support/management/commands/run_signal_mesh_retry_sweep.py](../../shared_support/management/commands/run_signal_mesh_retry_sweep.py)
2. [../../jobs/reprocessing.py](../../jobs/reprocessing.py)
3. [../../integrations/whatsapp/reprocessing.py](../../integrations/whatsapp/reprocessing.py)

## Settings operacionais

Configuracoes default:

1. [../../config/settings/base.py](../../config/settings/base.py) com `JOB_RETRY_SWEEP_LIMIT`
2. [../../config/settings/base.py](../../config/settings/base.py) com `WEBHOOK_RETRY_SWEEP_LIMIT`

## Render

O repositório atual ja usa [render.yaml](../../render.yaml).

Exemplo recomendado de cron service para anexar ao stack atual:

```yaml
- type: cron
  name: octobox-signal-mesh-retries
  runtime: python
  schedule: "*/1 * * * *"
  buildCommand: pip install -r requirements.txt
  startCommand: python manage.py run_signal_mesh_retry_sweep --job-limit 25 --webhook-limit 25
  envVars:
    - key: DJANGO_ENV
      value: production
    - key: DJANGO_SECRET_KEY
      sync: false
    - key: DATABASE_URL
      fromDatabase:
        name: octobox-control-db
        property: connectionString
    - key: REDIS_URL
      fromService:
        name: octobox-control-cache
        type: keyvalue
        property: connectionString
```

Leitura pratica:

1. o `web service` continua servindo HTTP
2. o `cron service` vira o maquinista do corredor de retries
3. nenhum scheduler novo precisa ser instalado dentro do app

## VPS com systemd

Exemplo pronto no repositório:

1. [../../infra/hostgator-vps/systemd/octobox-signal-mesh-retries.service](../../infra/hostgator-vps/systemd/octobox-signal-mesh-retries.service)
2. [../../infra/hostgator-vps/systemd/octobox-signal-mesh-retries.timer](../../infra/hostgator-vps/systemd/octobox-signal-mesh-retries.timer)

Passos tipicos:

1. copiar os arquivos para `/etc/systemd/system/`
2. rodar `sudo systemctl daemon-reload`
3. rodar `sudo systemctl enable --now octobox-signal-mesh-retries.timer`
4. validar com `sudo systemctl status octobox-signal-mesh-retries.timer`

## Windows Task Scheduler

Programa:

1. `C:\Users\renan\OneDrive\Documents\OctoBOX\.venv\Scripts\python.exe`

Argumentos:

1. `manage.py run_signal_mesh_retry_sweep --job-limit 25 --webhook-limit 25`

Pasta inicial:

1. `C:\Users\renan\OneDrive\Documents\OctoBOX`

Frequencia inicial:

1. repetir a cada 1 minuto

## Observabilidade minima

Metricas novas:

1. [../../monitoring/signal_mesh_metrics.py](../../monitoring/signal_mesh_metrics.py)

Elas expõem:

1. sweeps totais por corredor
2. backlog vencido por corredor
3. itens reenfileirados/processados
4. skips por motivo

## Guardrails

1. nao ligue dois schedulers para o mesmo ambiente sem coordenacao
2. prefira execucao frequente com `limit` baixo
3. se o backlog crescer, primeiro ajuste `limit`; depois a frequencia
4. so migrar para scheduler mais sofisticado quando a dor for escala real
