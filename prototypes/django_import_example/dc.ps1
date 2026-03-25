param(
  [Parameter(ValueFromRemainingArguments=$true)]
  $args
)

function Run-Compose([string[]]$composeArgs) {
  if (Get-Command -Name docker -ErrorAction SilentlyContinue) {
    try {
      docker compose version > $null 2>&1
      docker compose @composeArgs
      return
    } catch { }
  }

  if (Get-Command -Name docker-compose -ErrorAction SilentlyContinue) {
    docker-compose @composeArgs
    return
  }

  Write-Error "Nenhum 'docker compose' ou 'docker-compose' disponível no PATH. Instale o Docker Desktop ou o binário apropriado."
  exit 1
}

Run-Compose $args
