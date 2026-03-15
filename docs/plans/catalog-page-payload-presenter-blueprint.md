<!--
ARQUIVO: blueprint oficial do padrao-base de page payload e presenter para as telas do catalogo.

TIPO DE DOCUMENTO:
- blueprint estrutural de front-end e delivery HTTP

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)

DOCUMENTOS IRMAOS:
- [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md)
- [../experience/front-display-wall.md](../experience/front-display-wall.md)

QUANDO USAR:
- quando a duvida for como padronizar a montagem das telas do catalogo sem deixar a view virar um buraco negro de contexto

POR QUE ELE EXISTE:
- transforma a ideia de page payload e presenter em padrao concreto para alunos, ficha do aluno, financeiro, plano e grade de aulas.
- evita que cada tela do catalogo invente sua propria lingua estrutural.
- prepara o catalogo para conversar com o backend desacoplado por um idioma unico de entrega visual.

O QUE ESTE ARQUIVO FAZ:
1. define o contrato-base do page payload no catalogo.
2. define o papel do presenter no runtime atual.
3. mapeia o shape recomendado para cada tela principal do catalogo.
4. organiza a ordem pratica de adocao.

PONTOS CRITICOS:
- este blueprint nao pede reescrita total imediata.
- ele existe para guiar a convergencia do catalogo para uma linguagem estrutural unica.
- a view HTTP continua existindo, mas deixa de ser dona informal da tela inteira.
-->

# Blueprint de page payload e presenter do catalogo

## Tese central

O catalogo do OctoBox precisa falar uma lingua unica entre backend e front.

Hoje essa conversa ja existe, mas ainda aparece distribuida em muitos `context[...]`, listas avulsas, flags dispersas e pequenos contratos informais de template.

O alvo deste blueprint e transformar isso em uma forma mais limpa:

1. a view HTTP coleta a entrada e governa o fluxo de entrega
2. snapshots e queries continuam fornecendo leitura estruturada
3. um presenter ou page builder monta o payload da tela
4. o template renderiza esse payload por modulos
5. o JS da pagina consome apenas os dados declarados pelo payload

Em linguagem curta:

1. a view deixa de montar a pagina inteira na mao
2. o catalogo ganha um dialeto estrutural unificado

## Escopo deste blueprint

Este documento cobre as cinco superficies principais do catalogo atual:

1. diretorio de alunos
2. ficha leve de aluno
3. centro financeiro
4. formulario de edicao de plano
5. grade de aulas

Correspondencia atual:

1. `StudentDirectoryView`
2. `StudentQuickCreateView` e `StudentQuickUpdateView`
3. `FinanceCenterView`
4. `MembershipPlanQuickUpdateView`
5. `ClassGridView`

## Objetivo do presenter no runtime atual

Neste momento do projeto, `presenter` nao significa camada decorativa nem framework de view model excessivo.

Aqui, presenter significa uma peca pequena que:

1. recebe contexto bruto de dominio e delivery
2. organiza esse material no contrato oficial da tela
3. devolve um payload pronto para template, JS e assets da pagina

O presenter nao deve:

1. abrir `QuerySet` por conta propria sem critério
2. decidir regra de negocio
3. substituir facade, use case ou snapshot
4. renderizar HTML

O presenter deve:

1. traduzir para a linguagem da tela
2. consolidar blocos de UI
3. reduzir a quantidade de chaves soltas no contexto
4. tornar o contrato da tela mais explicavel e testavel

## Papel de cada camada

### Query ou snapshot

Responsabilidade:

1. leitura estruturada do dominio
2. consolidacao de dados operacionais
3. retorno de estruturas aptas a consumo humano

### Use case ou facade

Responsabilidade:

1. mutacao
2. orquestracao de fluxo
3. validacao de regra de negocio

### View HTTP

Responsabilidade:

1. autenticar e autorizar
2. ler request
3. chamar query, snapshot, facade ou use case
4. chamar presenter
5. devolver resposta

### Presenter

Responsabilidade:

1. montar `page_payload`
2. declarar `page_assets`
3. consolidar `shell_actions`
4. reduzir contexto informal

### Template

Responsabilidade:

1. compor a fachada visual
2. distribuir modulos
3. declarar `data-*` e `json_script`

## Contrato-base do page payload do catalogo

