# Docker Compose para Load Tests (k6 + InfluxDB + Grafana)

Arquivos:
- docker-compose.yml — define serviços InfluxDB, Grafana e k6
- grafana/provisioning/... — configura datasource (InfluxDB) e dashboards
- grafana/dashboards/octobox_dashboard.json — dashboard de exemplo
- run_compose.ps1 — script PowerShell para iniciar e rodar k6

Como usar

1) Instale Docker Desktop no Windows e habilite WSL2 (se necessário).
2) No PowerShell, execute:

```powershell
# sobe influxdb e grafana
docker-compose -f load_tests/docker-compose.yml up -d
# aguarde alguns segundos para os serviços iniciarem
# então rode o k6 via container (exemplo usa o k6_suite.js)
docker-compose -f load_tests/docker-compose.yml run --rm k6 run -o influxdb=http://influxdb:8086/k6 /scripts/load_tests/k6_suite.js
```

Notas
- O `k6` rodará dentro do container e enviará métricas para InfluxDB (database `k6`).
- Grafana deve iniciar com a datasource `InfluxDB` provisionada automaticamente (url: http://influxdb:8086, database: k6). Usuário padrão Grafana: `admin` / `admin`.
- Ajuste `run_compose.ps1` se seu host do app não for acessível via `host.docker.internal`.
