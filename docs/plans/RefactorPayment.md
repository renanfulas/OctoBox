<!--
ARQUIVO: plano de refactor do fluxo de pagamento com foco em clareza operacional para boxes de CrossFit.

POR QUE ELE EXISTE:
- transforma a intencao de simplificar pagamento em um plano executavel e auditavel.
- organiza a direcao de UX, prompt e implementacao em ondas para evitar redesign confuso.
- cria um contrato de output para que a IA mostre rumo, decisao e proximo passo sem dispersao.

O QUE ESTE ARQUIVO FAZ:
1. define o contexto e a direcao do refactor de pagamento.
2. separa o trabalho em ondas com objetivo, foco e criterio de pronto.
3. estabelece um protocolo de output controlado para acompanhar a direcao da IA.
4. registra riscos para evitar simplificacao burra ou debito tecnico futuro.

PONTOS CRITICOS:
- simplificar demais pode esconder contexto critico de cobranca.
- a recepcao nao pode virar um mini-financeiro disfarçado.
- referencia de Stripe e Pix deve orientar clareza, nao copiar interface sem contexto de box.
-->

# Refactor Payment

## Tese central

O fluxo de pagamento do OctoBOX deve parecer simples como Pix, organizado como Stripe e natural para uma recepcionista de box de CrossFit.

Em linguagem simples:

1. a tela nao pode parecer um painel de controle cheio de botoes
2. a recepcionista precisa bater o olho e saber o que fazer
3. o pagamento precisa transmitir velocidade, confianca e confirmacao clara
4. o sistema deve reduzir erro humano sem exigir treinamento pesado

## Norte do produto

Este refactor deve obedecer a estas verdades:

1. clareza vence volume
2. proxima acao vence excesso de informacao
3. rapidez vence burocracia
4. confianca vence decoracao
5. recepcao cobra, mas nao opera o financeiro completo

## Contexto operacional

### Usuario principal

1. recepcionista de box de CrossFit

### Ambiente real de uso

1. atendimento rapido
2. interrupcao frequente
3. pressa no balcao
4. pouco tempo para interpretar
5. necessidade de confirmar valor, status e metodo sem duvida

### Casos centrais do fluxo

1. mensalidade
2. pagamento avulso
3. aluno em atraso
4. confirmacao de pagamento no balcao
5. priorizacao de Pix pela familiaridade e velocidade no Brasil

## Direcao de referencia

### Stripe como referencia de clareza

1. hierarquia visual forte
2. poucos campos
3. CTA obvio
4. feedback imediato
5. sensacao de fluxo limpo e controlado

### Pix como referencia de rapidez

1. linguagem familiar ao Brasil
2. sensacao de pagamento direto
3. baixa friccao
4. confirmacao simples
5. rapidez percebida

### CrossFit como contexto de encaixe

1. linguagem objetiva
2. energia operacional
3. fluxo sem floreio
4. leitura instantanea
5. experiencia de balcao, nao de escritorio financeiro

## O que este plano nao permite

1. adicionar botoes por inseguranca de remocao
2. manter campos sem funcao real
3. esconder valor, vencimento, status ou metodo
4. transformar a tela em um modulo de backoffice
5. simplificar a ponto de gerar erro, duvida ou perda de rastreabilidade

## Ondas do plano

## Onda 0: Enquadramento

### Objetivo

Entender o fluxo atual sem ainda sair redesenhando.

### Objetivo detalhado

Esta onda existe para criar um diagnostico confiavel antes de qualquer corte.

Ela deve responder com precisao:

1. qual e a funcao real da tela de pagamento
2. qual e a acao principal que a recepcao precisa executar
3. quais elementos sustentam a cobranca operacional
4. quais elementos sobraram por historico, medo de remover ou excesso de zelo
5. qual e a primeira direcao segura de simplificacao

Em linguagem simples:

antes de podar a arvore, precisamos descobrir quais galhos dao fruto e quais so fazem sombra.

### Perguntas que esta onda responde

