<!--
ARQUIVO: C.O.R.D.A. da Sprint 2 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, plano de execucao e validacao de runtime

AUTORIDADE:
- alta para a Sprint 2 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)

QUANDO USAR:
- antes de alterar busca global, topbar search ou autocomplete
- antes de dividir `shell.js`
- quando for validar se a busca global ainda tem fallback server-side

POR QUE ELE EXISTE:
- registra a decisao de transformar autocomplete global em interacao sob demanda.
- protege a busca contra regressao de carregamento global.
- garante que performance nao quebre acessibilidade nem fallback.

O QUE ESTE ARQUIVO FAZ:
1. aplica C.O.R.D.A. para a Sprint 2.
2. lista arquivos investigados.
3. define a estrategia de lazy-load.
4. registra riscos e validacoes.
5. prepara a Sprint 3.

PONTOS CRITICOS:
- o formulario de busca precisa continuar funcionando sem JavaScript rico.
- `search.js` nao deve voltar a ser carregado diretamente no `base.html`.
- a inicializacao sob demanda nao pode quebrar o papel Coach, que nao renderiza busca na topbar.
-->

# Sprint 2: topbar search sob demanda C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A Sprint 0 mostrou que `search.js` e carregado em toda pagina autenticada.

O custo em bytes e pequeno, aproximadamente `6.2KB`, mas o problema real e arquitetural:

1. a busca global acorda antes da intencao do usuario
2. o autocomplete global instala listeners e fica pronto em toda pagina
3. o plano mestre define que interacoes ricas devem acordar por intencao
4. a Sprint 2 precisa reduzir imposto fixo sem perder fallback

O HTML atual da topbar ja ajuda:

1. `topbar_search.html` renderiza um `<form method="get">`
2. `action` aponta para o diretorio de alunos
3. `data-autocomplete-url` aponta para o endpoint de autocomplete
4. Enter continua podendo abrir a busca server-side

Metafora simples:

1. antes o atendente da busca ficava em pe o dia inteiro mesmo se ninguem perguntasse nada
2. agora ele fica sentado e levanta quando alguem toca no balcao

## O - Objetivo

Objetivos da sprint:

1. remover `search.js` do carregamento global direto
2. criar um loader minimo para acordar o autocomplete por intencao
3. ativar autocomplete no primeiro `focusin`, `pointerdown` ou `input`
4. manter fallback server-side do formulario
5. evitar erro quando a topbar search nao existe para Coach
6. adicionar testes contra regressao

Criterios de pronto:

1. HTML base carrega `search-loader.js`, nao `search.js`
2. `search.js` so e injetado depois de intencao
3. se o input ja tiver texto ao carregar o autocomplete, o loader dispara `input` sintetico
4. submit sem autocomplete continua funcionando
5. testes focados passam

## R - Riscos

Riscos considerados:

1. primeiro caractere digitado antes do autocomplete carregar nao disparar fetch
2. loader duplicar script se receber eventos repetidos
3. Coach nao ter form de busca e gerar erro
4. falha ao carregar autocomplete quebrar o submit
5. `search.js` ser carregado duas vezes se outra pagina incluir manualmente

Mitigacoes:

1. loader usa estado `isLoading` e `isLoaded`
2. loader dispara evento `input` apos carregar se houver texto
3. loader retorna cedo se nao encontrar form/input
4. falha de load apenas registra estado no DOM e preserva formulario
5. teste protege que `base.html` nao renderiza `js/core/search.js`

## D - Direcao

Direcao escolhida:

1. criar `static/js/core/search-loader.js`
2. trocar `search.js` por `search-loader.js` em `templates/layouts/base.html`
3. manter `static/js/core/search.js` como modulo classico, sem reescrita ampla
4. adicionar `data-search-autocomplete-state` ao form durante load/success/error
5. proteger com teste de renderizacao de alunos

Alternativas rejeitadas:

1. `import()` de modulo ES: rejeitado porque `search.js` atual e script classico IIFE
2. colocar listener inline no template: rejeitado por higiene de front-end
3. mover busca para `shell.js`: rejeitado porque aumentaria o monolito da Sprint 3
4. remover autocomplete: rejeitado porque melhora performance empobrecendo UX

## A - Acoes executadas

Arquivos investigados:

1. `templates/includes/ui/layout/topbar/topbar_search.html`
2. `templates/layouts/base.html`
3. `static/js/core/search.js`
4. `static/js/core/shell.js`
5. `shared_support/shell_payloads.py`
6. `access/context_processors.py`

Arquivos alterados:

1. `templates/layouts/base.html`
2. `static/js/core/search-loader.js`
3. `boxcore/tests/test_catalog.py`
4. `docs/plans/front-end-performance-master-plan.md`

Mudancas:

1. criado `static/js/core/search-loader.js`
2. `base.html` deixou de carregar `js/core/search.js` diretamente
3. `base.html` passou a carregar `js/core/search-loader.js`
4. loader injeta `search.js` apenas no primeiro `focusin`, `pointerdown` ou `input`
5. loader preserva fallback server-side se o script de autocomplete falhar
6. teste da pagina de alunos protege contra volta de `search.js` no HTML inicial

Validacao planejada:

1. verificar que `js/core/search.js` nao aparece no HTML inicial
2. verificar que `js/core/search-loader.js` aparece no HTML inicial
3. verificar que busca server-side segue com `action` para alunos
4. rodar testes focados de catalogo e page payload

## Estado esperado antes e depois

Antes:

1. `base.html` carrega `js/core/search.js` em toda pagina autenticada
2. autocomplete inicializa imediatamente quando existe form

Depois:

1. `base.html` carrega apenas `js/core/search-loader.js`
2. `search.js` e inserido no DOM apenas apos intencao
3. formulario continua submisso via GET para o diretorio de alunos

## Validacao executada

Comando:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_page_payloads.PagePayloadBridgeContractTests --verbosity 1
```

Resultado:

1. renderizacao de alunos continua verde
2. HTML inicial contem `js/core/search-loader.js`
3. HTML inicial nao contem `js/core/search.js`
4. page payload continua expandindo assets como antes
5. `5` testes executados com status `OK`

## Proxima sprint recomendada

Sprint 3: shell JavaScript em camadas.

Antes de editar:

1. mapear responsabilidades de `shell.js`
2. separar essencial, interativo e cosmetico
3. preservar acessibilidade de tema, sidebar e perfil
