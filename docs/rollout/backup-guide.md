<!--
ARQUIVO: guia operacional de backup do banco.

TIPO DE DOCUMENTO:
- guia operacional de seguranca

AUTORIDADE:
- media

DOCUMENTO PAI:
- [first-box-rollout-plan.md](first-box-rollout-plan.md)

QUANDO USAR:
- quando a duvida for como proteger dados com backup minimo antes de expor o sistema a uso real

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
$securePassword = Read-Host "Senha do banco" -AsSecureString
./scripts/backup_postgres.ps1 -DbHost localhost -Port 5432 -Database octobox_control -User postgres -Password $securePassword
```

## Restauracao PostgreSQL

```powershell
Set-ExecutionPolicy -Scope Process Bypass
$securePassword = Read-Host "Senha do banco" -AsSecureString
./scripts/restore_postgres.ps1 -DbHost localhost -Port 5432 -Database octobox_restore_test -User postgres -BackupFile backups/octobox-AAAAmmdd-HHmmss.dump -Password $securePassword
```

## O que validar depois do backup

1. tamanho do arquivo gerado
2. data e hora do backup
3. capacidade real de restauracao em ambiente de teste

## Scripts incluidos no projeto

1. [scripts/backup_sqlite.ps1](../../scripts/backup_sqlite.ps1)
2. [scripts/backup_postgres.ps1](../../scripts/backup_postgres.ps1)
3. [scripts/restore_postgres.ps1](../../scripts/restore_postgres.ps1)
