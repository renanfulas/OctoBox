<!--
ARQUIVO: guia operacional de backup do banco.

POR QUE ELE EXISTE:
- Garante que o pacote minimo de producao inclua recuperacao de dados e nao apenas deploy.

O QUE ESTE ARQUIVO FAZ:
1. Explica a estrategia minima de backup.
2. Mostra fluxo para SQLite e PostgreSQL.
3. Referencia os scripts reais incluidos no projeto.

PONTOS CRITICOS:
- Backup sem teste de restauracao vira documentacao decorativa e nao protecao real.
-->

# Backup minimo do banco

Este projeto pode rodar com SQLite em desenvolvimento e com PostgreSQL em homologacao/producao.

## Estrategia recomendada

1. backup diario do banco
2. retencao de pelo menos 7 copias
3. restauracao testada periodicamente

## SQLite local

Para um backup simples do ambiente local:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/backup_sqlite.ps1
```

## PostgreSQL em homologacao/producao

Exemplo com pg_dump:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/backup_postgres.ps1 -Host localhost -Port 5432 -Database octobox_control -User postgres -Password "sua_senha"
```

## Restauracao PostgreSQL

```powershell
$env:PGPASSWORD="sua_senha"
pg_restore -h localhost -U postgres -d octobox_control --clean --if-exists backups/octobox-AAAAmmdd-HHmmss.dump
```

## O que validar depois do backup

1. tamanho do arquivo gerado
2. data e hora do backup
3. capacidade real de restauracao em ambiente de teste

## Scripts incluidos no projeto

1. [scripts/backup_sqlite.ps1](../scripts/backup_sqlite.ps1)
2. [scripts/backup_postgres.ps1](../scripts/backup_postgres.ps1)