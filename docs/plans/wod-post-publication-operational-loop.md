<!--
ARQUIVO: contrato operacional do loop pos-publicacao do WOD.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional
- referencia de governanca leve

AUTORIDADE:
- alta para alertas, acoes sugeridas, retorno registrado e reavaliacao pos-publicacao

DOCUMENTOS PAIS:
- [coach-wod-approval-corda.md](coach-wod-approval-corda.md)
- [student-app-grade-wod-rm-corda.md](student-app-grade-wod-rm-corda.md)
- [cross-box-operational-intelligence-corda.md](cross-box-operational-intelligence-corda.md)
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)

QUANDO USAR:
- quando a duvida for como medir o que aconteceu depois de publicar um WOD
- quando precisarmos evoluir alertas, follow-up e leitura executiva sem cair em analytics pesado
- quando quisermos manter a board operacional curta, mas confiavel

POR QUE ELE EXISTE:
- evita que o historico de publicacao vire apenas memoria morta
- garante que acao sugerida, retorno registrado e resultado observado tenham contrato claro
- protege o produto contra overengineering de observabilidade precoce

O QUE ESTE ARQUIVO FAZ:
1. formaliza o loop alerta -> acao -> retorno -> releitura
2. define as metricas minimas e a foto de baseline
3. explica o criterio de resolucao, monitoramento e falha
4. registra o proximo passo natural da trilha
5. documenta o escalonamento operacional curto

PONTOS CRITICOS:
- nao transformar o WOD em ferramenta de analytics pesada
- manter a heuristica honesta: boa o suficiente para operacao, nao fake precision
- preservar a trilha mesmo quando o alerta some, para nao apagar a historia
-->

# Loop operacional pos-publicacao do WOD

## Tese central

Depois que o WOD vai ao ar, o sistema precisa responder tres perguntas simples:

1. houve sinal de risco?
2. alguem agiu?
3. melhorou de verdade depois da acao?

Em linguagem simples:

1. primeiro vemos a fumaca
2. depois anotamos quem pegou o balde
3. por fim confirmamos se o fogo abaixou

## O que ja esta fundamentado

### Onda 11 - consumo real

O sistema passou a observar:

1. tamanho da turma
2. check-in
3. abertura do WOD no app do aluno

### Onda 12 - alerta operacional

O sistema passou a gerar sinais como:

1. WOD urgente sem leitura
2. aula comecando com pouco consumo
3. aluno em aula sem leitura equivalente

### Onda 13 - acao sugerida

O sistema passou a sugerir respostas curtas:

1. reforcar chamada no WhatsApp
2. avisar coach
3. acompanhar recepcao ou operacao

### Onda 14 - retorno registrado

Owner ou manager podem registrar:

1. o que foi feito
2. quem fez
3. quando fez
4. se marcou como `Resolvido` ou `Descartado`

### Onda 15 - reavaliacao leve

Ao registrar o retorno, o sistema guarda um `baseline_metrics`.

Esse baseline e a foto do momento da acao:

1. `reserved_count`
2. `checked_in_count`
3. `viewer_count`
4. `viewer_rate`

Depois, na board, ele compara baseline vs estado atual.

## Contrato oficial da Onda 15

### Baseline

`SessionWorkoutFollowUpAction.baseline_metrics` guarda a foto do antes.

Ele existe para:

1. evitar memoria subjetiva do operador
2. mostrar diferenca objetiva depois da acao
3. permitir before/after barato sem pipeline analitico

### Releitura atual

A releitura atual usa as mesmas metricas operacionais vivas:

1. reservas
2. check-ins
3. aberturas do WOD

### Estados de monitoramento

Hoje o sistema trabalha com quatro leituras executivas:

1. `Resolvido`
2. `Monitorando`
3. `Nao resolveu`
4. `Encerrado`

#### `Resolvido`

Quando:

1. os alertas relevantes daquela acao sumiram

#### `Monitorando`

Quando:

1. ainda existe algum alerta relevante
2. mas houve melhora visivel de consumo ou check-in depois da acao

#### `Nao resolveu`

Quando:

1. ainda existe alerta relevante
2. e nao houve melhora suficiente depois da acao

#### `Encerrado`

Quando:

1. o operador marcou a acao como `Descartado`

Observacao:

`Descartado` nao quer dizer necessariamente erro. Pode significar:

