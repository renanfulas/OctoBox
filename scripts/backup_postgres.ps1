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
    [string]$DbHost = "localhost",
    [int]$Port = 5432,
    [string]$Database = "octobox_control",
    [string]$User = "postgres",
    [string]$OutputDirectory = "backups",
    [System.Security.SecureString]$Password
)

$ErrorActionPreference = 'Stop'

if (-not $Password) {
    throw "Informe a senha via parametro -Password com SecureString ou adapte o script para ler de um secret manager."
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = Join-Path $OutputDirectory ("octobox-{0}.dump" -f $timestamp)

# Usa a variavel temporaria do ambiente porque pg_dump le PGPASSWORD diretamente.
$passwordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
$env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPtr)
try {
    pg_dump -h $DbHost -p $Port -U $User -d $Database -F c -f $destination
}
finally {
    # A limpeza evita deixar a senha viva no ambiente da sessao alem do necessario.
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    if ($passwordPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPtr)
    }
}

Write-Host "Backup PostgreSQL criado em $destination"