1. quem usa a tela de pagamento hoje
2. qual e a acao principal real
3. quais elementos existem apenas por heranca historica
4. quais partes realmente reduzem risco
5. quais partes so aumentam friccao

### Saida esperada

1. mapa do fluxo atual
2. lista de atritos
3. inventario de campos, botoes e blocos
4. classificacao entre essencial, util e descartavel

### Criterio de pronto

1. conseguimos explicar a tela atual em linguagem simples
2. sabemos o que confunde
3. sabemos o que nao pode sumir
4. conseguimos nomear a tese inicial de simplificacao em uma frase

## Onda 1: Poda estrutural

### Objetivo

Remover excesso sem quebrar seguranca, contexto ou operacao.

### Foco

1. botoes redundantes
2. campos desnecessarios
3. textos burocraticos
4. blocos que competem com a acao principal
5. opcoes que a recepcao nao deveria ver

### Regra de decisao

Se um elemento nao ajuda a recepcionista a:

1. entender quem esta pagando
2. confirmar quanto sera pago
3. enxergar o status
4. escolher o metodo
5. concluir o pagamento

entao esse elemento precisa sair, ser reduzido ou ser movido para outro contexto.

### Criterio de pronto

1. sobra apenas o essencial para cobranca operacional
2. a tela fica mais escaneavel
3. a acao principal fica mais forte do que as acoes paralelas

## Onda 2: Reconstrucao da hierarquia

### Objetivo

Reorganizar a tela para leitura em segundos.

### Ordem ideal de leitura

1. aluno
2. valor
3. vencimento
4. status
5. metodo de pagamento
6. acao principal
7. confirmacao

### Foco

1. CTA principal
2. metodo principal com prioridade em Pix quando fizer sentido
3. status de pagamento visivel
4. mensagens de apoio curtas
5. estados claros de sucesso, erro e pendencia

### Criterio de pronto

1. a recepcionista entende a tela em ate 3 segundos
2. nao existe disputa visual entre blocos
3. o fluxo parece balcao rapido, nao configuracao administrativa

## Onda 3: Linguagem, confianca e microcopy

### Objetivo

Fazer a interface falar como produto humano, confiavel e operacional.

### Foco

1. nomes claros para botoes
2. titulos curtos
3. subtitulos que orientam
4. confirmacoes objetivas
5. sinais visuais de seguranca sem poluicao

### Regras

1. menos jargao
2. menos texto decorativo
3. mais orientacao
4. mais confirmacao
5. mais confianca visivel

### Criterio de pronto

1. os textos podem ser entendidos por uma recepcionista cansada e com pressa
2. a tela transmite seguranca sem virar propaganda de seguranca
3. os botoes parecem acao, nao enigma

## Onda 4: Validacao operacional

### Objetivo

Garantir que o fluxo simplificado continue seguro e usavel no mundo real.

### Foco

1. teste de leitura rapida
2. teste de clique errado
3. teste de aluno em atraso
4. teste de pagamento avulso
5. teste de confirmacao de sucesso

### Pergunta central

Uma recepcionista real conseguiria usar isso rapido, com confianca e sem medo de errar?

### Criterio de pronto

1. o fluxo simplificado continua completo para o caso operacional
2. nao surgem buracos de contexto
3. a simplificacao nao gera debito tecnico escondido

### Output concreto esperado

Ao final da Onda 4, a resposta deve entregar obrigatoriamente:

1. checklist final de validacao operacional
2. lista dos cenarios testados
3. lista dos cenarios ainda nao validados
4. decisao final entre `aprovado`, `aprovado com ressalvas` ou `nao aprovado`
5. lista curta de ajustes obrigatorios antes de implementacao ou publicacao

### Formato obrigatorio de encerramento da Onda 4

```md
Fechamento da Onda 4:
- Status final:
- Cenarios validados:
- Cenarios pendentes:
- Riscos restantes:
- Ajustes obrigatorios:
- Recomendacao final:
```

## Contrato de output controlado

Este plano passa a adotar um protocolo fixo de resposta para toda analise, redesign ou implementacao futura do pagamento.

