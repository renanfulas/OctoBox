# Technology Stack - OctoBOX

Este documento descreve as tecnologias, linguagens e frameworks utilizados no ecossistema OctoBOX.

## Backend (Python/Django)

Organizado sob a arquitetura de monolito modular, focado em performance e segurança bancária.

| Tecnologia | Versão | Propósito |
| :--- | :--- | :--- |
| **Python** | 3.14+ | Linguagem base |
| **Django** | 6.0.3 | Framework web principal |
| **Django REST Framework** | 3.16.1 | Camada de API (Internal & Integrations) |
| **dj-database-url** | 2.3.0 | Configuração dinâmica de banco de dados |
| **WhiteNoise** | 6.9.0 | Servidor de arquivos estáticos de alta performance |
| **Gunicorn** | 23.0.0 | Servidor WSGI para produção |

## Banco de Dados e Cache

| Tecnologia | Versão | Propósito |
| :--- | :--- | :--- |
| **PostgreSQL** | 16+ | Banco de dados relacional (Produção) |
| **SQLite** | 3.x | Banco de dados local (Desenvolvimento) |
| **Redis** | 7.x | Cache, Snapshots e Session Storage |
| **django-redis** | 5.4.0 | Cliente Redis otimizado para Django |

## Integrações e Serviços

| Tecnologia | Versão | Propósito |
| :--- | :--- | :--- |
| **Stripe** | 15.0.0 | Processamento de pagamentos e checkouts |
| **WhatsApp API** | Cloud API | Mensageria e identidade de canal |
| **Cryptography** | - | Criptografia de dados sensíveis (PII) e Blind Index |
| **ReportLab** | 4.4.1 | Geração de PDFs e relatórios |

## Monitoramento e Qualidade

| Tecnologia | Versão | Propósito |
| :--- | :--- | :--- |
| **Sentry** | 2.12.0 | Rastreamento de erros em tempo real |
| **Prometheus** | 0.23.1 | Métricas de performance e monitoramento |
| **Pytest** | - | Framework de testes unitários e de integração |

## Front-end e Ferramentas

| Tecnologia | Propósito |
| :--- | :--- |
| **Vanilla JS** | Lógica de front-end sem frameworks pesados |
| **Vanilla CSS** | Estilização pura focada em performance |
| **ESLint** | Linting de código JavaScript (v8.48.0) |
| **Prettier** | Formatação de código consistente (v2.8.8) |
| **Stylelint** | Linting de folhas de estilo CSS (v15.10.0) |
