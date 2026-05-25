<!--
ARQUIVO: inventario de runtime drift observado na primeira onda da Signal Mesh.

POR QUE ELE EXISTE:
- registra inconsistencias reais que podem distorcer a Fase 2 se forem ignoradas.
- separa o que ja e semente valida da malha do que ainda esta desalinhado no runtime.
- evita que a equipe trate drift estrutural como detalhe menor.

TIPO DE DOCUMENTO:
- inventario tecnico de inconsistencias (historico fechado)

AUTORIDADE:
- baixa — todos os itens foram resolvidos. Consulte o runtime atual.

DOCUMENTO PAI:
- [signal-mesh-phase2-minimum-backlog.md](signal-mesh-phase2-minimum-backlog.md)

PONTOS CRITICOS:
- este documento nao autoriza rewrite.
- se o runtime mudar, este inventario precisa acompanhar.
-->

# Signal Mesh: inventario de runtime drift

> **STATUS: FECHADO — todos os 5 itens resolvidos em 2026-05 durante a onda de
> implementacao da Signal Mesh.**
>
> Para o estado atual da malha consulte diretamente o runtime:
> - `integrations/mesh/` — contratos, failure_policy, retry_policy
> - `monitoring/` — beacon_snapshot, alert_siren, signal_mesh_runtime
> - `integrations/whatsapp/reprocessing.py` — policy ativa de retry
> - `api/v1/jobs_views.py` — uso real de correlation_id e SignalEnvelope

## Resolucoes confirmadas (2026-05-25)

| Item | Drift original | Resolucao |
|---|---|---|
| 1 | `AsyncImportJobView` criava `AsyncJob` com campos fora do contrato exposto | `jobs_views.py` agora usa `build_signal_envelope` e passa `signal_envelope` como metadata — contrato unificado |
| 2 | Retry de webhook existia no modelo mas sem corredor ativo consumindo `next_retry_at` | `integrations/whatsapp/reprocessing.py` tem `reprocess_due_webhook_events` consumindo `next_retry_at` com policy formal |
| 3 | Idempotencia dividida entre middleware, poll_processor e communications sem lingua comum | `integrations/middleware.py` agora importa `resolve_idempotency_key` de `integrations.mesh` — lingua unica |
| 4 | Nenhum uso real de `correlation_id` nos corredores inspecionados | `api/v1/jobs_views.py` usa `build_correlation_id` e propaga `X-OctoBox-Correlation-Id` em todos os fluxos |
| 5 | Middleware importava `calculate_webhook_fingerprint` direto de `communications.infrastructure` | Middleware agora importa `calculate_signal_fingerprint` de `integrations.mesh` — ownership correto |

## Itens originais (historico)

### 1. `AsyncImportJobView` escrevia campos que o modelo exposto nao mostrava

**Onde aparecia**

1. [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py)
2. [../../jobs/models.py](../../jobs/models.py)

**Sinal observado**

1. a view criava `AsyncJob.objects.create(job_type='student_import_csv', created_by_id=request.user.id, status='pending')`
2. o modelo exposto mostrava apenas `status`, `result`, `error`, `started_at`, `finished_at`

**Risco original:** alto para a Fase 2

---

### 2. Retry de webhook existia no modelo mas nao aparecia como policy ativa compartilhada

**Onde aparecia**

1. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py)
2. [../../integrations/whatsapp/poll_processor.py](../../integrations/whatsapp/poll_processor.py)

**Sinal observado**

1. `WebhookEvent` possuia `attempts`, `max_retries`, `next_retry_at` e `increment_retry_with_backoff()`
2. nao havia corredor explicito consumindo `next_retry_at` para reprocessamento

**Risco original:** medio-alto

---

### 3. Idempotencia de webhook estava dividida em duas camadas sem contrato comum

**Onde aparecia**

1. [../../integrations/middleware.py](../../integrations/middleware.py)
2. [../../integrations/whatsapp/poll_processor.py](../../integrations/whatsapp/poll_processor.py)
3. [../../communications/infrastructure/django_inbound_idempotency.py](../../communications/infrastructure/django_inbound_idempotency.py)

**Sinal observado**

1. middleware deduplicava por `X-Idempotency-Key`, `event_id`, `external_id`, `id`, `message_id` e `webhook_fingerprint`
2. processador de enquete usava `event_id` ou `external_id`
3. inbound de communications usava `external_message_id` e `webhook_fingerprint`

**Risco original:** medio

---

### 4. Nao existia `correlation_id` transversal no runtime observado

**Onde aparecia**

1. `api/v1/`, `integrations/`, `communications/`, `jobs/`

**Sinal observado**

1. nenhum uso real de `correlation_id` nos corredores inspecionados

**Risco original:** medio

---

### 5. Middleware dependia de helper tecnico de `communications.infrastructure`

**Onde aparecia**

1. [../../integrations/middleware.py](../../integrations/middleware.py)
2. [../../communications/infrastructure/django_inbound_idempotency.py](../../communications/infrastructure/django_inbound_idempotency.py)

**Sinal observado**

1. middleware importava `calculate_webhook_fingerprint` direto de `communications.infrastructure`

**Risco original:** medio

---

## O que nao entrou como drift confirmado (continua valido)

1. o webhook de enquete do WhatsApp normaliza `event_id` de forma coerente com o contrato atual
2. `WebhookEvent` como modelo de deduplicacao e semente valida
3. `integrations/whatsapp/services.py` permanece fino e coerente como casca de integracao