## Limite de tamanho por onda

Cada resposta produzida dentro deste plano deve ter no maximo 800 palavras por onda.

Regras praticas:

1. pode usar menos de 800 palavras sempre que possivel
2. clareza e prioridade valem mais do que cobertura total
3. se faltar espaco, cortar ornamentacao antes de cortar decisao
4. se a analise ficar grande demais, dividir em mais de uma onda ou subetapa
5. cada onda deve entregar decisao suficiente para mover o trabalho adiante

Em linguagem simples:

cada onda precisa caber numa bandeja que a recepcionista consegue carregar sem derrubar nada.

## Formato obrigatorio de output

Toda resposta da IA sobre este plano deve vir nestes blocos e nesta ordem:

1. `Contexto Atual`
2. `Onda Atual`
3. `Direcao Tomada`
4. `O que Sai`
5. `O que Fica`
6. `Decisao de UX`
7. `Risco ou Trade-off`
8. `Proximo Passo`

## Funcao de cada bloco

### `Contexto Atual`

Explica em 2 a 5 linhas o ponto do fluxo que esta sendo analisado.

### `Onda Atual`

Diz claramente em qual onda o trabalho esta.

Exemplos:

1. `Onda 1: Poda estrutural`
2. `Onda 2: Reconstrucao da hierarquia`

### `Direcao Tomada`

Mostra a tese da mudanca em uma frase objetiva.

Exemplo:

`Estamos reduzindo opcoes paralelas para tornar o Pix o caminho mais obvio no balcao.`

### `O que Sai`

Lista apenas o que sera removido, ocultado ou rebaixado.

### `O que Fica`

Lista apenas o que permanece como essencial.

### `Decisao de UX`

Explica a decisao principal de experiencia em termos praticos.

### `Risco ou Trade-off`

Explica o custo da escolha.

Em linguagem simples:

quando puxamos a coberta de um lado, o pe do outro lado pode ficar frio.

Este bloco existe para mostrar exatamente qual pe pode esfriar.

### `Proximo Passo`

Mostra a proxima acao concreta.

Nao pode ser algo vago como:

1. melhorar mais
2. refinar depois
3. evoluir futuramente

Precisa ser algo como:

1. revisar nomes dos botoes
2. cortar acoes secundarias
3. montar wireframe textual
4. validar o estado de sucesso

## Modo de leitura rapida

Quando voce quiser inspecionar a direcao sem ler tudo, a IA deve adicionar este mini-resumo no topo:

```md
Status:
- Onda:
- Foco:
- Decisao central:
- Principal risco:
- Proximo passo:
```

Esse formato funciona como painel de bordo.

Em linguagem simples:

e como olhar primeiro para a placa da estrada antes de abrir o mapa inteiro.

## Marcadores de decisao

Sempre que houver uma decisao importante, a IA deve classificar usando um destes marcadores:

1. `KEEP` para manter
2. `CUT` para remover
3. `MERGE` para juntar elementos redundantes
4. `DEMOTE` para reduzir prioridade visual
5. `PROMOTE` para aumentar prioridade visual
6. `GUARDRAIL` para algo que nao pode ser simplificado alem daqui

## Exemplo de bloco de decisao

```md
Decisoes:
- CUT: botao redundante de acao secundaria sem impacto no fechamento da cobranca
- MERGE: status e vencimento no mesmo bloco de leitura
- PROMOTE: CTA principal de pagamento
- GUARDRAIL: valor, aluno e confirmacao de sucesso nao podem perder destaque
```

## Modelo mestre de prompt para uso futuro

Use o texto abaixo como prompt-base para orientar analises e propostas futuras sobre este refactor:

