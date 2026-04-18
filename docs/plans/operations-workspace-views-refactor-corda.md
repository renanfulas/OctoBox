<!--
ARQUIVO: C.O.R.D.A. de refatoracao segura das views de workspace operacional.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional
- trilho de refatoracao incremental

AUTORIDADE:
- alta para a evolucao estrutural de `operations/workspace_views.py`

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [wod-post-publication-operational-loop.md](wod-post-publication-operational-loop.md)

QUANDO USAR:
- quando a duvida for como emagrecer `operations/workspace_views.py` sem reescrever a operacao
- quando precisarmos separar view HTTP, leitura operacional, payload e mutacao
- quando a board de aprovacao do WOD estiver crescendo mais rapido do que a seguranca de manutencao

POR QUE ELE EXISTE:
- evita que a borda HTTP vire o cerebro do produto
- reduz acoplamento entre request/response, heuristica operacional e montagem de contexto
- protege a evolucao da board contra regressao silenciosa e performance acidental ruim

O QUE ESTE ARQUIVO FAZ:
1. formaliza o problema atual de concentracao em `operations/workspace_views.py`
2. define o alvo arquitetural sem rewrite
3. organiza a refatoracao por ondas pequenas e testaveis
4. registra o que nao fazer agora para evitar overengineering
5. aponta para o inventario vivo da Onda 0 em [operations-workspace-views-wave0-inventory.md](operations-workspace-views-wave0-inventory.md)
6. referencia o mapa final de ownership em [../reference/operations-wod-ownership-map.md](../reference/operations-wod-ownership-map.md)

PONTOS CRITICOS:
- arquivo grande sozinho nao significa gargalo de CPU
- o risco real aqui e mistura de responsabilidades, dificuldade de teste e regressao de query
- refatorar sem baseline de comportamento pode trocar bagunca visivel por bug invisivel
-->

# C.O.R.D.A. - Refatoracao segura das views de workspace operacional

## C - Contexto

O runtime atual do OctoBox ja evoluiu para um modelo melhor do que um Django solto por paginas:

1. `operations/queries.py` ja concentra leituras reutilizaveis
2. `operations/presentation.py` ja concentra contratos de page payload
3. `operations/actions.py` e `operations/action_views.py` ja mostram a tese de tirar mutacao da borda HTTP
4. `operations/facade/` ja existe como corredor oficial em partes do dominio

Mesmo assim, `operations/workspace_views.py` cresceu demais e hoje concentra funcoes demais no mesmo lugar.

Estado observado na base atual:

1. `operations/workspace_views.py` esta com 2535 linhas
2. o arquivo mistura builders puros, leitura operacional, heuristicas executivas, action views e classes HTTP
3. a board de aprovacao/publicacao do WOD puxou para dentro da mesma borda:
   - historico publicado
   - follow-up
   - memoria operacional
   - tendencias
   - checkpoint semanal
   - maturidade
   - governanca

Em linguagem simples:

1. a porta de entrada da casa esta fazendo trabalho de recepcao, cozinha, almoxarifado e diretoria ao mesmo tempo

### Leitura arquitetural correta

Pelo modelo oficial do projeto:

1. view HTTP pertence ao `Nivel 1: acesso externo`
2. payload e leitura organizada deveriam ficar mais proximos da camada de apresentacao e leitura
3. regra e heuristica nao devem ficar espremidas na borda se precisarem crescer com seguranca

### Tese do problema

O problema principal nao e "arquivo grande deixa o servidor lento" por si so.

O problema principal e:

1. acoplamento excessivo
2. baixa previsibilidade de manutencao
3. baixa testabilidade isolada
4. risco de regressao de query e contexto
5. dificuldade de enxergar onde otimizar de verdade

## O - Objetivo

Refatorar `operations/workspace_views.py` por ondas, sem rewrite, para que:

1. as views HTTP fiquem curtas e orquestradoras
2. builders puros saiam da borda e fiquem em modulos mais apropriados
3. mutacoes relacionadas ao WOD operacional saiam da view monolitica e ganhem ownership claro
4. a board continue com o mesmo comportamento funcional
5. a refatoracao crie mais seguranca para proximas evolucoes, e nao so "beleza de codigo"

### Sucesso significa

1. `WorkoutApprovalBoardView` orquestra em vez de pensar demais
2. action views do WOD nao ficam misturadas com toda a leitura do workspace
3. conseguimos testar snapshot, leitura executiva e heuristica sem depender da view inteira
4. a performance nao piora
5. o time passa a ter corredores mais claros para continuar evoluindo

## R - Riscos

### 1. Refatorar cedo demais para uma arquitetura teatral

Se tentarmos criar 12 camadas novas agora:

1. o time perde velocidade
2. a base fica mais dificil para onboarding
3. o ganho real nao paga o custo

Traducao infantil:

1. nao vamos construir aeroporto para atravessar a rua

### 2. Trocar concentracao por espalhamento caotico

Se quebrarmos o arquivo em muitos lugares sem ownership claro:

1. a leitura piora
2. o debug fica mais lento
3. cada bug vira caça ao tesouro

### 3. Mover logica para a camada errada

