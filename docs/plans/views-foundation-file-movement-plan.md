<!--
ARQUIVO: plano de movimentacao dos arquivos de views inchadas para uma fundacao mais estavel.

TIPO DE DOCUMENTO:
- plano estrutural de refatoracao por ondas

AUTORIDADE:
- alta para a frente atual de reorganizacao das views alvo

DOCUMENTO PAI:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

DOCUMENTOS IRMAOS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)

QUANDO USAR:
- quando a duvida for como mover responsabilidade para fora de views inchadas sem quebrar comportamento
- quando precisarmos decidir a ordem de extracao por capacidade nos corredores de student identity, onboarding e catalog student
- quando um PR tocar movimentacao estrutural desses arquivos e precisarmos de guardrails claros

POR QUE ELE EXISTE:
- evita refatoracao por impulso ou por tamanho bruto de arquivo
- transforma a reorganizacao das views em um corredor governado por capacidade, performance e contrato visual
- deixa explicita a trilha de movimentacao de arquivos e os criterios tecnicos que devem acompanhar cada corte

O QUE ESTE ARQUIVO FAZ:
1. define a tese estrutural para mover responsabilidade para fora das views alvo.
2. organiza a movimentacao dos arquivos por ondas, dominios e capacidades.
3. registra guardrails de arquitetura, performance e front-end para cada extracao.
4. entrega blocos de execucao em formato `/elite prompt` para acelerar a aplicacao da frente.

PONTOS CRITICOS:
- este plano nao autoriza mover arquivos por estetica; cada corte precisa reduzir acoplamento real.
- a view nao pode engordar de novo por atalhos locais depois da extracao.
- qualquer movimentacao que aumente queries, payload ou fragilidade visual deve ser revista antes de seguir.
-->

# Plano de movimentacao das views inchadas

## Tese central

As views alvo desta frente nao devem continuar crescendo como salas onde caixa, recepcao, cozinha e estoque dividem a mesma bancada.

A forma-alvo do OctoBox para essas areas e:

1. `HTTP View` como casca fina
2. `Loader/Policy` como porta de entrada e validacao
3. `Query/Context` como corredor de leitura
4. `Dispatcher` como roteador de intent
5. `Action/Use Case` como corredor de mutacao
6. `Presenter/Page Payload` como contrato da fachada

Em linguagem simples:

1. a view deve receber o pedido
2. outra camada deve pensar
3. outra camada deve salvar
4. a tela deve receber um contrato limpo e previsivel

## Escopo desta frente

Os tres hotspots principais desta rodada sao:

1. [student_identity/views.py](../../student_identity/views.py)
2. [onboarding/views.py](../../onboarding/views.py)
3. [catalog/views/student_views.py](../../catalog/views/student_views.py)

Eles entram nesta ordem:

1. `student_identity`
2. `onboarding`
3. `catalog student`

Motivo:

1. `student_identity` e a porta mais sensivel do aluno
2. `onboarding` e o corredor operacional de intake e convite
3. `catalog student` e o grande galpao que precisa ser quebrado por capacidades, nao por volume bruto

## Regra oficial da movimentacao

Toda movimentacao precisa obedecer a esta ordem mental:

1. separar responsabilidade antes de separar pastas
2. separar por capacidade antes de separar por tamanho
3. separar leitura de escrita antes de separar nomes
4. estabilizar contrato visual antes de espalhar includes, CSS ou JS
5. medir risco de performance antes de chamar uma extracao de melhoria

Se um corte nao reduzir pelo menos um destes pontos, ele ainda nao merece existir:

1. acoplamento
2. mistura de leitura e mutacao
3. duplicacao de contexto
4. side effect no request principal
5. inflacao de payload
6. risco visual por contexto improvisado

## Guardrails tecnicos obrigatorios

### Arquitetura

1. nao mover por tema tecnico aleatorio; mover por capacidade real
2. nao criar mini framework interno
3. nao fazer reescrita geral de uma vez
4. preservar rotas publicas e comportamento antes de reformatar a casca
5. promover `facade`, `action`, `query` e `presenter` apenas quando houver funcao clara

### Performance

1. cada extracao de `query/context` deve reduzir ou manter o numero de queries
2. usar `select_related` e `prefetch_related` quando a leitura for composta
3. evitar recomputar o mesmo snapshot varias vezes no mesmo request
4. nao inflar JSON, fragments ou page payload sem justificativa semantica
5. side effects externos devem ser candidatos a async quando nao forem criticos para a resposta

### Front-end e CSS

