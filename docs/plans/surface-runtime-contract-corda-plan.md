<!--
ARQUIVO: C.O.R.D.A. do contrato unificado de runtime de superficie para performance, cache local e hidratacao progressiva.

TIPO DE DOCUMENTO:
- plano arquitetural e de execucao

AUTORIDADE:
- alta para a frente de runtime de superficie, cache local e invalidacao no frontend autenticado

DOCUMENTO PAI:
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)

DOCUMENTOS IRMAOS:
- [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- quando a decisao for padronizar cache local, hidratacao, invalidacao e reaproveitamento de leitura entre telas autenticadas
- quando uma superficie rica estiver fazendo requests repetidos sem mudanca real
- quando o frontend precisar decidir entre render local, hidratacao em idle, SSE, polling ou refresh completo
- antes de criar mais logica ad hoc de performance em `students`, `onboarding`, `operations`, `dashboard` ou `finance`

POR QUE ELE EXISTE:
- evita que cada tela invente sua propria estrategia de performance
- unifica a linguagem entre backend, frontend, page payload, assets e observabilidade
- protege contra cache rapido porem impreciso
- cria uma fundacao reutilizavel para otimizar cada superficie na raiz sem reabrir o debate estrutural toda vez

PONTOS CRITICOS:
- este plano nao transforma o frontend em fonte da verdade
- este plano nao autoriza persistir dados sensiveis em disco sem classificacao explicita
- este plano nao substitui otimizacao de payload, query ou CSS; ele organiza o reaproveitamento seguro
- se runtime, testes e este plano divergirem, o runtime vence e o plano deve ser atualizado
-->

# Contrato unificado de runtime de superficie C.O.R.D.A.

Data de referencia: 2026-04-17.

## C - Contexto

O OctoBox ja convergiu bem na linguagem de `page payload`, `presenter`, `snapshot`, `behavior` e `assets`.

Temos sinais fortes de maturidade:

1. `Dashboard` ja usa cache de snapshot no backend.
2. `Alunos` ja usa `directory_search`, `refresh_token`, bootstrap local e prefetch.
3. `Operations` ja carrega `snapshot_version` e convivencia entre evento e degradacao.
4. `Financeiro` ja melhorou muito no backend e expoe `performance_timing`.
5. a shell e o `page payload` ja existem como corredor oficial de entrega para o frontend.

O problema e que essas pecas ainda vivem com estrategias diferentes por superficie.

Na pratica:

1. cada tela pensa performance de um jeito
2. o navegador nao tem um contrato unico para saber quando pode confiar no cache local
3. algumas superficies mandam payload demais cedo demais
4. outras aproveitam bem o backend, mas ainda nao entregam a mesma semantica de reuso no frontend
5. o time acaba corrigindo tela por tela, sem acumular uma fundacao comum

Medicoes locais recentes reforcam isso:

1. `Entradas` ficou com HTML inicial muito pesado e `current_page_behavior` largo
2. `Alunos` melhorou bastante, mas ainda depende de uma linguagem propria
3. `Financeiro` segue como a superficie backend mais cara do grupo
4. `Dashboard` melhora muito apos warm-up, o que mostra oportunidade clara de reaproveitamento controlado
5. quase todas as telas ainda pagam um imposto fixo de CSS amplo no primeiro carregamento

Traducao simples:

1. o predio ja tem bons elevadores
2. o problema e que cada andar aperta botoes de forma diferente
3. falta um protocolo unico para o elevador saber quando subir, quando esperar e quando usar escada de emergencia

## O - Objetivo

Criar um contrato unificado para o runtime de superficie do frontend autenticado, de modo que cada tela rica declare, de forma explicita:

1. o que pode ser reaproveitado localmente
2. o que precisa ser invalidado
3. o que pode hidratar em idle ou sob demanda
4. o que depende de SSE, polling ou refresh completo
5. o que pode ou nao pode ser persistido em disco
6. quais assets sao criticos, progressivos ou de enhancement

Sucesso significa:

1. o primeiro carregamento pode continuar honesto e um pouco mais pesado quando fizer sentido
2. os proximos cliques e reaberturas curtas ficam quase instantaneos quando a leitura ainda e valida
3. o backend continua sendo a fonte oficial da verdade
4. o frontend deixa de reinventar performance por pagina
5. cada superficie continua livre para otimizar a raiz depois, sem quebrar a lingua estrutural do produto

### Objetivos tecnicos concretos

1. reduzir requests repetidos sem mudanca real
2. reduzir payload inicial inutil em `Entradas`
3. unificar criterios de invalidação
4. criar telemetria de hit, miss, stale e revalidate
5. amarrar dados e assets no mesmo contrato de superficie

## R - Riscos

### 1. Cache rapido, porem incorreto

Se o frontend reutilizar leitura local sem regra clara:

1. mostra dado velho
2. perde confianca operacional
3. cria bugs dificeis de reproduzir

Mitigacao:

1. backend segue como fonte oficial da verdade
2. `refresh_token`, `snapshot_version`, `cache_key` e `scope` decidem reuso
3. na duvida, invalida e revalida

### 2. Abstracao bonita demais e util de menos

Se o contrato nascer grande e magico:

1. cada tela vai contornar por fora
2. a base ganha mais uma camada sem ownership claro

Mitigacao:

1. contrato pequeno, declarativo e testavel
2. rollout por superficie
3. runtime compartilhado minimo, sem virar mini framework ornamental

### 3. Persistencia sensivel em lugar errado

Se `Financeiro`, `Locks`, estados de edicao ou leitura sensivel forem para `localStorage` sem criterio:

1. aumenta risco de vazamento local
2. mistura conveniencia com superficie sensivel

Mitigacao:

1. classificar dados por nivel de persistencia
2. usar memoria para leitura sensivel de curtissima vida
3. usar `sessionStorage` so para superficies permitidas
4. evitar persistencia em disco para estados financeiros criticos e locks

### 4. Invalidação insuficiente entre abas

Sem sincronizacao entre guias:

1. uma aba muta
2. a outra continua confiando em snapshot obsoleto

Mitigacao:

1. `BroadcastChannel` quando disponivel
2. fallback por `storage` event
3. evento local de mutacao bem-sucedida precisa propagar invalidacao

### 5. Requisições duplicadas por competicao entre componentes

Mesmo com cache local, a UX continua ruim se varios modulos disparam o mesmo fetch em paralelo.

Mitigacao:

1. deduplicacao de request por chave
2. `AbortController` para fetch superseded
3. fila de hidratacao com prioridade e limite de concorrencia

### 6. Performance de dados sem performance visual

Podemos acertar cache e ainda perder primeira pintura por CSS ou JS global.

Mitigacao:

1. o contrato de superficie precisa conversar com `assets`
2. cada tela deve declarar `critical`, `deferred` e `enhancement`
3. nao tratar dados e assets como trilhos separados

### 7. Drift de deploy

Mesmo com contrato bom, deploy novo pode deixar cache local incompatível com HTML e JS antigos na sessao.

Mitigacao:

1. adicionar `runtime_contract_version`
2. adicionar `asset_version` ou `build_version` como parte do escopo de invalidação
3. purge automatico quando a versao estrutural mudar

## D - Direcao

## Tese

A solucao elegante nao e um "guia solto" por pagina.

A solucao elegante e um **Surface Runtime Kernel** pequeno e oficial, alimentado por um **Contrato Unificado de Runtime de Superficie**, encaixado no `page payload`.

Em linguagem curta:

1. o backend declara a politica
2. o frontend executa a politica
3. a tela para de improvisar

### O corte arquitetural mais elegante

Em vez de um unico bloco confuso, o contrato deve nascer em duas metades irmas:

1. `surface_behavior`
2. `asset_behavior`

Isso e mais elegante do que jogar tudo em `behavior` sem divisao porque:

1. protege a lingua de dados e a lingua de assets
2. conecta performance de leitura com performance visual
3. evita que CSS e JS virem detalhe incidental fora do contrato da superficie

### Kernel compartilhado recomendado

O frontend autenticado deve convergir para um pequeno runtime compartilhado com cinco responsabilidades:

1. resolver reuso local seguro
2. coordenar hidratacao progressiva
3. deduplicar requests e abortar fetch obsoleto
4. propagar invalidacao entre componentes e abas
5. emitir telemetria de hit, miss, stale e fallback

O nome recomendado no codigo:

1. `surface_runtime`
2. `surface_contract`
3. `surface_cache`
4. `surface_hydrator`
5. `surface_invalidation_bus`

### Regra de verdade

1. backend continua sendo fonte oficial da verdade
2. frontend pode atuar como replica de leitura temporaria validada
3. mutacao nunca depende da confianca cega no cache local
4. a validacao estrutural sempre vence a conveniencia

### Shape recomendado do contrato

Modelo conceitual alvo:

```text
surface_runtime_contract
|-- surface_behavior
|   |-- surface_key
|   |-- runtime_contract_version
|   |-- scope
|   |-- cache
|   |-- bootstrap
|   |-- hydration
|   |-- filters
|   |-- events
|   |-- invalidation
|   `-- safety
|-- asset_behavior
|   |-- asset_contract_version
|   |-- critical_css
|   |-- deferred_css
|   |-- enhancement_css
|   |-- critical_js
|   |-- progressive_js
|   `-- interaction_triggers
`-- observability
    |-- telemetry_key
    |-- surface_budget_key
    `-- expected_hot_path
```

Exemplo orientativo:

```json
{
  "surface_behavior": {
    "surface_key": "student-directory",
    "runtime_contract_version": "v1",
    "scope": {
      "role_slug": "Owner",
      "session_scope": "authenticated",
      "storage_tier": "session"
    },
    "cache": {
      "enabled": true,
      "cache_key": "all",
      "refresh_token": "23:2026-04-17T12:00:00",
      "snapshot_version": "abc123",
      "ttl_ms": 120000
    },
    "bootstrap": {
      "mode": "minimal",
      "item_count": 15,
      "has_more": true,
      "next_offset": 15
    },
    "hydration": {
      "mode": "idle",
      "page_url": "/alunos/busca/paginas/",
      "page_size": 50,
      "prefetch_limit": 3,
      "max_parallel_requests": 1
    },
    "filters": {
      "local": ["query", "status", "sort"],
      "server": ["created_window", "financial_scope"]
    },
    "events": {
      "primary": "sse",
      "fallback": "poll",
      "poll_interval_ms": 30000
    },
    "invalidation": {
      "on_refresh_token_change": true,
      "on_snapshot_version_change": true,
      "on_mutation_success": true,
      "on_role_change": true,
      "on_contract_version_change": true,
      "cross_tab_sync": true
    },
    "safety": {
      "data_classification": "operational",
      "persist_to_disk": false,
      "requires_server_revalidation_before_commit": true
    }
  },
  "asset_behavior": {
    "asset_contract_version": "v1",
    "critical_css": ["shell", "hero", "active-panel"],
    "deferred_css": ["secondary-panels"],
    "enhancement_css": ["quick-panel", "signature-effects"],
    "critical_js": [],
    "progressive_js": ["interactive_tabs", "surface_runtime"],
    "interaction_triggers": {
      "quick_panel": "click",
      "search_hydration": "idle"
    }
  },
  "observability": {
    "telemetry_key": "student-directory",
    "surface_budget_key": "students-hot-path",
    "expected_hot_path": "cache-hit-after-first-load"
  }
}
```

## Responsabilidades backend e frontend

### Backend

O backend deve:

1. definir a verdade do dado
2. emitir `cache_key`, `refresh_token`, `snapshot_version` e escopo
3. declarar filtros locais seguros e filtros server-side obrigatorios
4. entregar bootstrap minimo e estavel
5. expor endpoints incrementais pequenos
6. publicar tokens ou eventos baratos de invalidacao
7. classificar sensibilidade e persistencia permitida
8. declarar assets por prioridade, nunca so por costume

O backend nao deve:

1. presumir que o cache local esta correto
2. delegar autorizacao ao frontend
3. mandar payload amplo so para "talvez usar depois"
4. misturar HTML auxiliar massivo com bootstrap de dados

### Frontend

O frontend deve:

1. obedecer o contrato da superficie
2. decidir entre render local, hydrate, fetch incremental ou refresh total
3. aplicar filtros locais apenas quando explicitamente permitidos
4. sincronizar invalidacao entre componentes e abas
5. deduplicar requests
6. abortar requests superseded
7. degradar com seguranca para backend na duvida
8. emitir telemetria de hit, miss, stale, revalidate e wait-for-backend

O frontend nao deve:

1. inventar heuristica sem contrato
2. usar `localStorage` como deposito universal de payload
3. persistir leitura sensivel em disco por conveniencia
4. manter UI otimista de estado critico sem revalidacao

## Regras de invalidacao

### Regra-mestra

Se houver duvida sobre validade, invalida e revalida.

### Invalidação obrigatoria

1. mudanca de `cache_key`
2. mudanca de `refresh_token`
3. mudanca de `snapshot_version`
4. mudanca de `runtime_contract_version`
5. mudanca de papel ou escopo autenticado
6. logout
7. mutacao bem-sucedida que afete a superficie
8. deploy que altere `asset_version` ou contrato de build

### Invalidação por tempo

TTL continua existindo, mas como linha de seguranca e nao como criterio principal de coerencia.

Regra:

1. `ttl_ms` protege contra sessao longa e estado esquecido
2. `refresh_token` e `snapshot_version` continuam vencendo TTL

### Sincronizacao entre abas

Toda superficie que permitir cache local precisa suportar:

1. invalidacao por `BroadcastChannel`
2. fallback por `storage` event
3. purge em logout

### Purge de sessao

Ao fazer logout ou trocar usuario:

1. limpar cache em memoria
2. limpar `sessionStorage`
3. limpar chaves persistidas permitidas daquela sessao
4. emitir evento local de purge

## Classificacao de persistencia

Para evitar risco escondido, cada superficie deve declarar sua classe.

### Classe `memory-only`

Usar para:

1. locks
2. estados de edicao
3. leitura financeira critica
4. qualquer estado que nao pode sobrar em disco da maquina

### Classe `session`

Usar para:

1. indices operacionais
2. listas de leitura reaproveitavel por poucos minutos
3. superficies com ganho claro dentro da mesma sessao autenticada

### Classe `persistent`

Evitar por padrao no produto autenticado.

So considerar quando:

1. o dado for nao sensivel
2. houver forte ganho de UX
3. houver purge e versionamento bem amarrados

## O que estavamos esquecendo e precisa entrar no plano

1. **classificacao de sensibilidade do dado**
   - performance sem classificacao vira risco silencioso
2. **purge no logout**
   - sem isso, sessao nova pode herdar leitura velha
3. **coerencia entre abas**
   - sem isso, mutacao em uma guia nao se propaga
4. **versao estrutural do contrato**
   - sem isso, deploy pode conviver com cache incompatível
5. **deduplicacao de fetch**
   - sem isso, otimizar payload nao elimina tempestade de request
6. **abort de requisicao obsoleta**
   - sem isso, resposta velha ainda pode ganhar da nova
7. **telemetria de hit e miss**
   - sem isso, a melhoria fica baseada em impressao
8. **ligacao com assets**
   - sem isso, o app melhora em dados e continua pagando caro na primeira pintura
9. **fallback quando SSE falhar**
   - sem isso, runtime bom vira dependencia fragil
10. **governanca de filtros locais**
    - sem isso, o frontend pode "mentir" em filtros que exigem backend

## Estrategia por superficie

## 1. Alunos

Estado atual:

1. melhor candidato a piloto oficial
2. ja tem `directory_search`, `refresh_token` e `student_prefetch`

Direcao:

1. promover `Alunos` para primeira implementacao oficial do contrato
2. encapsular a logica atual dentro do `surface_runtime`
3. manter bootstrap curto
4. manter quick panel e ficha sob demanda
5. idle hydration opcional para completar indice

O que nao fazer:

1. voltar a inflar o payload inicial
2. persistir snapshot da ficha financeira em disco

## 2. Entradas

Estado atual:

1. maior candidato a regressao estrutural
2. payload inicial ainda envia indice largo demais
3. `row_html` em massa pesa no `current_page_behavior`

Direcao:

1. aplicar o mesmo contrato de `Alunos`
2. reduzir bootstrap inicial
3. mandar apenas dados compactos no indice inicial
4. mover HTML rico para fetch incremental ou montagem local quando seguro
5. usar `refresh_token` como sentinela principal

O que nao fazer:

1. manter `200` itens com `row_html` no bootstrap
2. transformar filtro complexo em filtro local sem garantia

## 3. Operations

Estado atual:

1. ja conversa bem com `snapshot_version`
2. ja tem caminho de SSE e degradacao

Direcao:

1. encaixar `snapshot_version` no contrato unificado
2. declarar `events.primary = sse`
3. declarar `fallback = poll`
4. reaproveitar leitura local curta so quando a versao continuar valida

O que nao fazer:

1. assumir SSE como sempre disponivel
2. esconder regra de fallback fora do contrato

## 4. Dashboard

Estado atual:

1. snapshot backend cacheado ja entrega ganho forte
2. ainda falta semantica unica de reuso no cliente

Direcao:

1. contrato leve de superficie
2. paineis auxiliares em hidratacao progressiva
3. retorno curto a tela pode reaproveitar leitura se o token continuar valido

O que nao fazer:

1. recalcular tudo no frontend
2. mover decisao gerencial para heuristica local

## 5. Financeiro

Estado atual:

1. backend esta bem melhor
2. continua a superficie mais cara em custo quente
3. leitura e mais sensivel

Direcao:

1. aplicar o contrato com mais cautela
2. separar blocos criticos e auxiliares
3. usar memoria ou session curta para o que for permitido
4. manter revalidacao forte em estados criticos
5. hidratar trilhos auxiliares sob demanda ou idle

O que nao fazer:

1. cachear leitura financeira sensivel em disco
2. usar estado local como verdade final em mutacao

## Solucao mais elegante identificada na revisao

O plano base de "guia de comportamento por pagina" e bom.

A revisao conjunta de arquitetura, performance e frontend aponta para uma solucao ainda mais elegante:

## `Surface Runtime Kernel` + `Surface Contract`

Em vez de cada pagina ter um "manual proprio", o produto ganha:

1. um **kernel** compartilhado no frontend
2. um **contrato declarativo** emitido pelo backend
3. uma **ponte oficial com `page payload` e `assets`**

Isso e mais elegante porque:

1. reduz logica duplicada
2. evita que paginas virem mini frameworks
3. acumula otimizacao estrutural
4. permite otimizar cada tela na raiz depois sem reabrir a fundacao

### Blocos do kernel recomendados

1. `surface_runtime`
   - orquestrador principal
2. `surface_cache`
   - cache em memoria e sessao
3. `surface_hydrator`
   - idle, on-demand e fila progressiva
4. `surface_invalidation_bus`
   - cross-tab, mutation e purge
5. `surface_request_coordinator`
   - dedupe, abort e prioridade
6. `surface_telemetry`
   - hit, miss, stale, wait e fallback

### O que torna essa solucao superior ao "guia puro"

Um guia puro ainda pode virar documentacao obedecida pela metade.

O kernel pequeno:

1. torna o contrato executavel
2. reduz liberdade para regressao
3. protege coerencia entre telas

Metafora simples:

1. o guia e a regra da cozinha
2. o kernel e o fogao industrial ja configurado para seguir a regra

## A - Acoes

## Fase 0 - Fundacao do contrato

Objetivo:

1. consolidar a lingua oficial

Acoes:

1. criar helpers backend para `surface_behavior`
2. criar helpers backend para `asset_behavior`
3. criar `runtime_contract_version`
4. criar classificacao de persistencia
5. definir chaves padrao de telemetria

Critério de pronto:

1. shape oficial documentado
2. helper minimo implementavel
3. sem impactar ainda todas as telas

## Fase 1 - Kernel minimo no frontend

Objetivo:

1. tirar a inteligencia ad hoc de dentro das paginas

Acoes:

1. criar `surface_runtime`
2. criar cache em memoria
3. criar cache de sessao permitido
4. implementar dedupe e abort
5. implementar purge de logout
6. implementar invalidação por versao e token

Critério de pronto:

1. kernel funciona em uma superficie piloto
2. requests duplicados ja caem
3. telemetria basica ja existe

## Fase 2 - Alunos como piloto oficial

Objetivo:

1. transformar o caso mais maduro no padrao oficial

Acoes:

1. adaptar `Alunos` ao contrato
2. ligar `student_prefetch` ao kernel
3. validar filtros locais seguros
4. medir hit, miss e wait-for-backend

Critério de pronto:

1. `Alunos` continua correto
2. menos branching especifico de pagina
3. melhoria comprovada de requests repetidos

## Fase 3 - Entradas como correcao estrutural

Objetivo:

1. derrubar o maior payload inicial desnecessario do grupo

Acoes:

1. reduzir bootstrap
2. remover HTML auxiliar massivo do indice inicial
3. paginar indice local
4. fetch incremental sob contrato
5. deduplicar refresh

Critério de pronto:

1. HTML inicial cai
2. `current_page_behavior` cai
3. proximos cliques reaproveitam leitura local

## Fase 4 - Operations e Dashboard

Objetivo:

1. unificar `snapshot_version`, SSE e warm paths

Acoes:

1. encaixar `Operations` no contrato
2. declarar fallback de evento
3. adicionar semantica de reaproveitamento no `Dashboard`
4. medir retorno curto a tela

Critério de pronto:

1. menos logica fora do contrato
2. degradacao segura confirmada

## Fase 5 - Financeiro com regra mais dura

Objetivo:

1. ganhar fluidez sem comprometer leitura sensivel

Acoes:

1. classificar blocos criticos e auxiliares
2. limitar persistencia a memoria ou sessao curta quando permitido
3. hidratar trilhos secundarios sob demanda
4. revalidar em mutacoes criticas

Critério de pronto:

1. UX mais fluida
2. sem risco de estado financeiro stale em ponto decisivo

## Validacao obrigatoria

Para cada superficie migrada, medir antes e depois:

1. tamanho do HTML inicial
2. tamanho do `current_page_behavior`
3. quantidade de requests no primeiro clique util
4. quantidade de requests em clique repetido
5. tempo do primeiro clique util
6. tempo do segundo clique util
7. cache hit rate
8. stale invalidate rate
9. ocorrencias de `wait-for-backend`
10. regressao visual de assets criticos

## Nao-objetivos

Este plano nao busca:

1. transformar o OctoBox em SPA
2. fazer cache agressivo de HTML autenticado no edge
3. jogar tudo em `localStorage`
4. trocar verdade transacional por heuristica de frontend
5. resolver query ruim so com runtime bonito
6. resolver CSS ruim so com cache de dados

## Regra final

O contrato unificado de runtime de superficie so esta pronto quando:

1. o primeiro request puder continuar honesto
2. os proximos cliques forem muito mais rapidos quando nada mudou
3. a invalidacao continuar mais confiavel do que a conveniencia
4. backend, frontend e assets falarem a mesma lingua
5. cada tela puder continuar sendo otimizada na raiz sem quebrar a fundacao comum
