<!--
ARQUIVO: C.O.R.D.A. da Sprint 8 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, consolidacao controlada e contrato de bundles CSS

AUTORIDADE:
- alta para a Sprint 8 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
- [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
- [front-end-performance-sprint-3-shell-layers-corda.md](front-end-performance-sprint-3-shell-layers-corda.md)
- [front-end-performance-sprint-4-asset-priority-corda.md](front-end-performance-sprint-4-asset-priority-corda.md)
- [front-end-performance-sprint-5-students-critical-css-corda.md](front-end-performance-sprint-5-students-critical-css-corda.md)
- [front-end-performance-sprint-6-dynamic-visuals-corda.md](front-end-performance-sprint-6-dynamic-visuals-corda.md)
- [front-end-performance-sprint-7-budgets-corda.md](front-end-performance-sprint-7-budgets-corda.md)

QUANDO USAR:
- antes de criar novos assets com prefixo `bundle:`
- antes de consolidar CSS critico
- quando budgets de CSS progressivo de alunos falharem

POR QUE ELE EXISTE:
- registra a primeira consolidacao controlada depois de separar criticidade.
- cria uma forma explicita de preservar manifestos como links unicos.
- evita transformar ownership modular em um arquivo opaco.

PONTOS CRITICOS:
- esta sprint consolida apenas CSS progressivo de alunos.
- CSS critico de alunos continua modular e protegido por budget.
- `bundle:` deve ser usado com parcimonia e com teste.
-->

# Sprint 8: consolidacao controlada C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A Sprint 7 colocou sensores de fumaca em volta das conquistas anteriores.

Com os budgets verdes, a Sprint 8 podia reduzir fragmentacao sem voltar para um CSS gigante.

Estado antes da sprint em alunos:

1. `css`: 9 links criticos
2. `deferred_css`: 4 links progressivos
3. `enhancement_css`: 5 links progressivos

O risco seria consolidar o CSS critico e piorar LCP.

Por isso a consolidacao escolhida foi apenas nos grupos progressivos.

Metafora simples:

1. a mochila que usamos na chegada continua com bolsos separados
2. os brinquedos que so usamos depois vao em duas sacolas organizadas
3. cada brinquedo ainda tem sua caixinha dentro da sacola

## O - Objetivo

Objetivos da sprint:

1. reduzir links de CSS progressivo de alunos
2. manter CSS critico intocado
3. preservar ownership modular via manifestos com `@import`
4. criar contrato explicito para manifestos que nao devem ser expandidos
5. manter budgets verdes

Criterios de pronto:

1. `resolve_runtime_css_paths(...)` suporta `bundle:`
2. alunos usa 1 link para `deferred_css`
3. alunos usa 1 link para `enhancement_css`
4. CSS critico de alunos continua com 9 arquivos resolvidos
5. testes de budgets e page payload passam

## R - Riscos

Riscos considerados:

1. consolidar critico cedo demais e piorar LCP
2. esconder ownership em um arquivo opaco
3. quebrar a expansao normal de manifestos existentes
4. criar prefixo magico sem teste
5. perder fallback `noscript` dos grupos progressivos

Mitigacoes:

1. somente `deferred_css` e `enhancement_css` foram consolidados
2. os bundles sao manifestos pequenos com `@import`
3. `bundle:` e opt-in; manifestos normais continuam expandindo
4. teste cobre preservacao de bundle sem expansao
5. renderizacao do `base.html` continua usando `preload` + `onload` + `noscript`

## D - Direcao

Direcao executada:

1. adicionar prefixo `bundle:` em `shared_support/static_assets.py`
2. criar `css/catalog/students-deferred.css`
3. criar `css/catalog/students-enhancement.css`
4. alterar o presenter de alunos para usar os dois bundles progressivos
5. atualizar budgets para exigir 1 link por grupo progressivo
6. manter CSS critico de alunos sem bundle

Alternativas rejeitadas:

1. copiar CSS para arquivos concatenados: rejeitado porque destruiria ownership modular
2. consolidar CSS critico de alunos agora: rejeitado porque o budget atual protege LCP e a cascata critica
3. trocar todos os manifestos do sistema para bundle: rejeitado por escopo e risco
4. remover `resolve_runtime_css_paths`: rejeitado porque ainda e util para critical path

## A - Acoes executadas

Arquivos investigados:

1. `docs/plans/front-end-performance-master-plan.md`
2. `docs/plans/front-end-performance-sprint-7-budgets-corda.md`
3. `shared_support/static_assets.py`
4. `catalog/presentation/student_directory_page.py`
5. `boxcore/tests/test_frontend_performance_budgets.py`
6. `boxcore/tests/test_page_payloads.py`

Arquivos alterados:

1. `shared_support/static_assets.py`
2. `catalog/presentation/student_directory_page.py`
3. `static/css/catalog/students-deferred.css`
4. `static/css/catalog/students-enhancement.css`
5. `boxcore/tests/test_frontend_performance_budgets.py`
6. `boxcore/tests/test_catalog.py`
7. `boxcore/tests/test_page_payloads.py`
8. `docs/plans/front-end-performance-master-plan.md`
9. `docs/plans/front-end-performance-sprint-8-controlled-consolidation-corda.md`

Contrato novo:

```text
bundle:css/catalog/students-deferred.css
```

Significado:

1. renderizar `css/catalog/students-deferred.css` como link unico
2. nao expandir seus `@import` no HTML
3. manter os arquivos fonte importados como ownership modular

## Medicao

Depois da Sprint 5:

1. `css`: 9 arquivos resolvidos, aproximadamente 51.4KB
2. `deferred_css`: 4 arquivos resolvidos
3. `enhancement_css`: 5 arquivos resolvidos

Depois da Sprint 8:

1. `css`: 9 arquivos resolvidos, aproximadamente 51.4KB
2. `deferred_css`: 1 link, `css/catalog/students-deferred.css`
3. `enhancement_css`: 1 link, `css/catalog/students-enhancement.css`

Leitura:

1. o caminho critico nao foi alterado
2. a fragmentacao progressiva caiu de 9 links para 2 links
3. os bytes dos bundles medidos diretamente sao pequenos porque eles sao manifestos de imports

## Validacao

Comando executado:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_frontend_performance_budgets boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_catalog.CatalogViewTests.test_class_grid_renders boxcore.tests.test_page_payloads --verbosity 1
```

Resultado:

1. 14 testes executados
2. 14 testes passaram
3. `System check identified no issues`

## Proxima sprint recomendada

Sprint 9: aplicar a mesma disciplina em financeiro ou criar medicao visual real.

Opcoes:

1. dieta/consolidacao de CSS da tela financeira
2. validar visualmente alunos em desktop/mobile/drawer
3. adicionar medicao Lighthouse ou trace em ambiente estavel
