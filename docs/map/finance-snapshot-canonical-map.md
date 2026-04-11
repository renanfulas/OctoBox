<!--
ARQUIVO: mapa canônico do snapshot financeiro após as ondas de split.

TIPO DE DOCUMENTO:
- mapa técnico de ownership

AUTORIDADE:
- média-alta para imports, ownership e manutenção da fundação financeira

DOCUMENTO PAI:
- [../plans/finance-ia-traditional-foundation-split-plan.md](../plans/finance-ia-traditional-foundation-split-plan.md)

QUANDO USAR:
- quando a dúvida for "de onde eu devo importar?"
- quando alguém encontrar fachadas antigas em `catalog/finance_snapshot`
- quando formos remover compatibilidade transitória no futuro
-->

# Finance Snapshot Canonical Map

Para leitura executiva curta, use tambem o checkpoint final em
[finance-architecture-checkpoint.md](./finance-architecture-checkpoint.md).

## Regra-mestra

Para desenvolvimento novo, use os namespaces canônicos:

1. `catalog.finance_snapshot.traditional`
2. `catalog.finance_snapshot.ai`
3. `catalog.finance_snapshot.hybrid`

As fachadas no raiz de `catalog.finance_snapshot` continuam existindo só para compatibilidade.

Em linguagem simples:

1. o bairro oficial agora tem nome
2. as ruas antigas ainda recebem carta
3. mas casa nova deve usar o endereço certo

## Ownership canônico

### Traditional

Use para leitura factual:

1. `catalog.finance_snapshot.traditional.base`
2. `catalog.finance_snapshot.traditional.comparison`
3. `catalog.finance_snapshot.traditional.metrics`
4. `catalog.finance_snapshot.traditional.portfolio`

Responsável por:

1. filtros
2. querysets factuais
3. métricas
4. comparativos
5. carteira

Não deve fazer:

1. score assistido
2. heurística de recomendação
3. bridge visual

### AI

Use para leitura assistida:

1. `catalog.finance_snapshot.ai.foundation`
2. `catalog.finance_snapshot.ai.analytics`
3. `catalog.finance_snapshot.ai.recommendation`
4. `catalog.finance_snapshot.ai.learning`
5. `catalog.finance_snapshot.ai.timing`
6. `catalog.finance_snapshot.ai.scoring`
7. `catalog.finance_snapshot.ai.facts`
8. `catalog.finance_snapshot.ai.common`

Responsável por:

1. analytics histórico
2. foundation de churn
3. timing
4. score
5. guidance contextual

Não deve fazer:

1. montar template
2. tomar conta de gráfico factual
3. virar verdade transacional

### Hybrid

Use para pontes entre fato e recomendação:

1. `catalog.finance_snapshot.hybrid.flow_bridge`

Responsável por:

1. handoff visual/operacional
2. superfície de transição entre leitura factual e assistida

## Fachadas transitórias

Estes arquivos continuam válidos, mas são compatibilidade:

1. [base.py](../../catalog/finance_snapshot/base.py)
2. [comparison.py](../../catalog/finance_snapshot/comparison.py)
3. [metrics.py](../../catalog/finance_snapshot/metrics.py)
4. [portfolio.py](../../catalog/finance_snapshot/portfolio.py)
5. [churn_foundation.py](../../catalog/finance_snapshot/churn_foundation.py)
6. [follow_up_analytics.py](../../catalog/finance_snapshot/follow_up_analytics.py)

Regra:

1. não abrir import novo apontando para essas fachadas
2. manter apenas para estabilidade de transição
3. remover só quando a busca recursiva mostrar que não há consumidores relevantes

## Imports recomendados

### Use

```python
from catalog.finance_snapshot.ai import build_financial_churn_foundation
from catalog.finance_snapshot.ai import build_finance_follow_up_analytics
from catalog.finance_snapshot.traditional import build_finance_metrics
from catalog.finance_snapshot.traditional import build_monthly_comparison
from catalog.finance_snapshot.hybrid import build_finance_flow_bridge
```

### Evite em código novo

```python
from catalog.finance_snapshot.follow_up_analytics import build_finance_follow_up_analytics
from catalog.finance_snapshot.churn_foundation import build_financial_churn_foundation
from catalog.finance_snapshot.metrics import build_finance_metrics
```

## Critério para remover compatibilidade depois

Só remover fachadas transitórias quando:

1. busca recursiva não encontrar consumidores reais
2. testes de financeiro continuarem verdes
3. docs e presenters já estiverem usando só os imports canônicos

Tradução prática:

1. primeiro todo mundo aprende a usar a porta da frente
2. depois a porta lateral pode sumir sem susto
