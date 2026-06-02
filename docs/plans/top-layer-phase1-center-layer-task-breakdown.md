<!--
ARQUIVO: decomposicao tecnica atomica da Fase 1 do plano de arquitetura superior.

POR QUE ELE EXISTE:
- transforma a Fase 1 em tarefas pequenas, ordenadas e prontas para execucao no codigo.
- reduz risco de refatoracao ampla sem visibilidade.
- permite atacar o crescimento do Center Layer por fatias seguras.

O QUE ESTE ARQUIVO FAZ:
1. quebra a Fase 1 em tarefas tecnicas atômicas.
2. amarra cada tarefa a arquivos reais do repositorio.
3. define criterio de pronto, risco dominante e contencao por tarefa.

TIPO DE DOCUMENTO:
- backlog tecnico executavel

AUTORIDADE:
- alta para a execucao da Fase 1 do Center Layer

DOCUMENTO PAI:
- [top-layer-architecture-execution-plan.md](top-layer-architecture-execution-plan.md)

QUANDO USAR:
- quando a duvida for qual mudanca fazer agora para expandir o Center Layer
- quando a equipe precisar executar a Fase 1 sem abrir refatoracao difusa
- quando agentes precisarem de cortes pequenos e testaveis

PONTOS CRITICOS:
- este backlog nao autoriza mover regra de negocio para facade.
- tarefas devem preservar compatibilidade e preferir adaptador fino a corte brusco.
- cada tarefa deve poder parar no meio sem deixar o sistema incoerente.
-->

# Fase 1 detalhada: expansao do Center Layer

## Regra de execucao desta fase

1. facade antes de extracao
2. adaptador fino antes de corte de compatibilidade
3. mover a entrada, nao a regra
4. terminar uma travessia antes de abrir duas novas

## Objetivo da fase

1. fazer a borda do sistema depender menos de wiring interno
2. reforcar facades publicas como corredores oficiais por capacidade
3. registrar explicitamente o que ainda e bypass inevitavel

## Sequencia recomendada

1. confirmar o inventario das entradas atuais
2. apertar `communications` como primeiro corte de compatibilidade
3. reancorar a API v1 nos corredores certos
4. revisar `operations` para garantir que views usem apenas facades
5. revisar `catalog` para impedir recaida direta em infrastructure
6. formalizar o inventario dos bypasses remanescentes

## Tarefa 1: inventario local das entradas por capacidade

### Objetivo

1. confirmar por arquivo quais entradas hoje usam facade e quais ainda atravessam para dentro demais

### Arquivos-alvo

1. [../../api/v1/views.py](../../api/v1/views.py)
2. [../../communications/services.py](../../communications/services.py)
3. [../../operations/action_views.py](../../operations/action_views.py)
4. [../../operations/workspace_views.py](../../operations/workspace_views.py)
5. modulos em `catalog/views/`

### Mudanca esperada

1. produzir tabela curta de consumo por capacidade:
2. entrada HTTP
3. facade usada
4. dependencia interna ainda vazando

### Critério de pronto

1. cada entrada relevante ja esta classificada como:
2. usa facade correta
3. usa adaptador fino
4. ainda bypassa demais

### Risco dominante

1. pular esta tarefa e abrir refatoracao sem mapa

### Contencao

1. nenhuma mudanca funcional aqui

## Tarefa 2: apertar communications.services como adaptador fino canonico

### Objetivo

1. garantir que [../../communications/services.py](../../communications/services.py) nao volte a concentrar logica, ORM e fluxo central

### Arquivos-alvo

1. [../../communications/services.py](../../communications/services.py)
2. [../../communications/facade/messaging.py](../../communications/facade/messaging.py)
3. [../../communications/application/commands.py](../../communications/application/commands.py)
4. [../../communications/application/use_cases.py](../../communications/application/use_cases.py)

### Mudanca esperada

1. revisar cada funcao publica de `communications/services.py`
2. manter apenas traducao de chamada, compatibilidade e reexport util
3. mover qualquer regra residual para facade/application se ainda houver vazamento

### Critério de pronto

1. `communications/services.py` fica com papel claramente de compatibilidade fina
2. facade segue sendo a porta oficial do dominio

