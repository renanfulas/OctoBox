<!--
ARQUIVO: backlog tecnico minimo para iniciar a Fase 2 da Signal Mesh no runtime atual.

POR QUE ELE EXISTE:
- transforma a tese da Signal Mesh em uma primeira onda pequena, concreta e verificavel.
- evita que a Fase 2 vire barramento abstrato sem contrato, politica e dono.
- alinha idempotencia, correlation id, classificacao de falha e retry com os canais assincronos ja existentes.

TIPO DE DOCUMENTO:
- backlog tecnico executavel

AUTORIDADE:
- alta para a primeira onda da Fase 2

DOCUMENTO PAI:
- [top-layer-architecture-execution-plan.md](top-layer-architecture-execution-plan.md)

PONTOS CRITICOS:
- este backlog nao autoriza criar mesh generica sem uso real.
- a Fase 2 deve nascer em cima dos canais atuais, nao em cima de um framework inventado.
- se runtime e doc divergirem, o runtime vence e a divergencia precisa virar item explicito.
-->

# Signal Mesh: backlog minimo da Fase 2

## Tese pratica desta onda

A Fase 2 minima da `Signal Mesh` nao comeca com fila nova, barramento novo ou replatforming.

Ela comeca com quatro disciplinas compartilhadas:

1. `correlation id`
2. `idempotency key`
3. classificacao de falha
4. politica minima de retry

Em linguagem simples:

1. cada pacote precisa de etiqueta
2. cada pacote precisa de trava contra duplicidade
3. cada falha precisa dizer se vale tentar de novo
4. cada tentativa precisa obedecer uma regra comum

## Baseline atual observado no runtime

### Sementes ja reais

1. [../../integrations/middleware.py](../../integrations/middleware.py) ja tenta deduplicar webhooks por `X-Idempotency-Key`, `event_id` e `webhook_fingerprint`
2. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py) ja possui `WebhookEvent` com `event_id`, `webhook_fingerprint`, `status`, `attempts`, `max_retries` e `next_retry_at`
3. [../../communications/infrastructure/django_inbound_idempotency.py](../../communications/infrastructure/django_inbound_idempotency.py) ja deduplica inbound WhatsApp por `external_message_id` e `webhook_fingerprint`
4. [../../api/v1/integrations_views.py](../../api/v1/integrations_views.py) ja normaliza `event_id` para voto de enquete
5. [../../jobs/base.py](../../jobs/base.py) ja declara que job deve ser idempotente e reexecutavel

### Fragilidades observadas

1. nao existe um contrato comum de `correlation id` atravessando `api`, `integrations`, `communications` e `jobs`
2. a classificacao de falha ainda esta espalhada e implicita
3. o retry existe em `WebhookEvent`, mas ainda nao esta formalizado como policy reutilizavel
4. `jobs/base.py` ainda e minimo demais para rastrear idempotencia, correlation e retry
5. [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py) aparenta drift de runtime ao criar `AsyncJob` com campos `job_type` e `created_by_id`, enquanto [../../jobs/models.py](../../jobs/models.py) exposto hoje nao mostra esses campos

## Objetivo da onda minima

1. criar uma lingua comum da malha para os canais assincronos reais
2. reduzir improviso de retry e deduplicacao por canal
3. preparar telemetria e reprocessamento sem contaminar o dominio

## Canais-alvo desta primeira onda

1. webhook de enquete do WhatsApp via [../../api/v1/integrations_views.py](../../api/v1/integrations_views.py)
2. inbound WhatsApp via [../../integrations/whatsapp/services.py](../../integrations/whatsapp/services.py) e [../../communications/facade/messaging.py](../../communications/facade/messaging.py)
3. jobs rastreados via [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py), [../../jobs/base.py](../../jobs/base.py) e [../../jobs/models.py](../../jobs/models.py)

## Backlog tecnico atomico

## Item 1: contrato minimo de envelope da malha

### Objetivo

1. definir um envelope tecnico comum para sinais assincronos sem tocar no dominio

### Arquivos-alvo

1. novo modulo sugerido: `integrations/mesh/contracts.py`
2. [../../jobs/base.py](../../jobs/base.py)
3. [../../integrations/whatsapp/contracts.py](../../integrations/whatsapp/contracts.py)

### Entregas

1. `correlation_id`
2. `idempotency_key`
3. `source_channel`
4. `occurred_at`
5. `raw_reference` opcional

### Criterio de pronto

1. webhook e job conseguem carregar a mesma lingua minima de rastreabilidade

### Risco dominante

1. inventar envelope pesado demais e travar a evolucao

## Item 2: correlation id transversal

### Objetivo

1. garantir rastreabilidade ponta a ponta entre recebimento, processamento e reprocessamento

### Arquivos-alvo

