$ErrorActionPreference = 'Stop'

$env:OCTOBOX_VPS_HOST = '129.121.47.167'
$env:OCTOBOX_VPS_PORT = '22022'
$env:OCTOBOX_VPS_USER = 'root'
$env:OCTOBOX_DOMAIN = 'app.octoboxfit.com.br'
if (-not $env:OCTOBOX_BRANCH) {
    $env:OCTOBOX_BRANCH = 'main'
}

$confirmation = Read-Host "Voce quer fazer deploy em PRODUCAO para $($env:OCTOBOX_DOMAIN) usando a branch $($env:OCTOBOX_BRANCH)? Digite DEPLOY para continuar"
if ($confirmation -ne 'DEPLOY') {
    throw 'Deploy cancelado pelo usuario.'
}

$securePassword = Read-Host "Digite a senha da VPS (${env:OCTOBOX_VPS_USER}@${env:OCTOBOX_VPS_HOST})" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

try {
    $env:OCTOBOX_VPS_PASSWORD = $plainPassword
    py "$PSScriptRoot\hostgator_deploy_octobox.py"
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    Remove-Item Env:OCTOBOX_VPS_PASSWORD -ErrorAction SilentlyContinue
}
