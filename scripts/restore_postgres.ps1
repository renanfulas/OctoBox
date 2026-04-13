<#
ARQUIVO: script PowerShell de restore do PostgreSQL.

POR QUE ELE EXISTE:
- Permite ensaiar restauracao real do banco em homologacao ou ambiente isolado sem depender de comando manual disperso.

O QUE ESTE ARQUIVO FAZ:
1. Recebe host, porta, banco, usuario e arquivo dump por parametro.
2. Exporta a senha temporariamente via PGPASSWORD.
3. Executa `pg_restore` com limpeza do banco alvo.
4. Limpa a senha do ambiente ao final.

PONTOS CRITICOS:
- Nao usar este script contra o banco ativo do box real.
- Requer `pg_restore` instalado no ambiente.
- O arquivo dump precisa existir antes da execucao.
#>

param(
    [string]$DbHost = "localhost",
    [int]$Port = 5432,
    [string]$Database = "octobox_restore_test",
    [string]$User = "postgres",
    [string]$BackupFile,
    [System.Security.SecureString]$Password
)

$ErrorActionPreference = 'Stop'

if (-not $BackupFile) {
    throw "Informe o caminho do arquivo dump via -BackupFile."
}

if (-not (Test-Path -LiteralPath $BackupFile)) {
    throw "Arquivo de backup nao encontrado: $BackupFile"
}

if (-not $Password) {
    throw "Informe a senha via parametro -Password com SecureString ou adapte o script para ler de um secret manager."
}

$passwordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
$env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPtr)
try {
    pg_restore -h $DbHost -p $Port -U $User -d $Database --clean --if-exists $BackupFile
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    if ($passwordPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPtr)
    }
}

Write-Host "Restore PostgreSQL concluido para $Database usando $BackupFile"
