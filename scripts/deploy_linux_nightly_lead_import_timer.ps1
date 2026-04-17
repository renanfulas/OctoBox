<#
ARQUIVO: instalador PowerShell do timer Linux de imports noturnos.

POR QUE ELE EXISTE:
- permite instalar o scheduler noturno da VPS Linux a partir de um Windows com PowerShell.
- evita copia manual de arquivos e reduz erro operacional.

O QUE ESTE ARQUIVO FAZ:
1. valida os arquivos locais necessarios.
2. copia runner, installer e units do systemd para a VPS via scp.
3. executa a instalacao remota via ssh.
4. mostra comandos de validacao do timer ao final.

PONTOS CRITICOS:
- exige `ssh` e `scp` disponiveis no Windows.
- o usuario remoto precisa ter permissao para escrever no destino e elevar para root.
- a VPS alvo e Linux; este script nao serve para Windows Server.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Host,

    [Parameter(Mandatory = $true)]
    [string]$User,

    [int]$Port = 22,

    [string]$RemoteAppDir = "/srv/octobox/app",

    [string]$RemoteSharedDir = "/srv/octobox/shared",

    [string]$RemoteSystemdDir = "/etc/systemd/system",

    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

function Test-RequiredCommand {
    param([string]$CommandName)

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatorio nao encontrado no Windows: $CommandName"
    }
}

function Invoke-ExternalCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar: $FilePath $($Arguments -join ' ')"
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$LocalFiles = @(
    @{
        Source = (Join-Path $RepoRoot "scripts\linux\run_due_nightly_lead_import_jobs.sh")
        Target = "$RemoteAppDir/scripts/linux/run_due_nightly_lead_import_jobs.sh"
    },
    @{
        Source = (Join-Path $RepoRoot "scripts\linux\install_nightly_lead_import_timer.sh")
        Target = "$RemoteAppDir/scripts/linux/install_nightly_lead_import_timer.sh"
    },
    @{
        Source = (Join-Path $RepoRoot "infra\hostgator-vps\systemd\octobox-nightly-lead-imports.service")
        Target = "$RemoteAppDir/infra/hostgator-vps/systemd/octobox-nightly-lead-imports.service"
    },
    @{
        Source = (Join-Path $RepoRoot "infra\hostgator-vps\systemd\octobox-nightly-lead-imports.timer")
        Target = "$RemoteAppDir/infra/hostgator-vps/systemd/octobox-nightly-lead-imports.timer"
    }
)

foreach ($file in $LocalFiles) {
    if (-not (Test-Path -LiteralPath $file.Source)) {
        throw "Arquivo local nao encontrado: $($file.Source)"
    }
}

Test-RequiredCommand -CommandName "ssh"
Test-RequiredCommand -CommandName "scp"

$Remote = "$User@$Host"
$RemoteAppHome = ($RemoteAppDir -replace '/+$', '') -replace '/app$', ''
if ([string]::IsNullOrWhiteSpace($RemoteAppHome)) {
    $RemoteAppHome = "/srv/octobox"
}

Write-Host "== OctoBOX Nightly Lead Import Timer Deploy ==" -ForegroundColor Cyan
Write-Host "Host: $Host"
Write-Host "User: $User"
Write-Host "Port: $Port"
Write-Host "Remote app dir: $RemoteAppDir"
Write-Host ""

$RemoteDirs = @(
    "$RemoteAppDir/scripts/linux",
    "$RemoteAppDir/infra/hostgator-vps/systemd"
)

foreach ($dir in $RemoteDirs) {
    Write-Host "Criando diretorio remoto: $dir" -ForegroundColor Yellow
    Invoke-ExternalCommand -FilePath "ssh" -Arguments @(
        "-p", "$Port",
        $Remote,
        "mkdir -p '$dir'"
    )
}

foreach ($file in $LocalFiles) {
    Write-Host "Copiando $($file.Source) -> $($file.Target)" -ForegroundColor Yellow
    Invoke-ExternalCommand -FilePath "scp" -Arguments @(
        "-P", "$Port",
        $file.Source,
        "${Remote}:$($file.Target)"
    )
}

if (-not $SkipInstall) {
    $InstallCommand = @"
set -euo pipefail
chmod +x '$RemoteAppDir/scripts/linux/run_due_nightly_lead_import_jobs.sh'
chmod +x '$RemoteAppDir/scripts/linux/install_nightly_lead_import_timer.sh'
cd '$RemoteAppDir'
sudo OCTOBOX_APP_HOME='$RemoteAppHome' ./scripts/linux/install_nightly_lead_import_timer.sh
systemctl status octobox-nightly-lead-imports.timer --no-pager || true
systemctl list-timers octobox-nightly-lead-imports.timer --no-pager || true
"@

    Write-Host "Executando instalacao remota..." -ForegroundColor Yellow
    Invoke-ExternalCommand -FilePath "ssh" -Arguments @(
        "-p", "$Port",
        $Remote,
        $InstallCommand
    )
}

Write-Host ""
Write-Host "Deploy concluido." -ForegroundColor Green
Write-Host "Comandos uteis na VPS:" -ForegroundColor Cyan
Write-Host "systemctl status octobox-nightly-lead-imports.timer --no-pager"
Write-Host "systemctl status octobox-nightly-lead-imports.service --no-pager"
Write-Host "journalctl -u octobox-nightly-lead-imports.service -n 100 --no-pager"
