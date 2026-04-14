<!--
ARQUIVO: plano de split da fundacao do financeiro em camadas Tradicional, IA e Hibrida.

TIPO DE DOCUMENTO:
- plano estrutural de evolucao controlada

AUTORIDADE:
- media-alta para a frente de evolucao do financeiro

DOCUMENTO PAI:
- [finance-ml-foundation-refactor-watch-plan.md](finance-ml-foundation-refactor-watch-plan.md)

DOCUMENTOS IRMAOS:
- [../architecture/finance-churn-ml-foundation.md](../architecture/finance-churn-ml-foundation.md)
- [finance-visual-bridge-risk-inventory.md](finance-visual-bridge-risk-inventory.md)
- [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)

QUANDO USAR:
- quando a duvida for se a frente de IA do financeiro ja pede fundacao separada
- quando formos abrir novos indicadores, scores ou explicacoes assistidas
- quando precisarmos separar claramente apresentacao tradicional de leitura assistida

POR QUE ELE EXISTE:
- evita que a camada de IA cresca como remendo dentro do presenter principal
- protege o launch atual sem congelar a evolucao da frente financeira
- transforma a ideia "modo IA vs modo tradicional" em arquitetura executavel

PONTOS CRITICOS:
- este plano nao pede reescrever o financeiro inteiro agora
- o launch nao deve ser bloqueado por esta frente
- a assinatura publica do snapshot deve permanecer estavel durante a migracao
-->

# Finance IA/Tradicional Foundation Split Plan

## Resumo executivo

Decisao recomendada:

1. lancar o produto com a base atual
2. preparar imediatamente a fundacao de split para o financeiro
3. separar a evolucao futura em tres camadas:
   - `tradicional`
   - `ia`
   - `hibrida`

Em linguagem simples:

1. a operacao atual funciona
2. mas a mochila da IA ja esta ficando pesada demais num ombro so
3. entao vamos redistribuir o peso antes de continuar enchendo a mochila

## Diagnostico objetivo

Os pontos que mais concentram peso hoje sao:

1. [../../catalog/finance_snapshot/follow_up_analytics.py](../../catalog/finance_snapshot/follow_up_analytics.py)
2. [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. [../../catalog/finance_snapshot/churn_foundation.py](../../catalog/finance_snapshot/churn_foundation.py)

Leitura tecnica:

1. `snapshot.py` continua relativamente saudavel como orquestrador
2. o risco real esta no crescimento conjunto de:
   - analytics historico
   - heuristica
   - recomendacao
   - prioridade contextual
   - traducao de UI

Conclusao:

1. a base ainda aguenta
2. mas novos indicadores colocados direto nesses arquivos vao aumentar custo de manutencao, teste e explicacao

## Objetivo do split

Separar a frente financeira em contratos claros:

### 1. Camada Tradicional

Responde:

1. "o que aconteceu?"

Escopo:

1. metricas
2. movimentos
3. carteira
4. filtros
5. comparativos
6. fila factual

### 2. Camada IA

Responde:

1. "o que isso provavelmente significa e o que vale fazer agora?"

Escopo:

1. fundacao de churn
2. score assistido
3. analytics historico
4. recomendacao
5. prioridade contextual
6. explicacao de leitura assistida

### 3. Camada Hibrida

Responde:

1. "como mostrar lado a lado dado objetivo e leitura assistida sem confundir o usuario?"

Escopo:

1. boards hibridos
2. ponte visual entre tradicional e IA
3. labels de contraste entre fato e interpretacao
4. organizacao de apresentacao por modo

## CORDA refinado para esta frente

```text
You are a senior OctoBOX refactoring architect for financial intelligence foundations.

Mission:
Prepare and execute a controlled foundation split for the Finance surface so the product can support both Traditional mode and AI mode without increasing hidden technical debt.

Primary outcome:
Keep the current finance runtime stable while reorganizing the codebase into clear ownership layers for:
1. traditional financial reading
2. AI-assisted financial reading
3. hybrid presentation

Context:
- The current launch must not be blocked.
- The biggest concentration risks are in:
  - `catalog/finance_snapshot/follow_up_analytics.py`
  - `catalog/finance_snapshot/churn_foundation.py`
  - `catalog/presentation/finance_center_page.py`
- `catalog/finance_snapshot/snapshot.py` should remain a stable orchestration entry point.
- The user wants a future UI split between Traditional mode and AI mode, with a hybrid bridge that makes the difference visible.

Inputs:
- current finance snapshot modules
- current finance presenter modules
- watch plan in `docs/plans/finance-ml-foundation-refactor-watch-plan.md`
- current UI bridge and queue presentation contracts

Non-goals:
- do not redesign the full finance UI now
- do not rewrite the whole finance domain
- do not break launch readiness
- do not rename public snapshot entry points without a compatibility bridge

Constraints:
- preserve `build_finance_snapshot(...)` as public entry point during migration
- preserve stable payload contracts for active templates unless a compatibility bridge is added
- separate domain facts from heuristics from UI translation
- avoid moving presentation logic into analytics modules
- avoid moving heuristics into templates
- do not split by file size alone; split by responsibility

Required design:
Organize the target architecture into three layers:
1. `traditional`
2. `ai`
3. `hybrid`

For each layer, define:
- ownership
- allowed responsibilities
- forbidden responsibilities
- public builders
- migration path

Output format:
1. Current diagnosis
2. Target architecture
3. Module split proposal
4. Public contracts to freeze
5. Migration phases
6. Risks by phase
7. Verification plan
8. What can wait until after launch

Quality bar:
- no vague "refactor later" language
- every split must map to a real responsibility boundary
- migration must be incremental
- the runtime must stay shippable throughout

Fallback:
If a module is still too mixed to split immediately, classify it as transitional and define the exact trigger that will force the next split.
```

## Aplicacao do CORDA

### Arquitetura-alvo

Proposta de destino:

```text
catalog/
  finance_snapshot/
    traditional/
      base.py
      metrics.py
      portfolio.py
      comparison.py
      queue_facts.py
    ai/
      foundation.py
      scoring.py
      recommendation.py
      analytics.py
      learning.py
      timing.py
    hybrid/
      flow_bridge.py
      summary_bridge.py
      queue_bridge.py
    snapshot.py
```

```text
catalog/
  presentation/
    finance_center_page.py
    finance_traditional_page.py
    finance_ai_page.py
    finance_hybrid_page.py
    finance_risk_queue_page.py
```

### Ownership claro

#### Tradicional

Pode:

1. montar fatos
2. somar metricas
3. comparar periodos
4. organizar carteira e movimentos

Nao pode:

1. inventar score
2. decidir recomendacao
3. traduzir heuristica de IA para copy final

#### IA

Pode:

1. calcular score assistido
2. produzir recomendacao
3. medir historico
4. ajustar confianca
5. ajustar janela de acao
6. aprender com outcomes

Nao pode:

1. virar presenter
2. renderizar labels visuais finais
3. decidir composicao do board sozinho

#### Hibrida

Pode:

1. mostrar "dado observado" versus "leitura sugerida"
2. montar resumo visivel para o usuario
3. decidir a ordem de exibicao entre blocos tradicionais e IA

Nao pode:

1. recalcular score
2. redefinir heuristica
3. substituir o snapshot tradicional

## Split proposto por arquivo

### 1. `follow_up_analytics.py`

Estado:

1. grande demais
2. mistura historico, recomendacao, timing, divergencia e aprendizado

Split recomendado:

1. `ai/analytics.py`
   - agregacoes historicas base
2. `ai/scoring.py`
   - historical score map
   - queue assist score helpers
3. `ai/timing.py`
   - best action by timing
   - prediction window override
4. `ai/learning.py`
   - divergence matrices
   - turn recommendation learning
   - turn priority tension learning

### 2. `churn_foundation.py`

Estado:

1. ainda aceitavel
2. mas ja concentra regra base + override + ordenacao

Split recomendado:

1. manter um `foundation.py` como orquestrador da IA
2. mover blocos de decisao para:
   - `recommendation.py`
   - `scoring.py`
   - `timing.py`

### 3. `finance_center_page.py`

Estado:

1. presenter forte demais
2. mistura hero, ponte operacional, analytics board, risk queue e traducao de surfaces

Split recomendado:

1. `finance_traditional_page.py`
2. `finance_ai_page.py`
3. `finance_hybrid_page.py`
4. manter `finance_center_page.py` como composer principal e facade de compatibilidade

## Contratos publicos que devem congelar

Durante a migracao, nao quebrar:

1. `build_finance_snapshot(...)`
2. `build_finance_flow_bridge(...)`
3. payloads esperados pelos templates ativos
4. `build_finance_risk_queue(...)` enquanto a fila assistida continuar na UI atual

Regra:

1. reformar por dentro
2. manter a torneira no mesmo lugar por fora

## Fases de migracao

### Fase 0 - Launch protegido

1. nao bloquear release
2. documentar arquitetura-alvo
3. congelar contratos publicos

### Fase 1 - Split interno da IA

1. quebrar `follow_up_analytics.py`
2. manter imports de compatibilidade
3. cobrir com testes equivalentes

### Fase 2 - Split da apresentacao

1. extrair apresentacao tradicional
2. extrair apresentacao IA
3. criar camada hibrida
4. manter `finance_center_page.py` como fachada

### Fase 3 - Exposicao de modos

1. introduzir "modo tradicional"
2. introduzir "modo IA"
3. introduzir leitura hibrida lado a lado

### Fase 4 - Limpeza de compatibilidade

1. remover bridges antigas so depois de prova de uso estavel

## Riscos por fase

### Risco alto

1. misturar split tecnico com redesign total de UI
2. renomear contratos publicos cedo demais

### Risco medio

1. espalhar heuristica entre presenter e analytics ao mesmo tempo
2. duplicar logica temporariamente por muito tempo

### Risco baixo

1. criar novos modulos mantendo fachada publica estavel

## Verificacao

Cada fase deve provar:

1. snapshot continua estavel
2. presenter continua entregando o mesmo contrato visivel
3. testes de finance/churn/follow-up continuam verdes
4. nenhuma regra de IA migrou para template
5. nenhum fato tradicional passou a depender de heuristica de IA

## O que pode esperar para depois do launch

Pode esperar:

1. redesign visual completo do Financeiro
2. mudanca radical de naming da UI
3. remocao de todas as facades de compatibilidade

Nao deveria esperar:

1. o split de `follow_up_analytics.py`
2. a separacao explicita entre camada tradicional, IA e hibrida
3. o congelamento dos contratos publicos antes de novos indicadores grandes

## Decisao final

Decisao recomendada:

1. lancar agora
2. abrir imediatamente a fundacao de split
3. usar este plano como guia para evitar que o crescimento de IA force refactor traumatico depois

Em frase unica:

1. o Financeiro nao esta quebrado, mas ja merece trilho proprio para a parte assistida antes que novos indicadores transformem inteligencia em emaranhado.
