<!--
ARQUIVO: diario operacional de uso e evolucao de prompts do OctoBOX.

POR QUE ELE EXISTE:
- transforma o uso da IA em pratica mensuravel e repetivel.
- evita confiar apenas na memoria ou na sensacao de que um prompt "pareceu bom".

O QUE ESTE ARQUIVO FAZ:
1. registra cada tarefa relevante executada com IA.
2. mede resultado, custo, retrabalho e qualidade do prompt.
3. converte erros e acertos em melhoria de sistema.

PONTOS CRITICOS:
- se este diario nao for alimentado, a biblioteca de prompts perde poder de evolucao.
- registre o suficiente para aprender, sem transformar isso em burocracia pesada.
-->

# Prompt Journal

Este arquivo e o painel de bordo da sua operacao de AI Engineering.

Em linguagem simples:

- o prompt e a jogada
- o journal e o replay da jogada
- sem replay, voce lembra da emocao
- com replay, voce aprende o padrao

## Quando registrar

Registre quando a tarefa for:

- importante
- repetivel
- cara em tokens
- dificil
- ou ensinar algo novo sobre como voce usa IA

Nao precisa registrar microtarefas triviais do tipo:

- trocar um texto pequeno
- ajustar um espacamento isolado
- renomear uma variavel simples

## Objetivo do journal

Voce vai usar este diario para responder perguntas como:

- qual prompt funciona melhor para debug?
- onde eu gasto tokens demais?
- qual tipo de tarefa acerta de primeira?
- onde a IA alucina mais?
- qual modelo combina melhor com qual problema?
- quais guardrails eu preciso adicionar?

## Template de entrada por tarefa

Copie este bloco e preencha a cada tarefa relevante:

```md
## Entrada: AAAA-MM-DD - Nome curto da tarefa

### 1. Identificacao
- Tipo: debug | refactor | frontend | architecture | review | research
- Modo: Fast | Planning
- Modelo:
- Fluxo afetado:

### 2. Tarefa
- Descricao curta:
- Objetivo real:
- O que nao podia quebrar:

### 3. Prompting
- Workflow usado:
  - orquestrador-total | corda-diagnostico | corda-fast | corda manual
- Prompt-base usado:
- Checklist usado:
- G.E.N.I.O. aplicado? sim | nao

### 4. Contexto enviado
- Arquivos principais:
- Docs citados:
- Skills citados:
- Lacunas de contexto:

### 5. Resultado
- Saiu bom de primeira? sim | nao | parcialmente
- O que acertou:
- O que errou:
- Houve alucinacao? sim | nao
- Houve ampliacao indevida de escopo? sim | nao

### 6. Custo e tempo
- Tempo total:
- Tokens aproximados:
- Numero de rodadas:

### 7. Validacao
- Como validei:
- Passou no checklist? sim | nao | parcial
- Grau de confianca final: baixo | medio | alto

### 8. Aprendizado
- O que este caso ensinou:
- O que devo mudar no prompt:
- O que vira guardrail:
- O que virou padrao reutilizavel:
```

## Template diario de 60-90 min

Se voce quiser operar isso como treino diario, use:

```md
# Sessao: AAAA-MM-DD

- Tarefa escolhida:
- Tipo:
- Prompt-base:
- Modelo e modo:

## Antes
- Minha hipotese inicial:
- Meu risco principal:

## Durante
- Onde a IA ajudou bem:
- Onde ela derrapou:

## Depois
- Resultado final:
- O que aprendi:
- O que vou ajustar na biblioteca:
```

## Template semanal de retro

No fim da semana, responda:

```md
# Retro semanal: AAAA-MM-DD

## Volume
- Tarefas registradas:
- Tipos de tarefa mais comuns:

## Qualidade
- First-pass success rate:
- Revisoes medias por tarefa:
- Tokens medios por tarefa simples:
- Tempo medio ate causa raiz:
- Taxa de reuso de prompt:

## Leitura honesta
- Onde fui muito bem:
- Onde desperdicei tokens:
- Onde escolhi modelo errado:
- Onde faltou contexto:
- Onde o checklist me salvou:

## Ajustes da proxima semana
- Prompt para melhorar:
- Workflow para simplificar:
- Guardrail novo:
- Tarefa benchmark para repetir:
```

## Como medir sem enlouquecer

Voce nao precisa virar contador de token em cada respiracao.

Use estas regras praticas:

- tarefa pequena: estimativa simples
- tarefa media ou cara: anote token aproximado
- tarefa repetivel: compare entre execucoes

O objetivo nao e perfeicao estatistica.
O objetivo e detectar padrao.

## Metricas principais

Estas metricas conversam com [`mer.md`](./mer.md):

- `first-pass success rate`
- `revisoes por tarefa`
- `tokens por tarefa simples`
- `tempo ate causa raiz no debug`
- `taxa de reuso de prompt`

## Como transformar erro em sistema

Quando algo der errado, classifique:

- `erro de contexto`
  voce mandou pouca informacao
- `erro de classificacao`
  escolheu o prompt-base errado
- `erro de escopo`
  a IA abriu demais a tarefa
- `erro de auditoria`
  faltou pedir evidencia ou validacao
- `erro de modelo`
  usou modo ou modelo fraco para tarefa critica

Cada erro deve gerar pelo menos um destes resultados:

- melhorar prompt
- melhorar checklist
- melhorar workflow
- melhorar criterio de roteamento

## Regra de ouro

Nao registre para guardar historico.
Registre para criar alavanca.

Se o journal nao mudar sua proxima decisao, ele virou diario bonito em vez de sistema de evolucao.
