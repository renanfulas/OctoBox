<#
ARQUIVO: script PowerShell de backup do banco SQLite local.

POR QUE ELE EXISTE:
- Automatiza o snapshot do banco local sem depender de copia manual.

O QUE ESTE ARQUIVO FAZ:
1. Garante que a pasta de backups exista.
2. Valida a presenca do banco SQLite.
3. Gera uma copia com timestamp.

PONTOS CRITICOS:
- Este script depende da policy do PowerShell permitir execucao no processo atual.
- Ele cobre o banco local, nao substitui backup real de PostgreSQL em homologacao/producao.
#>

param(
    [string]$DatabasePath = "db.sqlite3",
    [string]$OutputDirectory = "backups"
)

$ErrorActionPreference = 'Stop'

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

if (-not (Test-Path $DatabasePath)) {
    throw "Banco SQLite nao encontrado em: $DatabasePath"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = Join-Path $OutputDirectory ("db-{0}.sqlite3" -f $timestamp)

Copy-Item $DatabasePath $destination

Write-Host "Backup SQLite criado em $destination"