1. falso positivo operacional
2. acao nao fazia mais sentido
3. caso absorvido por outra resposta fora daquela trilha

## Regra de honestidade

O sistema nao deve fingir precisao que ele nao tem.

Por isso:

1. ele nao promete causalidade estatistica
2. ele mostra apenas melhoria observada
3. ele mantem leitura operacional, nao cientifica

Metafora curta:

1. isso e um painel de ambulancia
2. nao um laboratorio de pesquisa

## Onda 16 - fila de pendencias reais

Transformar essa leitura em `fila de pendencias reais`.

### Objetivo

Mostrar rapidamente quais publicacoes ainda pedem atencao humana agora.

### Criterio de entrada na fila

Um item entra na fila quando houver pelo menos um destes pontos:

1. alerta ainda ativo
2. acao sem retorno registrado
3. acao em `Monitorando`
4. acao em `Nao resolveu`

### O que a fila deve mostrar

1. aula
2. WOD
3. estado temporal da aula
4. razoes do risco ainda vivo
5. proxima acao sugerida ou ainda pendente

### O que ela nao deve virar

1. backlog infinito
2. dashboard separado demais da board
3. sistema de tickets

## Onda 17 - escalonamento operacional curto

### Objetivo

Fazer a board dizer claramente:

1. quem e o proximo dono da bola
2. qual corredor deve ser aberto agora
3. quando esse caso merece resposta imediata

### Regra de produto

Escalonamento curto nao e ticket.

Ele e apenas:

1. definicao de dono imediato
2. caminho curto de resposta
3. leitura executiva sem ambiguidade

### Contrato atual

Cada `pendencia real` pode ganhar:

1. `owner_label`
2. `escalation_label`
3. `tone`
4. `href` quando existir rota operacional util

### Heuristica atual

#### Operacao/Recepcao

Quando:

1. a aula ja esta em andamento
2. ou o risco fala de aluno em aula

Leitura:

1. precisa de olho no chao da operacao agora

#### Coach

Quando:

1. a pendencia pede alinhamento de treino
2. ou a urgencia operacional sugere ajuste verbal ou tatico

Leitura:

1. precisa de ajuste humano no discurso ou condução da aula

#### WhatsApp

Quando:

1. a pendencia e principalmente de comunicacao e abertura de WOD

Leitura:

1. o melhor proximo passo e reforcar o canal de mensagem

#### Manager/Owner

Quando:

1. nenhum corredor especifico venceu claramente

Leitura:

1. precisa de leitura executiva curta antes de delegar

### Regra de honestidade

O escalonamento nao promete resolver o caso sozinho.

Ele apenas reduz a pergunta:

1. `quem precisa olhar isso agora?`

Em metafora simples:

1. nao e abrir chamado
2. e apontar o extintor certo na parede

## Onda 18 - fechamento executivo do caso

### Objetivo

Responder para lideranca, em uma linha, em que pe o caso esta.

Nao basta saber:

1. qual foi o alerta
2. quem deveria agir

Tambem precisamos saber:

1. a operacao absorveu o caso?
2. ainda estamos so acompanhando?
3. falta alguem agir?
4. ja virou caso de intervencao forte?

### Contrato atual

Cada caso publicado pode ganhar uma leitura executiva:

1. `Absorvido`
2. `Acompanhando`
3. `Aguardando acao`
4. `Intervencao forte`

### Heuristica atual

#### `Absorvido`

Quando:

1. nao existem alertas vivos relevantes
2. e nao falta acao registrada

#### `Acompanhando`

Quando:

1. houve resposta
2. ainda existe algum sinal vivo ou monitoramento curto
3. mas o caso nao pede resposta forte imediata

#### `Aguardando acao`

Quando:

1. a board ja leu o risco
2. mas alguma acao sugerida ainda esta sem retorno

#### `Intervencao forte`

Quando:

1. uma acao foi registrada e mesmo assim o caso segue em `Nao resolveu`
2. ou a aula ja esta em andamento com risco vivo

### Leitura de produto

O fechamento executivo e o resumo que um gestor quer ver sem abrir cada card.

Metafora curta:

1. alerta mostra a fumaca
2. escalonamento mostra quem pega o extintor
3. fechamento executivo mostra se o incendio ja foi absorvido pelo predio ou se ainda esta perigoso

## Onda 19 - memoria operacional curta por caso

### Objetivo

Dar a cada caso um diario de bordo curto, sem virar sistema de tickets.

