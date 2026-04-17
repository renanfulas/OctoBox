<!--
ARQUIVO: guia de instalacao do scheduler Linux para imports noturnos de leads.

TIPO DE DOCUMENTO:
- plano operacional de infra para VPS Linux

AUTORIDADE:
- alta para a rotina `async_night` do pipeline de importacao de leads

DOCUMENTO PAI:
- [lead-import-pipeline-corda-plan.md](./lead-import-pipeline-corda-plan.md)

POR QUE ELE EXISTE:
- entregar um caminho pronto para instalar o agendamento noturno em VPS Linux sem reinventar a operacao.
- manter o deploy alinhado ao padrao existente de `systemd service + timer` do projeto.
-->

# Scheduler Linux dos imports noturnos

## O que foi preparado

Arquivos prontos no repositório:

1. Runner shell:
   - [scripts/linux/run_due_nightly_lead_import_jobs.sh](../../scripts/linux/run_due_nightly_lead_import_jobs.sh)
2. Instalador do timer:
   - [scripts/linux/install_nightly_lead_import_timer.sh](../../scripts/linux/install_nightly_lead_import_timer.sh)
3. Unit files do `systemd`:
   - [infra/hostgator-vps/systemd/octobox-nightly-lead-imports.service](../../infra/hostgator-vps/systemd/octobox-nightly-lead-imports.service)
   - [infra/hostgator-vps/systemd/octobox-nightly-lead-imports.timer](../../infra/hostgator-vps/systemd/octobox-nightly-lead-imports.timer)

## Janela configurada

O timer foi configurado para rodar a cada `30 minutos` nos seguintes horarios:

1. `00:00`
2. `00:30`
3. `01:00`
4. `01:30`
5. `02:00`
6. `02:30`
7. `03:00`
8. `03:30`

Mesmo nesses horarios, o comando Django so dispara a task se:

1. estiver dentro da janela `00h-04h`
2. existir `LeadImportJob` noturno elegivel

Se nao houver job elegivel, ele encerra sem disparar nada.

## Premissas de caminho

Os arquivos foram preparados para o padrao atual da VPS:

1. app home: `/srv/octobox`
2. repo: `/srv/octobox/app`
3. env file: `/srv/octobox/shared/octobox.env`
4. python da venv: `/srv/octobox/app/.venv/bin/python`

Se sua VPS usar outro layout, ajuste:

1. o `service` do `systemd`
2. ou as variaveis exportadas antes do instalador

## Instalação na VPS Linux

Como `root`:

```bash
cd /srv/octobox/app
chmod +x scripts/linux/run_due_nightly_lead_import_jobs.sh
chmod +x scripts/linux/install_nightly_lead_import_timer.sh
./scripts/linux/install_nightly_lead_import_timer.sh
```

## Validação depois da instalação

Ver o timer:

```bash
systemctl list-timers octobox-nightly-lead-imports.timer --no-pager
```

Ver status detalhado:

```bash
systemctl status octobox-nightly-lead-imports.timer --no-pager
systemctl status octobox-nightly-lead-imports.service --no-pager
```

Testar manualmente a rotina:

```bash
cd /srv/octobox/app
source /srv/octobox/shared/octobox.env
./scripts/linux/run_due_nightly_lead_import_jobs.sh
```

Forçar pelo Django, se quiser validar fora da janela:

```bash
cd /srv/octobox/app
/srv/octobox/app/.venv/bin/python manage.py run_due_nightly_lead_import_jobs --force
```

Ver logs recentes:

```bash
journalctl -u octobox-nightly-lead-imports.service -n 100 --no-pager
journalctl -u octobox-nightly-lead-imports.timer -n 100 --no-pager
```

## Como desligar ou religar

Desligar:

```bash
systemctl disable --now octobox-nightly-lead-imports.timer
```

Religar:

```bash
systemctl enable --now octobox-nightly-lead-imports.timer
```

## Risco evitado

Este desenho evita um debito tecnico comum:

1. nao depende de criar/remover agendamentos dinamicamente por upload
2. nao roda processamento inutil quando nao ha job elegivel
3. segue o mesmo estilo de operacao que o projeto ja usa em outras rotinas `systemd`
