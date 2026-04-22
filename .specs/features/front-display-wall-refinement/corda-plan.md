# Front Display Wall Refinement C.O.R.D.A.

**Status**: Approved
**Approved On**: 2026-03-29
**Decision**: Official north star for the current OctoBOX UI/UX refinement phase

## Contexto

O OctoBOX ja saiu da fase em que o maior risco era quebrar layout ou travar a operacao basica. A base visual principal existe, a navegacao central esta de pe, e as superficies `students`, `finance` e `reports-hub` ja funcionam como produto utilizavel.

O problema agora e mais sofisticado:

1. a fachada ainda mostra sinais de obra
2. a hierarquia da leitura ainda nao conduz tao bem quanto deveria
3. a experiencia ainda carrega pequenos bugs e dividas visiveis
4. algumas telas entregam informacao, mas ainda nao entregam presenca e decisao com a forca pedida pela Front Display Wall

Em linguagem simples:

- a casa esta pronta para morar
- mas a entrada principal ainda nao tem o impacto, a calma e a clareza de uma casa de alto padrao

Este plano usa como norte:

1. `docs/experience/front-display-wall.md`
2. `docs/experience/layout-decision-guide.md`
3. `.specs/codebase/CONVENTIONS.md`
4. `.specs/codebase/CONCERNS.md`
5. `.specs/features/front-display-wall-refinement/spec.md`
6. `.specs/features/front-display-wall-refinement/design.md`
7. `.specs/features/front-display-wall-refinement/tasks.md`

---

## Objetivo

Refinar a fachada principal do OctoBOX para que as superfices centrais parecam:

1. simples
2. rapidas
3. bonitas
4. faceis
5. intuitivas

sem reabrir a arquitetura do produto e sem criar debito tecnico inutil.

Objetivo operacional:

1. fazer `students`, `finance` e `reports-hub` comunicarem proposito, pressao atual e proxima acao logo no topo
2. remover sinais visiveis de obra, bugs frontais e ruido estrutural
3. aumentar velocidade percebida e clareza de uso
4. reforcar acessibilidade, confianca e continuidade visual

Objetivo de produto:

1. o usuario precisa bater o olho e entender a tela
2. o usuario precisa sentir que o sistema esta pronto
3. o usuario precisa querer continuar usando

---

## Riscos

### 1. Risco de maquiagem sem verdade

Se deixarmos a tela mais bonita, mas sem destacar o que esta pressionado e o que pede acao agora, a fachada vira cenografia vazia.

Traducao:

- fica bonita no screenshot
- falha no uso real

### 2. Risco de reconstruir demais

Se tentarmos reescrever a frente inteira, vamos gastar energia demais, tocar backend sem necessidade e criar debito tecnico novo.

Traducao:

- trocar o piso inteiro quando bastava alinhar a porta, pintar a parede e esconder os fios

### 3. Risco de ruído de obra continuar dominante

Se mantivermos copy de transicao, estilos inline, JS inline, markup torto e CTAs confusos, a frente continua com cheiro de canteiro.

### 4. Risco de latencia percebida

Mesmo sem erro tecnico, telas muito densas ou carregadas de uma vez parecem lentas e cansativas.

### 5. Risco de quebrar operacao ao mexer na fachada

`students` e `finance` nao sao landing pages; sao areas vivas de uso operacional. Qualquer refinamento precisa preservar:

1. filtros
2. bulk actions
3. tabs
4. permissoes
5. fluxo atual

### 6. Risco de acessibilidade continuar secundaria

Se a gente depender so de clique em linha inteira, scripts inline e feedback visual implicito, o produto parece bom para mouse, mas nao para uso robusto.

---

## Direcao

### Regra-mestra

**Patch forte, reconstrucao local apenas quando a fachada atual for insuficiente.**

Ou seja:

1. nao vamos demolir
2. vamos lapidar duro
3. so reconstruimos parcialmente onde a camada superior estiver claramente fraca

### Norte visual

A frente do produto deve seguir:

1. `Luxo Discreto`
2. `O Silencio Que Acolhe`
3. prioridade, pendencia e proxima acao como verdade central

### Norte tecnico

1. tirar inline CSS/JS da fachada principal
2. corrigir bugs e markup antes de mexer em presenca visual
3. manter a arquitetura modular atual
4. preservar o backend de export e esconder apenas os comandos visuais durante esta fase

