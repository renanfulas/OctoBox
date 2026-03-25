param(
  [switch]$StartWorker
)

Write-Host "Building and starting services..."
docker-compose up -d --build

Write-Host "Running migrations..."
docker-compose run --rm web python manage.py migrate

if ($StartWorker) {
  Write-Host "Starting Celery worker..."
  docker-compose up -d worker
}

Write-Host "Ambiente rodando em http://localhost:8000"
