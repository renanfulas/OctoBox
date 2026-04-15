<!--
ARQUIVO: C.O.R.D.A. da Sprint 4 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, contrato de assets e validacao de runtime

AUTORIDADE:
- alta para a Sprint 4 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
- [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
- [front-end-performance-sprint-3-shell-layers-corda.md](front-end-performance-sprint-3-shell-layers-corda.md)
- [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)

QUANDO USAR:
- antes de alterar `build_page_assets`, `attach_page_payload`, `resolve_runtime_css_paths` ou a renderizacao de assets no `base.html`
- antes de iniciar a Sprint 5 de CSS critico por tela
- quando uma pagina precisar declarar CSS ou JS por prioridade

POR QUE ELE EXISTE:
- registra a evolucao do contrato de assets sem quebrar payloads legados.
- cria o trilho tecnico para separar CSS critico, pagina e acabamento.
- evita consolidacao prematura de CSS antes de existir prioridade explicita.

O QUE ESTE ARQUIVO FAZ:
1. aplica C.O.R.D.A. para a Sprint 4.
2. define o shape novo de assets.
3. registra a compatibilidade com `css` e `js` legados.
4. lista riscos, validacoes e proxima sprint.

PONTOS CRITICOS:
- esta sprint cria contrato e renderizacao por prioridade; ela nao faz ainda a dieta visual de cada pagina.
- `css` e `js` legados continuam aceitos.
- CSS diferido precisa ter fallback com `noscript`.
-->

# Sprint 4: asset priority no page payload C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

As sprints anteriores reduziram dependencias externas e separaram scripts globais.

O contrato de assets ainda era simples:

1. `assets.css`
2. `assets.js`
3. `current_page_assets.css_runtime` gerado por `resolve_runtime_css_paths(...)`

Isso funcionava, mas nao permitia dizer ao template:

1. este CSS e critico
2. este CSS e da pagina mas pode vir depois
3. este CSS e apenas acabamento
4. este JS deve carregar antes
5. este JS pode ser diferido

Metafora simples:

1. antes todos os materiais da obra chegavam no mesmo caminhao
2. agora separamos cimento, tinta e decoracao em caixas diferentes

## O - Objetivo

Objetivos da sprint:

1. adicionar prioridade no contrato de assets
2. manter compatibilidade com `css` e `js` legados
3. expandir manifestos CSS por prioridade
4. renderizar CSS critico no head como antes
5. renderizar CSS diferido/enhancement com preload/onload e fallback `noscript`
6. permitir JS critico e diferido sem quebrar scripts atuais
7. adicionar testes de contrato

Criterios de pronto:

1. `build_page_assets(...)` aceita campos novos
2. `attach_page_payload(...)` mergeia campos novos e antigos
3. `base.html` renderiza os grupos novos
4. testes de page payload passam
5. renderizacao de alunos continua verde

## R - Riscos

Riscos considerados:

1. quebrar payloads antigos que usam apenas `css` e `js`
2. duplicar assets entre grupos
3. diferir CSS essencial antes de mapear criticidade real
4. criar shape complexo demais
5. `noscript` gerar duplicacao visual quando JS esta ativo

Mitigacoes:

1. `css` legado continua virando `css_runtime`
2. campos novos sao opcionais
3. merge preserva ordem e remove duplicatas por grupo
4. Sprint 4 nao move CSS real de paginas para diferido ainda
5. `noscript` so protege usuarios sem JS para CSS diferido/enhancement

## D - Direcao

Direcao escolhida:

1. adicionar `critical_css`, `deferred_css`, `enhancement_css`
2. adicionar `critical_js`, `deferred_js`
3. manter `css` e `js`
4. gerar `critical_css_runtime`, `deferred_css_runtime`, `enhancement_css_runtime`
5. manter `css_runtime` como alias de compatibilidade para CSS critico/legado
6. atualizar `base.html` para renderizar prioridades
7. atualizar testes de contrato

Alternativas rejeitadas:

1. trocar todos os presenters agora: rejeitado por escopo alto
2. remover `css/js` legados: rejeitado por quebra desnecessaria
3. consolidar CSS agora: rejeitado porque pertence a sprint futura
4. usar helper template customizado agora: rejeitado porque o template ainda e simples o bastante

## A - Acoes executadas

Arquivos investigados:

1. `shared_support/page_payloads.py`
2. `shared_support/static_assets.py`
3. `templates/layouts/base.html`
4. `catalog/presentation/shared.py`
5. `boxcore/tests/test_page_payloads.py`
6. `boxcore/tests/test_catalog.py`

Arquivos alterados:

1. `shared_support/page_payloads.py`
2. `catalog/presentation/shared.py`
3. `templates/layouts/base.html`
4. `boxcore/tests/test_page_payloads.py`
5. `docs/plans/front-end-performance-master-plan.md`

Implementacao aplicada:

1. `build_page_assets(...)` agora aceita `critical_css`, `deferred_css`, `enhancement_css`, `critical_js` e `deferred_js`
2. `attach_page_payload(...)` preserva `css` e `js` legados e mergeia os novos grupos por prioridade
3. `current_page_assets` agora expoe `critical_css_runtime`, `css_runtime`, `deferred_css_runtime` e `enhancement_css_runtime`
4. `current_page_assets.has_runtime_css_groups` evita fallback indevido quando um grupo resolvido fica vazio por dedupe
5. `base.html` renderiza CSS critico no head e CSS diferido/enhancement com `preload` + `onload` + fallback `noscript`
6. `base.html` renderiza `critical_js` antes dos scripts de pagina legados e `deferred_js` como diferido
7. `build_catalog_assets(...)` repassa os novos grupos sem obrigar migracao imediata das telas existentes
8. testes cobrem compatibilidade legada, grupos de prioridade e dedupe entre grupos

Shape novo:

```text
assets
|-- css
|-- js
|-- critical_css
|-- deferred_css
|-- enhancement_css
|-- critical_js
`-- deferred_js
```

Shape resolvido em `current_page_assets`:

```text
current_page_assets
|-- css
|-- js
|-- critical_css
|-- deferred_css
|-- enhancement_css
|-- critical_js
|-- deferred_js
|-- css_runtime
|-- critical_css_runtime
|-- deferred_css_runtime
|-- enhancement_css_runtime
`-- has_runtime_css_groups
```

## Proxima sprint recomendada

Sprint 5: CSS critico por tela.

## Validacao

Comando executado:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_page_payloads boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders --verbosity 1
```

Resultado:

1. 9 testes executados
2. 9 testes passaram
3. `System check identified no issues`

Antes de editar:

1. reler Sprints 0-4
2. escolher uma tela inicial, preferencialmente alunos
3. mapear CSS acima da dobra
4. mover somente CSS comprovadamente nao critico para `deferred_css` ou `enhancement_css`