Exemplos de erro:

1. query pesada em presenter
2. heuristica de negocio em template
3. mutacao sensivel em helper sem auditoria

### 4. Regressao silenciosa de payload

Se a board mudar shape sem perceber:

1. template quebra
2. leitura visual degrada
3. testes podem ficar verdes demais se cobrirem pouco contexto

### 5. Regressao de performance sem perceber

Ao mover codigo:

1. podemos duplicar queryset
2. repetir prefetch
3. perder reuso de snapshot

### 6. Querer otimizar CPU sem medir o gargalo real

Arquivo grande aumenta risco arquitetural, mas nao prova gargalo de runtime.

Se a gente atacar o alvo errado:

1. reorganiza o codigo
2. mas nao melhora a experiencia do usuario

## D - Direcao

### Tese central

Refatorar por extracao de responsabilidade, nao por reescrita.

### Regra-mestra

1. view HTTP orquestra
2. query monta leitura
3. builder puro monta payload e leitura executiva
4. mutacao vive em action view ou use case/facade

### Alvo de organizacao

Sem mexer no produto visivel primeiro, o alvo e aproximar o modulo do seguinte formato mental:

1. `operations/workspace_views.py`
   - classes HTTP de workspace
   - dispatch, permissao, contexto minimo
2. `operations/queries.py`
   - querysets, prefetch, leitura base e joins
3. `operations/presentation.py` ou modulo de apresentacao especifico
   - page payload e shape de tela
4. modulo especifico da board de WOD
   - snapshots puros
   - historico publicado
   - leitura executiva
   - resumo semanal
5. `operations/action_views.py` ou modulo de action views do WOD
   - aprovar, rejeitar, follow-up, memoria operacional, checkpoint semanal

### Direcao recomendada de extração

Para conversar com a estrutura real do repo, a refatoracao deve preferir:

1. criar poucos modulos novos e bem nomeados
2. reaproveitar `queries.py`, `presentation.py`, `actions.py` e `action_views.py`
3. evitar pacote novo se um arquivo claro resolver

### Nomeacao pragmatica recomendada

Se precisarmos abrir corredores novos, a ordem mais saudavel e:

1. `operations/workout_board_builders.py`
   - builders puros de snapshot, diff, resumo e leitura executiva
2. `operations/workout_board_history.py`
   - montagem do historico publicado, follow-up e checkpoint semanal
3. `operations/workout_action_views.py`
   - action views especificas do WOD

Observacao:

1. isso e uma direcao recomendada
2. se durante a implementacao der para resolver com 1 ou 2 arquivos novos, melhor
3. a regra e clareza com o menor numero util de modulos

### Antialvo oficial

Nao fazer agora:

1. microservices
2. CQRS formal
3. event bus novo
4. camada generica de presenter ultra-abstrata
5. "framework interno" para board

## A - Acoes por ondas

## Onda 0 - Congelar comportamento e medir o corredor

### Objetivo

Criar um baseline para refatorar sem andar no escuro.

### Acoes

1. mapear os grupos de responsabilidade atuais dentro de `operations/workspace_views.py`
2. listar quais helpers sao puros e quais tocam banco
3. revisar cobertura atual de:
   - `tests/test_coach_wod_editor.py`
   - testes de workspace e student app que dependam do WOD publicado
4. registrar os contratos minimos da board:
   - shape principal de contexto
   - filtros
   - approval flow
   - follow-up
   - checkpoint semanal

### Check de pronto

1. sabemos exatamente o que pode ser movido sem tocar em regra
2. temos testes suficientes para nao refatorar no escuro

## Onda 1 - Extrair builders puros da board

### Objetivo

Tirar da view tudo que e calculo puro e montagem de dicionario sem responsabilidade HTTP.

### Candidatos diretos

1. `_build_student_preview_payload`
2. `_build_student_preview_diff`
3. `_build_workout_decision_assist`
4. `_build_workout_diff_snapshot`
5. `_build_operational_memory_patterns`
6. `_build_operational_leverage_summary`
7. `_build_operational_leverage_trends`
8. `_build_management_alert_priority`
9. `_build_management_recommendations`
10. `_build_weekly_executive_summary`
11. `_build_weekly_checkpoint_rhythm`
12. `_build_weekly_checkpoint_maturity`
13. `_build_weekly_governance_action`

### Direcao

Mover para modulo especifico da board, mantendo assinatura simples e sem dependencias de request.

### Check de pronto

1. `WorkoutApprovalBoardView` chama builders externos
2. o template continua recebendo o mesmo shape
3. testes continuam verdes

## Onda 2 - Extrair montagem do historico publicado

### Objetivo

Separar a leitura mais densa da board em um corredor proprio.

### Candidato principal

1. `_build_published_workout_history`

### Direcao

Essa extracao deve consolidar:

1. prefetch e acesso a revisoes
2. runtime metrics
3. follow-up actions
4. executive closure
5. live follow-up entries
6. weekly executive summary

O resultado ideal e:

1. um builder/coordinator claro
2. com helpers pequenos em volta
3. deixando a view so pedir "me devolva a historia publicada pronta"

