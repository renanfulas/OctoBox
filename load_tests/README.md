Load tests: k6 suite and seed data

Arquivos gerados:
- load_tests/k6_suite.js  — suíte k6 para endpoints críticos (editar HOST, TEST_USER, TEST_PASS via env)
- load_tests/seed_data.py — gera CSVs sintéticos para import (ex.: students_seed.csv)

Como usar

1) Gerar CSV de teste:

```bash
python load_tests/seed_data.py --rows 10000 --out students_seed.csv
```

2) Rodar k6 (instale o k6):

```bash
# exemplo básico
HOST=http://127.0.0.1:8000 TEST_USER=test TEST_PASS=pass k6 run load_tests/k6_suite.js
```

3) Coleta de métricas
- Recomendo Prometheus + Grafana para coletar métricas da aplicação e do banco.
- Habilitar slow query log no DB e coletar traces APM se disponível.

Observações
- Ajuste endpoints no arquivo `k6_suite.js` conforme rotas reais da sua API.
- Para testes de import multipart (upload de arquivo real), adapte a etapa de import no k6 para usar `http.file()` e multipart/form-data.