1. template principal deve ficar mais fino, nunca mais magico
2. a tela deve receber payload estavel, nao contexto espalhado
3. partials devem nascer por papel claro
4. CSS nao pode depender de logica de dominio
5. JS deve conversar por `data-*`, payload e endpoints estaveis
6. zero inline CSS novo
7. evitar vazamento de nomes temporarios de contexto para a fachada

## Forma-alvo de diretorios por corredor

Esta e a forma-alvo recomendada para a movimentacao.

### 1. `student_identity`

Estado alvo:

```text
student_identity/
|-- views.py
|-- oauth_loader.py
|-- oauth_policy.py
|-- oauth_actions.py
|-- oauth_journeys.py
|-- oauth_presenter.py
```

Regra:

1. `views.py` continua como casca HTTP e ponto de entrada publico
2. o callback OAuth perde peso primeiro
3. journeys especiais ganham corredor proprio antes de novas regras entrarem

### 2. `onboarding`

Estado alvo:

```text
onboarding/
|-- views.py
|-- intake_loader.py
|-- intake_context.py
|-- intake_dispatcher.py
|-- intake_actions.py
|-- intake_invite_actions.py
|-- intake_presenter.py
```

Regra:

1. a central de intake nao deve continuar sendo um arquivo que pensa, salva e monta a tela ao mesmo tempo
2. o fluxo de invite e handoff para WhatsApp precisa ficar separado do corredor de queue e create

### 3. `catalog student`

Estado alvo:

```text
catalog/views/
|-- student_views.py

catalog/
|-- student_directory_context.py
|-- student_directory_actions.py
|-- student_directory_presenter.py
|-- student_form_context.py
|-- student_form_actions.py
|-- student_payment_actions.py
|-- student_enrollment_actions.py
|-- student_lock_actions.py
|-- student_quick_sale_actions.py
|-- student_import_actions.py
|-- student_source_capture_actions.py
```

Regra:

1. `student_views.py` nao deve ser quebrado por classe arbitraria
2. ele deve ser drenado por corredor funcional
3. cada capacidade nova precisa ter ownership claro antes de ganhar arquivo proprio

## Ondas de movimentacao

## Onda 1: `student_identity`

### Objetivo

Separar o callback OAuth da view principal sem quebrar o fluxo de aluno.

### Movimento de arquivos

1. criar `student_identity/oauth_loader.py`
2. criar `student_identity/oauth_policy.py`
3. criar `student_identity/oauth_actions.py`
4. criar `student_identity/oauth_journeys.py`
5. manter [student_identity/views.py](../../student_identity/views.py) como casca de entrada

### Atitudes tecnicas obrigatorias

1. extrair validacao de state, rate limit e precondicoes para `loader/policy`
2. extrair autenticacao e attach de sessao para `actions`
3. extrair jornadas especiais para `oauth_journeys.py`
4. manter mensagens e redirects identicos antes de qualquer refinamento
5. revisar queries duplicadas de invite, membership e journey

### `/elite prompt`

```text
/elite prompt
Objetivo: executar a Onda 1 de student_identity sem mudar comportamento do login do aluno.
Contexto: a view student_identity/views.py ainda concentra callback OAuth, state validation, rate limit, journeys especiais, sessao e alertas.
Direcao:
1. manter views.py como casca HTTP fina
2. extrair loader/policy para validacoes e precondicoes
3. extrair actions para autenticacao, sessao e efeitos persistentes
4. extrair journeys especiais para modulo proprio
5. preservar redirects, messages, auditoria e contratos atuais
Guardrails:
1. sem reescrita geral
2. sem trocar rotas
3. sem inflar queries
4. sem quebrar o fluxo invite -> OAuth -> home ou aguardando aprovacao
Entrega esperada:
1. views.py menor e mais legivel
2. novos modulos com cabecalho padrao
3. smoke ou testes focados do fluxo OAuth
```

## Onda 2: `onboarding`

### Objetivo

Transformar a `IntakeCenterView` em casca fina com separacao real entre leitura, dispatcher e mutacao.

### Movimento de arquivos

1. criar `onboarding/intake_loader.py`
2. criar `onboarding/intake_context.py`
3. criar `onboarding/intake_dispatcher.py`
4. criar `onboarding/intake_actions.py`
5. criar `onboarding/intake_invite_actions.py`
6. criar `onboarding/intake_presenter.py`

### Atitudes tecnicas obrigatorias

1. extrair snapshot e payload da tela antes de mover mutacoes
2. extrair dispatcher por intent do `post()`
3. separar quick-create, queue action e send invite
4. isolar a logica de resolver ou criar aluno a partir do intake
5. garantir que o handoff de convite e WhatsApp nao polua o request com logica difusa

