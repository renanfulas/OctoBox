# Technology Stack - OctoBOX

Este documento descreve as tecnologias, linguagens e frameworks utilizados no ecossistema OctoBOX.

## Backend (Python/Django)

Organizado sob a arquitetura de monolito modular, focado em performance e seguranca bancaria.

| Tecnologia | Versao | Proposito |
| :--- | :--- | :--- |
| **Python** | 3.12+ | Linguagem base |
| **Django** | 6.x | Framework web principal |
| **Django REST Framework** | 3.16+ | Camada de API interna e integracoes |
| **django-tenants** | 3.10+ | Schema-per-tenant e isolamento por box |
| **dj-database-url** | 2.3+ | Configuracao dinamica de banco de dados |
| **WhiteNoise** | 6.9+ | Servidor de arquivos estaticos de alta performance |
| **Gunicorn** | 23+ | Servidor WSGI para producao |

## Banco de Dados e Cache

| Tecnologia | Versao | Proposito |
| :--- | :--- | :--- |
| **PostgreSQL** | 15+ | Banco relacional padrao para desenvolvimento, testes, homologacao e producao |
| **SQLite** | 3.x | Escape legado de diagnostico sem tenants, habilitado apenas por `OCTOBOX_ALLOW_SQLITE_FALLBACK=1` |
| **Redis** | 7.x | Cache, snapshots e session storage |
| **django-redis** | 5.4+ | Cliente Redis otimizado para Django |

## Integracoes e Servicos

| Tecnologia | Versao | Proposito |
| :--- | :--- | :--- |
| **Stripe** | 15+ | Processamento de pagamentos e checkouts |
| **WhatsApp API** | Cloud API | Mensageria e identidade de canal |
| **Cryptography** | - | Criptografia de dados sensiveis e blind index |
| **ReportLab** | 4.4+ | Geracao de PDFs e relatorios |

## Monitoramento e Qualidade

| Tecnologia | Versao | Proposito |
| :--- | :--- | :--- |
| **Sentry** | 2.12+ | Rastreamento de erros em tempo real |
| **Prometheus** | 0.23+ | Metricas de performance e monitoramento |
| **Pytest** | - | Framework de testes unitarios, integracao e E2E |

## Front-end e Ferramentas

| Tecnologia | Proposito |
| :--- | :--- |
| **Vanilla JS** | Logica de front-end sem frameworks pesados |
| **Vanilla CSS** | Estilizacao pura focada em performance |
| **ESLint** | Linting de codigo JavaScript |
| **Prettier** | Formatacao de codigo consistente |
| **Stylelint** | Linting de folhas de estilo CSS |
