<!--
ARQUIVO: runbook de backup e restore para Hostinger VPS unica.

TIPO DE DOCUMENTO:
- runbook operacional

AUTORIDADE:
- alta para producao em VPS unica

DOCUMENTOS IRMAOS:
- [hostinger-vps-production-deploy.md](hostinger-vps-production-deploy.md)
- [hostinger-vps-restore-postgres.md](hostinger-vps-restore-postgres.md)
- [backup-guide.md](backup-guide.md)

QUANDO USAR:
- quando o banco estiver em PostgreSQL local na mesma VPS
- quando for preciso configurar backup diario
- quando for preciso provar restore real antes do go-live

PONTOS CRITICOS:
- nao restore diretamente no banco ativo do cliente
- backup sem copia externa e protecao incompleta
-->

# Runbook de backup e restore para Hostinger VPS unica

## Objetivo

Garantir que uma VPS unica com app, Postgres e Redis juntos ainda tenha protecao operacional real.

## Estrategia minima obrigatoria

1. dump diario do PostgreSQL
2. copia do dump fora da VPS
3. retencao minima definida
4. restore ensaiado em banco isolado

## Script Linux recomendado

Use [../../scripts/linux/backup_postgres.sh](../../scripts/linux/backup_postgres.sh).

Exemplo:

```bash
PGPASSWORD='troque-esta-senha' \
/srv/octobox/app/scripts/linux/backup_postgres.sh \
  --host 127.0.0.1 \
  --port 5432 \
  --database octobox_control \
  --user octobox_app \
  --output-dir /srv/octobox/backups
```

## Cron sugerido

Rodar diariamente em horario fixo:

```cron
0 3 * * * PGPASSWORD='troque-esta-senha' /srv/octobox/app/scripts/linux/backup_postgres.sh --host 127.0.0.1 --port 5432 --database octobox_control --user octobox_app --output-dir /srv/octobox/backups >> /var/log/octobox-backup.log 2>&1
```

## O que precisa existir fora da VPS

Nao trate `/srv/octobox/backups` como destino final.

Pelo menos uma destas rotas precisa existir:

1. upload para storage externo
2. sincronizacao para outra maquina segura
3. coleta automatica por agente externo

## Restore de prova

Use um banco isolado, por exemplo:

1. `octobox_restore_test`

Passos:

1. criar o banco de restore
2. restaurar o dump nele
3. subir a app temporariamente contra esse banco ou testar as tabelas principais
4. registrar horario, arquivo e responsavel

Template de comando:

1. [hostinger-vps-restore-postgres.md](hostinger-vps-restore-postgres.md)

## O que validar apos cada backup

1. arquivo criado
2. tamanho maior que zero
3. timestamp coerente
4. copia externa confirmada

## O que validar apos cada restore de prova

1. `pg_restore` terminou sem erro
2. conexao ao banco restaurado funciona
3. tabelas principais existem
4. healthcheck ou smoke minimo pode ser executado

## Frequencia operacional recomendada

1. backup diario
2. revisao semanal dos logs de backup
3. restore de prova quinzenal ou mensal
4. snapshot manual antes de mudancas grandes

## Failure checks

Pare a liberacao do cliente se qualquer item abaixo acontecer:

1. backup com arquivo zero
2. ultimo backup muito antigo
3. restore nunca ensaiado
4. arquivo apenas local, sem copia externa
