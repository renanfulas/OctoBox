# Student Financial Workspace Refinement C.O.R.D.A.

**Status**: Draft
**Created On**: 2026-03-30
**Decision**: Proposed north star for the next OctoBOX internal workspace refinement phase

## Contexto

O OctoBOX acabou de atravessar uma fase forte de refinamento da fachada. `students`, `finance` e `reports-hub` agora comunicam melhor proposito, prioridade e proxima acao. A porta da casa ficou boa.

Mas, ao entrar mais fundo na operacao, ainda existe contraste visivel:

1. a ficha do aluno e o seu miolo financeiro ainda carregam sinais de obra
2. alguns templates internos ainda dependem de inline style, markup torto ou linguagem envelhecida
3. certas superficies mais densas ainda passam mais sensacao de "sistema acumulado" do que de produto calmo

Em linguagem simples:

- a recepcao da casa ficou bonita
- mas o escritorio interno e o armario do caixa ainda pedem curadoria

Este plano usa como norte:

1. `docs/experience/front-display-wall.md`
2. `docs/experience/layout-decision-guide.md`
3. `.specs/codebase/CONVENTIONS.md`
4. `.specs/codebase/CONCERNS.md`
5. `.specs/features/front-display-wall-refinement/corda-plan.md`

---

## Objetivo

Levar a mesma qualidade de leitura, calma e confianca da fachada para o espaco interno mais sensivel da operacao:

1. ficha do aluno
2. overview financeiro do aluno
3. miolo financeiro residual que ainda destoa da nova linguagem

Objetivo operacional:

1. reduzir ruido visual, inline debt e markup quebrado nos fluxos internos
2. tornar a ficha do aluno mais legivel e menos cansativa
3. fazer o workspace financeiro interno soar como produto atual, nao como legado em uso
4. reforcar acessibilidade, hierarquia e confianca em acoes sensiveis

Objetivo de produto:

1. quem entra na ficha do aluno nao pode sentir que saiu de um produto bom e caiu num sistema antigo
2. a operacao financeira precisa parecer segura, clara e guiada
3. o produto precisa continuar coerente mesmo quando a pessoa entra nas areas mais densas

---

## Riscos

### 1. Risco de contraste interno

Se a fachada parece premium e o miolo parece improvisado, a confianca cai no segundo clique.

Traducao:

- o lobby impressiona
- a sala de reuniao decepciona

### 2. Risco de reconstruir demais

Se tentarmos redesenhar todos os fluxos de aluno e financeiro de uma vez, abrimos frente demais e geramos debito tecnico novo.

### 3. Risco de mexer em superficies sensiveis

Ficha do aluno e financeiro profundo mexem com:

1. cobranca
2. matricula
3. historico
4. status
5. locks de edicao

Qualquer refino precisa preservar o contrato funcional.

### 4. Risco de esconder tensao real

Se a tela ficar mais bonita, mas continuar sem hierarquia clara para acoes sensiveis, vira maquiagem.

### 5. Risco de manter divida invisivel

Inline style, inline script, encoding ruim e markup fragil nao aparecem sempre em print bonito, mas cobram juros no futuro.

---

## Direcao

### Regra-mestra

**Patch forte nas superficies internas, com reconstrucao local apenas quando o contrato atual estiver claramente subdimensionado.**

Ou seja:

1. nao reabrir arquitetura de dominio
2. nao reescrever os fluxos por vaidade
3. limpar, reorganizar e fortalecer onde a experiencia ainda denuncia idade

### Norte visual

O espaco interno deve seguir:

1. `Luxo Discreto`
2. `O Silencio Que Acolhe`
3. prioridade, seguranca e proxima acao como linguagem visivel

### Norte tecnico

1. remover inline debt das superficies mais sensiveis
2. corrigir markup quebrado antes de embelezar
3. preservar hooks, formularios e comportamento atual
4. manter JS vanilla-first com IDs e `data-*` estaveis

### Norte de experiencia

Cada workspace interno precisa responder rapido:

1. o que eu estou editando?
2. o que esta saudavel?
3. o que exige cuidado agora?
4. o que acontece se eu agir daqui?

---

## Acoes

## Onda 1. Integridade e Higiene Interna

Objetivo:
tirar os defeitos que fazem o interior parecer improvisado.

Inclui:

1. corrigir markup quebrado residual no financeiro
2. identificar e reduzir inline style/JS dominantes
3. limpar texto com encoding ruim nas superficies-alvo
4. preservar paridade funcional

Resultado esperado:

1. menos cheiro de obra no miolo
2. menos risco de regressao futura
3. base mais segura para lapidacao visual

---

## Onda 2. Hierarquia da Ficha do Aluno

Objetivo:
fazer a ficha do aluno parecer um workspace guiado, nao uma pilha de secoes.

Inclui:

1. reforcar a camada superior da ficha
2. organizar melhor o salto entre formulario essencial e financeiro
3. tornar o resumo financeiro mais legivel no primeiro olhar
4. reduzir cansaco cognitivo em blocos densos

Resultado esperado:

1. o usuario entende melhor onde esta
2. a ficha passa seguranca
3. o fluxo parece mais moderno e menos acumulado

---

## Onda 3. Miolo Financeiro com Calma e Controle

Objetivo:
alinhar os boards e historicos financeiros internos com a nova linguagem do produto.

Inclui:

1. refinar `movements.html`
2. refinar boards residuais como `portfolio_board.html`
3. melhorar copy, semantica e leitura em blocos de historico
4. tornar estados vazios e pressao financeira mais elegantes e claros

Resultado esperado:

1. leitura financeira mais serena
2. menos ruido visual
3. melhor continuidade com o front refinado

---

## Onda 4. Confianca de Interacao

Objetivo:
garantir que o espaco interno nao seja so bonito, mas confiavel de operar.

Inclui:

1. foco visivel e navegacao por teclado onde fizer sentido
2. feedback acessivel em acoes sensiveis
3. estados de lock e mudanca com contrato mais claro
4. reforco da semantica nos blocos internos

Resultado esperado:

1. mais previsibilidade
2. mais confianca em uso prolongado
3. menos dependencia de mouse e intuicao implicita

---

## Prioridade de Execucao

1. Onda 1 - Integridade e Higiene Interna
2. Onda 2 - Hierarquia da Ficha do Aluno
3. Onda 3 - Miolo Financeiro com Calma e Controle
4. Onda 4 - Confianca de Interacao

---

## Criterio de Aceite

Consideramos esta fase bem sucedida quando:

1. a ficha do aluno parece parte natural do produto refinado
2. o overview financeiro do aluno ficou mais legivel e menos cansativo
3. o miolo financeiro residual nao denuncia legado de forma dominante
4. markup quebrado, encoding ruim e inline debt principal deixam de liderar a experiencia
5. a operacao sensivel continua funcional e mais confiavel

---

## Resumo Executivo

Se eu resumir o plano inteiro em uma frase:

**vamos levar o mesmo cuidado da vitrine para dentro da sala de operacao, para que o OctoBOX continue parecendo produto premium mesmo quando o usuario entra nos fluxos mais densos.**
