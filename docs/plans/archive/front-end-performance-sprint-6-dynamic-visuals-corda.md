<!--
ARQUIVO: C.O.R.D.A. da Sprint 6 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, loader de efeitos declarativos e validacao de runtime

AUTORIDADE:
- alta para a Sprint 6 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
- [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
- [front-end-performance-sprint-3-shell-layers-corda.md](front-end-performance-sprint-3-shell-layers-corda.md)
- [front-end-performance-sprint-4-asset-priority-corda.md](front-end-performance-sprint-4-asset-priority-corda.md)
- [front-end-performance-sprint-5-students-critical-css-corda.md](front-end-performance-sprint-5-students-critical-css-corda.md)

QUANDO USAR:
- antes de alterar `dynamic-visuals.js` ou `dynamic-visuals-loader.js`
- antes de criar novas barras declarativas com `data-visual-width`, `data-visual-height` ou `data-visual-columns`
- quando um grafico/barrinha visual parecer atrasar ou nao aplicar variavel CSS

POR QUE ELE EXISTE:
- registra a remocao do script de visuais declarativos do carregamento direto global.
- preserva graficos e barras declarativas sem executar o modulo completo antes da necessidade.
- documenta o trade-off de loader pequeno e modulo real sob demanda.

PONTOS CRITICOS:
- esta sprint nao apaga efeitos premium.
- o loader e propositalmente compacto porque vive no caminho inicial.
- o modulo completo continua existindo para paginas com elementos declarativos.
-->

# Sprint 6: dynamic visuals sob demanda C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A Sprint 0 mostrou que `static/js/core/dynamic-visuals.js` entrava globalmente em toda pagina.

O script e pequeno, mas ainda era um imposto fixo:

1. carregava em toda tela
2. executava scan global por atributos visuais
3. competia com a primeira leitura mesmo em paginas sem barras/graficos declarativos

Usos reais encontrados:

1. importacao de alunos
2. grade de aulas
3. financeiro
4. dashboard/operations com cards e barras de ocupacao

Metafora simples:

1. antes o pintor entrava em toda sala procurando parede para pintar
2. agora um porteiro pequeno chama o pintor apenas quando existe parede marcada

## O - Objetivo

Objetivos da sprint:

1. remover `dynamic-visuals.js` do HTML inicial direto
2. criar `dynamic-visuals-loader.js`
3. carregar o modulo real apenas quando houver `data-visual-*`
4. executar o scan inicial em idle ou timeout seguro
5. manter `window.OctoDynamicVisuals.apply/applyElement` como API para scripts existentes
6. proteger com teste de renderizacao

Criterios de pronto:

1. `base.html` carrega `dynamic-visuals-loader.js`
2. `base.html` nao carrega `dynamic-visuals.js` diretamente
3. loader passa em `node --check`
4. alunos e grade continuam renderizando
5. page payload continua verde

## R - Riscos

Riscos considerados:

1. `import-progress.js` chamar `OctoDynamicVisuals.applyElement` antes do modulo real carregar
2. barras visuais aparecerem com valor fallback ate idle
3. loader ficar maior que o modulo original e virar falsa otimizacao
4. erro de URL carregar o script de outro diretorio
5. apagar assinatura visual em telas financeiras

Mitigacoes:

1. o loader instala um stub `window.OctoDynamicVisuals`
2. quando o modulo real carrega, ele aplica no documento inteiro
3. o loader foi compactado para `976` bytes
4. a URL usa `new URL('dynamic-visuals.js', document.currentScript.src)` para manter o mesmo diretorio
5. o modulo real nao foi alterado

## D - Direcao

Direcao executada:

1. criar `static/js/core/dynamic-visuals-loader.js`
2. trocar o script direto no `templates/layouts/base.html`
3. manter `static/js/core/dynamic-visuals.js` como modulo completo
4. adicionar teste para impedir retorno do carregamento direto
5. validar grade, alunos e page payload

Alternativas rejeitadas:

1. apagar `dynamic-visuals.js`: rejeitado porque financeiro/grade/dashboard usam barras declarativas
2. mover todos os visuais para CSS inline: rejeitado por higiene e CSP
3. deixar carregamento direto: rejeitado porque mantem imposto global
4. criar API grande de behavior no payload agora: rejeitado porque o seletor declarativo ja e suficiente

## A - Acoes executadas

Arquivos investigados:

1. `docs/plans/front-end-performance-master-plan.md`
2. `docs/plans/front-end-performance-sprint-5-students-critical-css-corda.md`
3. `static/js/core/dynamic-visuals.js`
4. `templates/layouts/base.html`
5. templates com `data-visual-width`, `data-visual-height` e `data-visual-columns`
6. `static/js/pages/catalog/import-progress.js`
7. `boxcore/tests/test_catalog.py`

Arquivos alterados:

1. `static/js/core/dynamic-visuals-loader.js`
2. `templates/layouts/base.html`
3. `boxcore/tests/test_catalog.py`
4. `docs/plans/front-end-performance-master-plan.md`
5. `docs/plans/front-end-performance-sprint-6-dynamic-visuals-corda.md`

## Medicao

Antes:

1. `dynamic-visuals.js`: `1516` bytes
2. carregado diretamente em todo HTML base
3. executava scan global imediatamente apos carregar

Depois:

1. `dynamic-visuals-loader.js`: `976` bytes
2. carregado no HTML base
3. agenda scan em idle ou timeout
4. injeta `dynamic-visuals.js` somente se houver elementos `data-visual-*`

## Validacao

Comandos executados:

```powershell
node --check static\js\core\dynamic-visuals-loader.js
```

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_catalog.CatalogViewTests.test_class_grid_renders boxcore.tests.test_page_payloads --verbosity 1
```

Resultado:

1. sintaxe JS valida
2. 10 testes executados
3. 10 testes passaram
4. `System check identified no issues`

## Proxima sprint recomendada

Sprint 7: budgets e testes anti-regressao.

Antes de editar:

1. reler Sprints 0-6
2. transformar os contratos ja conquistados em budgets automatizados
3. proteger fonte externa, scripts globais diretos, CSS critico de alunos e contratos de hero
