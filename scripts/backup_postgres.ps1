<#
ARQUIVO: script PowerShell de backup do PostgreSQL.

POR QUE ELE EXISTE:
- Permite executar backup operacional do banco de homologacao/producao de forma repetivel.

O QUE ESTE ARQUIVO FAZ:
1. Recebe host, porta, banco e usuario por parametro.
2. Prepara a pasta de destino.
3. Executa pg_dump em formato compactado.
4. Limpa a senha do ambiente ao final.

PONTOS CRITICOS:
- Requer pg_dump disponivel no ambiente.
- A senha nao deve ser hardcoded; o parametro aqui e apenas um ponto de entrada operacional.
#>

param(
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "octobox_control",
    [string]$User = "postgres",
    [string]$OutputDirectory = "backups",
    [string]$Password = ""
)

$ErrorActionPreference = 'Stop'

if (-not $Password) {
    throw "Informe a senha via parametro -Password ou adapte o script para ler de um secret manager."
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = Join-Path $OutputDirectory ("octobox-{0}.dump" -f $timestamp)

# Usa a variavel temporaria do ambiente porque pg_dump le PGPASSWORD diretamente.
$env:PGPASSWORD = $Password
try {
    pg_dump -h $Host -p $Port -U $User -d $Database -F c -f $destination
}
finally {
    # A limpeza evita deixar a senha viva no ambiente da sessao alem do necessario.
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Backup PostgreSQL criado em $destination"