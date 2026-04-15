$ErrorActionPreference = 'Stop'

$environmentChoice = Read-Host "Ambiente? Digite PRODUCTION para usar app.octoboxfit.com.br ou CUSTOM para informar manualmente"

switch ($environmentChoice.ToUpperInvariant()) {
    'PRODUCTION' {
        $env:OCTOBOX_VPS_HOST = '129.121.47.167'
        $env:OCTOBOX_VPS_PORT = '22022'
        $env:OCTOBOX_VPS_USER = 'root'
        $env:OCTOBOX_DOMAIN = 'app.octoboxfit.com.br'
    }
    'CUSTOM' {
        $env:OCTOBOX_VPS_HOST = Read-Host 'Host/IP da VPS'
        $env:OCTOBOX_VPS_PORT = Read-Host 'Porta SSH'
        $env:OCTOBOX_VPS_USER = Read-Host 'Usuario SSH'
        $env:OCTOBOX_DOMAIN = Read-Host 'Dominio da aplicacao'
    }
    default {
        throw 'Ambiente invalido. Use PRODUCTION ou CUSTOM.'
    }
}

$env:OCTOBOX_RCLONE_REMOTE_NAME = Read-Host 'Nome do remote do rclone (Enter = r2)'
if (-not $env:OCTOBOX_RCLONE_REMOTE_NAME) {
    $env:OCTOBOX_RCLONE_REMOTE_NAME = 'r2'
}

$env:OCTOBOX_R2_ACCOUNT_ID = Read-Host 'Cloudflare Account ID do R2'
$env:OCTOBOX_R2_ACCESS_KEY_ID = Read-Host 'R2 Access Key ID'
$secureR2Secret = Read-Host 'R2 Secret Access Key' -AsSecureString
$env:OCTOBOX_R2_BUCKET = Read-Host 'Bucket do R2 (Enter = octobox-backups)'
if (-not $env:OCTOBOX_R2_BUCKET) {
    $env:OCTOBOX_R2_BUCKET = 'octobox-backups'
}

$env:OCTOBOX_BACKUP_REMOTE_PREFIX = Read-Host 'Prefixo do backup remoto (Enter = octoboxfit-production)'
if (-not $env:OCTOBOX_BACKUP_REMOTE_PREFIX) {
    $env:OCTOBOX_BACKUP_REMOTE_PREFIX = 'octoboxfit-production'
}

$env:OCTOBOX_BACKUP_RETENTION_DAYS = Read-Host 'Retencao em dias (Enter = 30)'
if (-not $env:OCTOBOX_BACKUP_RETENTION_DAYS) {
    $env:OCTOBOX_BACKUP_RETENTION_DAYS = '30'
}

$env:OCTOBOX_BACKUP_MAX_AGE_HOURS = Read-Host 'Idade maxima aceitavel do ultimo backup em horas (Enter = 36)'
if (-not $env:OCTOBOX_BACKUP_MAX_AGE_HOURS) {
    $env:OCTOBOX_BACKUP_MAX_AGE_HOURS = '36'
}

$env:OCTOBOX_RUNTIME_DISK_THRESHOLD = Read-Host 'Limite de disco em percentual para alerta (Enter = 85)'
if (-not $env:OCTOBOX_RUNTIME_DISK_THRESHOLD) {
    $env:OCTOBOX_RUNTIME_DISK_THRESHOLD = '85'
}

$env:OCTOBOX_ALERT_WEBHOOK_URL = Read-Host 'Webhook de alerta opcional (Enter = vazio)'

$confirmation = Read-Host "Confirme a instalacao do backup externo diario no bucket $($env:OCTOBOX_R2_BUCKET) para $($env:OCTOBOX_DOMAIN). Digite INSTALAR para continuar"
if ($confirmation -ne 'INSTALAR') {
    throw 'Instalacao cancelada pelo usuario.'
}

$securePassword = Read-Host "Digite a senha da VPS (${env:OCTOBOX_VPS_USER}@${env:OCTOBOX_VPS_HOST})" -AsSecureString

$bstrPassword = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstrPassword)
$bstrR2Secret = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureR2Secret)
$plainR2Secret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstrR2Secret)

try {
    $env:OCTOBOX_VPS_PASSWORD = $plainPassword
    $env:OCTOBOX_R2_SECRET_ACCESS_KEY = $plainR2Secret
    py "$PSScriptRoot\hostgator_setup_r2_backup.py"
}
finally {
    if ($bstrPassword -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstrPassword)
    }
    if ($bstrR2Secret -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstrR2Secret)
    }
    Remove-Item Env:OCTOBOX_VPS_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:OCTOBOX_R2_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue
}