1. [../../api/v1/integrations_views.py](../../api/v1/integrations_views.py)
2. [../../integrations/middleware.py](../../integrations/middleware.py)
3. [../../integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
4. [../../jobs/base.py](../../jobs/base.py)

### Entregas

1. extrair `correlation_id` de header quando existir
2. gerar fallback deterministico quando nao existir
3. propagar o id em logs, metadata de `JobResult` e registros de webhook

### Criterio de pronto

1. um incidente de webhook ou job pode ser seguido do request ate o reprocessamento

### Risco dominante

1. confundir `correlation_id` com `idempotency_key`

## Item 3: consolidar idempotency key por canal

### Objetivo

1. parar de tratar idempotencia como detalhe local de cada fluxo

### Arquivos-alvo

1. [../../integrations/middleware.py](../../integrations/middleware.py)
2. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py)
3. [../../communications/infrastructure/django_inbound_idempotency.py](../../communications/infrastructure/django_inbound_idempotency.py)
4. [../../integrations/stripe/services.py](../../integrations/stripe/services.py)

### Entregas

1. nomenclatura comum para `idempotency_key`
2. regra de precedencia por canal:
3. id externo do provider
4. header explicito
5. fingerprint deterministico
6. metadados minimos guardados junto ao evento

### Criterio de pronto

1. cada canal sabe qual chave usa e por que usa
2. duplicidade deixa de depender de leitura implicita do codigo

### Risco dominante

1. tentar unificar todos os canais em uma chave magica unica

## Item 4: classificacao minima de falha

### Objetivo

1. decidir quando repetir, bloquear, degradar ou desistir

### Arquivos-alvo

1. novo modulo sugerido: `integrations/mesh/failure_policy.py`
2. [../../integrations/whatsapp/poll_processor.py](../../integrations/whatsapp/poll_processor.py)
3. [../../jobs/base.py](../../jobs/base.py)
4. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py)

### Entregas

1. categorias minimas:
2. `retryable`
3. `non_retryable`
4. `duplicate`
5. `invalid_payload`
6. `unauthorized`

### Criterio de pronto

1. um erro deixa claro se vale reprocessar ou nao

### Risco dominante

1. misturar regra de negocio com classificacao tecnica de falha

## Item 5: policy minima de retry e backoff

### Objetivo

1. tirar o retry do modo implícito e transformá-lo em policy legivel

### Arquivos-alvo

1. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py)
2. novo modulo sugerido: `integrations/mesh/retry_policy.py`
3. [../../jobs/models.py](../../jobs/models.py)

### Entregas

1. policy simples com:
2. maximo de tentativas
3. backoff exponencial basal
4. histerese ou cooldown minimo
5. razao final de falha

### Criterio de pronto

1. webhook e job conseguem compartilhar a mesma semantica minima de retry

### Risco dominante

1. codificar policy em muitos lugares e chamar isso de padrao

## Item 6: endurecer `jobs` como canal da malha

### Objetivo

1. fazer `jobs` falar a lingua minima da Signal Mesh

### Arquivos-alvo

1. [../../jobs/base.py](../../jobs/base.py)
2. [../../jobs/models.py](../../jobs/models.py)
3. [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py)

### Entregas

1. adicionar metadata minima em `JobResult`
2. preparar `BaseJob` para aceitar `correlation_id` e `idempotency_key`
3. revisar drift entre `AsyncImportJobView` e `AsyncJob`

### Criterio de pronto

1. jobs deixam de ser trilho isolado e passam a ser corredor oficial da malha
2. existe um runner institucional para reprocessar jobs vencidos por `next_retry_at`
3. o runner pode ser ligado por cron sem introduzir broker ou scheduler novo

### Risco dominante

1. tentar consertar Celery, tracking e schema ao mesmo tempo

## Item 7: inventario de runtime drift da malha

### Objetivo

1. registrar inconsistencias que podem travar a Fase 2 se forem ignoradas

### Arquivos-alvo

1. [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py)
2. [../../jobs/models.py](../../jobs/models.py)
3. [../../integrations/middleware.py](../../integrations/middleware.py)
4. [../../integrations/whatsapp/models.py](../../integrations/whatsapp/models.py)
5. [signal-mesh-runtime-drift-inventory.md](signal-mesh-runtime-drift-inventory.md)

### Entregas

1. lista curta de drift confirmado
2. impacto
3. risco
4. ordem recomendada de saneamento
5. inventario canônico em [signal-mesh-runtime-drift-inventory.md](signal-mesh-runtime-drift-inventory.md)

### Criterio de pronto

1. a equipe sabe quais inconsistencias sao obstaculo real para a malha

## Ordem recomendada de execucao

1. Item 7
2. Item 1
3. Item 2
4. Item 4
5. Item 5
6. Item 3
7. Item 6

## O que nao fazer ainda

1. nao criar broker novo so para parecer que existe mesh
2. nao mover regra de negocio para middleware
3. nao introduzir event bus generico
4. nao misturar observabilidade profunda com `Red Beacon`
5. nao tentar fechar todos os canais externos na mesma onda

## Explicacao simples

Hoje o predio ja tem alguns guardas e algumas etiquetas, mas cada corredor usa um caderno diferente.

A Fase 2 minima faz quatro coisas:

1. da um nome unico para cada pacote
2. impede que o mesmo pacote entre duas vezes
3. decide quais tombos merecem nova tentativa
4. ensina jobs e webhooks a falarem a mesma lingua