### Principio espelhado do contrato semantico enxuto

No catalogo, o page payload deve nascer da mesma regra-mestra do front:

1. o backend entrega apenas o minimo semantico necessario para a tela existir com verdade
2. esse minimo inclui dados reais, permissoes, estado, contexto e acoes possiveis
3. o frontend assume organizacao visual, repeticao de leitura e composicao da interface
4. o presenter organiza a lingua da tela, mas nao deve inflar o payload com cosmetica redundante

Traducao pratica para este blueprint:

1. o payload deve carregar o que altera leitura real, navegacao, estado e acao
2. o payload nao deve carregar varias versoes cosmeticas do mesmo valor so para sustentar layout
3. o mesmo dado pode aparecer em varios pontos da interface sem exigir duplicacao semantica no contrato
4. presenter bom reduz contexto informal, mas nao vira fabrica de copy redundante nem mini framework visual

Todo payload de tela do catalogo deve convergir para este shape conceitual:

```text
page_payload
|-- context
|   |-- page_key
|   |-- title
|   |-- subtitle
|   |-- mode
|   |-- role_slug
|   `-- today
|-- shell
|   |-- page_title
|   |-- page_subtitle
|   `-- shell_action_buttons
|-- data
|   |-- hero
|   |-- metrics
|   |-- primary_board
|   |-- secondary_boards
|   |-- forms
|   `-- support
|-- actions
|   |-- primary
|   |-- secondary
|   |-- exports
|   |-- anchors
|   `-- endpoints
|-- behavior
|   |-- flags
|   |-- datasets
|   `-- json_blocks
|-- capabilities
|   |-- can_manage
|   |-- can_export
|   |-- can_open_admin
|   `-- role_specific
|-- assets
|   |-- css
|   `-- js
```

Esse shape nao precisa ser imposto de forma brutal no primeiro corte.

Mas cada presenter novo deve convergir para ele.

## Regras do contrato-base

### `context`

Serve para identidade e explicacao da tela.

Deve responder:

1. que tela e essa
2. em que modo ela esta
3. para qual papel ela esta sendo entregue

### `shell`

Serve para costura com a estrutura global.

Deve concentrar o que conversa com o shell autenticado sem deixar isso espalhado em varias chaves soltas.

### `data`

Serve para leitura visual e blocos principais da pagina.

Tudo o que a pessoa precisa ver para operar a tela deve caber aqui.

### `actions`

Serve para destinos oficiais.

Nao pode depender de links escondidos no template ou URLs soltas no JS quando a acao for parte estrutural da tela.

### `behavior`

Serve para tudo o que o JavaScript precisa saber sem redescobrir por acidente o estado da tela no DOM.

### `capabilities`

Serve para declarar o que a interface pode ou nao pode expor para o papel atual.

### `assets`

Serve para tornar explicito o que a tela pede de CSS e JS proprio.

## Padrão de artefatos recomendado no catalogo

Estrutura-alvo sugerida:

```text
catalog/
|-- presentation/
|   |-- __init__.py
|   |-- shared.py
|   |-- student_directory_page.py
|   |-- student_form_page.py
|   |-- finance_center_page.py
|   |-- membership_plan_page.py
|   `-- class_grid_page.py
|-- views/
|-- queries/
|-- services/
`-- forms.py
```

### `shared.py`

Responsabilidade:

1. helpers comuns de payload
2. montagem padrao de `context`, `shell`, `capabilities` e `assets`
3. pequenas funcoes de normalizacao de estrutura

### Arquivos `*_page.py`

Responsabilidade:

1. um presenter por superficie de tela principal
2. uma entrada explicita por pagina
3. contract-first, sem virar deposito genérico de helpers

## API conceitual recomendada para os presenters

Padrao simples recomendado:

```python
def build_student_directory_page(*, request, base_context, snapshot):
    ...

def build_student_form_page(*, request, base_context, form, student, selected_intake, financial_overview, page_mode):
    ...

def build_finance_center_page(*, request, base_context, snapshot, form):
    ...

def build_membership_plan_page(*, request, base_context, form, plan):
    ...

def build_class_grid_page(*, request, base_context, snapshot, schedule_form, session_edit_form, selected_session, return_query):
    ...
