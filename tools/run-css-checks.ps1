<#
ARQUIVO: utilitário PowerShell para lint e format de CSS no Windows.

POR QUE ELE EXISTE:
- Permite rodar lint e formatador de CSS em ambiente Windows, mesmo sem npm local, usando fallback Docker.

O QUE ESTE ARQUIVO FAZ:
1. Detecta se npm está disponível e executa lint/format CSS via scripts npm.
2. Se npm não está disponível, tenta rodar os comandos em um container Docker node:lts.
3. Exibe instruções de instalação caso nenhum método esteja disponível.

PONTOS CRÍTICOS:
- Falhas aqui podem impedir a padronização visual do CSS do projeto em ambientes Windows.
- Mudanças podem impactar pipelines de CI e desenvolvedores sem npm local.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-HasCommand($name) {
  return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

$repoRoot = Resolve-Path -Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

Write-Host "[run-css-checks] working directory: $((Get-Location).Path)"

if (Test-HasCommand npm) {
  Write-Host "[run-css-checks] npm detected — running linter and formatter via npm scripts..."
  & npm run lint:css
  $code = $LASTEXITCODE
  if ($code -ne 0) {
    Write-Error "stylelint reported errors (exit $code). Fix issues or run the formatter after addressing problems."
    exit $code
  }

  & npm run format:css
  exit $LASTEXITCODE
}

if (Test-HasCommand docker) {
  Write-Host "[run-css-checks] npm not found — docker detected. Running inside node:lts container (requires Docker Desktop)."
  $pwdPath = (Get-Location).Path -replace '\\','/'
  $mount = "${pwdPath}:/work"
  $dockerArgs = @('run','--rm','-v', $mount, '-w','/work','node:lts','bash','-lc','npm ci --silent && npm run lint:css && npm run format:css')
  Write-Host "[run-css-checks] invoking: docker $($dockerArgs -join ' ')"
  & docker @dockerArgs
  exit $LASTEXITCODE
}

Write-Host "[run-css-checks] neither npm nor docker were found on PATH." -ForegroundColor Yellow
Write-Host "Install Node.js (LTS) from https://nodejs.org/ and then run: npm install --silent && npm run lint:css && npm run format:css"
Write-Host "Or install Docker Desktop and re-run this script to use the container fallback."
exit 2
