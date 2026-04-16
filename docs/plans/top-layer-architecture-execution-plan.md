<!--
ARQUIVO: plano tecnico de execucao para consolidar o topo arquitetural do OctoBox sobre o runtime atual.

POR QUE ELE EXISTE:
- traduz a tese arquitetural do predio em backlog tecnico por fase, com arquivos reais do repositorio.
- evita que Signal Mesh, Scaffold Agents, Alert Siren, Red Beacon e Vertical Sky Beam virem linguagem bonita sem aterrissagem operacional.
- organiza a ordem segura de execucao a partir do estado atual do monolito modular.

O QUE ESTE ARQUIVO FAZ:
1. define o que ja esta pronto, o que ainda e transicao e o que ainda e conceito.
2. quebra a evolucao em fases pequenas e verificaveis.
3. amarra cada fase a modulos, guardrails e sinais de pronto.

TIPO DE DOCUMENTO:
- execucao ativa e backlog arquitetural

AUTORIDADE:
- alta para a trilha de consolidacao do topo arquitetural

DOCUMENTO PAI:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for como sair da tese arquitetural e entrar na execucao tecnica real
- quando for decidir em que ordem implementar Center, Signal Mesh, Scaffold Agents, Alert Siren, Red Beacon e Vertical Sky Beam
- quando for revisar se uma mudanca arquitetural esta ancorada no runtime atual ou apenas no discurso

PONTOS CRITICOS:
- este plano nao autoriza reescrita do produto.
- o plano presume preservacao do monolito modular e crescimento por facades, contratos e observabilidade.
- Vertical Sky Beam nao deve ser implementado antes de existir Beacon e Siren com criterio real.
-->

# Plano de execucao da arquitetura superior

## Regra de autoridade deste documento

1. [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md) define a linguagem oficial do predio
2. [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md) define o rumo macro de crescimento
3. este documento define a ordem tecnica de ataque, os modulos reais e o backlog por fase
4. se o runtime divergir deste plano, o codigo e os testes vencem e este documento deve ser corrigido

## Tese central

O OctoBox ja tem a fundacao do `Center Layer` parcialmente aterrissada, mas ainda nao materializou a camada superior inteira do predio.

Hoje o estado correto do projeto e este:

1. `Center Layer` ja existe de forma real em facades publicas
2. `Signal Mesh` existe como necessidade clara e sementes isoladas no runtime
3. `Scaffold Agents` ainda nao existem como namespace tecnico explicito
4. `Alert Siren` ainda nao existe como engine operacional
5. `Red Beacon` ainda nao existe como snapshot consolidado de estado
6. `Vertical Sky Beam` ainda e conceito extraordinario e deve continuar assim ate haver base suficiente

Traducao pratica:

1. a porta principal ja começou a ser construida
2. os mensageiros e alarmes ainda estao dispersos
3. o topo do predio ainda nao pode ser ligado sem disciplina

## Estado atual resumido

### O que ja esta concreto

Corredores reais do `Center Layer`:

1. [../../operations/facade/class_grid.py](../../operations/facade/class_grid.py)
2. [../../operations/facade/workspace.py](../../operations/facade/workspace.py)
3. [../../students/facade/student_lifecycle.py](../../students/facade/student_lifecycle.py)
4. [../../communications/facade/messaging.py](../../communications/facade/messaging.py)

Leituras e snapshots publicos ja reais:

1. [../../dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
2. [../../catalog/student_queries.py](../../catalog/student_queries.py)
3. [../../catalog/finance_queries.py](../../catalog/finance_queries.py)
4. [../../catalog/class_grid_queries.py](../../catalog/class_grid_queries.py)
5. [../../operations/session_snapshots.py](../../operations/session_snapshots.py)

Sementes reais de borda, integracao e observabilidade:

1. [../../config/urls.py](../../config/urls.py)
2. [../../api/urls.py](../../api/urls.py)
3. [../../api/v1/urls.py](../../api/v1/urls.py)
4. [../../api/v1/views.py](../../api/v1/views.py)
5. [../../integrations/whatsapp/contracts.py](../../integrations/whatsapp/contracts.py)
6. [../../integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
7. [../../jobs/base.py](../../jobs/base.py)
8. [../../monitoring/prometheus_middleware.py](../../monitoring/prometheus_middleware.py)

### O que ainda e fragilidade estrutural

1. a API v1 ainda mistura endpoints de natureza diferente no mesmo modulo
2. jobs ainda sao contrato base, nao sistema maduro de reexecucao e observabilidade
3. canais externos ainda nao compartilham uma disciplina unica de idempotencia, retry e backpressure
4. nao existe namespace tecnico explicito para mecanismos temporarios de transicao
5. nao existe engine formal de risco consolidado e mudanca de postura defensiva

### O que ainda nao deve ser tratado como pronto

1. `Signal Mesh` como malha operacional completa
2. `Alert Siren` como sistema real de mobilizacao
3. `Red Beacon` como emissao consolidada e confiavel
4. `Vertical Sky Beam` como implementacao utilizavel

## Regra geral de execucao

Toda fase deste plano deve obedecer esta ordem mental:

1. preservar o que ja funciona
2. reduzir dependencia publica da borda em relacao ao miolo
3. explicitar contratos antes de espalhar automacao
4. introduzir observabilidade antes de declarar controle
5. introduzir estados extraordinarios apenas depois da base confiavel

Anti-padroes proibidos:

1. criar um barramento generico chamado mesh sem caso real
2. mover regra de negocio para scaffold temporario
3. fazer Alert Siren nascer como badge visual
4. fazer Red Beacon nascer como endpoint de debug disfarçado
5. disparar Vertical Sky Beam por empolgacao ou estetica

## Regra operacional para abrir a proxima rodada

Esta trilha nao deve abrir nova rodada por ansiedade arquitetural.

Ela abre quando:

1. a producao atual provou estabilidade suficiente
2. o proximo gargalo ficou legivel
3. a proxima fatia cabe em um corredor pequeno e verificavel

### Abrir

Abrir a proxima rodada quando estes sinais aparecerem juntos:

1. `estabilidade`
2. `pressao real`
3. `clareza de alvo`

Thresholds simples:

1. pelo menos uma janela curta de operacao sem erro novo relevante em login, dashboard, jobs, retries e health
2. `Red Beacon`, `Alert Siren`, smoke operacional e logs contam uma historia coerente sobre onde esta o proximo atrito
3. existe um proximo bloco pequeno e fechado para atacar, por exemplo:
4. `Scaffold Agents`
5. ampliacao controlada da `Alert Siren`
6. consolidacao do `Red Beacon` por capacidade

Regra pratica:

1. se a producao esta estavel e o proximo gargalo esta obvio, abrir

### Aguardar

Aguardar quando a base parece boa, mas ainda falta confianca operacional suficiente para mexer de novo.

Sinais:

1. producao sem falha grave, mas com pouco tempo de observacao
2. sinais operacionais ainda curtos demais para mostrar um gargalo dominante
3. mais de um proximo caminho parece plausivel e ainda nao ficou claro qual vence

Thresholds simples:

1. smoke tests verdes, mas janela de observacao ainda recente
2. sem erro grave, mas sem repeticao suficiente para chamar o proximo alvo de obvio
3. a pergunta ainda e `qual bloco abrir?` e nao `quando comecamos este bloco?`

Regra pratica:

1. se a producao esta limpa, mas o proximo gargalo ainda nao ficou nitido, aguardar

### Nao abrir

Nao abrir a proxima rodada quando a base atual ainda esta instavel ou quando a proxima fase ainda seria abstracao demais.

Sinais:

1. regressao ou surpresa em producao
2. drift de schema, integridade historica ou smoke falhando
3. necessidade de hotfix corretivo antes de qualquer evolucao nova
4. vontade de abrir varias frentes ao mesmo tempo sem um corredor dominante

Thresholds simples:

1. `check`, migrate, smoke, health ou dashboard falham
2. `Alert Siren` ou `Red Beacon` contam historia incoerente com o runtime
3. a operacao ainda esta corrigindo parafuso da rodada anterior

Regra pratica:

1. se a base ainda pede correcao ou se a proxima fase ainda seria discurso demais, nao abrir

## Guardrail de revisao durante a Fase 1

Enquanto a Fase 1 estiver aberta, toda mudanca em borda externa deve obedecer estas regras:

1. novo fluxo externo prefere facade publica ja promovida
2. novo flow de compatibilidade pode usar adaptador fino, mas nao deve recentralizar regra
3. novo import de `*.infrastructure` em view, API, webhook, admin action ou service de borda precisa justificativa explicita
4. se o bypass for inevitavel, ele deve entrar no inventario ativo da fase antes de ser tratado como aceitavel

Fronteiras cobertas por este guardrail:

1. `catalog/views/`
2. `operations/*views.py`
3. `api/v1/*`
4. `integrations/*`
5. `communications/services.py`

Checklist curto de revisao:

1. esta entrada nova ja poderia usar facade publica existente?
2. a borda esta falando com contrato estavel ou com detalhe tecnico?
3. se houve bypass, ele esta classificado com motivo, risco e destino futuro?

Regra de decisao:

1. se existir facade promovida, o PR deve usar facade promovida
2. se nao existir facade promovida, o PR deve deixar claro que o bypass e temporario e documentado
3. se o PR introduzir novo import de `*.infrastructure` sem justificativa, a mudanca nao fecha a Fase 1; ela reabre o problema

## Fase 0: baseline frio da obra

### Objetivo

1. mapear a diferenca entre arquitetura declarada e arquitetura realmente aterrissada
2. congelar a fotografia atual antes de novas extracoes

### Arquivos e modulos de leitura obrigatoria

1. [../../config/urls.py](../../config/urls.py)
2. [../../api/v1/urls.py](../../api/v1/urls.py)
3. [../../api/v1/views.py](../../api/v1/views.py)
4. [../../communications/services.py](../../communications/services.py)
5. [../../integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
6. [../../jobs/base.py](../../jobs/base.py)
7. [../../monitoring/prometheus_middleware.py](../../monitoring/prometheus_middleware.py)
8. [../architecture/promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md)

### Entregas

1. inventario dos corredores oficiais ja reais
2. inventario dos bypasses ainda fora do `Center`
3. tabela separando permanente, transicional e extraordinario
4. lista dos pontos que hoje parecem `Signal Mesh`, mas ainda nao obedecem politica comum

### Sinal de pronto

1. ficou claro por onde cada fluxo entra hoje
2. ficou claro o que ainda e rapel arquitetural

### Contencao

1. nenhuma mudanca estrutural nesta fase
2. so leitura, classificacao e backlog

## Fase 1: expandir o Center Layer

### Objetivo

1. tornar o `Center Layer` a entrada dominante dos fluxos externos relevantes
2. reduzir o conhecimento da borda sobre wiring interno

### Arquivos e modulos-alvo

1. [../../operations/facade/class_grid.py](../../operations/facade/class_grid.py)
2. [../../operations/facade/workspace.py](../../operations/facade/workspace.py)
3. [../../students/facade/student_lifecycle.py](../../students/facade/student_lifecycle.py)
4. [../../communications/facade/messaging.py](../../communications/facade/messaging.py)
5. [../../communications/services.py](../../communications/services.py)
6. [../../api/v1/views.py](../../api/v1/views.py)
7. [../../operations/urls.py](../../operations/urls.py)
8. modulos de views em `catalog/views/` e `operations/`

### Entregas

1. reancorar entradas externas nas facades corretas
2. reduzir services historicos a adaptadores finos
3. impedir novos atalhos diretos para infrastructure
4. registrar explicitamente os bypasses ainda inevitaveis

### Sinal de pronto

1. fluxo novo entra por facade publica
2. view deixa de conhecer detalhes de infrastructure
3. service legado vira capa fina, nao centro de regra

### Rollback ou contencao

1. manter compatibilidade por adaptador fino em vez de cortar chamada antiga de uma vez
2. reancorar por fatias, nao por renomeacao massiva

### Detalhamento executavel

1. a decomposicao atomica desta fase fica em [top-layer-phase1-center-layer-task-breakdown.md](top-layer-phase1-center-layer-task-breakdown.md)

## Fase 2: materializar a Signal Mesh minima

### Objetivo

1. transformar contratos externos, webhooks, retries e jobs em uma disciplina unica
2. impedir que payload bruto e reprocessamento contaminem o nucleo

### Arquivos e modulos-alvo

1. [../../integrations/whatsapp/contracts.py](../../integrations/whatsapp/contracts.py)
2. [../../integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
3. [../../api/v1/views.py](../../api/v1/views.py)
4. [../../jobs/base.py](../../jobs/base.py)
5. novo namespace sugerido: `integrations/mesh/` ou `communications/mesh/`

### Entregas

1. contratos normalizados por canal
2. correlation id e idempotency key para entradas assincronas relevantes
3. politica minima de retry e classificacao de falha
4. separacao entre recebimento HTTP e processamento reexecutavel
5. ponto unico para guardrails de canal
6. corredor oficial de `jobs` com despacho por `job_type`
7. runner institucional de reprocessamento por `next_retry_at`
8. comando operacional acionavel por cron do stack atual

### Sinal de pronto

1. payload bruto nao sobe para dominio como lingua oficial
2. webhook deixa de carregar fan-out e retry na borda
3. jobs passam a ter semantica minima comum
4. jobs vencidos podem ser reencaminhados sem depender de wiring manual por task

### Rollback ou contencao

1. manter caminhos antigos atras de fachada enquanto a nova malha consolida
2. nao remover fluxo antigo sem telemetria suficiente do novo

### Backlog minimo desta fase

1. a primeira onda executavel da `Signal Mesh` fica em [signal-mesh-phase2-minimum-backlog.md](signal-mesh-phase2-minimum-backlog.md)
2. o scheduler explicito desta onda fica em [signal-mesh-retry-scheduler-runbook.md](signal-mesh-retry-scheduler-runbook.md)
3. o deploy controlado do saneamento de `AsyncJob` fica em [asyncjob-signal-mesh-migration-deploy-runbook.md](asyncjob-signal-mesh-migration-deploy-runbook.md)

## Fase 3: introduzir Scaffold Agents explicitos

### Objetivo

1. transformar mecanismos temporarios de protecao em objetos arquiteturais rastreaveis
2. impedir que remendos invisiveis virem estrutura permanente

### Arquivos e modulos-alvo

1. novo namespace sugerido: `monitoring/scaffold/` ou `shared_support/transition/`
2. [../../communications/services.py](../../communications/services.py)
3. [../../api/v1/views.py](../../api/v1/views.py)
4. fluxos de integracao em `integrations/`

### Entregas

1. registro explicito de cada scaffold ativo
2. motivo de existencia
3. risco mitigado
4. owner tecnico
5. criterio de remocao
6. apontamento do corredor definitivo que deve substitui-lo

### Sinal de pronto

1. todo andaime tem nome e prazo moral de saida
2. nenhum bypass relevante fica sem classificacao

### Rollback ou contencao

1. se o scaffold começar a carregar regra central, interromper e devolver a regra ao corredor permanente

## Fase 4: implementar Alert Siren

### Objetivo

1. fazer o sistema mudar de postura defensiva quando o risco sobe
2. ligar alerta a politica real de protecao

### Arquivos e modulos-alvo

1. novo arquivo sugerido: [../../monitoring/alert_siren.py](../../monitoring/alert_siren.py)
2. novo arquivo sugerido: [../../monitoring/risk_states.py](../../monitoring/risk_states.py)
3. novo arquivo sugerido: [../../monitoring/defense_actions.py](../../monitoring/defense_actions.py)
4. [../../monitoring/prometheus_middleware.py](../../monitoring/prometheus_middleware.py)
5. `jobs/` e `integrations/` como consumidores das politicas defensivas

### Entregas

1. niveis `silent`, `low`, `medium`, `high`
2. consolidacao de risco por fila, latencia, falha recorrente e canal critico
3. politicas reais de contencao, degradacao e protecao
4. criterio de retorno ao estado normal

### Sinal de pronto

1. a sirene muda comportamento do sistema, nao so o texto da tela
2. canais nao essenciais podem ser contidos sob risco alto

### Rollback ou contencao

1. iniciar com politicas observaveis e reversiveis
2. evitar travas irreversiveis na primeira onda

## Fase 5: implementar Red Beacon

### Objetivo

1. emitir para fora um estado consolidado, legivel e seguro do predio
2. separar telemetria interna profunda de sinal externo curado

### Arquivos e modulos-alvo

1. novo arquivo sugerido: [../../monitoring/beacon_snapshot.py](../../monitoring/beacon_snapshot.py)
2. [../../dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
3. [../../monitoring/prometheus_middleware.py](../../monitoring/prometheus_middleware.py)
4. [../../config/urls.py](../../config/urls.py) se for preciso expor endpoint proprio

### Entregas

1. snapshot consolidado por capacidade
2. estado da `Alert Siren` refletido no topo emissor
3. health sintetizado de canais criticos
4. modo degradado ou pronto, sem vazar detalhe sensivel

### Sinal de pronto

1. operacao consegue ler o estado geral sem abrir o caos interno
2. o Beacon nao depende de um unico ponto fragil

### Rollback ou contencao

1. comecar com consumo interno no dashboard antes de abertura maior
2. nao expor payload interno cru em nenhuma hipotese

## Fase 6: habilitar Vertical Sky Beam

### Objetivo

1. criar o modo extraordinario do topo emissor com criterio tecnico real
2. impedir banalizacao do estado maximo de exposicao

### Arquivos e modulos-alvo

1. novo arquivo sugerido: [../../monitoring/vertical_sky_beam.py](../../monitoring/vertical_sky_beam.py)
2. [../../monitoring/beacon_snapshot.py](../../monitoring/beacon_snapshot.py)
3. [../../monitoring/alert_siren.py](../../monitoring/alert_siren.py)
4. [vertical-sky-beam-readiness-guide.md](vertical-sky-beam-readiness-guide.md)

### Entregas

1. modo `critical`
2. modo `readiness`
3. bloqueio contra disparo frequente
4. histerese e criterio de retorno

### Sinal de pronto

1. Beam so dispara sob crise severa ou prontidao estrutural rara
2. Beam nao substitui Siren nem Beacon

### Rollback ou contencao

1. manter o Beam desligado por padrao ate haver confianca nos criterios
2. comecar em ambiente interno e observavel

## Fase 7: podar a borda e organizar API

### Objetivo

1. impedir que a API vire corredor misto e psicologicamente central demais
2. organizar contratos externos por capacidade real

### Arquivos e modulos-alvo

1. [../../api/urls.py](../../api/urls.py)
2. [../../api/v1/urls.py](../../api/v1/urls.py)
3. [../../api/v1/views.py](../../api/v1/views.py)
4. `api/v1/finance_views.py`
5. `api/v1/jobs_views.py`
6. novos modulos por capacidade em `api/v1/`

### Entregas

1. separar manifesto e health de endpoints de negocio
2. agrupar rotas por capacidade
3. revisar endpoints sensiveis de debug e bootstrap
4. reduzir mistura entre API publica, integracao e utilitarios transitivos

### Sinal de pronto

1. a API passa a ser lida por capacidade, nao por acumulacao historica
2. a borda externa fica mais previsivel

### Rollback ou contencao

1. preservar nomes publicos quando possivel
2. usar alias de compatibilidade curta se houver contrato ja consumido externamente

## Guardrails operacionais obrigatorios

### Observabilidade

1. toda nova peca precisa publicar metricas minimas de sucesso, falha e latencia
2. labels de Prometheus devem evitar cardinalidade perigosa
3. jobs precisam registrar status e motivo de falha

### Seguranca

1. nao expor endpoints de health ampliado sem criterio
2. endpoints de integracao devem usar autenticacao, idempotencia e trilha de auditoria
3. Beacon nao pode vazar detalhes sensiveis do miolo

### Idempotencia e retry

1. entradas assincronas devem nascer com chave idempotente quando isso mudar o risco
2. retry sem classificacao de falha e proibido
3. reprocessamento deve ser rastreavel

### Backpressure e falha

1. canais nao criticos devem poder degradar antes de derrubar o nucleo
2. Alert Siren deve priorizar isolamento local antes de retracao ampla
3. falha extraordinaria deve ser contida antes de ser exposta como Beam

### Performance

1. nenhum novo corredor deve aumentar recomposicao manual na borda
2. consolidacao de snapshots deve continuar favorecendo leitura pronta
3. se a arquitetura ficar mais bonita e a leitura operacional ficar mais lenta, a mudanca falhou

### Custo

1. evitar instalar infraestrutura externa sem uso real
2. aproveitar `monitoring/`, `jobs/`, `integrations/` e facades atuais antes de criar novas casas
3. preferir extracao pequena e iterativa a framework novo por prestígio

## O que nao fazer ainda

1. nao abrir microservicos
2. nao criar event bus distribuido
3. nao mover `boxcore` agressivamente por causa desta frente
4. nao declarar Beam de consagracao antes de Beacon e Siren funcionarem de verdade
5. nao chamar qualquer adaptador temporario de scaffold sem owner e criterio de remocao

## Backlog ativo imediato

Inicio recomendado desta trilha:

1. executar a Fase 0 e registrar o inventario frio
2. atacar a Fase 1 nos pontos onde a borda ainda conhece demais o miolo
3. escolher um primeiro canal de `Signal Mesh` real, comecando por WhatsApp e jobs relacionados
4. so depois abrir a frente de `Alert Siren` e `Red Beacon`

## Saida minima desta rodada

Ao fim da primeira rodada desta frente, precisamos ter:

1. inventario canonico de bypasses
2. backlog curto de reancoragem no `Center`
3. proposta minima de namespace para `Signal Mesh`
4. proposta minima de namespace para `Scaffold Agents`
5. criterios objetivos iniciais para `Alert Siren`

Se isso nao existir, o topo arquitetural ainda estara bonito no discurso e fraco na estrutura.
