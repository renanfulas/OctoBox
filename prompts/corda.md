<!--
ARQUIVO: framework mestre C.O.R.D.A para prompts do OctoBOX.

POR QUE ELE EXISTE:
- padroniza a montagem de prompts com contexto suficiente e validacao forte.
- transforma intuicao boa em processo repetivel.

O QUE ESTE ARQUIVO FAZ:
1. define o significado de C.O.R.D.A.
2. mostra como preencher cada parte.
3. oferece um template pronto para qualquer tarefa importante.

PONTOS CRITICOS:
- se o contexto ficar fraco, a IA improvisa.
- se a auditoria ficar fraca, a IA pode soar convincente e ainda assim errar.
-->

# C.O.R.D.A

`C.O.R.D.A` e o framework mestre para montar prompts no OctoBOX.

Pense nele como o cinto de seguranca da conversa com a IA:

- ele prende o contexto
- evita curva brusca sem controle
- e ajuda a chegar rapido sem sair da pista

## Contexto

Explique o que a IA precisa saber antes de agir.

Inclua:

- objetivo de negocio
- fase atual do produto
- arquivos, docs e skills relevantes
- fluxo real envolvido
- ambiente, restricoes e risco de mexer

Perguntas-guia:

- em que parte do predio arquitetural essa tarefa mora?
- qual fluxo real do usuario ou da operacao esta em jogo?
- quais arquivos e docs nao podem ser ignorados?

## Objetivo

Defina com precisao o que a IA precisa resolver agora.

Boa formula:

- `resolver X sem quebrar Y`
- `diagnosticar X e provar a causa raiz`
- `refatorar X preservando o contrato Y`

Evite objetivo fofo ou vago como:

- `melhorar`
- `deixar mais bonito`
- `dar uma organizada`

## Restricoes

Diga o que a IA nao pode fazer.

Inclua:

- o que nao pode quebrar
- o que nao pode ser reescrito
- limite de escopo
- regras de stack
- nivel de risco aceitavel
- exigencia de citar arquivos, linhas e evidencias quando for caso

Exemplos bons:

- nao transformar isso em SPA
- nao reescrever modulo inteiro
- nao inventar dependencias novas sem necessidade
- nao concluir sem validacao objetiva

## Definition of done

Defina como saber que a tarefa ficou pronta.

Inclua criterios observaveis:

- comando passa
- teste smoke passa
- tela carrega sem erro
- contrato fica mais claro
- asset deixa de dar 404
- causa raiz fica comprovada

Boa regra:

se uma crianca de 6 anos pudesse olhar e perguntar "como voce sabe que terminou?", a resposta precisa ser concreta.

## Auditoria

Defina como checar que a IA nao alucinou.

Inclua:

- pedir arquivos reais e, quando possivel, linhas
- separar fato de hipotese
- exigir validacao
- explicitar suposicoes
- pedir riscos e impacto
- pedir o que faltou para ter 100 por cento de confianca

## Template mestre

Copie, preencha e use este molde:

```md
Contexto:
- Projeto: OctoBOX
- Fase atual:
- Fluxo afetado:
- Arquivos relevantes:
- Docs obrigatorios:
- Skills de apoio:
- Restricoes reais:

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
```

## Regra de ouro

Prompt bom nao e o que parece inteligente.
Prompt bom e o que faz a IA trabalhar dentro de um trilho claro, com contexto suficiente, limite explicito e auditoria forte.
