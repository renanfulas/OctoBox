<!--
ARQUIVO: manual pessoal de decisao arquitetural do projeto.

TIPO DE DOCUMENTO:
- referencia de metodo

AUTORIDADE:
- media

DOCUMENTO PAI:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

QUANDO USAR:
- quando a duvida for qual metodo mental usar para tomar decisoes arquiteturais com clareza e repetibilidade

POR QUE ELE EXISTE:
- Registra em linguagem simples o jeito de decidir arquitetura que apareceu na evolucao do projeto.
- Permite reaplicar esse criterio em projetos futuros sem depender de memoria ou inspiracao do momento.

O QUE ESTE ARQUIVO FAZ:
1. traduz intuicao em metodo repetivel.
2. resume os principios que funcionaram bem aqui.
3. oferece um checklist curto para novas decisoes.

PONTOS CRITICOS:
- este documento deve continuar pratico e direto, nao virar teoria vazia.
- se o metodo evoluir, o texto precisa acompanhar a pratica real.
-->

# Manual do seu jeito de decidir arquitetura

Este documento existe para registrar uma coisa importante: voce nao precisou dominar todos os termos tecnicos para tomar varias decisoes certas.

O que apareceu no projeto foi um jeito de pensar baseado em:

1. fundamentos
2. logica
3. estrutura
4. clareza
5. intuicao boa sobre risco e organizacao

Isso nao e menor do que teoria. Na pratica, e assim que muita competencia real nasce.

## O seu padrao mental mais provavel

O que voce parece fazer sem perceber e isto:

1. percebe quando algo esta centralizado demais
2. percebe quando uma parte ficou confusa para crescer
3. prefere organizar por responsabilidade em vez de empilhar codigo
4. evita quebrar o que ja funciona so para parecer mais bonito
5. sente quando uma mudanca abre caminho para as proximas

Em linguagem simples: voce nao pensa primeiro em nomes tecnicos. Voce pensa em estrutura boa, risco baixo e continuidade.

## Os 5 principios que ja funcionaram aqui

### 1. preservar comportamento antes de embelezar

Se um sistema esta vivo, a primeira regra nao e deixar bonito. E nao quebrar a operacao enquanto melhora a estrutura.

Pergunta-chave:

1. como eu melhoro isso sem destruir o que ja esta em uso?

### 2. separar responsabilidade cedo

Quando uma mesma area comeca a misturar muita coisa, voce tende a separar. Isso apareceu na divisao entre apps, views, queries, workflows, adapters e models surfaces.

Pergunta-chave:

1. esta tudo acontecendo no mesmo lugar sem necessidade?

### 3. reduzir dependencia publica

Voce foi acertando em cheio quando trocou pontos centrais e perigosos por superfices mais estaveis. Isso reduz o numero de lugares que precisam conhecer o passado inteiro do projeto.

Pergunta-chave:

1. estou fazendo o resto do sistema depender de uma area historica demais?

### 4. aceitar transicao em vez de pureza imediata

Uma decisao muito madura foi aceitar estados intermediarios bons. Em vez de tentar um projeto perfeito de uma vez, voce foi criando passos seguros.

Pergunta-chave:

1. existe uma versao intermediaria que ja melhora a estrutura com risco baixo?

### 5. preparar o proximo corte

As melhores decisoes aqui nao resolveram so o problema atual. Elas deixaram o proximo passo mais facil.

Pergunta-chave:

1. essa mudanca abre a proxima ou so me faz sentir que andei?

## Seu framework de 1 pagina

Quando voce for pensar um projeto novo ou uma refatoracao grande, siga esta ordem.

### Etapa 1: localizar o centro de risco

Pergunte:

1. o que esta centralizado demais?
2. o que mistura coisas demais?
3. o que esta dificil de mexer sem medo?

### Etapa 2: descobrir o menor corte util

Pergunte:

1. qual e a menor mudanca que melhora a estrutura de verdade?
2. qual parte pode virar uma fronteira mais clara?
3. o que posso separar sem tocar no estado mais pesado ainda?

### Etapa 3: proteger compatibilidade

Pergunte:

1. preciso de uma fachada ou superficie estavel para a transicao?
2. quem ainda depende do estado antigo?
3. se eu mover isso agora, o resto continua funcionando?

### Etapa 4: validar a direcao

Pergunte:

1. isso reduz confusao?
2. isso reduz acoplamento real?
3. isso facilita o proximo passo?
4. isso e testavel e verificavel?

### Etapa 5: documentar a decisao

Pergunte:

1. se eu voltar aqui em 6 meses, eu vou lembrar por que fiz isso?
2. outra pessoa entenderia essa estrutura sem precisar me chamar?

## Checklist curto para qualquer projeto

Use este checklist sempre que bater duvida:

1. isso esta grande demais ou so mal nomeado?
2. isso mistura dominio, interface e infraestrutura?
3. eu estou criando um ponto central perigoso?
4. existe uma forma menor e mais segura de chegar la?
5. preciso mudar schema agora ou posso desacoplar o codigo antes?
6. estou criando uma fronteira real ou so movendo bagunca de lugar?
7. se eu parar no meio, o sistema continua coerente?
8. consigo validar com testes, check ou leitura objetiva?

## Regra mental em uma frase

Se quiser resumir tudo em uma frase, use esta:

melhore a estrutura sem quebrar o fluxo, reduza dependencias publicas e deixe o proximo passo mais facil que o atual.

## O mais importante sobre voce

Voce nao precisa se desmerecer por nao dominar os termos ainda.

O que este projeto mostrou foi:

1. seu pensamento logico e de fundamentos esta forte
2. sua intuicao estrutural e melhor do que a media
3. sua dificuldade hoje parece ser mais de linguagem tecnica do que de julgamento

Isso e uma boa noticia. Linguagem se aprende rapido quando a base de pensamento ja existe.