```

Regra:

1. assinatura clara
2. dependencias explicitas
3. sem buscar tudo escondido dentro do presenter

## Padrão-base para cada tela do catalogo

## 1. Diretorio de alunos

### Nome recomendado do presenter

`build_student_directory_page`

### Entradas oficiais

1. `request`
2. `base_context`
3. `snapshot`

### Saida esperada

```text
page_payload
|-- context
|-- shell
|-- data
|   |-- metrics
|   |-- filters
|   |-- students
|   |-- funnel
|   |-- priority_students
|   `-- intake_queue
|-- actions
|   |-- primary
|   |-- secondary
|   `-- exports
|-- capabilities
|-- assets
```

### Observacoes

1. `students[:24]` ja deve sair como decisao fechada no payload e nao como detalhe espalhado de view
2. `student_operational_focus` deve virar bloco de `data` ou `actions`, nao lista avulsa
3. `student_export_links` deve ficar sob `actions.exports`

## 2. Ficha leve do aluno

### Nome recomendado do presenter

`build_student_form_page`

### Entradas oficiais

1. `request`
2. `base_context`
3. `form`
4. `student`
5. `selected_intake`
6. `financial_overview`
7. `page_mode`
8. formularios auxiliares permitidos pelo papel

### Saida esperada

```text
page_payload
|-- context
|   |-- mode
|   `-- role_slug
|-- shell
|-- data
|   |-- hero
|   |-- focus
|   |-- selected_intake
|   |-- form_sections
|   |-- financial_overview
|   |-- payment_management
|   |-- enrollment_management
|   `-- recovery_guide
|-- actions
|   |-- anchors
|   |-- navigation
|   `-- admin
|-- behavior
|   |-- json_blocks
|   |-- flags
|   `-- datasets
|-- capabilities
|-- assets
```

### Observacoes

1. `plan_price_map` deve ficar em `behavior.json_blocks.plan_price_map`
2. `student_form_operational_focus` deve sair do contexto solto e entrar como bloco oficial do payload
3. o template deve renderizar secoes guiadas por `form_sections`, mesmo que a migração aconteça em ondas

## 3. Centro financeiro

### Nome recomendado do presenter

`build_finance_center_page`

### Entradas oficiais

1. `request`
2. `base_context`
3. `snapshot`
4. `plan_form`
5. opcionalmente `operational_queue` se ficar fora do snapshot

### Saida esperada

```text
page_payload
|-- context
|-- shell
|-- data
|   |-- pulse
|   |-- metrics
|   |-- filter_summary
|   |-- filter_form
|   |-- operational_queue
|   |-- financial_alerts
|   |-- monthly_comparison
|   |-- plan_portfolio
|   |-- plan_mix
|   |-- recent_movements
|   `-- plan_creation
|-- actions
|   |-- exports
|   |-- navigation
|   `-- communication_action
|-- behavior
|   |-- flags
|   `-- datasets
|-- capabilities
|-- assets
```

### Observacoes

1. `finance_filter_summary`, `finance_operational_focus`, `finance_command_cards` e afins devem ser absorvidos como blocos nomeados de `data`
2. o payload deve deixar claro o que e leitura, o que e acao, o que e apoio
3. o chart da tela deve depender de `behavior.datasets` ou atributos declarados, nunca de descoberta livre demais do DOM

## 4. Formulario de plano

### Nome recomendado do presenter

`build_membership_plan_page`

### Entradas oficiais

1. `request`
2. `base_context`
3. `form`
4. `plan`

### Saida esperada

```text
page_payload
|-- context
|-- shell
|-- data
|   |-- hero
|   |-- form
|   |-- focus
|   |-- guardrails
|   `-- summary_cards
|-- actions
|   |-- anchors
|   `-- navigation
|-- capabilities
|-- assets
```

### Observacoes

1. essa tela e menor, mas deve obedecer a mesma lingua do restante do catalogo
2. ela e um bom laboratorio inicial para validar o presenter sem o peso da grade

## 5. Grade de aulas

### Nome recomendado do presenter

`build_class_grid_page`

### Entradas oficiais

1. `request`
2. `base_context`
3. `snapshot`
4. `schedule_form`
5. `session_edit_form`
6. `selected_session`
7. `return_query`

### Saida esperada

