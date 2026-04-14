<!--
ARQUIVO: checkpoint final curto da arquitetura do financeiro apos o split por ondas.

TIPO DE DOCUMENTO:
- checkpoint tecnico de encerramento

AUTORIDADE:
- media-alta para leitura rapida do estado atual da fundacao financeira

DOCUMENTO PAI:
- [../plans/finance-ia-traditional-foundation-split-plan.md](../plans/finance-ia-traditional-foundation-split-plan.md)

QUANDO USAR:
- quando a pergunta for "como ficou a arquitetura agora?"
- quando alguem precisar saber o que e canonico e o que ainda e ponte
- quando formos decidir se ja da para remover compatibilidade antiga
-->

# Finance Architecture Checkpoint

## Estado atual

O financeiro terminou as ondas de split da fundacao e agora opera com tres camadas canonicas:

1. `catalog.finance_snapshot.traditional`
2. `catalog.finance_snapshot.ai`
3. `catalog.finance_snapshot.hybrid`

Na apresentacao, a pagina tambem foi separada por papel:

1. `catalog.presentation.finance_traditional_page`
2. `catalog.presentation.finance_ai_page`
3. `catalog.presentation.finance_hybrid_page`
4. `catalog.presentation.finance_center_page` como fachada de orquestracao

Em linguagem simples:

1. a oficina agora tem bancada de ferramenta normal
2. bancada de leitura assistida
3. e uma bancada do meio que explica como as duas conversam

## O que ficou canonico

Use estes caminhos em codigo novo:

1. `catalog.finance_snapshot.traditional` para fatos, metricas, comparativos e carteira
2. `catalog.finance_snapshot.ai` para analytics, scoring, timing, recommendation e churn foundation
3. `catalog.finance_snapshot.hybrid` para a ponte entre leitura factual e assistida

Contratos que devem permanecer estaveis:

1. `build_finance_snapshot(...)`
2. `build_finance_flow_bridge(...)`
3. payload com `finance_mode_contract`
4. payload com `page.behavior.active_mode`

## O que ainda e ponte

Estes arquivos continuam existindo, mas agora sao somente fachadas finas de compatibilidade:

1. [base.py](../../catalog/finance_snapshot/base.py)
2. [comparison.py](../../catalog/finance_snapshot/comparison.py)
3. [metrics.py](../../catalog/finance_snapshot/metrics.py)
4. [portfolio.py](../../catalog/finance_snapshot/portfolio.py)
5. [churn_foundation.py](../../catalog/finance_snapshot/churn_foundation.py)
6. [follow_up_analytics.py](../../catalog/finance_snapshot/follow_up_analytics.py)

Regra pratica:

1. nao abrir import novo nessas fachadas
2. manter enquanto elas ainda protegem consumidores antigos
3. tratar como corredor lateral, nao como entrada principal

## Gatilho real para remover as pontes

So remover essas fachadas quando os tres sinais acontecerem juntos:

1. busca recursiva sem consumidores relevantes nos caminhos antigos
2. presenters, docs e testes usando apenas imports canonicos
3. suite focada do financeiro verde apos a remocao

Checklist curto:

1. `rg "catalog\\.finance_snapshot\\.(base|comparison|metrics|portfolio|churn_foundation|follow_up_analytics)"`
2. validar imports internos e docs
3. rodar testes de financeiro e payload

## Leitura final

O split nao esta mais "em obra". Ele ja virou fundacao governavel.

Traducao para uma crianca de 6 anos:

1. antes a casa tinha porta nova e porta velha sendo usadas ao mesmo tempo
2. agora todo mundo importante ja entra pela porta nova
3. a porta velha continua ali so para garantir que ninguem fique preso do lado de fora
4. quando a gente tiver certeza de que ninguem mais usa a porta velha, ela pode ser retirada sem susto
