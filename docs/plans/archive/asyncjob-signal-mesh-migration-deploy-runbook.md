<!--
ARQUIVO: runbook de deploy controlado da migracao de AsyncJob para a Signal Mesh.

POR QUE ELE EXISTE:
- transforma a migracao additive de `AsyncJob` em procedimento operacional seguro.
- evita aplicar schema no impulso e descobrir drift no horario errado.

TIPO DE DOCUMENTO:
- runbook operacional

AUTORIDADE:
- alta para a rodada de deploy desta migracao

DOCUMENTO PAI:
- [top-layer-architecture-execution-plan.md](top-layer-architecture-execution-plan.md)
-->

# Runbook de deploy: migracao AsyncJob + Signal Mesh

## Tese curta

A migracao [../../boxcore/migrations/0021_asyncjob_signal_mesh_fields.py](../../boxcore/migrations/0021_asyncjob_signal_mesh_fields.py) e aditiva.

Em linguagem simples:

1. nao estamos derrubando uma parede
2. estamos abrindo novos campos no formulario que o runtime ja esperava preencher
3. mesmo assim, o certo e entrar com capacete e checklist

## O que muda no schema

Novos campos em `AsyncJob`:

1. `job_type`
2. `created_by_id`
3. `attempts`
4. `max_retries`
5. `next_retry_at`
6. `last_failure_kind`

## Pre-flight

Antes de rodar `migrate`:

1. confirmar que o deploy inclui o codigo que ja e resiliente ao schema antigo
2. confirmar que o comando `python manage.py check` esta limpo no build
3. confirmar backup ou snapshot recente do banco
4. rodar `python manage.py check_historical_integrity --fail-on-orphans`
5. confirmar janela curta de observacao apos o deploy
6. confirmar quem vai olhar dashboard, logs e retries nos 10 a 15 minutos seguintes

## Ordem recomendada

1. publicar o codigo novo
2. validar health basico da aplicacao
3. rodar `python manage.py migrate`
4. rodar `python manage.py showmigrations boxcore`
5. rodar `python manage.py check_asyncjob_signal_mesh_migration --require-applied`
6. rodar `python manage.py run_pre_vps_operational_smoke`
7. validar um sweep manual se quiser dupla confirmacao:
8. `python manage.py run_due_async_job_retries --limit 1`

## Checklist de verificacao

Depois da migracao:

1. o dashboard continua abrindo
2. o bloco do `Red Beacon` continua renderizando
3. criar um `AsyncJob` novo nao gera erro de coluna ausente
4. o status de job mostra `attempts`, `max_retries`, `next_retry_at` e `last_failure_kind`
5. o sweep manual termina sem erro
6. o verificador `check_asyncjob_signal_mesh_migration` volta verde
7. o smoke `run_pre_vps_operational_smoke` fecha verde

## Sinais de sucesso

1. sumiu qualquer erro de coluna ausente relacionado a `AsyncJob`
2. o `Red Beacon` passa a ler backlog de `jobs` pelo banco sem precisar cair no snapshot de runtime
3. a `Alert Siren` continua coerente entre dashboard e workspaces

## Contencao se algo sair errado

1. se o codigo subir mas a migracao ainda nao rodar, o sistema continua resiliente, mas o saneamento nao esta completo
2. se `migrate` falhar, parar a rodada e investigar antes de repetir
3. nao fazer rollback manual de coluna na pressa; como a migracao e aditiva, o caminho mais seguro costuma ser corrigir e reexecutar
4. se o dashboard abrir com degradacao, usar isso como pista, nao como desculpa para esconder o problema

## Explicacao simples

Pense no banco como uma ficha de cadastro.

O codigo novo ja sabe lidar com ficha antiga sem brigar.
Mas o objetivo desta rodada e entregar a ficha nova de verdade para o funcionario do balcao, para que ele pare de anotar metade no papel e metade na memoria.