### Contrato atual

Cada WOD publicado pode receber pequenos marcos operacionais como:

1. `Recepcao assumiu`
2. `Coach alinhado`
3. `WhatsApp disparado`
4. `Nota de monitoramento`
5. `Marco livre`

### Regra de produto

Esses marcos existem para responder:

1. o que ja aconteceu nesse caso?
2. quem registrou isso?
3. em que momento isso entrou na historia?

### O que essa memoria nao deve virar

1. conversa longa
2. log infinito de comentarios
3. sistema paralelo de atendimento

### Leitura de arquitetura

Essa memoria curta e um caderno de bordo:

1. poucas linhas
2. marcos claros
3. dono explicito
4. leitura rapida na propria board

## Onda 20 - leitura executiva agregada da memoria operacional

### Objetivo

Transformar os marcos curtos da Onda 19 em um placar executivo leve.

As perguntas aqui deixam de ser:

1. `o que aconteceu neste caso?`

E passam a incluir:

1. `quais corredores a operacao mais usa para absorver casos?`
2. `quantos casos precisaram de recepcao?`
3. `quantos so fecharam quando o coach entrou?`
4. `quantos dependeram de WhatsApp?`

### Regra de honestidade

Essa leitura agregada conta `casos`, nao `eventos brutos`.

Exemplo:

1. se um mesmo WOD recebeu dois registros de `WhatsApp disparado`
2. ele continua contando como um caso que dependeu de WhatsApp

Isso evita inflar o painel com ruido de repeticao.

### Contrato atual

A board executiva agrega, por janela curta do historico publicado:

1. casos com `Recepcao assumiu`
2. casos com `Coach alinhado`
3. casos `absorvidos com coach`
4. casos com `WhatsApp disparado`
5. casos com `Nota de monitoramento`
6. casos com `Marco livre`

### Leitura de produto

Essa camada nao e analytics pesado.

Ela e um placar tatico para responder:

1. qual trilha operacional mais aparece
2. onde o box mais precisa intervir
3. quais alavancas estao realmente absorvendo problema

Metafora curta:

1. nao e um centro de inteligencia militar
2. e o quadro do tecnico mostrando por qual lado o time mais atacou e por onde mais sofreu

## Onda 21 - cruzamento entre alavanca e fechamento executivo

### Objetivo

Parar de olhar so `qual alavanca apareceu` e passar a olhar `qual alavanca realmente absorveu melhor os casos`.

As perguntas agora passam a ser:

1. `recepcao aparece muito, mas fecha bem ou so segura a fumaça?`
2. `quando o coach entra, o caso costuma ser absorvido ou fica monitorando?`
3. `WhatsApp esta resolvendo ou so repetindo esforco?`

### Contrato atual

Para cada alavanca registrada na memoria operacional curta, a board passa a cruzar:

1. total de casos observados
2. quantos terminaram `Absorvido`
3. quantos ficaram `Acompanhando`
4. quantos ficaram `Aguardando acao`
5. quantos chegaram em `Intervencao forte`

### Regra de honestidade

Isso continua sendo leitura executiva leve, nao ciencia causal.

Ou seja:

1. o sistema nao afirma que a alavanca causou o fechamento
2. ele afirma apenas que essa alavanca apareceu em casos que terminaram nesses estados

### Leitura de produto

Essa camada ajuda o box a descobrir, com baixo custo:

1. quais corredores mais absorvem problema
2. quais corredores ainda parecem caros ou fracos
3. onde vale reforcar processo, treinamento ou automacao

Metafora curta:

1. antes viamos quantas vezes cada jogador tocou na bola
2. agora vemos em quais jogadas o time realmente conseguiu matar a partida

## Onda 22 - tendencia curta de melhoria ou desgaste

### Objetivo

Perceber cedo se uma alavanca operacional esta ficando mais forte, estavel ou cansada nas ultimas publicacoes.

### Contrato atual

A board divide a janela curta do historico em duas metades:

1. metade anterior
2. metade mais recente

E compara, por alavanca:

1. taxa de absorcao da metade anterior
2. taxa de absorcao da metade recente

### Rotulos atuais

1. `Melhora recente`
2. `Estavel`
3. `Sinal de desgaste`
4. `Base curta`

### Regra de honestidade

Quando uma alavanca nao aparece dos dois lados da janela, o sistema mostra `Base curta`.

Isso evita um erro classico:

