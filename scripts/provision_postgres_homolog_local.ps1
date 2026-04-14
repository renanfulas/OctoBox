<#
ARQUIVO: provisionamento local da homologacao PostgreSQL para a Fase 1.

POR QUE ELE EXISTE:
- Reduz improviso na criacao da homologacao local.
- Instala os componentes minimos para provar o restore PostgreSQL da Fase 1.
- Gera um arquivo `.env.homolog.local` com o baseline operacional necessario.

O QUE ESTE ARQUIVO FAZ:
1. Verifica se o PowerShell esta elevado como administrador.
2. Instala PostgreSQL 15 com command line tools, se necessario.
3. Instala Redis local, se necessario.
4. Garante os bancos `octobox_homolog` e `octobox_restore_test`.
5. Gera um `.env.homolog.local` com DATABASE_URL, REDIS_URL e chaves basicas.

PONTOS CRITICOS:
- Este script e para homologacao local. Nao usar cegamente em producao.
- Ele depende de `choco` e de permissao de administrador.
- A senha passada aqui e para homologacao local; troque em ambiente serio.
#>

param(
    [string]$PostgresPackage = "postgresql15",
    [string]$RedisPackage = "redis",
    [string]$PostgresUser = "postgres",
    [string]$PostgresPassword = "OctoBoxHomolog2026!",
    [int]$PostgresPort = 5432,
    [string]$PostgresHost = "localhost",
    [string]$MainDatabase = "octobox_homolog",
    [string]$RestoreDatabase = "octobox_restore_test",
    [string]$RedisUrl = "redis://localhost:6379/0",
    [string]$BoxRuntimeSlug = "homolog-local",
    [string]$OutputEnvFile = ".env.homolog.local"
)

$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Command {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Installer
    )

    if (Get-Command $Name -ErrorAction SilentlyContinue) {
        Write-Host "$Name ja esta disponivel."
        return
    }

    Write-Host "$Name ausente. Instalando..."
    & $Installer
}

function Add-PostgresBinToPath {
    $candidateRoots = @(
        "C:\Program Files\PostgreSQL\15\bin",
        "C:\Program Files\PostgreSQL\16\bin",
        "C:\Program Files\PostgreSQL\17\bin",
        "C:\Program Files\PostgreSQL\18\bin"
    )

    foreach ($path in $candidateRoots) {
        if (Test-Path $path) {
            if (-not ($env:Path -split ';' | Where-Object { $_ -eq $path })) {
                $env:Path = "$path;$env:Path"
            }
            return $path
        }
    }

    return $null
}

function Invoke-PostgresSql {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Database,
        [Parameter(Mandatory = $true)]
        [string]$Sql
    )

    $env:PGPASSWORD = $PostgresPassword
    try {
        & psql -h $PostgresHost -p $PostgresPort -U $PostgresUser -d $Database -v ON_ERROR_STOP=1 -tAc $Sql
    }
    finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Ensure-Database {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DatabaseName
    )

    $exists = Invoke-PostgresSql -Database "postgres" -Sql "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName';"
    if ($exists -match "1") {
        Write-Host "Banco $DatabaseName ja existe."
        return
    }

    Write-Host "Criando banco $DatabaseName..."
    $env:PGPASSWORD = $PostgresPassword
    try {
        & createdb -h $PostgresHost -p $PostgresPort -U $PostgresUser $DatabaseName
    }
    finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function New-RandomSecret {
    return -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
}

if (-not (Test-IsAdministrator)) {
    throw "Abra um PowerShell como Administrador antes de rodar este script. Sem isso, a instalacao do PostgreSQL/Redis vai falhar."
}

if (-not (Get-Command choco.exe -ErrorAction SilentlyContinue)) {
    throw "Chocolatey nao encontrado. Instale o choco antes de rodar este script."
}

Ensure-Command -Name "psql" -Installer {
    choco install $PostgresPackage -y --params "'/Password:$PostgresPassword /Port:$PostgresPort'" --ia "'--enable-components server,commandlinetools'"
}

$postgresBin = Add-PostgresBinToPath
if (-not $postgresBin) {
    throw "Nao foi possivel localizar o diretório bin do PostgreSQL em C:\Program Files\PostgreSQL."
}

Ensure-Command -Name "redis-server" -Installer {
    choco install $RedisPackage -y
}

$postgresServices = Get-Service | Where-Object { $_.Name -match "^postgresql" -or $_.DisplayName -match "PostgreSQL" }
if (-not $postgresServices) {
    throw "PostgreSQL foi instalado, mas nenhum servico foi encontrado."
}

foreach ($service in $postgresServices) {
    if ($service.Status -ne "Running") {
        Start-Service -Name $service.Name
    }
}

$redisServices = Get-Service | Where-Object { $_.Name -match "redis|memurai" -or $_.DisplayName -match "Redis|Memurai" }
foreach ($service in $redisServices) {
    if ($service.Status -ne "Running") {
        Start-Service -Name $service.Name
    }
}

Ensure-Database -DatabaseName $MainDatabase
Ensure-Database -DatabaseName $RestoreDatabase

$djangoSecret = New-RandomSecret
$blindIndexKey = New-RandomSecret
$databaseUrl = "postgresql://{0}:{1}@{2}:{3}/{4}" -f $PostgresUser, $PostgresPassword, $PostgresHost, $PostgresPort, $MainDatabase

$envContent = @"
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$djangoSecret
PHONE_BLIND_INDEX_KEY=$blindIndexKey
DATABASE_URL=$databaseUrl
REDIS_URL=$RedisUrl
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
BOX_RUNTIME_SLUG=$BoxRuntimeSlug
OPERATIONS_MANAGER_WORKSPACE_ENABLED=True
DJANGO_ADMIN_URL_PATH=painel-interno-homolog
DB_SSL_REQUIRE=False
"@

Set-Content -Path $OutputEnvFile -Value $envContent -Encoding UTF8

Write-Host ""
Write-Host "Provisionamento local concluido."
Write-Host "PostgreSQL host: $PostgresHost"
Write-Host "Banco principal: $MainDatabase"
Write-Host "Banco de restore: $RestoreDatabase"
Write-Host "Arquivo de ambiente gerado: $OutputEnvFile"
Write-Host ""
Write-Host "Proximos passos:"
Write-Host "1. Copiar $OutputEnvFile para .env ou carregar as variaveis na sessao."
Write-Host "2. Rodar: py manage.py migrate"
Write-Host "3. Rodar: py manage.py sync_runtime_assets --collectstatic"
Write-Host "4. Rodar: py manage.py bootstrap_roles"
Write-Host "5. Rodar o runbook de restore PostgreSQL."