### Risco dominante

1. service legado continuar atraindo novas dependencias

### Contencao

1. preservar assinatura publica atual sempre que possivel

## Tarefa 3: reancorar webhook e flows de integracao na facade certa

### Objetivo

1. garantir que a borda de integracao fale com `communications.facade`, nao com detalhes internos

### Arquivos-alvo

1. [../../integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
2. [../../integrations/whatsapp/contracts.py](../../integrations/whatsapp/contracts.py)
3. [../../communications/facade/messaging.py](../../communications/facade/messaging.py)

### Mudanca esperada

1. validar que os entrypoints publicos de integracao so traduzem contrato e encaminham
2. eliminar qualquer vazamento acidental de regra para a borda do WhatsApp

### Critério de pronto

1. integracao vira porta fina de contrato
2. dominio de communications continua dono do comportamento

### Risco dominante

1. provider externo contaminar o centro conceitual

### Contencao

1. nao alterar contrato externo sem necessidade real

## Tarefa 4: separar melhor a API v1 por capacidade

### Objetivo

1. reduzir a mistura de responsabilidades em [../../api/v1/views.py](../../api/v1/views.py)

### Arquivos-alvo

1. [../../api/v1/views.py](../../api/v1/views.py)
2. [../../api/v1/urls.py](../../api/v1/urls.py)
3. [../../api/v1/finance_views.py](../../api/v1/finance_views.py)
4. [../../api/v1/jobs_views.py](../../api/v1/jobs_views.py)
5. novo modulo sugerido: `api/v1/integrations_views.py`

### Mudanca esperada

1. manter manifesto e health em `views.py`
2. mover endpoint de webhook para modulo de integracoes
3. mover endpoint sensivel de bootstrap para modulo de operacoes internas ou debug controlado
4. revisar autocomplete e pagamento para verificar consumo de corredor oficial

### Critério de pronto

1. a API v1 fica mais legivel por capacidade
2. `views.py` deixa de ser corredor misto

### Risco dominante

1. quebrar rotas publicas ao mover views entre modulos

### Contencao

1. preservar paths e names em [../../api/v1/urls.py](../../api/v1/urls.py)

## Tarefa 5: revisar operations.action_views para garantir uso exclusivo de facade

### Objetivo

1. confirmar que actions operacionais entram por `operations.facade.workspace`

### Arquivos-alvo

1. [../../operations/action_views.py](../../operations/action_views.py)
2. [../../operations/facade/workspace.py](../../operations/facade/workspace.py)
3. [../../operations/application/workspace_commands.py](../../operations/application/workspace_commands.py)

### Mudanca esperada

1. revisar `AttendanceActionView`
2. revisar `PaymentEnrollmentLinkView`
3. revisar `TechnicalBehaviorNoteCreateView`
4. eliminar qualquer chamada que ainda atravesse para baixo sem passar pela facade

### Critério de pronto

1. action views viram casca HTTP fina
2. `workspace.py` vira corredor dominante das mutacoes operacionais expostas

### Risco dominante

1. view continuar conhecendo regra demais

### Contencao

1. mover apenas a entrada; nao reescrever use case

## Tarefa 6: revisar operations.workspace_views para consumo limpo de snapshot

### Objetivo

1. garantir que workspaces consumam snapshots por corredor oficial e nao remontem contexto manualmente

### Arquivos-alvo

1. [../../operations/workspace_views.py](../../operations/workspace_views.py)
2. [../../operations/facade/workspace.py](../../operations/facade/workspace.py)
3. [../../operations/queries.py](../../operations/queries.py)
4. [../../operations/presentation.py](../../operations/presentation.py)

### Mudanca esperada

1. revisar montagem de contexto por papel
2. identificar recomposicao manual que deveria subir pronta
3. puxar a view para consumir o menor contrato estavel possivel

### Critério de pronto

1. workspace view fala mais com snapshot do que com detalhes de query
2. leitura operacional sobe pronta e previsivel

### Risco dominante

1. piorar latencia ou duplicar montagem de dados

### Contencao

1. validar comportamento visual antes de qualquer consolidacao maior

## Tarefa 7: revisar catalog/views para impedir recaida em infrastructure

### Objetivo

1. garantir que a borda do catalog continue preferindo services e facades publicas

### Arquivos-alvo

1. [top-layer-phase1-bypass-inventory.md](top-layer-phase1-bypass-inventory.md)

1. `catalog/views/student_views.py`
2. `catalog/views/finance_views.py`
3. `catalog/views/class_grid_views.py`
4. [../../students/facade/student_lifecycle.py](../../students/facade/student_lifecycle.py)
5. [../../communications/facade/messaging.py](../../communications/facade/messaging.py)
6. [../../operations/facade/class_grid.py](../../operations/facade/class_grid.py)

### Mudanca esperada

1. localizar imports suspeitos de infrastructure direta
2. trocar por corredor oficial ja promovido quando existir
3. registrar onde ainda nao existe facade boa o bastante

### Critério de pronto

1. catalog reforca a lingua arquitetural nova
2. imports de infrastructure na borda ficam reduzidos ou explicitamente justificados

### Risco dominante

1. troca de import que muda comportamento sem perceber

### Contencao

1. mexer por arquivo e validar fluxo correspondente

## Tarefa 8: criar inventario de bypasses remanescentes

### Objetivo

1. formalizar o que ainda esta fora do caminho ideal para virar backlog controlado

### Arquivos-alvo

1. [top-layer-architecture-execution-plan.md](top-layer-architecture-execution-plan.md)
2. documento novo sugerido ou secao anexa no proprio plano

### Mudanca esperada

1. listar bypass
2. explicar por que ele ainda existe
3. dizer qual facade ou corredor deve substitui-lo
4. marcar risco e prioridade

### Critério de pronto

1. nenhum bypass importante fica implícito
2. a Fase 2 começa com mapa claro

### Risco dominante

1. remendo invisivel virar padrao por omissao

### Contencao

1. registrar apenas o que foi realmente observado no runtime

## Tarefa 9: adicionar guardrail de revisao para codigo novo

### Objetivo

1. impedir regressao enquanto a fase ainda esta em andamento

### Arquivos-alvo

1. [../architecture/promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md)
2. [top-layer-architecture-execution-plan.md](top-layer-architecture-execution-plan.md)

### Mudanca esperada

1. reforcar regra de revisao:
2. novo fluxo externo prefere facade publica
3. novo import de infrastructure na borda precisa justificativa
4. novo bypass precisa classificacao explicita

### Critério de pronto

1. a fase nao melhora um lado e regride no outro

### Risco dominante

1. a equipe abrir novo atalho enquanto refatora o antigo

### Contencao

1. usar checklist curto em review, nao burocracia grande

### Fechamento desta tarefa

1. a tarefa so fecha quando o guardrail estiver escrito em docs ativos de arquitetura e plano
2. o checklist de PR precisa caber em leitura de review sem virar processo pesado
3. a regra minima obrigatoria passa a ser:
4. fluxo externo novo prefere facade publica
5. import novo de `*.infrastructure` na borda exige justificativa explicita
6. bypass novo exige inventario ativo

## Ordem de execucao pronta para codigo

1. Tarefa 2
2. Tarefa 3
3. Tarefa 4
4. Tarefa 5
5. Tarefa 6
6. Tarefa 7
7. Tarefa 8
8. Tarefa 9

Observacao:

1. a Tarefa 1 pode rodar como baseline rapido antes ou em paralelo de leitura, mas nao deve bloquear as mudancas pequenas se o mapa ja estiver suficientemente claro

## Definicao de pronto da Fase 1

A Fase 1 so fecha quando:

1. `communications` estiver claramente reancorado em facade
2. a API v1 estiver menos misturada e mais legivel por capacidade
3. `operations` usar facade como corredor dominante nas mutacoes expostas
4. o `catalog` nao estiver recaindo para infrastructure sem necessidade
5. existir inventario explicito dos bypasses restantes

## Explicacao simples

Primeiro a gente para de deixar as pessoas entrarem por portas secretas.
Depois a gente coloca placas nas portas certas.
Depois anota quais buracos na cerca ainda existem.
So depois disso faz sentido organizar os mensageiros, alarmes e luzes do topo.
