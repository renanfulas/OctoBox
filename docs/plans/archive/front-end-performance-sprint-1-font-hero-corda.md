<!--
ARQUIVO: C.O.R.D.A. da Sprint 1 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, decisao tecnica e validacao de runtime

AUTORIDADE:
- alta para a Sprint 1 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)
- [../experience/css-guide.md](../experience/css-guide.md)

QUANDO USAR:
- antes de alterar novamente fonte critica, hero canonico ou contrato `data-max-lines`
- quando for comparar LCP antes/depois da remocao de Google Fonts do head
- antes de iniciar Sprint 2 de busca sob demanda

POR QUE ELE EXISTE:
- registra por que a Sprint 1 removeu a dependencia externa de fonte no caminho critico.
- documenta que o contrato visual do hero ja tinha suporte real no CSS canonico.
- preserva a decisao de nao consolidar CSS nesta etapa.

O QUE ESTE ARQUIVO FAZ:
1. aplica C.O.R.D.A. para a Sprint 1.
2. registra arquivos investigados.
3. documenta a mudanca em runtime.
4. lista riscos e validacoes.
5. prepara a Sprint 2.

PONTOS CRITICOS:
- esta sprint nao tenta resolver toda a explosao de CSS.
- esta sprint nao troca a identidade tipografica global por uma nova familia externa.
- a decisao principal e tirar a dependencia externa do heading critico e manter fallback local/sistema.
-->

# Sprint 1: fonte critica e contrato do hero C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A Sprint 0 mostrou que a tela de alunos ainda paga:

1. `44` links CSS no head
2. aproximadamente `319.0KB` de CSS inicial
3. `student-directory.js` com aproximadamente `101.6KB`
4. Google Fonts no head do `base.html`

Mesmo assim, a primeira correcao escolhida foi fonte critica e hero.

Motivo:

1. o hero `h1` e candidato natural de LCP
2. o atraso do LCP pode vir de fonte externa, CSS e layout anterior ao hero
3. remover a fonte externa do head e uma mudanca pequena, segura e diretamente alinhada ao plano mestre

Metafora simples:

1. antes o titulo principal esperava uma caneta que vinha de fora
2. agora ele escreve com a caneta que ja esta na mesa

## O - Objetivo

Objetivos da sprint:

1. remover dependencia de Google Fonts do caminho critico
2. garantir que o heading do hero use fonte local/sistema por `--font-display-critical`
3. confirmar que `data-max-lines` tem suporte visual real
4. manter a correcao no contrato compartilhado, nao em CSS local de alunos
5. nao iniciar consolidacao ampla de CSS nesta sprint

Criterios de pronto:

1. `base.html` nao carrega `fonts.googleapis` nem `fonts.gstatic.com`
2. CSP nao libera dominios de fonte externa sem uso
3. hero canonico continua usando `--font-display-critical`
4. `data-max-lines="1"` e `"2"` continuam suportados no CSS
5. testes relevantes passam

## R - Riscos

Riscos considerados:

1. mudanca visual leve por fallback de fonte em vez de Inter remoto
2. algum ambiente ainda esperar Google Fonts via CSP
3. CSP ficar restritiva demais se outra tela usar fonte externa sem declarar no template
4. mexer no CSS local de alunos poderia criar divergencia entre heroes

Mitigacoes:

1. `tokens.css` ja declara `--font-display-critical` com fontes locais/sistema
2. `--font-body` e `--font-display` ainda tem fallbacks fortes como `Aptos`, `Segoe UI Variable` e `system-ui`
3. busca por `fonts.googleapis` e `fonts.gstatic.com` indicou uso relevante no `base.html` e CSP
4. nenhuma regra local em `students.css` foi usada para corrigir o hero

## D - Direcao

Direcao executada:

1. remover os tres links externos de Google Fonts do `templates/layouts/base.html`
2. remover `https://fonts.googleapis.com` de `style-src`
3. remover `https://fonts.gstatic.com` de `font-src`
4. manter `tokens.css` como autoridade de fallback tipografico
5. manter `operations/refinements/hero.css` como autoridade operacional de clamp do hero