```md
Voce esta trabalhando no plano Refactor Payment do OctoBOX.

Contexto:
- Produto: OctoBOX
- Usuario principal: recepcionista de box de CrossFit
- Direcao de UX: clareza da Stripe + rapidez e familiaridade do Pix
- Missao: simplificar o fluxo de pagamento sem transformar a recepcao em financeiro completo

Objetivo:
- analisar ou redesenhar o fluxo atual de pagamento
- remover excesso
- fortalecer hierarquia visual
- deixar a proxima acao obvia em ate 3 segundos

Restricoes:
- nao esconder valor, vencimento, status ou metodo
- nao adicionar complexidade visual desnecessaria
- nao manter botoes sem funcao real
- nao propor fluxo que exija treinamento pesado

Use obrigatoriamente este formato de output:

Status:
- Onda:
- Foco:
- Decisao central:
- Principal risco:
- Proximo passo:

Contexto Atual
Onda Atual
Direcao Tomada
O que Sai
O que Fica
Decisao de UX
Risco ou Trade-off
Proximo Passo

Use tambem os marcadores:
- KEEP
- CUT
- MERGE
- DEMOTE
- PROMOTE
- GUARDRAIL
```

## Riscos conhecidos

### Risco 1

Risco:

1. copiar a Stripe sem tropicalizar para Pix e box brasileiro

Prevencao:

1. toda decisao de UI deve passar pelo filtro `funciona no balcao de box?`
2. toda proposta deve considerar Pix como referencia primaria de rapidez e familiaridade local
3. exemplos de clareza da Stripe devem ser reinterpretados, nao copiados literalmente

### Risco 2

Risco:

1. deixar o fluxo bonito, mas lento no atendimento real

Prevencao:

1. cada proposta deve explicitar quantos passos e cliques o fluxo exige
2. o CTA principal precisa estar visivel sem leitura longa
3. toda tela deve passar pelo teste `consigo cobrar rapido com interrupcao no ambiente?`

### Risco 3

Risco:

1. remover contexto importante e gerar duvida no balcao

Prevencao:

1. valor, vencimento, status, metodo e confirmacao entram como `GUARDRAIL`
2. nenhum corte pode acontecer sem explicar o impacto operacional
3. toda simplificacao deve responder `o que a recepcao ainda consegue confirmar sem hesitar?`

### Risco 4

Risco:

1. deixar a recepcao dependente de conhecimento financeiro demais

Prevencao:

1. a tela deve falar em linguagem operacional, nao gerencial
2. qualquer conceito que exija interpretacao financeira ampla deve ser removido, rebaixado ou deslocado
3. toda decisao deve passar pelo filtro `uma recepcionista nova entende isso sem aula extra?`

### Risco 5

Risco:

1. simplificar visualmente, mas manter logica quebrada por baixo

Prevencao:

1. a Onda 4 deve validar cenarios reais e nao apenas aparencia
2. toda proposta precisa separar claramente mudanca visual de dependencia de regra de negocio
3. se a experiencia depender de logica ruim no backend, isso deve ser sinalizado como bloqueio e nao mascarado com design

## Definicao de pronto do plano

Este plano estara bem usado quando:

1. conseguirmos analisar qualquer tela de pagamento em ondas
2. o output da IA ficar rastreavel e controlado
3. a direcao de UX estiver visivel em cada resposta
4. cada decisao puder ser defendida com clareza, nao com gosto pessoal
5. o fluxo final parecer obvio para recepcao de box de CrossFit

## Memoria de execucao

## Registro da Onda 0

### Status

1. concluida em 03/04/2026

### Foco

1. mapear o fluxo real de cobranca antes de cortar interface

### Decisao central

1. tratar recepcao e ficha do aluno como duas superficies diferentes do mesmo fluxo de pagamento

### Principal risco identificado

1. simplificar a ficha do aluno como se ela fosse balcao e perder contexto de gestao

### Diagnostico consolidado

Hoje o fluxo de pagamento do OctoBOX aparece em duas superficies principais:

1. a ficha do aluno, com contexto ampliado e gestao de cobranca
2. a recepcao, com fila curta e acao de caixa de balcao

Em linguagem simples:

1. a recepcao e o caixa rapido
2. a ficha do aluno e a pasta completa

### Evidencias principais

