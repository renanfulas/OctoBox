$ErrorActionPreference = 'Stop'

$environmentChoice = Read-Host "Ambiente? Digite PRODUCTION para usar app.octoboxfit.com.br ou CUSTOM para informar manualmente"

switch ($environmentChoice.ToUpperInvariant()) {
    'PRODUCTION' {
        $env:OCTOBOX_VPS_HOST = '129.121.47.167'
        $env:OCTOBOX_VPS_PORT = '22022'
        $env:OCTOBOX_VPS_USER = 'root'
        $env:OCTOBOX_DOMAIN = 'app.octoboxfit.com.br'
        if (-not $env:OCTOBOX_BRANCH) {
            $env:OCTOBOX_BRANCH = 'main'
        }
    }
    'CUSTOM' {
        $env:OCTOBOX_VPS_HOST = Read-Host 'Host/IP da VPS'
        $env:OCTOBOX_VPS_PORT = Read-Host 'Porta SSH'
        $env:OCTOBOX_VPS_USER = Read-Host 'Usuario SSH'
        $env:OCTOBOX_DOMAIN = Read-Host 'Dominio da aplicacao'
        $customBranch = Read-Host 'Branch para deploy/rollback (Enter = main)'
        $env:OCTOBOX_BRANCH = if ($customBranch) { $customBranch } else { 'main' }
    }
    default {
        throw 'Ambiente invalido. Use PRODUCTION ou CUSTOM.'
    }
}

$actionChoice = Read-Host "Acao? Digite DEPLOY para publicar ou ROLLBACK para voltar ao commit anterior"
switch ($actionChoice.ToUpperInvariant()) {
    'DEPLOY' {
        $env:OCTOBOX_ACTION = 'deploy'
        $confirmation = Read-Host "Confirme DEPLOY em $($env:OCTOBOX_DOMAIN) usando a branch $($env:OCTOBOX_BRANCH). Digite DEPLOY para continuar"
        if ($confirmation -ne 'DEPLOY') {
            throw 'Deploy cancelado pelo usuario.'
        }
    }
    'ROLLBACK' {
        $env:OCTOBOX_ACTION = 'rollback'
        $confirmation = Read-Host "Confirme ROLLBACK em $($env:OCTOBOX_DOMAIN). Digite ROLLBACK para continuar"
        if ($confirmation -ne 'ROLLBACK') {
            throw 'Rollback cancelado pelo usuario.'
        }
    }
    default {
        throw 'Acao invalida. Use DEPLOY ou ROLLBACK.'
    }
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
    Remove-Item Env:OCTOBOX_ACTION -ErrorAction SilentlyContinue
}
