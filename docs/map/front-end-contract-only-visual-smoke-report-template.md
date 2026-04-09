<!--
ARQUIVO: planilha-base de execucao para smoke visual das telas `contract-only`.

POR QUE ELE EXISTE:
- transforma o checklist visual em relatorio curto e preenchivel.
- padroniza como registrar falha, suspeita e acao.
- reduz retrabalho e memoria informal depois da rodada de smoke.

O QUE ESTE ARQUIVO FAZ:
1. lista as 5 telas auditadas.
2. fornece colunas prontas para status e diagnostico.
3. ajuda a distinguir problema local de problema do contrato minimo.

PONTOS CRITICOS:
- preencher uma linha por achado real; se a tela passar, marcar `PASS`.
- quando houver falha, registrar o breakpoint.
- usar nomes de arquivos reais nos suspeitos, nao descricoes vagas.
-->

# Relatorio base de smoke visual das telas `contract-only`

Use este arquivo como prancheta de inspeccao.

Em linguagem simples:

1. cada linha e um comodo da casa
2. voce marca se a luz acendeu direito
3. se nao acendeu, anota qual parede olhar primeiro

## Legenda de status

1. `PASS`: sem regressao visual relevante
2. `WARN`: comportamento estranho, mas nao bloqueante
3. `FAIL`: regressao visual clara
4. `NA`: nao foi possivel validar

## Colunas

1. `tela`
2. `status`
3. `breakpoint`
4. `falha visual`
5. `primeiro suspeito`
6. `correcao sugerida`
7. `observacoes`

## Planilha

| tela | status | breakpoint | falha visual | primeiro suspeito | correcao sugerida | observacoes |
| --- | --- | --- | --- | --- | --- | --- |
| students | PENDENTE | `>=1280px` / `900-1024px` |  |  |  | validar hero, tabs, quick panel e quick financial summary |
| student-form | PENDENTE | `>=1280px` / `900-1024px` |  |  |  | validar hero, action rail e table wrap |
| class-grid | PENDENTE | `>=1280px` / `900-1024px` |  |  |  | validar hero, metricas e estrutura da grade |
| finance-center | PENDENTE | `>=1280px` / `900-1024px` |  |  |  | validar hero, KPIs, tabs, boards e card head compartilhado |
| finance-plan-form | PENDENTE | `>=1280px` / `900-1024px` |  |  |  | validar hero, summary rail e formulario |

## Atalhos de suspeita

Use estes suspeitos rapidos quando aparecer regressao:

1. hero quebrado: [../../static/css/design-system/operations/refinements/hero.css](../../static/css/design-system/operations/refinements/hero.css)
2. cabecalho de card quebrado: [../../static/css/design-system/operations/components/card-shell.css](../../static/css/design-system/operations/components/card-shell.css)
3. tabela quebrada: [../../static/css/design-system/operations/workspace/tables.css](../../static/css/design-system/operations/workspace/tables.css)
4. identidade local quebrada em alunos: [../../static/css/catalog/students.css](../../static/css/catalog/students.css)
5. identidade local quebrada em financeiro: [../../static/css/catalog/finance.css](../../static/css/catalog/finance.css)
6. identidade local quebrada em class-grid: [../../static/css/catalog/class-grid/](../../static/css/catalog/class-grid/)

## Exemplo de preenchimento

| tela | status | breakpoint | falha visual | primeiro suspeito | correcao sugerida | observacoes |
| --- | --- | --- | --- | --- | --- | --- |
| students | WARN | `900-1024px` | quick financial summary com titulo esmagado | `static/css/design-system/operations/components/card-shell.css` | revisar espacamento e wrap do `operation-card-head` | tabs e hero ok |

## Regra de ouro

1. se a falha aparecer so em uma tela, suspeite primeiro do CSS local
2. se a falha aparecer em varias telas, suspeite primeiro do contrato minimo
3. se a falha for de dados ou acao, nao tente curar com CSS