### `/elite prompt`

```text
/elite prompt
Objetivo: executar a Onda 2 de onboarding para esvaziar onboarding/views.py com seguranca.
Contexto: IntakeCenterView ainda mistura contexto da tela, busca, quick create, queue action, send-whatsapp-invite e conversao intake -> student.
Direcao:
1. extrair intake_context e intake_presenter primeiro
2. extrair dispatcher por intent sem mudar endpoints
3. extrair actions por capacidade: quick-create, queue, invite, conversion
4. manter a view como porta HTTP e orquestradora minima
5. preservar page payload e comportamento visual
Guardrails:
1. nao criar mini framework
2. nao duplicar snapshots
3. nao deixar template dependente de contexto improvisado novo
4. manter a fachada visual limpa e previsivel
Entrega esperada:
1. view mais fina
2. ownership claro por capacidade
3. fluxo de invite e intake mais testavel
```

## Onda 3: `catalog student`

### Objetivo

Quebrar [catalog/views/student_views.py](../../catalog/views/student_views.py) por capacidades de negocio e nao por obsessao com tamanho.

### Movimento de arquivos por prioridade

#### Faixa A: risco operacional alto

1. `student_payment_*`
2. `student_enrollment_*`
3. `student_lock_*`

#### Faixa B: leitura e contexto de tela

1. `student_directory_*`
2. `student_form_*`

#### Faixa C: extensoes e corredores laterais

1. `student_quick_sale_*`
2. `student_import_*`
3. `student_source_capture_*`

### Atitudes tecnicas obrigatorias

1. iniciar por pagamento e matricula, porque erro aqui impacta caixa e operacao
2. atacar lock cedo para evitar logica de concorrencia espalhada
3. extrair contexto do diretorio com foco em performance e snapshot
4. so depois mover create/update leves
5. quick sale, import e source capture entram depois que o tronco principal estiver estabilizado

### `/elite prompt`

```text
/elite prompt
Objetivo: iniciar a drenagem de catalog/views/student_views.py por capacidades reais.
Contexto: student_views.py e hoje o maior hotspot de views do repositorio, misturando diretorio, create/update, payment, enrollment, lock, quick sale, import e source capture.
Direcao:
1. nao quebrar o arquivo por classe arbitraria
2. quebrar por corredores de negocio
3. priorizar payment/enrollment/lock
4. depois extrair directory/form com query/context/presenter
5. deixar quick sale, import e source capture para a terceira passada
Guardrails:
1. preservar rotas e contratos existentes
2. sem mover tudo de uma vez
3. cada corte deve ter ROI tecnico claro
4. manter ou melhorar performance de leitura
Entrega esperada:
1. student_views.py menor por ondas
2. ownership claro por capacidade
3. menos medo de tocar nos corredores centrais do aluno
```

## Matriz de decisoes para a movimentacao

Antes de criar um novo arquivo, responder:

1. esta extracao reduz acoplamento real ou so move bagunca?
2. existe uma capacidade clara por tras do corte?
3. esta camada nova protege a view ou so a deixa indireta?
4. a leitura ficara mais performatica ou pelo menos igual?
5. o contrato visual ficara mais estavel ou mais opaco?

Se duas ou mais respostas forem negativas, o corte ainda nao esta pronto.

## Criterio de pronto por etapa

Cada onda so fecha quando:

1. a view principal ficou visivelmente mais fina
2. o ownership novo ficou explicavel por leitura direta
3. o numero de queries nao piorou
4. payload e contexto nao ficaram mais inflados
5. templates nao receberam logica residual nova
6. testes focados ou smoke do fluxo principal ficaram verdes

## Antipadroes proibidos nesta frente

1. mover arquivos por moda
2. criar presenter sem presenter de verdade
3. criar action que apenas faz ponte inutil
4. espalhar contratos visuais em dicionarios ad hoc
5. trocar nomes, imports e pastas sem reduzir a complexidade do corredor
6. aumentar latencia para ganhar “beleza arquitetural”

## Resumo infantil

Pense nisso como arrumar uma escola grande:

1. primeiro arrumamos a porta principal do aluno
2. depois arrumamos a secretaria de intake
3. depois organizamos o galpao enorme dos alunos em salas separadas

Nao vamos derrubar a escola inteira.

Vamos tirar cada turma do lugar errado e colocar cada uma na sala certa, com placa na porta e caminho curto para encontrar.
