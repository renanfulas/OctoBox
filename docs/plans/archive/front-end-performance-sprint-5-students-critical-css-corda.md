<!--
ARQUIVO: C.O.R.D.A. da Sprint 5 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, classificacao de CSS critico e validacao de alunos

AUTORIDADE:
- alta para a Sprint 5 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
- [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
- [front-end-performance-sprint-3-shell-layers-corda.md](front-end-performance-sprint-3-shell-layers-corda.md)
- [front-end-performance-sprint-4-asset-priority-corda.md](front-end-performance-sprint-4-asset-priority-corda.md)

QUANDO USAR:
- antes de mover mais CSS da tela de alunos entre `css`, `deferred_css` e `enhancement_css`
- antes de aplicar a mesma estrategia em financeiro
- quando algum teste de alunos falhar por asset ausente

POR QUE ELE EXISTE:
- registra a primeira dieta real de CSS critico por tela.
- explica por que certos arquivos continuam bloqueantes e outros viraram progressivos.
- protege contra a volta de manifestos amplos em `alunos`.

PONTOS CRITICOS:
- esta sprint nao consolida CSS.
- esta sprint nao altera as regras CSS em si.
- a classificacao preserva hero, KPIs, filtros e diretorio ativo como caminho critico.
-->

# Sprint 5: CSS critico de alunos C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A Sprint 4 criou prioridade no contrato de assets.

Antes desta sprint, `alunos` ainda usava:

1. `css/design-system/catalog-operation-contract.css`
2. `css/catalog/shared.css`
3. `css/catalog/students.css`

Esses manifestos resolviam `18` arquivos de pagina.

O problema:

1. `css/catalog/shared.css` puxa CSS financeiro e de pagamento que nao sustenta a primeira dobra de alunos
2. `css/catalog/students.css` puxa painel rapido, fila de prioridade e abas que nao aparecem no estado inicial
3. todo esse conjunto entrava como CSS bloqueante

Metafora simples:

1. antes a pagina montava a recepcao, o estoque, o escritorio financeiro e a gaveta secreta antes de abrir a porta
2. agora a recepcao abre primeiro; gavetas e escritorio acordam quando alguem precisa

## O - Objetivo

Objetivos da sprint:

1. comecar por `alunos`
2. mover somente CSS comprovadamente nao critico para `deferred_css` ou `enhancement_css`
3. manter hero, KPIs, filtros e diretorio ativo no caminho critico
4. reduzir CSS bloqueante de pagina sem quebrar a assinatura visual
5. proteger o contrato com teste

Criterios de pronto:

1. `alunos` nao usa mais `css/catalog/shared.css` como manifesto critico amplo
2. `alunos` nao usa mais `css/catalog/students.css` como manifesto critico amplo
3. CSS do drawer rapido vai para `enhancement_css`
4. CSS de prioridade/intake/legado vai para `deferred_css`
5. teste de renderizacao de alunos passa

## R - Riscos

Riscos considerados:

1. mover CSS do diretorio ativo para deferred e causar FOUC em telas grandes
2. mover CSS responsivo de alunos para deferred e quebrar mobile
3. mover CSS financeiro usado pelo drawer sem fallback
4. perder ordem de cascade entre utilitarios compartilhados e ajustes locais
5. mascarar o problema real com consolidacao prematura

Mitigacoes:

1. `intake-directory.css` ficou critico porque o diretorio e a aba padrao
2. `students/responsive.css` ficou critico porque mobile tambem e primeira dobra
3. `quick-panel.css` foi para enhancement porque o drawer nasce fechado e exige clique/intencao
4. `focus-priority.css` foi para deferred porque a aba de prioridade nao e o painel padrao
5. nenhum CSS foi reescrito nesta sprint

## D - Direcao

Direcao executada:

1. substituir os manifestos amplos da tela por arquivos explicitos no presenter
2. manter o contrato operacional minimo como CSS critico
3. manter `shared/scene.css`, `students/scene.css`, `students/filters.css`, `students/intake-directory.css` e `students/responsive.css` como criticos
4. mover `shared/utilities.css`, `shared/responsive.css`, `shared/lock-banner.css` e `students/focus-priority.css` para deferred
5. mover `shared/student-financial.css`, `shared/student-financial-foundations.css` e `students/quick-panel.css` para enhancement

Alternativas rejeitadas:

1. diferir `intake-directory.css`: rejeitado porque o diretorio e o painel padrao e pode aparecer cedo em viewport grande
2. diferir `students/responsive.css`: rejeitado porque mobile nao pode esperar para montar a primeira dobra
3. editar os manifestos globais: rejeitado porque impactaria outras telas do catalogo
4. consolidar CSS agora: rejeitado porque Sprint 8 trata consolidacao controlada

## A - Acoes executadas

Arquivos investigados:

1. `docs/plans/front-end-performance-master-plan.md`
2. `docs/plans/front-end-performance-sprint-0-baseline-corda.md`
3. `docs/plans/front-end-performance-sprint-1-font-hero-corda.md`
4. `docs/plans/front-end-performance-sprint-2-topbar-search-corda.md`
5. `docs/plans/front-end-performance-sprint-3-shell-layers-corda.md`
6. `docs/plans/front-end-performance-sprint-4-asset-priority-corda.md`
7. `catalog/presentation/student_directory_page.py`
8. `templates/catalog/students.html`
9. `templates/catalog/includes/student/*.html`
10. `static/css/catalog/shared.css`
11. `static/css/catalog/students.css`
12. `static/css/catalog/shared/*.css`
13. `static/css/catalog/students/*.css`
14. `boxcore/tests/test_catalog.py`

Arquivos alterados:

1. `catalog/presentation/student_directory_page.py`
2. `boxcore/tests/test_catalog.py`
3. `docs/plans/front-end-performance-master-plan.md`
4. `docs/plans/front-end-performance-sprint-5-students-critical-css-corda.md`

Classificacao aplicada:

```text
css critico
|-- css/design-system/catalog-operation-contract.css
|-- css/catalog/shared/scene.css
|-- css/catalog/students/scene.css
|-- css/catalog/students/filters.css
|-- css/catalog/students/intake-directory.css
`-- css/catalog/students/responsive.css

deferred_css
|-- css/catalog/shared/utilities.css
|-- css/catalog/shared/responsive.css
|-- css/catalog/shared/lock-banner.css
`-- css/catalog/students/focus-priority.css

enhancement_css
|-- css/catalog/shared/student-financial.css
|-- css/catalog/shared/student-financial-foundations.css
`-- css/catalog/students/quick-panel.css
```

## Medicao

Antes, CSS de pagina de alunos:

1. `18` arquivos resolvidos
2. aproximadamente `108.9KB`
3. todos bloqueantes

Depois, CSS de pagina de alunos:

1. `css`: `9` arquivos resolvidos, aproximadamente `51.4KB`
2. `deferred_css`: `4` arquivos resolvidos, aproximadamente `14.8KB`
3. `enhancement_css`: `5` arquivos resolvidos, aproximadamente `42.7KB`

Leitura:

1. reducao de `18` para `9` arquivos bloqueantes de pagina
2. reducao aproximada de `108.9KB` para `51.4KB` no CSS bloqueante de pagina
3. o restante continua disponivel via preload/onload e fallback `noscript`

Observacao tecnica:

1. `resolve_runtime_css_paths(...)` trata arquivos com `@import` como manifestos
2. se um arquivo tem `@import` e tambem regras proprias, as regras proprias podem nao entrar como arquivo pai resolvido
3. isso ja existia antes desta sprint e merece higiene futura nos manifestos hibridos

## Validacao

Comando executado:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_page_payloads --verbosity 1
```

Resultado:

1. 9 testes executados
2. 9 testes passaram
3. `System check identified no issues`

## Proxima sprint recomendada

Sprint 5.1 ou Sprint 6, dependendo da prioridade:

1. aplicar a mesma classificacao em financeiro
2. ou mover `dynamic-visuals.js` para atmosfera sob demanda

Antes de continuar:

1. validar visualmente alunos desktop e mobile
2. conferir drawer rapido apos clique em aluno
3. decidir se a proxima tela da dieta sera financeiro