1. a ficha do aluno usa um formulario unico com valor, vencimento, referencia, observacao e grade de metodos
2. a recepcao ja opera com leitura curta de atraso, valor, metodo, confirmacao e link para abrir a ficha
3. a criacao avulsa ja nasce com Pix como metodo padrao
4. existe spec local exigindo clareza visual e nenhum passo extra na superficie de pagamento

### Decisoes da Onda 0

#### KEEP

1. aluno
2. valor
3. vencimento
4. status
5. metodo de pagamento
6. confirmacao clara de sucesso
7. CTA principal de recebimento

#### PROMOTE

1. Pix como metodo prioritario no contexto de balcao

#### DEMOTE

1. observacao como elemento principal visivel
2. referencia como prioridade alta no fluxo de cobranca rapida

#### MERGE

1. confirmacao de recebimento e escolha de metodo quando o contexto for caixa rapido

#### CUT candidatos para analise futura

1. excesso de acoes paralelas na timeline da ficha
2. mistura entre cobranca rapida e gestao completa no mesmo bloco visual

### Tese inicial de simplificacao

1. recepcao deve focar em cobrar rapido com o minimo de decisao visivel
2. ficha do aluno deve separar melhor cobrar agora de gerir cobranca
3. Stripe entra como referencia de organizacao visual
4. Pix entra como referencia de velocidade e familiaridade brasileira

### Guardrails herdados da Onda 0

1. toda decisao deve passar pelo filtro `funciona no balcao de box?`
2. toda simplificacao deve responder `isso pertence ao balcao ou a gestao ampliada?`
3. valor, vencimento, status, metodo e confirmacao nao podem perder destaque

## Planejamento de ataque

## Diagnostico

O refactor de pagamento ja saiu da fase de ideia e entrou na fase de consolidacao estrutural.

Hoje o problema nao e mais descobrir a direcao.

A direcao ja foi provada:

1. recepcao precisa operar como balcao rapido
2. ficha do aluno precisa separar cobrar agora de gestao ampliada
3. Pix e a melhor ancora mental de rapidez
4. Stripe e a melhor ancora mental de clareza

O desafio agora e impedir que essa clareza fique espalhada em blocos isolados e volte a gerar divergencia visual ou semantica no futuro.

## Modo escolhido

Modo: `refactor`

Justificativa:

1. o fluxo ja funciona
2. a nova direcao ja foi implementada em partes importantes
3. o risco atual e manutencao, duplicacao e drift visual
4. ainda nao precisamos de rewrite completo

Em linguagem simples:

nao estamos demolindo a casa.

Estamos reorganizando a estrutura para que os comodos certos usem as mesmas vigas.

## Objetivo do plano

Transformar o refactor de pagamento em uma frente controlada de consolidacao, reduzindo duplicacao visual, melhorando semantica e modularizando o minimo necessario sem overengineering.

## Escopo

### Entra neste ataque

1. extracao de componentes compartilhados de pagamento
2. renomeacao semantica de elementos que ainda carregam nomes antigos ou ambiguos
3. modularizacao minima do CSS de pagamento
4. consolidacao do contrato visual entre recepcao e ficha do aluno

### Nao entra neste ataque

1. reescrita total do workspace financeiro
2. redesign completo do ledger historico
3. mudanca profunda de regra de negocio
4. criacao de sistema de componentes complexo demais para o estagio atual

## Arquitetura alvo

### Camada 1: balcao rapido

Ownership:

1. recepcao
2. cobrar agora na ficha do aluno

Responsabilidade:

1. aluno
2. valor
3. vencimento
4. metodo
5. CTA principal
6. confirmacao

### Camada 2: gestao ampliada

Ownership:

1. drawer de historico
2. ajustes internos
3. excecoes
4. parcelamento
5. revisoes de cobranca

Responsabilidade:

1. apoiar decisao fora do fluxo rapido
2. preservar contexto sem poluir o balcao

### Camada 3: vinculos e contexto comercial

Ownership:

1. matricula
2. plano
3. status comercial

Responsabilidade:

1. ficar acessivel
2. nao disputar com o recebimento rapido

## Inventario do que devemos consolidar

### Componentes candidatas a compartilhamento