1. pegar um unico caso novo
2. chamar isso de tendencia
3. tomar decisao de processo em cima de ruido

### Leitura de produto

Essa camada serve para o gestor perceber:

1. se o coach esta resolvendo melhor que antes
2. se recepcao esta segurando, mas nao absorvendo
3. se WhatsApp esta ficando cansado como resposta

Metafora curta:

1. nao e o VAR do campeonato
2. e o tecnico olhando os ultimos jogos para ver se a jogada esta amadurecendo ou perdendo forca

## Onda 23 - alerta leve de gestao

### Objetivo

Transformar tendencia recorrente em um sinal executivo curto e acionavel.

### Contrato atual

Quando a board encontra:

1. `Melhora recente`
2. `Sinal de desgaste`

ela pode subir um `alerta leve de gestao`.

### Regra de produto

Esse alerta nao e incidente.

Ele e apenas um aviso curto para lideranca enxergar:

1. uma alavanca que esta amadurecendo
2. uma alavanca que esta cansando

### Regra de honestidade

`Base curta` nao vira alerta.

Isso protege o produto contra o erro de tratar falta de base como tendencia real.

### Leitura de produto

Esse alerta ajuda o gestor a agir cedo:

1. consolidando uma boa pratica que esta melhorando
2. revisando um corredor que esta perdendo forca

Metafora curta:

1. nao e um alarme de incendio
2. e a luz amarela do painel dizendo qual parte do motor merece olho antes de quebrar

## Onda 24 - priorizacao executiva dos alertas

### Objetivo

Fazer a board dizer nao apenas `isso merece atencao`, mas `isso merece atencao antes dos outros`.

### Contrato atual

Os alertas leves de gestao passam a ganhar uma ordem curta de prioridade.

Regra atual:

1. `Sinal de desgaste` vem antes de `Melhora recente`
2. entre alertas do mesmo tipo, quem tem maior base recente sobe antes

### Leitura de produto

Isso evita que a lideranca veja uma parede de cards sem saber onde pousar o olho primeiro.

Metafora curta:

1. nao basta acender varias luzes no painel
2. precisamos destacar qual luz esta no vermelho e qual esta so mostrando boa noticia

### Regra de honestidade

Essa priorizacao e executiva, nao matematica pesada.

Ela serve para triagem curta, nao para ranking cientifico.

## Onda 25 - recomendacao executiva curta

### Objetivo

Traduzir o alerta priorizado em uma proxima acao simples para a lideranca.

### Contrato atual

A board pode transformar alertas priorizados em recomendacoes como:

1. `Revisar processo de WhatsApp esta semana`
2. `Formalizar coach alinhado como boa pratica do box`
3. `Reforcar protocolo curto da recepcao nesta semana`

### Regra de produto

Isso nao vira plano de projeto.

E apenas uma instrucao curta, pronta para decisao de rotina.

### Regra de honestidade

A recomendacao nasce do tipo de alerta e da prioridade, nao de IA inventando estrategia profunda.

Ela aponta um proximo passo plausivel e curto, sem fingir que conhece todas as causas do problema.

Metafora curta:

1. o painel nao escreve a temporada inteira
2. ele so entrega a proxima jogada que faz sentido chamar do banco

## Onda 26 - resumo executivo semanal do box

### Objetivo

Fechar a leitura operacional inteira em uma linha que a lideranca consiga bater o olho e entender.

### Contrato atual

O resumo semanal do box junta tres respostas:

1. qual foi o principal ponto de ajuste
2. qual foi o melhor sinal de melhora
3. qual acao virou recomendacao principal

### Regra de produto

Isso nao substitui os cards abaixo.

Ele funciona como manchete executiva da semana, enquanto os outros blocos seguem como prova e detalhe.

### Regra de honestidade

Se a janela da semana ficar curta demais, o resumo continua usando o melhor sinal disponivel da janela atual, sem prometer mais do que sabe.

Metafora curta:

1. os cards sao o filme
2. o resumo semanal e o trailer certo para o dono do cinema entender a historia em 10 segundos

## Onda 28 - historico leve dos checkpoints semanais

### Objetivo

Permitir comparar semanas sem transformar a board em dashboard pesado.

### Contrato atual

O sistema mostra um historico curto dos checkpoints semanais com:

1. semana
2. status de execucao
3. responsavel
4. fechamento
5. nota curta

### Regra de produto

