Prometheus instrumentation (Django)

1) Instalação de dependências (virtualenv):

```bash
pip install prometheus_client
```

2) Adicione o middleware em `settings.py` (aprox. no topo da lista de middlewares):

```python
MIDDLEWARE = [
    'monitoring.prometheus_middleware.PrometheusBeforeMiddleware',
    # ... outros middlewares
]
```

3) Adicione a rota para expor métricas (ex.: em `urls.py` do projeto):

```python
from monitoring.prometheus_middleware import metrics_view
urlpatterns += [
    path('metrics/', metrics_view, name='metrics'),
]
```

4) Configure o Prometheus para coletar `http://<host>:<port>/metrics`.

5) Métricas recomendadas extra:
- Expor histograms por endpoints críticos (login, listagens, imports, snapshots)
- Instrumentar jobs assíncronos (imports/snapshots) com duração e status

6) Observação:
- Essa é uma implementação simples para começar. Para produção, considere usar libraries específicas (django-prometheus) e ajustar cardinalidade das labels (evitar endpoints com IDs diretamente nas labels).