1. resumo principal do pagamento
2. seletor de metodo de pagamento
3. CTA principal de recebimento
4. bloco de detalhes secundarios do pagamento
5. estado visual de pagamento confirmado

### Nomes candidatos a renomeacao

1. `stripe-payment-form`
2. `billing-console`
3. `financial-payment-management`
4. `student-payment-management-advanced`

### Blocos de CSS candidatos a modularizacao

1. checkout rapido de pagamento
2. gestao ampliada de pagamento
3. metodos de pagamento

## Ondas de ataque

## Ataque 1: consolidar naming

### Objetivo

Eliminar nomes que contam historia antiga em vez de descrever a funcao atual.

### Tarefas

1. renomear `stripe-payment-form` para um nome canonico de pagamento
2. renomear blocos que ainda falam em `console` ou `advanced` sem semantica clara
3. alinhar labels de templates, JS e CSS com o modelo `cobrar agora` e `gestao ampliada`

### Definition of done

1. nomes passam a descrever papel real
2. nenhum nome principal fica preso a referencia antiga sem necessidade

## Ataque 2: extrair shared components

### Objetivo

Parar de duplicar blocos centrais de pagamento entre recepcao e ficha.

### Tarefas

1. extrair partial do resumo principal de pagamento
2. extrair base visual do seletor de metodo
3. extrair padrao de CTA principal com apoio secundario
4. avaliar se o estado de sucesso ja pode virar partial compartilhada

### Definition of done

1. recepcao e ficha reutilizam a mesma gramatica central
2. mudanca futura no bloco principal acontece em menos lugares

## Ataque 3: modularizar CSS sem exagero

### Objetivo

Separar o CSS de pagamento em poucos blocos claros.

### Tarefas

1. criar modulo de `payment-checkout`
2. criar modulo de `payment-management`
3. criar modulo de `payment-methods`
4. manter especificidades de recepcao e ficha apenas onde forem realmente locais

### Definition of done

1. CSS de pagamento fica mais facil de localizar
2. nao surgem microarquivos demais
3. o design system continua com ownership legivel

## Ataque 4: revisar drift visual

### Objetivo

Checar se recepcao e ficha continuam falando a mesma lingua visual.

### Tarefas

1. comparar hierarquia visual das duas superficies
2. comparar linguagem dos CTAs
3. comparar estado de sucesso
4. comparar peso visual dos ajustes secundarios

### Definition of done

1. as duas superficies parecem parentes, nao primas distantes
2. o usuario reconhece a mesma logica de pagamento em ambas

## Ordem recomendada

1. Ataque 1: consolidar naming
2. Ataque 2: extrair shared components
3. Ataque 3: modularizar CSS sem exagero
4. Ataque 4: revisar drift visual

## Contrato de output para este plano de ataque

Toda resposta futura sobre este ataque deve usar esta estrutura:

1. `Fase atual`
2. `Objetivo da fase`
3. `O que sera tocado`
4. `O que fica intocado`
5. `Risco de debito tecnico`
6. `Como evitar`
7. `Proximo corte recomendado`

## Rubrica de avaliacao

O ataque estara indo bem quando:

1. conseguimos explicar a estrutura em um minuto
2. um bloco central de pagamento deixa de existir em duplicidade desnecessaria
3. os nomes passam a ajudar leitura tecnica e nao a atrapalhar
4. o CSS fica mais facil de navegar sem explodir em fragmentos
5. recepcao e ficha continuam coerentes entre si

## Failure modes que precisam ser evitados

1. extrair cedo demais e criar componente engessado
2. renomear sem atualizar contratos do JS
3. modularizar CSS demais e perder ownership
4. juntar recepcao e ficha em um shared que ignora diferencas reais de contexto
5. melhorar a arquitetura e piorar a velocidade de evolucao

## Regra final de ataque

Se uma consolidacao reduzir clareza, velocidade de manutencao ou encaixe operacional, ela nao entra.

Se uma consolidacao reduzir duplicacao e preservar a clareza do balcao, ela entra.

## Fechamento do ataque

