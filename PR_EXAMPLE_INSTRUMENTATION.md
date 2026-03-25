PR: Adicionar instrumentação Prometheus (middleware + rota)

Resumo
- Adiciona `monitoring.prometheus_middleware.PrometheusBeforeMiddleware` em `MIDDLEWARE` (config/settings/base.py).
- Expõe endpoint `/metrics/` em `config/urls.py` apontando para `monitoring.prometheus_middleware.metrics_view`.
- Inclui arquivos de instrumentação em `monitoring/` (middleware e README) e dependências em `load_tests/requirements_for_tests.txt`.

Como criar PR localmente

```bash
# cria branch
git checkout -b feat/monitoring-prometheus
# adiciona mudanças (se ainda não aplicadas localmente)
git add monitoring/ config/settings/base.py config/urls.py load_tests/requirements_for_tests.txt
git commit -m "feat(monitoring): add prometheus middleware and /metrics endpoint"
# push
git push origin feat/monitoring-prometheus
# abra PR via GitHub UI ou gh cli:
# gh pr create --base main --head feat/monitoring-prometheus --title "Add Prometheus instrumentation" --body "Adds middleware and /metrics endpoint for Prometheus scraping. See monitoring/README.md for setup."
```

Notas
- Evite usar o path do endpoint em labels de métricas que contenham IDs (alta cardinalidade). O middleware já tenta usar `resolver_match.view_name` quando disponível.
- Teste localmente antes de promover: instale `prometheus_client` e acesse `/metrics/`.
