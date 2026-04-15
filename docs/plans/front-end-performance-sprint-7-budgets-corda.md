<!--
ARQUIVO: C.O.R.D.A. da Sprint 7 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, budgets automatizados e guardrails anti-regressao

AUTORIDADE:
- alta para a Sprint 7 da frente de performance front-end

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

QUANDO USAR:
- antes de alterar budgets de performance front-end
- quando um teste de `test_frontend_performance_budgets.py` falhar
- antes da Sprint 8 de consolidacao controlada

POR QUE ELE EXISTE:
- transforma as otimizacoes das sprints anteriores em contratos automatizados.
- impede regressao silenciosa no HTML inicial de alunos.
- diferencia falha funcional de falha de budget/performance.

PONTOS CRITICOS:
- budgets nao sao verdades eternas; qualquer aumento precisa de justificativa e atualizacao deste documento.
- os testes protegem contratos de carregamento, nao substituem Lighthouse ou trace real.
- a Sprint 8 so deve consolidar depois que esses guardrails estiverem verdes.
-->

# Sprint 7: budgets anti-regressao C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

As Sprints 1-6 reduziram custo inicial em varias frentes:

1. fonte externa removida do caminho critico
2. busca global carregada por intencao
3. shell dividido entre essencial, interativo e efeitos
4. assets de pagina ganharam prioridade
5. CSS critico de alunos foi reduzido
6. `dynamic-visuals.js` virou modulo sob demanda

Sem budget automatizado, qualquer mudanca futura poderia desfazer isso sem alarme.

Metafora simples:

1. arrumamos a mochila para ficar leve
2. agora colocamos uma balanca na porta
3. se alguem colocar tijolo dentro, a balanca apita

## O - Objetivo

Objetivos da sprint:

1. criar testes dedicados de budget front-end
2. proteger fonte externa zero no HTML inicial
3. proteger busca lazy
4. proteger dynamic visuals sob demanda
5. proteger shell effects indireto
6. proteger CSS critico de alunos por contagem e tamanho
7. proteger separacao entre CSS critico, deferred e enhancement

Criterios de pronto:

1. novo arquivo de testes existe
2. testes passam isolados
3. testes passam junto com catalogo/page payload
4. plano mestre referencia a Sprint 7

## R - Riscos

Riscos considerados:

1. budget ficar fragil por detalhe cosmetico
2. budget ficar frouxo demais e nao proteger nada
3. duplicar asserts que ja existem em testes funcionais
4. contar CSS sem considerar expansao de manifestos
5. bloquear mudanca legitima sem documentar o motivo

Mitigacoes:

1. budgets foram colocados em arquivo dedicado
2. contagem e bytes usam `resolve_runtime_css_paths(...)`
3. o budget de alunos protege apenas contratos que ja foram conquistados
4. o teste renderiza HTML real da tela de alunos para scripts/fonte
5. alteracao futura deve atualizar teste e doc com justificativa

## D - Direcao

Direcao executada:

1. criar `boxcore/tests/test_frontend_performance_budgets.py`
2. usar `TestCase` com renderizacao real de `student-directory`
3. usar presenter de alunos para budget de CSS critico sem depender de HTML inteiro
4. validar scripts globais permitidos e proibidos por string no HTML inicial
5. validar CSS critico por lista resolvida e bytes

Alternativas rejeitadas:

1. colocar tudo em `test_catalog.py`: rejeitado porque mistura budget com comportamento funcional
2. usar snapshot completo de HTML: rejeitado por fragilidade alta
3. testar Lighthouse aqui: rejeitado porque ambiente local de teste Django nao substitui navegador real
4. budgetar todas as telas agora: rejeitado porque alunos e a primeira tela classificada pela Sprint 5

## A - Acoes executadas

Arquivos investigados:

1. `docs/plans/front-end-performance-master-plan.md`
2. `docs/plans/front-end-performance-sprint-5-students-critical-css-corda.md`
3. `docs/plans/front-end-performance-sprint-6-dynamic-visuals-corda.md`
4. `boxcore/tests/test_catalog.py`
5. `boxcore/tests/test_page_payloads.py`
6. `catalog/presentation/student_directory_page.py`
7. `shared_support/static_assets.py`

Arquivos alterados:

1. `boxcore/tests/test_frontend_performance_budgets.py`
2. `docs/plans/front-end-performance-master-plan.md`
3. `docs/plans/front-end-performance-sprint-7-budgets-corda.md`

Budgets criados:

```text
HTML inicial de alunos
|-- fonts.googleapis.com: proibido
|-- fonts.gstatic.com: proibido
|-- js/core/search-loader.js: obrigatorio
|-- js/core/search.js: proibido
|-- js/core/dynamic-visuals-loader.js: obrigatorio
|-- js/core/dynamic-visuals.js: proibido
|-- js/core/shell-effects-loader.js: obrigatorio
`-- js/core/shell-effects.js: proibido

CSS critico de alunos
|-- arquivos resolvidos: <= 9
|-- bytes resolvidos: <= 56KB
|-- css/catalog/shared.css: proibido no grupo critico
|-- css/catalog/students.css: proibido no grupo critico
|-- quick-panel.css: enhancement
`-- focus-priority.css: deferred
```

## Validacao

Comando isolado:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_frontend_performance_budgets --verbosity 1
```

Resultado:

1. 3 testes executados
2. 3 testes passaram

Comando focado:

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_frontend_performance_budgets boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_catalog.CatalogViewTests.test_class_grid_renders boxcore.tests.test_page_payloads --verbosity 1
```

Resultado:

1. 13 testes executados
2. 13 testes passaram
3. `System check identified no issues`

## Proxima sprint recomendada

Sprint 8: consolidacao controlada.

Antes de editar:

1. reler Sprints 0-7
2. decidir se a consolidacao sera por tela ou por camada
3. manter ownership modular mesmo que a entrega fique mais compacta
4. nunca remover budgets para passar build sem justificar no plano