Alternativas rejeitadas:

1. self-host imediato de Inter: rejeitado para esta sprint porque adicionaria pipeline de assets antes de provar necessidade visual real
2. trocar toda tipografia global: rejeitado por escopo amplo demais
3. corrigir somente alunos: rejeitado porque quebraria o contrato canonico do hero
4. consolidar CSS junto: rejeitado porque pertence a sprint futura

## A - Acoes executadas

Arquivos investigados:

1. `docs/plans/front-end-performance-master-plan.md`
2. `docs/plans/front-end-performance-sprint-0-baseline-corda.md`
3. `docs/reference/front-end-ownership-map.md`
4. `docs/experience/css-guide.md`
5. `templates/layouts/base.html`
6. `templates/includes/ui/layout/page_hero.html`
7. `static/css/design-system/tokens.css`
8. `static/css/design-system/components/hero.css`
9. `static/css/design-system/operations/refinements/hero.css`
10. `shared_support/security/__init__.py`

Arquivos alterados:

1. `templates/layouts/base.html`
2. `shared_support/security/__init__.py`
3. `boxcore/tests/test_catalog.py`
4. `boxcore/tests/test_security_guards.py`

Mudancas:

1. removido `preconnect` para `https://fonts.googleapis.com`
2. removido `preconnect` para `https://fonts.gstatic.com`
3. removido stylesheet remoto de Inter
4. CSP deixou de permitir `fonts.googleapis.com` em `style-src`
5. CSP deixou de permitir `fonts.gstatic.com` em `font-src`
6. teste da pagina de alunos protege ausencia de Google Fonts no HTML renderizado
7. teste de seguranca protege CSP sem hosts externos de fonte

## Achados tecnicos

`tokens.css` ja tinha:

1. `--font-body` com `Inter`, `Aptos`, `Segoe UI Variable Text`, `Segoe UI`, `system-ui`, `sans-serif`
2. `--font-display` com `Inter`, `Aptos Display`, `Iowan Old Style`, `Palatino Linotype`, `serif`
3. `--font-display-critical` com `Aptos Display`, `Segoe UI Variable Display`, `Segoe UI`, `system-ui`, `sans-serif`

`operations/refinements/hero.css` ja tinha:

1. `.operation-hero-title` usando `font-family: var(--font-display-critical, var(--font-display))`
2. `display: -webkit-box`
3. `line-clamp: 2`
4. `-webkit-line-clamp: 2`
5. suporte especifico para `data-max-lines="1"`
6. suporte especifico para `data-max-lines="2"`

Conclusao:

1. o contrato visual do hero ja estava tecnicamente preparado
2. o custo restante da Sprint 1 estava no head e na CSP

## Estado antes e depois

Antes:

1. `base.html` abria conexao com Google Fonts
2. `base.html` baixava CSS remoto de Inter
3. CSP permitia `fonts.googleapis.com` e `fonts.gstatic.com`

Depois:

1. `base.html` nao referencia Google Fonts
2. heading critico usa fallback local/sistema
3. CSP fica mais fechada e coerente com assets locais

## Validacao esperada

Validar:

1. renderizacao da tela de alunos
2. renderizacao de financeiro, dashboard e operations com hero canonico
3. ausencia de `fonts.googleapis.com` no HTML base
4. ausencia de permissao desnecessaria de fonte externa na CSP
5. testes de catalogo e page payload

Validacao executada:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_security_guards.SecurityGuardTests.test_csp_does_not_allow_external_font_hosts boxcore.tests.test_page_payloads.PageHeroContractTests --verbosity 1
```

Resultado:

1. `4` testes executados
2. status `OK`

## Proxima sprint recomendada

Sprint 2: topbar search sob demanda.

Antes de editar:

1. reler este C.O.R.D.A.
2. reler Sprint 0
3. investigar `topbar_search.html`, `search.js`, `shell.js`, `shell_payloads.py` e `context_processors.py`
4. planejar lazy-load com fallback server-side