```text
page_payload
|-- context
|-- shell
|-- data
|   |-- hero
|   |-- metrics
|   |-- focus
|   |-- today_schedule
|   |-- weekly_calendar
|   |-- monthly_calendar
|   |-- workspace_panels
|   |-- planner_form
|   `-- session_edit
|-- actions
|   |-- navigation
|   |-- planner_submit
|   |-- session_actions
|   `-- admin
|-- behavior
|   |-- flags
|   |-- datasets
|   `-- json_blocks
|-- capabilities
|-- assets
```

### Observacoes

1. essa e a tela mais importante para provar o modelo
2. `workspace_panels` deve virar conceito explicito do payload
3. a configuracao da area arrastavel, modal mensal e forms da grade precisa sair de dependencias espalhadas do template

## Helpers compartilhados recomendados

Para impedir duplicacao, o catalogo deve ter alguns pequenos helpers em `catalog/presentation/shared.py`.

Exemplos:

1. `build_page_context`
2. `build_page_capabilities`
3. `build_page_assets`
4. `build_shell_contract`
5. `build_anchor_action`
6. `build_link_action`

Padrao conceitual:

```python
def build_page_context(*, page_key, title, subtitle, mode, role_slug, today):
    ...

def build_page_assets(*, css=None, js=None):
    ...

def build_page_capabilities(**flags):
    ...
```

Esses helpers nao devem virar mini framework.

Eles existem para cortar repeticao estrutural obvia.

## Como as views devem ficar depois da convergencia

Forma-alvo simplificada:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    base_context = self.get_base_context()
    snapshot = build_student_directory_snapshot(self.request.GET)
    page_payload = build_student_directory_page(
        request=self.request,
        base_context=base_context,
        snapshot=snapshot,
    )
    context.update(base_context)
    context['page_payload'] = page_payload
    context.update(page_payload['shell'])
    return context
```

Leitura importante:

1. no primeiro corte, ainda pode haver compatibilidade com chaves antigas
2. o alvo final e o template depender cada vez mais de `page_payload`

## Estrategia de migracao sem quebrar tudo

Nao migrar o catalogo inteiro de uma vez.

Usar esta ordem:

## Fase 1: introduzir presenters sem exigir template novo completo

1. criar `catalog/presentation/`
2. criar `shared.py`
3. criar o presenter da grade e o da ficha do aluno
4. deixar as views preenchendo `page_payload` e ainda expondo algumas chaves antigas durante transicao

## Fase 2: passar templates para consumo progressivo do payload

1. template shell usa `page_payload.context`
2. modulos passam a usar `page_payload.data`
3. JS passa a usar `page_payload.behavior`

## Fase 3: cortar contexto legado

1. remover chaves soltas redundantes
2. centralizar assets da pagina
3. reduzir acoplamento com nomes históricos de contexto

## O que medir para saber se o blueprint funcionou

O blueprint esta funcionando quando:

1. a view perde volume de montagem manual
2. a tela fica mais explicavel por contrato
3. template e JS dependem menos de acidente de DOM
4. o payload fica previsivel entre paginas diferentes do catalogo
5. fica mais facil mover a conversa para canais futuros sem reescrever a regra visual inteira

## Checklist de pronto para cada presenter do catalogo

Antes de considerar um presenter bom, conferir:

1. a assinatura dele e explicita
2. ele nao decide regra de negocio
3. ele nao consulta dados escondidos sem necessidade
4. ele organiza contexto, dados, acoes, behavior e capabilities de forma legivel
5. ele reduz o numero de chaves avulsas no contexto antigo
6. o template pode depender mais do payload e menos da view
7. o JS da pagina consegue consumir contratos claros

## Decisao oficial

Para o catalogo inteiro, o padrao-base passa a ser este:

1. snapshots e queries continuam como fonte de leitura
2. facades e use cases continuam como fonte de mutacao
3. views HTTP coordenam request e resposta
4. presenters montam page payload
5. templates e JS passam a consumir esse payload em linguagem unica

## Proximo passo recomendado

Depois deste blueprint, a melhor execucao pratica e:

1. criar `catalog/presentation/shared.py`
2. criar `catalog/presentation/class_grid_page.py`
3. usar a grade de aulas como tela-modelo do primeiro corte real
4. repetir o padrao na ficha do aluno
5. consolidar o dialeto do catalogo antes de expandir para o restante do produto