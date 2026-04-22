# Premium Legacy Islands Cleanup C.O.R.D.A.

**Status**: Approved
**Created On**: 2026-03-30
**Approved On**: 2026-03-30
**Decision**: Official north star for the next post-governance refinement mountain

## Contexto

O OctoBOX acabou de atravessar a unificacao do tema canonico. Isso resolveu a soberania de:

1. tokens
2. cards e surfaces
3. hero
4. notice/banner
5. topbar

O predio principal agora ja parece do mesmo arquiteto.

Mas a varredura visual curta apos a governanca mostrou que ainda existem ilhas premium legadas muito evidentes:

1. `advisor_narrative.html`
2. `advisor_manifesto_modal.html`
3. `finance hero` e `movements`
4. o miolo financeiro do aluno com `elite-glass-card` e `glass-panel-elite`

Em linguagem simples:

- a cidade agora tem uma prefeitura central
- mas ainda existem alguns bairros nobres usando lei antiga

Este plano usa como norte:

1. `docs/experience/front-display-wall.md`
2. `docs/experience/css-guide.md`
3. `.specs/codebase/CONVENTIONS.md`
4. `.specs/codebase/CONCERNS.md`
5. `.specs/features/canonical-theme-unification/corda-plan.md`

---

## Objetivo

Absorver as ultimas ilhas premium legadas no tema canonico sem perder:

1. identidade premium
2. leitura clara
3. confianca operacional
4. velocidade de manutencao

Objetivo operacional:

1. remover inline style e inline script dominantes das ilhas-alvo
2. aposentar `elite-glass-card` e `glass-panel-elite` como soberania visual nessas areas
3. fazer advisor, financeiro e ficha financeira falarem a mesma lingua do tema canonico
4. reduzir o contraste entre a fachada refinada e os nucleos internos restantes

Objetivo de produto:

1. nao deixar nenhum bloco importante soar como produto de outra epoca
2. manter o dark premium aberto, respiravel e ajustavel
3. fazer o app parecer um sistema unico, nao uma colagem de vitorias locais

---

## Riscos

### 1. Risco de mexer em ilhas sensiveis sem mapa

Essas ilhas parecem cosmeticas, mas algumas carregam:

1. interacao
2. modal
3. estados financeiros
4. leitura gerencial

Se entrarmos sem plano, podemos trocar o lustre e quebrar o interruptor.

### 2. Risco de nivelar por baixo

Se a gente matar o dialeto premium do jeito errado, o app pode perder presenca e personalidade.

O alvo nao e deixar tudo igual e sem vida.
O alvo e deixar tudo coerente.

### 3. Risco de abrir uma reforma grande demais

Essa fase nao pode virar:

1. rebuild do dashboard inteiro
2. rebuild do financeiro inteiro
3. rebuild da ficha inteira

Ela precisa agir nas ilhas onde o contraste ainda grita.

### 4. Risco de manter debito invisivel

Inline style, inline script, encoding ruim e classes paralelas parecem pequenas coisas.
Mas sao como fiacao exposta dentro da parede.

---

## Direcao

### Regra-mestra

**Aposentar ilhas premium legadas por absorcao controlada no tema canonico.**

Ou seja:

1. migrar para `card`, `hero`, `notice-panel` e tokens canonicos
2. preservar o brilho premium como acabamento local, nao como sistema paralelo
3. mover comportamento para CSS e JS oficiais quando ainda estiver preso em template

### Norte visual

As ilhas tocadas devem soar como:

1. dark premium aberto
2. profundo sem ser claustrofobico
3. elegante sem parecer decoracao de showroom

### Norte tecnico

1. reduzir inline debt dominante
2. diminuir classes soberanas legadas
3. estabilizar markup e hooks
4. manter o comportamento funcional intacto

### Norte de experiencia

Ao abrir essas areas, o usuario nao deve sentir:

1. quebra de epoca
2. mudanca de produto
3. tema paralelo

---

## Acoes

## Onda 1. Advisor Legacy Island Cleanup

Objetivo:
limpar o motor narrativo e o manifesto modal do dashboard advisor.

Inclui:

1. extrair inline style e inline script dominantes
2. alinhar o bloco ao hero canonico ou a uma variante oficial
3. transformar o modal numa superficie canonica e legivel
4. corrigir qualquer texto antigo, pesado ou com cara de experimento local

Resultado esperado:

1. advisor deixa de parecer um prototipo premium isolado
2. modal vira parte do sistema e nao um popup de outra era

---

## Onda 2. Finance Premium Surface Absorption

Objetivo:
absorver o hero e os movimentos financeiros residuais no tema canonico.

Inclui:

1. remover `glass-panel-elite` como autoridade da superficie
2. alinhar hero financeiro ao host canonico
3. alinhar `movements` a surfaces e notices canonicos
4. preservar leitura de pressao e movimento sem virar bloco apagado

Resultado esperado:

1. o financeiro fala a mesma lingua da governanca nova
2. o brilho premium fica como acabamento, nao como dialeto paralelo

---

## Onda 3. Student Financial Premium Legacy Retirement

Objetivo:
aposentar os ultimos dialetos premium antigos no workspace financeiro do aluno.

Inclui:

1. retirar `elite-glass-card`
2. retirar `glass-panel-elite`
3. alinhar ID card, KPIs, status e ledger ao card canonico
4. manter a sensacao de importancia e seguranca do espaco financeiro

Resultado esperado:

1. o workspace financeiro do aluno passa a parecer nativo do tema atual
2. some o contraste entre a fachada refinada e o miolo premium antigo

---

## Onda 4. Final Visual Consistency Pass

Objetivo:
fazer uma passada curta nas areas tocadas para eliminar o que sobrar de conflito dominante.

Inclui:

1. revisar classes remanescentes
2. revisar qualquer helper legado ainda mandando no bloco
3. revisar copy e ritmo visual
4. confirmar que o premium virou acento, nao sistema concorrente

Resultado esperado:

1. uma linguagem unica
2. menos cheiro de remendo
3. menos risco de regressao visual futura

---

## Prioridade de Execucao

1. Onda 1 - Advisor Legacy Island Cleanup
2. Onda 2 - Finance Premium Surface Absorption
3. Onda 3 - Student Financial Premium Legacy Retirement
4. Onda 4 - Final Visual Consistency Pass