### Norte de experiencia

Cada tela principal precisa responder rapidamente:

1. o que esta acontecendo aqui?
2. o que esta bem?
3. o que esta pressionado?
4. o que eu faco agora?

Se a tela nao responde isso em poucos segundos, a Front Display Wall ainda nao aterrissou.

---

## Acoes

## Onda 1. Integridade e Higiene

Objetivo:
tirar os defeitos que deixam a fachada parecer improvisada.

Inclui:

1. corrigir contrato do import de alunos
2. corrigir fechamento semantico da fila financeira
3. extrair inline CSS/JS das superficies principais
4. preservar comportamento atual com hooks estaveis

Resultado esperado:

1. menos debito tecnico visivel
2. menos risco de regressao visual
3. base mais limpa para a lapidacao seguinte

---

## Onda 2. Camada de Comando da Fachada

Objetivo:
fazer o topo de cada superficie parecer um centro de decisao, nao um cabecalho correto.

Superficies:

1. `students`
2. `finance`
3. `reports-hub`

Inclui:

1. criar ou reforcar uma camada superior que diga o papel da tela
2. explicitar o que esta pressionado e o que pede acao agora
3. alinhar hero, notices e CTA principal
4. reduzir linguagem de obra ou placeholder

Resultado esperado:

1. o usuario entende a tela mais rapido
2. a tela parece produto, nao painel tecnico
3. cada superficie ganha massa visual e editorial propria

---

## Onda 3. Ritmo, Voz e Continuidade

Objetivo:
fazer as telas parecerem partes do mesmo edificio visual.

Inclui:

1. alinhar copy entre `students`, `finance` e `reports-hub`
2. aplicar mais claramente o tom `O Silencio Que Acolhe`
3. reduzir comandos gritados e microcopy burocratica
4. reforcar pertencimento e calma operacional

Resultado esperado:

1. produto com voz unica
2. menos cansaco visual e cognitivo
3. maior confianca emocional no uso

---

## Onda 4. Velocidade Percebida

Objetivo:
fazer a experiencia parecer mais leve e mais instantanea.

Inclui:

1. staged loading ou deferencia controlada no financeiro
2. reduzir densidade inicial em `students`
3. revisar pontos de peso desnecessario na primeira dobra
4. preparar terreno para snapshots/cache onde houver ROI alto

Resultado esperado:

1. primeiro frame mais leve
2. menos sensacao de parede pesada de dados
3. mais fluidez no uso

---

## Onda 5. Acessibilidade e Confianca de Interacao

Objetivo:
garantir que a fachada nao seja apenas bonita, mas confiavel de operar.

Inclui:

1. foco mais claro
2. semantica mais robusta
3. resumo de filtros com contrato acessivel
4. menos dependencia de clique em linha inteira
5. melhoria progressiva dos contratos de interacao

Resultado esperado:

1. experiencia mais robusta
2. menos ambiguidade de uso
3. mais confianca para uso prolongado

---

## Prioridade de Execucao

1. Onda 1 - Integridade e Higiene
2. Onda 2 - Camada de Comando da Fachada
3. Onda 3 - Ritmo, Voz e Continuidade
4. Onda 4 - Velocidade Percebida
5. Onda 5 - Acessibilidade e Confianca de Interacao

---

## Critério de Aceite

Consideramos esta fase bem sucedida quando:

1. `students`, `finance` e `reports-hub` parecem claramente partes do mesmo produto
2. o topo dessas paginas comunica proposito e proxima acao sem exigir leitura profunda
3. os bugs frontais mais feios deixam de existir
4. a interface perde cheiro de obra e ganha cheiro de produto consolidado
5. a experiencia parece mais leve, mais calma e mais confiavel

---

## Decisao Estrategica

Durante esta fase:

1. os comandos visuais de CSV/PDF continuam fora da fachada principal
2. a infraestrutura backend continua preservada
3. so reativamos esses comandos no fechamento operacional certo

Isso evita poluir a frente com ferramentas de deposito enquanto estamos refinando a sala principal.

---

## Resumo Executivo

Se eu resumir o plano inteiro em uma frase:

**vamos tirar o cheiro de obra da fachada, reforcar o centro de decisao de cada tela e fazer o OctoBOX parecer tao bom quanto ja esta por dentro.**