Isso e memoria de gestao, nao analytics historico pesado.

Serve para responder:

1. como a semana passada foi fechada
2. quem puxou o ritual
3. se a recomendacao andou, travou ou ficou parcial

Metafora curta:

1. nao e um mural de guerra
2. e um caderno com as ultimas paginas abertas para comparar a semana atual com as anteriores

## Onda 29 - mudanca de ritmo entre semanas

### Objetivo

Destacar quando o checkpoint semanal muda de marcha ou entra em padrao repetido.

### Contrato atual

O sistema pode sinalizar leituras como:

1. `Virada de execucao`
2. `Sequencia parcial`
3. `Sequencia funcionando`

### Regra de produto

Essa camada nao mede performance longa.

Ela apenas mostra mudancas curtas que valem um olho da lideranca, como:

1. sair de `Nao iniciado` para `Concluido`
2. acumular varias semanas em `Parcial`
3. acumular varias semanas em `Funcionou`

### Regra de honestidade

A leitura usa poucas semanas e assume que isso e um sinal tatico, nao uma conclusao estrutural.

Metafora curta:

1. nao e a tabela do campeonato inteiro
2. e perceber se os ultimos jogos mostram que o time engatou ou comecou a emperrar

## Onda 30 - sinal de maturidade operacional

### Objetivo

Traduzir o ritmo das ultimas semanas em um estado simples de maturidade do ritual.

### Contrato atual

O sistema pode classificar o ritual como:

1. `Saudavel`
2. `Instavel`
3. `Travado`
4. `Em formacao`
5. `Base curta`

### Regra de produto

Essa leitura resume o estado do ritual, nao o resultado do box inteiro.

Ela responde:

1. o ritual ja esta ficando repetivel?
2. ele oscila demais?
3. ele esta travando antes de acontecer?

### Regra de honestidade

O sistema usa poucas semanas e leitura tática.

Ou seja:

1. nao e nota final do processo
2. e um semaforo curto para saber se o ritual esta ficando saudavel, instavel ou travado

Metafora curta:

1. nao e o boletim da escola do ano inteiro
2. e o termometro dizendo se a febre baixou, oscila ou continua presa

## Onda 31 - acao de governanca baseada na maturidade

### Objetivo

Transformar o sinal de maturidade em um movimento claro de governanca.

### Contrato atual

Exemplos de resposta:

1. `Saudavel` -> formalizar ritual como padrao do box
2. `Travado` -> abrir destrave executivo do ritual
3. `Instavel` -> rodar ajuste curto antes de formalizar

### Regra de produto

A governanca so entra depois da leitura de maturidade.

Ou seja:

1. primeiro entendemos se o ritual esta saudavel, instavel ou travado
2. depois decidimos se isso vira norma, ajuste curto ou destrave forte

### Regra de honestidade

Isso nao promete resolver cultura por texto.

E apenas um proximo passo executivo coerente com a leitura atual.

Metafora curta:

1. o painel nao governa a empresa sozinho
2. ele so entrega a alavanca certa para a lideranca puxar no momento certo

## Onda 32 - compromisso semanal rastreavel

### Objetivo

Garantir que a acao de governanca nao fique so como boa intencao na board.

### Contrato atual

O checkpoint semanal passa a registrar se a lideranca:

1. ainda nao assumiu o compromisso
2. assumiu a decisao
3. executou a decisao

Tambem guarda uma nota curta do compromisso.

### Regra de produto

Isso cria uma trilha leve para responder:

1. a lideranca assumiu a decisao?
2. isso foi realmente executado na semana seguinte?

### Regra de honestidade

Isso continua sendo rastreio leve de compromisso, nao motor completo de tarefas.

Metafora curta:

1. a board nao vira um Jira
2. ela so deixa de ser promessa falada e vira item assinado no quadro da semana

## Debito tecnico evitado por esse contrato

Este contrato evita tres problemas classicos:

1. registrar acao sem saber se mudou algo
2. apagar historico quando o alerta some
3. transformar heuristica simples em monstro analitico cedo demais

## Resumo executivo

Hoje o loop esta assim:

1. o sistema ve o risco
2. sugere uma resposta
3. registra o retorno humano
4. compara antes e depois
5. mostra se melhorou, se ainda monitora ou se nao resolveu

Isso e suficientemente forte para operacao real e suficientemente leve para nao criar um foguete burocratico onde ainda precisamos de uma moto rapida.
