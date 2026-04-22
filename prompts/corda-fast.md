<!--
ARQUIVO: prompt rapido para montar C.O.R.D.A no OctoBOX.

POR QUE ELE EXISTE:
- reduz a friccao de escrever o C.O.R.D.A inteiro toda vez.
- transforma uma descricao curta da tarefa em um prompt estruturado e auditavel.

O QUE ESTE ARQUIVO FAZ:
1. recebe uma tarefa curta em linguagem natural.
2. expande essa tarefa para a estrutura completa de C.O.R.D.A.
3. sugere tipo de prompt, modo e pontos de risco para o OctoBOX.

PONTOS CRITICOS:
- este prompt deve acelerar a montagem, nao enfraquecer o contexto.
- se os campos vierem vagos, a resposta precisa assumir pouco e marcar as lacunas.
-->

# C.O.R.D.A Fast

Use este prompt quando voce quiser montar rapidamente um `C.O.R.D.A` sem digitar tudo manualmente.

## Como usar

Voce vai preencher so este bloco curto:

```md
Tarefa:

Tipo:
- debug | refactor | frontend | architecture | review | research

Fluxo afetado:

Arquivos relevantes:

Nao pode quebrar:

Escopo maximo:

Observacoes:
```

Depois cole o prompt abaixo na IA.

## Prompt pronto para colar

```md
Voce vai atuar como montador de prompts do OctoBOX.

Sua tarefa e pegar minha descricao curta e transformá-la em um C.O.R.D.A completo, enxuto e forte, pronto para eu usar com outro prompt especializado.

Regras:
- responda em Portugues do Brasil
- use o contexto real do OctoBOX
- respeite a filosofia dos docs do projeto: corredor oficial, center layer, signal mesh, front display wall, comportamento antes de cosmetica, evidencia antes de chute
- se faltarem dados, nao invente com excesso de confianca; preencha o minimo razoavel e marque `Assuncao`
- sugira o prompt-base ideal entre: architecture, debug, refactor, frontend, review, research
- sugira tambem o modo ideal: Fast ou Planning
- no final, entregue tambem uma versao ultra-curta de 1 bloco para eu reutilizar no futuro

Monte a resposta exatamente nesta estrutura:

1. `Tipo recomendado`
2. `Modo recomendado`
3. `C.O.R.D.A montado`
4. `Prompt-base para combinar`
5. `Riscos de usar um escopo maior do que o necessario`
6. `Versao ultra-curta reutilizavel`

O C.O.R.D.A deve sair neste formato:

Contexto:
- Projeto: OctoBOX
- Fase atual:
- Fluxo afetado:
- Arquivos relevantes:
- Docs obrigatorios:
- Skills de apoio:
- Restricoes reais:
- Assuncao:

Objetivo:
- Resolver exatamente:

Restricoes:
- Nao pode quebrar:
- Nao pode reescrever:
- Escopo maximo:
- Forma de resposta esperada:

Definition of done:
- O trabalho estara pronto quando:
- Validacao minima:

Auditoria:
- Cite arquivos e linhas quando houver.
- Separe fato, hipotese e inferencia.
- Diga riscos e impacto.
- Diga o que falta para fechar a confianca.

Aqui esta a minha descricao curta:

Tarefa:
[cole aqui]

Tipo:
[cole aqui]

Fluxo afetado:
[cole aqui]

Arquivos relevantes:
[cole aqui]

Nao pode quebrar:
[cole aqui]

Escopo maximo:
[cole aqui]

Observacoes:
[cole aqui]
```

## Exemplo real

```md
Tarefa:
Refatorar a pagina de financas para reduzir acoplamento entre presenter, template e CSS.

Tipo:
refactor

Fluxo afetado:
Central financeira do catalogo.

Arquivos relevantes:
- catalog/views/finance_views.py
- catalog/presentation/finance_center_page.py
- templates/catalog/finance.html
- static/css/catalog/finance.css
- static/css/design-system/financial.css

Nao pode quebrar:
- filtros
- exportacao CSV/PDF
- quick form de plano
- fila financeira

Escopo maximo:
view, presenter, template principal e assets da pagina.

Observacoes:
Quero preparar a area para crescer sem reescrever a stack.
```

## Regra pratica

Se voce estiver com preguica de escrever o C.O.R.D.A inteiro, use este arquivo como se fosse um molde de concreto:

- voce joga os ingredientes
- ele te devolve a forma pronta
- depois voce so encaixa o prompt-base certo
