<!--
ARQUIVO: template curto de restore PostgreSQL para Hostinger VPS.

TIPO DE DOCUMENTO:
- template operacional

AUTORIDADE:
- media como roteiro curto; o runbook completo vence

DOCUMENTO PAI:
- [hostinger-vps-backup-and-restore-runbook.md](hostinger-vps-backup-and-restore-runbook.md)
-->

# Template de restore PostgreSQL para Hostinger VPS

## Objetivo

Fornecer um roteiro curto para restaurar um dump em banco isolado na VPS.

## Regras

1. nunca usar contra o banco ativo do cliente
2. sempre usar um banco isolado
3. registrar horario, arquivo e responsavel

## Exemplo de banco isolado

```sql
CREATE DATABASE octobox_restore_test OWNER octobox_app;
```

## Comando de restore

```bash
PGPASSWORD='troque-esta-senha' pg_restore \
  --host 127.0.0.1 \
  --port 5432 \
  --username octobox_app \
  --dbname octobox_restore_test \
  --clean \
  --if-exists \
  /srv/octobox/backups/octobox-AAAAmmdd-HHmmss.dump
```

## Pos-restore

1. testar conexao ao banco restaurado
2. validar tabelas principais
3. rodar um smoke minimo da app contra o banco isolado quando possivel
