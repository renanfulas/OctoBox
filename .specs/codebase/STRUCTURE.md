# Project Structure - OctoBOX

A estrutura do OctoBOX segue uma organização modular onde cada app Django encapsula um domínio de negócio, enquanto o core transversal reside em `shared_support`.

## Árvore de Diretórios Principal

```text
OctoBOX/
├── .specs/                 # Metodologia SDD (Especificações e Memória)
├── config/                 # Configurações do Django (base.py, dev.py, prod.py)
├── static/                 # Ativos estáticos (CSS, JS, Imagens)
├── templates/              # Base de templates HTML (estendidos pelos apps)
├── boxcore/                # App Âncora (Schema e Migrations globais)
│   └── migrations/         # SSOT de todas as mudanças de DB
├── shared_support/         # Core Transversal (O cérebro do sistema)
│   ├── security/           # Throttles, Honeypots e Impressão Digital
│   ├── crypto_fields.py    # Lógica de PII e Blind Index
│   └── redis_snapshots.py  # Gestão do Shadow State (Redis)
├── students/               # Domínio: Registro e Saúde do Aluno
├── finance/                # Domínio: Matrículas e Pagamentos
├── communications/         # Domínio: WhatsApp e Notificações
├── api/                    # Camada de API REST (DRF)
└── tests/                  # Suíte de testes centralizada
```

## Localização da Lógica de Negócio

Para manter as views magras e os modelos focados em dados, seguimos estes padrões:

*   **Modelos:** Definidos em `[app]/model_definitions.py` (com `app_label='boxcore'`).
*   **Queries/Selectors:** Lógicas de leitura complexas ficam em `[app]/[domain]_queries.py`.
    *   Ex: `students/student_queries.py`.
*   **Services:** Lógicas de escrita, mutações e integrações ficam em `[app]/[domain]_services.py`.
    *   Ex: `finance/enrollment_services.py`.
*   **Snapshots:** Lógicas que preparam dados para o Redis ficam em `shared_support/redis_snapshots.py`.

## Fluxo de Requisição

1.  **Middleware:** Throttling e Honeypots em `shared_support/security/`.
2.  **URL Routing:** Definido no `urls.py` de cada app e incluído no `config/urls.py`.
3.  **View:** Chama um `Service` (escrita) ou `Selector` (leitura).
4.  **Reposta:** Retorna Template HTML (Django/HTMX) ou JSON (API).
