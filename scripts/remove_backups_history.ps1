# Remove arquivos/pastas sensíveis do histórico Git usando BFG Repo-Cleaner.
#
# Este script faz um clone mirror do repositório atual, baixa o BFG (se necessário),
# executa a limpeza de pastas e arquivos especificados e prepara o repositório para push.
# Por segurança o push forçado para o remoto só será executado se você passar o flag
# `-AutoPush` ou confirmar explicitamente.
#
# Notas:
# - Teste em um clone mirror e leia o guia SECURITY_REMOVE_BACKUPS.md antes de executar.
# - Reescrever o histórico é destrutivo para commits antigos; coordene com sua equipe.

param(
    [string[]]$DeleteFolders = @('backups'),
    [string[]]$DeleteFiles = @('*.sqlite3'),
    [string]$BfgJarPath = '',
    [switch]$AutoPush = $false
)

function Write-ErrAndExit($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# Verificações básicas
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-ErrAndExit 'git não encontrado no PATH. Instale Git antes de continuar.'
}
if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
    Write-Host 'Aviso: java não encontrado no PATH. BFG requer Java para rodar.' -ForegroundColor Yellow
    Write-Host 'Instale Java (JRE) e reexecute o script.' -ForegroundColor Yellow
}

# Obter URL remoto (origin)
$originUrl = ''
try {
    $originUrl = (git remote get-url origin) -replace "\r|\n", ''
} catch {
    Write-ErrAndExit 'Falha ao obter origin URL. Execute este script a partir da raiz do repositório com origin configurado.'
}

$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$tempDir = Join-Path $env:TEMP "repo-clean-$timestamp"
$mirrorDir = Join-Path $tempDir 'repo.git'

Write-Host "Criando mirror clone em: $mirrorDir"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

# Clone mirror
git clone --mirror $originUrl $mirrorDir
if ($LASTEXITCODE -ne 0) { Write-ErrAndExit 'git clone --mirror falhou.' }

Push-Location $mirrorDir

# Preparar BFG
if (-not $BfgJarPath) {
    $bfgLocal = Join-Path $tempDir 'bfg.jar'
    $BfgJarPath = $bfgLocal
    # URL conhecida do BFG (versão estável conhecida). Atualize se necessário.
    $bfgUrl = 'https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar'
    Write-Host "Baixando BFG para: $bfgLocal"
    try {
        Invoke-WebRequest -Uri $bfgUrl -OutFile $bfgLocal -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-ErrAndExit "Falha ao baixar BFG de $bfgUrl. Baixe manualmente e passe o parâmetro -BfgJarPath." 
    }
} else {
    if (-not (Test-Path $BfgJarPath)) { Write-ErrAndExit "BFG jar não encontrado em: $BfgJarPath" }
}

# Montar argumentos do BFG
$bfgArgs = @()
foreach ($f in $DeleteFolders) { $bfgArgs += "--delete-folders"; $bfgArgs += $f }
foreach ($p in $DeleteFiles) { $bfgArgs += "--delete-files"; $bfgArgs += $p }
$bfgArgs += '--no-blob-protection'

Write-Host "Executando BFG com argumentos: $($bfgArgs -join ' ')"
$javaCmd = 'java'
$proc = Start-Process -FilePath $javaCmd -ArgumentList @('-jar', $BfgJarPath) + $bfgArgs -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) { Write-ErrAndExit 'BFG falhou durante a execução.' }

Write-Host 'BFG finalizado. Executando limpeza git (reflog expire e gc).'

git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host "Limpeza concluída no mirror: $mirrorDir" -ForegroundColor Green
Write-Host "ATENÇÃO: Agora você pode inspecionar o mirror antes de forçar push para o remoto." -ForegroundColor Yellow
Write-Host "Comandos para inspecionar:"
Write-Host "  cd $mirrorDir"
Write-Host "  git log --max-count=10"
Write-Host "Quando estiver pronto, faça push com: git push --force"

if ($AutoPush) {
    Write-Host 'Flag -AutoPush detectado. Executando push --force agora.' -ForegroundColor Yellow
    git push --force
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit 'git push --force falhou.' }
    Write-Host 'Push forçado concluído.' -ForegroundColor Green
} else {
    # Confirmar antes de push
    $confirm = Read-Host 'Deseja executar git push --force agora? (yes/no)'
    if ($confirm -eq 'yes') {
        git push --force
        if ($LASTEXITCODE -ne 0) { Write-ErrAndExit 'git push --force falhou.' }
        Write-Host 'Push forçado concluído.' -ForegroundColor Green
    } else {
        Write-Host 'Operação interrompida. Nenhum push foi realizado. Revise o mirror e execute o push manualmente quando pronto.' -ForegroundColor Yellow
    }
}

Pop-Location

Write-Host 'Próximo passo: rotacionar segredos e comunicar time. Veja SECURITY_REMOVE_BACKUPS.md' -ForegroundColor Cyan

exit 0
