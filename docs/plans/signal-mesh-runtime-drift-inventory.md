<!--
ARQUIVO: inventario de runtime drift observado na primeira onda da Signal Mesh.

POR QUE ELE EXISTE:
- registra inconsistencias reais que podem distorcer a Fase 2 se forem ignoradas.
- separa o que ja e semente valida da malha do que ainda esta desalinhado no runtime.
- evita que a equipe trate drift estrutural como detalhe menor.

TIPO DE DOCUMENTO:
- inventario tecnico de inconsistencias

AUTORIDADE:
- alta para a entrada do Item 7 da Fase 2

DOCUMENTO PAI:
- [signal-mesh-phase2-minimum-backlog.md](signal-mesh-phase2-minimum-backlog.md)

PONTOS CRITICOS:
- este documento nao autoriza rewrite.
- todo item listado aqui deve apontar impacto e ordem recomendada de saneamento.
- se o runtime mudar, este inventario precisa acompanhar.
-->

# Signal Mesh: inventario de runtime drift

## Leitura curta

Hoje a malha ja tem sementes fortes de idempotencia, mas ainda nao tem uma lingua comum completa.

Em linguagem simples:

1. ja existem algumas travas de portao
2. ja existem algumas etiquetas de pacote
3. mas cada corredor ainda usa uma regra diferente

## Drift confirmado

## 1. `AsyncImportJobView` escreve campos que o modelo exposto nao mostra

**Onde aparece**

1. [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py)
2. [../../jobs/models.py](../../jobs/models.py)

**Sinal observado**

1. a view cria `AsyncJob.objects.create(job_type='student_import_csv', created_by_id=request.user.id, status='pending')`
2. o modelo exposto em `jobs/models.py` mostra apenas:
3. `status`
4. `result`
5. `error`
6. `started_at`
7. `finished_at`

**Classificacao**

1. drift confirmado de runtime entre writer e model surface

**Impacto**

1. dificulta confiar em `jobs` como canal oficial da malha
2. impede desenhar metadata minima da mesh sem antes saber qual e a shape real do job tracking

**Risco**

1. alto para a Fase 2

**Ordem recomendada**

1. saneamento imediato antes de endurecer `jobs/base.py`

## 2. retry de webhook existe no modelo, mas nao aparece como policy ativa compartilhada

**Onde aparece**

1. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py)
2. [../../integrations/whatsapp/poll_processor.py](../../integrations/whatsapp/poll_processor.py)

**Sinal observado**

1. `WebhookEvent` possui `attempts`, `max_retries`, `next_retry_at` e `increment_retry_with_backoff()`
2. o fluxo lido no runtime usa `get_or_create(...)` e marca `status=PROCESSED`
3. nao apareceu, nesta leitura, um corredor explicito consumindo `next_retry_at` para reprocessamento

**Classificacao**

1. drift confirmado entre capacidade modelada e policy operacional exposta

**Impacto**

1. o runtime sugere retry formal, mas a malha ainda nao tem policy legivel e compartilhada
2. a equipe pode assumir que retry esta “resolvido” quando ele ainda esta parcial

**Risco**

1. medio-alto

**Ordem recomendada**

1. resolver junto do Item 5 da Fase 2

## 3. idempotencia de webhook esta dividida em duas camadas sem contrato comum

**Onde aparece**

1. [../../integrations/middleware.py](../../integrations/middleware.py)
2. [../../integrations/whatsapp/poll_processor.py](../../integrations/whatsapp/poll_processor.py)
3. [../../communications/infrastructure/django_inbound_idempotency.py](../../communications/infrastructure/django_inbound_idempotency.py)

**Sinal observado**

1. o middleware tenta deduplicar por `X-Idempotency-Key`, `event_id`, `external_id`, `id`, `message_id` e `webhook_fingerprint`
2. o processador de enquete usa `event_id` ou `external_id`
3. o inbound de `communications` usa `external_message_id` e `webhook_fingerprint`

**Classificacao**

1. drift confirmado de nomenclatura e precedencia

**Impacto**

1. cada canal sabe deduplicar, mas a malha ainda nao define uma lingua minima unica para chave de idempotencia
2. aumenta o risco de acerto parcial por canal e entendimento errado em review

**Risco**

1. medio

**Ordem recomendada**

1. resolver nos Itens 1, 2 e 3 da Fase 2

## 4. nao existe `correlation_id` transversal no runtime observado

**Onde aparece**

1. leitura de [../../api/v1/](../../api/v1/)
2. leitura de [../../integrations/](../../integrations/)
3. leitura de [../../communications/](../../communications/)
4. leitura de [../../jobs/](../../jobs/)

**Sinal observado**

1. nao foi encontrado uso real de `correlation_id` nos corredores inspecionados

**Classificacao**

1. gap confirmado de rastreabilidade transversal

**Impacto**

1. dificulta seguir um pacote da entrada externa ate job, retry ou reprocessamento
2. enfraquece debug e observabilidade da malha

**Risco**

1. medio

**Ordem recomendada**

1. resolver logo depois do saneamento de `jobs`

## 5. middleware de webhook depende de helper tecnico de `communications.infrastructure`

**Onde aparece**

1. [../../integrations/middleware.py](../../integrations/middleware.py)
2. [../../communications/infrastructure/django_inbound_idempotency.py](../../communications/infrastructure/django_inbound_idempotency.py)

**Sinal observado**

1. o middleware global de integrações importa `calculate_webhook_fingerprint` direto de `communications.infrastructure`

**Classificacao**

1. drift de ownership e de lingua da malha

**Impacto**

1. a logica de deduplicacao transversal ainda depende de um helper tecnico pertencente a `communications`
2. isso enfraquece a ideia de policy compartilhada da `Signal Mesh`

**Risco**

1. medio

**Ordem recomendada**

1. mover ou promover esse helper quando nascer o contrato minimo de mesh

## O que nao entrou como drift confirmado

1. o webhook de enquete do WhatsApp ja normaliza `event_id` e isso agora esta coerente com o contrato atual
2. `WebhookEvent` como modelo de deduplicacao ja e semente valida, mesmo ainda nao sendo policy completa
3. `integrations/whatsapp/services.py` permanece fino e coerente como casca de integracao

## Ordem recomendada de saneamento

1. confirmar e corrigir o drift de `AsyncJob`
2. definir envelope minimo da malha
3. introduzir `correlation_id`
4. unificar nomenclatura e precedencia de `idempotency_key`
5. formalizar retry policy minima
6. reancorar helper transversal de fingerprint para ownership mais neutro da mesh

## Explicacao simples

Se a `Signal Mesh` fosse um correio:

1. alguns pacotes ja tem selo contra duplicidade
2. alguns ja tem armario de reentrega
3. mas ainda nao existe a mesma etiqueta em todas as caixas
4. e o balcão de jobs parece estar anotando campos que o cadastro oficial nem mostra direito

Por isso o Item 7 vem antes do Item 1:

1. primeiro a gente confirma onde o correio esta desencontrado
2. depois define a etiqueta oficial para todo mundo
