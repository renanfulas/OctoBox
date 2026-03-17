<#
Run CSS linter + format helper for Windows (PowerShell).

Behavior:
- If `npm` is available it runs `npm run lint:css` then `npm run format:css`.
- If `npm` is missing and `docker` is available it runs the same commands
  inside a temporary `node:lts` container (mounts the repo into /work).
- Otherwise it prints installation instructions.

Usage: open PowerShell in the repo root and run:
  .\tools\run-css-checks.ps1
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
