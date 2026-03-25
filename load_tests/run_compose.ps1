# Instruções: execute este script no PowerShell (run as admin se necessário)
# 1) Iniciar os serviços: InfluxDB e Grafana
docker-compose -f load_tests/docker-compose.yml up -d

Write-Host "Aguardando serviços iniciarem (40s)..."
Start-Sleep -s 40

# 2) Rodar a suíte k6 apontando para InfluxDB (gera métricas para Grafana)
$env:HOST='http://host.docker.internal:8000' # ajuste se necessário
$env:TEST_USER='admin'
$env:TEST_PASS='admin'

# Executa k6 dentro do container configurado
docker-compose -f load_tests/docker-compose.yml run --rm k6 run -o influxdb=http://influxdb:8086/k6 /scripts/load_tests/k6_suite.js

Write-Host "Execução k6 finalizada. Abra http://localhost:3000 (admin/admin) para ver Grafana."
