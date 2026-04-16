<!--
ARQUIVO: runbook operacional minimo para ligar o retry de jobs ao scheduler atual.

POR QUE ELE EXISTE:
- documenta como operar o corredor oficial de retries sem introduzir scheduler novo.
- evita que o runtime tenha reprocessamento implementado, mas nao acionado.
-->

# Runbook: cron institucional para retry de jobs

## Tese pratica

O corredor oficial de retries de `jobs` agora existe no codigo, mas ele precisa de um maquinista.

Neste momento, o caminho mais seguro nao e instalar `celery beat`, `redbeat` ou outro scheduler novo.

O caminho recomendado e usar um cron institucional chamando o comando Django:

`python manage.py run_due_async_job_retries`

Em linguagem simples:

1. os jobs ja sabem quando devem tentar de novo
2. o comando pergunta quais deles ja venceram o horario
3. o cron so precisa tocar a campainha em intervalos curtos

## Comando oficial

Arquivo:

1. [../../jobs/management/commands/run_due_async_job_retries.py](../../jobs/management/commands/run_due_async_job_retries.py)

Uso basico:

```powershell
python manage.py run_due_async_job_retries
```

Uso com limite explicito:

```powershell
python manage.py run_due_async_job_retries --limit 50
```

Configuracao default:

1. [../../config/settings/base.py](../../config/settings/base.py) com `JOB_RETRY_SWEEP_LIMIT`

## Recomendacao operacional inicial

Agendamento recomendado de partida:

1. a cada 1 minuto em ambiente com volume baixo ou moderado
2. a cada 30 segundos apenas se o volume justificar e a observabilidade estiver madura

Meta de seguranca:

1. manter o runner pequeno e frequente
2. evitar lotes enormes que criem rajada artificial

## Exemplo de cron

Linux:

```cron
* * * * * cd /srv/octobox && /srv/octobox/.venv/bin/python manage.py run_due_async_job_retries --limit 25 >> /var/log/octobox/job-retries.log 2>&1
```

Windows Task Scheduler:

1. programa: `C:\Users\renan\OneDrive\Documents\OctoBOX\.venv\Scripts\python.exe`
2. argumentos: `manage.py run_due_async_job_retries --limit 25`
3. pasta inicial: `C:\Users\renan\OneDrive\Documents\OctoBOX`
4. frequencia: repetir a cada 1 minuto

## Guardrails

1. nao rodar varios schedulers concorrentes sem coordenacao
2. nao usar `limit` alto demais na primeira onda
3. nao ligar beat novo so para esta necessidade
4. se houver rajada, primeiro reduzir `limit`; depois rever o cron

## Sinais de que esta funcionando

1. `AsyncJob.next_retry_at` deixa de acumular itens vencidos
2. `AsyncJob.result.last_requeue_at` aparece nos jobs reenfileirados
3. o status endpoint de jobs mostra reencaminhamento real, nao estado congelado

## Proximo passo futuro

Quando o volume e a maturidade operacional crescerem, este runner pode migrar para um scheduler mais integrado.

Mas isso so deve acontecer quando o problema for escala real, nao vontade de sofisticacao.
