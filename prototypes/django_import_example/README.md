# Django import example

Exemplo leve de endpoints para upload de CSV, queue/processamento e polling de status.

Arquivos:

- `models.py` — `ImportJob` que guarda arquivo, status, contadores e erros.
- `views.py` — `upload_import` (POST multipart/form-data) e `job_status` (GET).
- `urls.py` — rotas `upload/` e `jobs/<id>/`.

Instruções rápidas de integração:

1. Copie a pasta `prototypes/django_import_example` para um app Django real ou adicione o diretório ao seu projeto.
2. Adicione o app em `INSTALLED_APPS` se o colocar como app.
3. Inclua as URLs no `urls.py` do projeto, por exemplo:

```py
from django.urls import path, include

urlpatterns = [
    # ...
    path('api/imports/', include('prototypes.django_import_example.urls')),
]
```

4. Para produção, substitua o processamento por `Celery`/`django-rq` e evite salvar o modelo a cada linha — use batch updates.
5. Exemplo com Celery (opcional):

 - Instale dependências: `pip install celery redis`
 - Configure no `settings.py` algo como:

```py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

 - Inicie o worker (no diretório do projeto):

```bash
celery -A prototypes.django_import_example.celery_app worker -l info
```

 - Ao enviar upload via `upload/`, o sistema enfileirará a task `process_import_job_task`.

Observação: o protótipo inclui `tasks.py` e `celery_app.py` com uma implementação básica.
5. Configure `MEDIA_ROOT`/`MEDIA_URL` para armazenar arquivos enviados.

Exemplo de uso (curl):

```bash
curl -F "file=@alunos.csv" http://localhost:8000/api/imports/upload/
# resposta: {"job_id": 12}

curl http://localhost:8000/api/imports/jobs/12/
# retorno: {"status":"processing","processed_rows":10, ...}
```

Notas e melhorias possíveis:
- Adicionar idempotência, deduplicação e validações por esquema (pydantic/schema).
- Oferecer polling via websocket/notifications para UX em tempo real.

Quick start (Docker)
---------------------

Para testes rápidos com Redis + Django + Celery neste protótipo:

```bash
cd prototypes/django_import_example
# Se seu sistema não tem o comando 'docker-compose' ou prefere que o script escolha automaticamente,
# use o wrapper incluido `dc.sh` (Linux/macOS) ou `dc.ps1` (PowerShell/Windows):

./dc.sh up -d --build
make start
# opcional: make worker
```

Ou use os scripts:

```bash
./start.sh    # script interativo em Linux/macOS
./start.sh    # script interativo em Linux/macOS
./dc.sh up -d --build        # usa 'docker compose' ou 'docker-compose' automaticamente
.
Start.ps1 -StartWorker  # PowerShell no Windows
```

Também existe um `Makefile` com alvos úteis: `up`, `down`, `migrate`, `createsuperuser`, `worker`, `logs`.