### Check de pronto

1. a leitura publicada sai de `workspace_views.py`
2. o ponto de query fica mais facil de revisar
3. conseguimos medir gargalo sem navegar no arquivo inteiro

## Onda 3 - Tirar action views do arquivo monolitico

### Objetivo

Separar leitura de workspace de mutacao operacional do WOD.

### Candidatos diretos

1. `WorkoutApprovalActionView`
2. `WorkoutFollowUpActionView`
3. `WorkoutOperationalMemoryCreateView`
4. `WorkoutWeeklyCheckpointUpdateView`

### Direcao

Mover essas classes para:

1. `operations/action_views.py`, se o arquivo ainda comportar com clareza
ou
2. `operations/workout_action_views.py`, se a densidade do dominio WOD justificar um modulo proprio

### Regra

Mutacao deve ficar perto de:

1. form
2. auditoria
3. permissao
4. redirecionamento

Mas nao precisa morar ao lado da board gigante so porque nasceu la.

### Check de pronto

1. `workspace_views.py` para de concentrar leitura e mutacao do WOD
2. `urls.py` continua estavel
3. auditoria e mensagens continuam identicas

## Onda 4 - Encurtar as workspace views

### Objetivo

Fazer cada workspace view funcionar como casca fina.

### Direcao

Aplicar o mesmo criterio em:

1. `OwnerWorkspaceView`
2. `ManagerWorkspaceView`
3. `CoachWorkspaceView`
4. `DevWorkspaceView`
5. `ReceptionWorkspaceView`

### Acoes

1. mover attach/builders de payload para helpers de apresentacao quando fizer sentido
2. evitar que a view tenha logica executiva longa
3. manter apenas:
   - permissao
   - chamada de snapshot
   - composicao de contexto final
   - render

### Check de pronto

1. uma pessoa nova entende a view em poucos minutos
2. a logica de decisao nao fica enterrada no meio da borda HTTP

## Onda 5 - Revisao de query e payload depois da extracao

### Objetivo

Conferir se a refatoracao trouxe clareza sem custo escondido.

### Acoes

1. revisar duplicacao de queryset
2. conferir `select_related` e `prefetch_related`
3. procurar montagens repetidas no mesmo request
4. validar tempo de render da board e do workspace

### Regra

Otimizar depois da organizacao, e nao antes.

### Check de pronto

1. nenhum N+1 novo apareceu
2. o payload nao cresceu sem necessidade
3. a extracao nao piorou o runtime

## Onda 6 - Atualizar docs de ownership e leitura

### Objetivo

Fazer a documentacao acompanhar a nova planta.

### Acoes

1. atualizar `docs/reference/reading-guide.md` se os pontos de entrada mudarem
2. atualizar planos ligados ao WOD quando os ownerships mudarem
3. deixar explicito onde mora:
   - leitura da board
   - mutacao da board
   - checkpoint semanal
   - aprendizado operacional

### Check de pronto

1. o mapa da cidade bate com a rua real

## Ordem recomendada de execucao

Se formos atacar isso agora, a melhor ordem e:

1. Onda 0
2. Onda 1
3. Onda 2
4. Onda 3
5. pausa curta para validar
6. Onda 4
7. Onda 5
8. Onda 6

## Guardrails finais

### O que manter

1. evolucao incremental
2. vocabulario oficial do OctoBox
3. borda HTTP curta
4. auditoria intacta
5. testes como rede de protecao

### O que evitar

1. refatorar por vaidade
2. abrir modulo demais sem necessidade
3. abstrair cedo demais
4. confundir organizacao de codigo com otimizacao comprovada

## Resumo executivo

Hoje `operations/workspace_views.py` ja esta grande o suficiente para merecer emagrecimento estrutural.

Mas a jogada certa nao e demolir a casa.

E:

1. tirar a cozinha da recepcao
2. separar o caixa da sala do gerente
3. deixar a porta de entrada so como porta

Traducao tecnica:

1. view HTTP deve orquestrar
2. board do WOD deve ter corredor proprio
3. mutacao deve sair da leitura monolitica
4. a refatoracao deve ser guiada por testes e por ownership, nao por ansiedade arquitetural

## Estado apos as ondas executadas

Ao final das ondas estruturais executadas nesta trilha, o corredor ficou assim:

1. `operations/workspace_views.py`
   - casca HTTP por papel
   - editor do coach
   - board de aprovacao fina
2. `operations/workout_board_builders.py`
   - builders puros de diff, preview e leitura executiva
3. `operations/workout_published_history.py`
   - historico publicado e pos-publicacao
4. `operations/workout_action_views.py`
   - mutacoes reais da board
5. `operations/workout_approval_board_context.py`
   - coordenacao do contexto da board
6. `operations/workout_support.py`
   - suporte compartilhado de snapshot, revisao, auditoria e review snapshot

Medida objetiva da trilha:

1. `operations/workspace_views.py` saiu de 2535 linhas
2. e terminou em 668 linhas

Leitura correta:

1. a view principal deixou de ser o cerebro do corredor de WOD
2. agora ela e a casca de entrada
3. os corredores internos passaram a ter ownership mais claro