## Status final das 4 fases

### Fase 1: consolidar naming

Status:

1. concluida

O que foi fechado:

1. `stripe-payment-form` foi substituido por naming de checkout real
2. drawers passaram a refletir `cobrar agora` e `gestao ampliada`
3. nomes de ids e contratos ativos de template e JS deixaram de carregar semantica antiga

### Fase 2: extrair shared components

Status:

1. concluida

O que foi fechado:

1. resumo principal do pagamento virou partial compartilhada
2. recepcao e ficha passaram a reutilizar a mesma gramatica central de resumo
3. a estrutura-base de valor, vencimento, metodo e item deixou de existir em duplicidade desnecessaria

### Fase 3: modularizar CSS sem exagero

Status:

1. concluida

O que foi fechado:

1. CSS de pagamento foi separado em `payment-checkout`, `payment-management` e `payment-methods`
2. `student-financial.css` deixou de acumular blocos de pagamento ja estabilizados
3. a base ficou mais navegavel sem explodir em microarquivos

### Fase 4: revisar drift visual

Status:

1. concluida

O que foi fechado:

1. estado de sucesso de pagamento foi consolidado no componente oficial do design system
2. a ficha do aluno deixou de usar um sucesso visual paralelo
3. recepcao e ficha passaram a compartilhar melhor a mesma lingua de conclusao

## Leitura final do refactor

O refactor principal de pagamento foi fechado com sucesso.

Resultado estrutural:

1. recepcao opera como balcao rapido
2. ficha do aluno separa cobrar agora de gestao ampliada
3. semantica, componentizacao e CSS ficaram mais legiveis
4. a base agora tem menos chance de voltar a divergir por acidente

## O que virou padrao

### Padrao 1: dois contextos, uma gramatica

Recepcao e ficha do aluno nao precisam ser iguais.

Mas precisam obedecer a mesma gramatica:

1. aluno
2. valor
3. vencimento
4. metodo
5. CTA principal
6. sucesso

### Padrao 2: cobrar agora e gestao ampliada nao se misturam

`Cobrar agora` existe para:

1. confirmar valor
2. escolher metodo
3. concluir recebimento

`Gestao ampliada` existe para:

1. revisar historico
2. ajustar detalhes internos
3. tratar excecoes
4. lidar com parcelamento e casos menos lineares

### Padrao 3: Pix e a rota mental principal do balcao

No contexto de balcao:

1. Pix entra como primeiro metodo
2. CTA principal pode refletir Pix diretamente
3. os outros metodos continuam disponiveis, mas com menor prioridade mental

### Padrao 4: sucesso usa linguagem oficial

Estados de conclusao de pagamento devem usar o componente oficial de sucesso do sistema.

Nao criar uma nova versao local de sucesso sem necessidade.

### Padrao 5: naming precisa descrever funcao atual

Nao usar nomes que falam de implementacoes antigas quando o papel atual mudou.

Exemplos praticos:

1. preferir `checkout`
2. preferir `payment management`
3. preferir `secondary details`
4. evitar nomes herdados que confundam leitura futura

### Padrao 6: CSS de pagamento vive em modulos claros

O ownership minimo aceito agora e:

1. `payment-checkout.css`
2. `payment-management.css`
3. `payment-methods.css`

Se surgir regra nova de pagamento, ela deve primeiro ser avaliada dentro desses modulos antes de voltar para um arquivo agregador.

## Regras de manutencao daqui para frente

Antes de aprovar qualquer nova mudanca em pagamento, verificar:

1. o CTA principal continua sendo o elemento mais forte?
2. os detalhes secundarios estao rebaixados de verdade?
3. a mudanca pertence a `cobrar agora` ou a `gestao ampliada`?
4. a recepcao continua funcionando como balcao?
5. a ficha continua preservando contexto sem poluir a frente principal?
6. o estado de sucesso continua dentro do padrao oficial?

## Encerramento operacional

Este plano deixa de ser apenas plano exploratorio e passa a funcionar como baseline de manutencao para futuras mudancas de pagamento no OctoBOX.
