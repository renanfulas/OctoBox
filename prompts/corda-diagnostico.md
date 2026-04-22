<!--
ARQUIVO: prompt de pre-diagnostico para montar C.O.R.D.A no OctoBOX.

POR QUE ELE EXISTE:
- permite conversar com a IA de forma solta antes de preencher o C.O.R.D.A.
- reduz o esforco de transformar intuicao crua em prompt operacional.

O QUE ESTE ARQUIVO FAZ:
1. recebe uma descricao informal do problema ou objetivo.
2. consulta a logica de `prompts/corda-fast.md`.
3. devolve um diagnostico pronto para preencher `prompts/corda.md`.

PONTOS CRITICOS:
- este prompt deve organizar o pensamento, nao tomar decisoes sem evidencia.
- se a tarefa estiver vaga, a resposta deve marcar as lacunas e nao fingir certeza.
-->

# C.O.R.D.A Diagnostico

Use este prompt quando voce ainda estiver pensando em voz alta e quiser que a IA organize a tarefa antes de montar o `C.O.R.D.A`.

Ele serve para o momento em que sua cabeca esta assim:

- "acho que preciso mexer em Celery"
- "quero melhorar cache"
- "parece que o banco pode ficar melhor"
- "nao sei ainda se isso e arquitetura, debug ou refator"

Pense nele como um tradutor entre intuicao e engenharia.

## Como usar

Voce so precisa escrever algo curto assim:

```md
Ideia crua:
Olha, preciso mexer no Celery porque quero que o cache melhore na estrutura do banco de dados.

Observacoes:
- ainda nao sei se isso e arquitetura, performance ou refator
- quero evitar retrabalho
- nao quero quebrar o que ja funciona
```

Depois cole o prompt abaixo.

## Prompt pronto para colar

```md
Voce vai atuar como diagnostico de prompts do OctoBOX.

Sua funcao nao e resolver o problema ainda.
Sua funcao e pegar minha ideia crua, verificar a logica de `prompts/corda-fast.md`, e montar um diagnostico operacional para que depois possamos preencher `prompts/corda.md` da forma certa.

Regras:
- responda em Portugues do Brasil
- primeiro pense no contexto do OctoBOX, nao em resposta generica
- considere os docs e a filosofia do projeto: corredor oficial, center layer, signal mesh, comportamento antes de cosmetica, evidencia antes de chute
- nao invente certeza quando eu estiver sendo vago
- se faltarem dados, marque claramente como `Lacuna`
- se houver confusao entre problema tecnico e solucao prematura, aponte isso
- diga se a minha ideia parece sintoma, causa raiz, estrategia ou implementacao
- use `prompts/corda-fast.md` como referencia de estrutura

Quero que voce entregue a resposta exatamente nesta ordem:

1. `Leitura da ideia crua`
2. `O que parece problema real`
3. `O que parece solucao prematura`
4. `Tipo mais provavel`
   - debug, refactor, frontend, architecture, review ou research
5. `Modo mais provavel`
   - Fast ou Planning
6. `Arquivos e areas que provavelmente entram`
7. `O que nao pode quebrar`
8. `Lacunas que precisamos preencher`
9. `Rascunho de C.O.R.D.A`
10. `Prompt-base recomendado`
11. `Versao curta para eu reaproveitar`

No item `Rascunho de C.O.R.D.A`, use exatamente este formato:

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

Minha ideia crua:
[cole aqui]

Observacoes:
[cole aqui]
```

## Exemplo de uso

```md
Minha ideia crua:
Olha, preciso mexer no Celery porque quero que o cache melhore na estrutura do banco de dados.

Observacoes:
- ainda nao sei se isso e arquitetura, performance ou refator
- quero evitar retrabalho
- nao quero quebrar o que ja funciona
```

## O que este prompt faz bem

- organiza pensamento vago
- separa problema de solucao prematura
- te diz qual prompt-base usar
- te entrega um rascunho pronto de C.O.R.D.A

## Regra de ouro

Quando sua ideia ainda estiver nebulosa, nao comece pelo prompt final.
Comece por este diagnostico.

E a diferenca entre dizer "quero construir alguma coisa aqui" e primeiro chamar um arquiteto para olhar o terreno, a fundacao e o peso da obra.
