<!--
ARQUIVO: arquitetura da iniciativa de growth engine do OctoBox.

TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta para a tese estrutural da camada de crescimento comercial e sua relacao com leads, operacao humana, ML e expansao

DOCUMENTO PAI:
- [architecture-growth-plan.md](architecture-growth-plan.md)

DOCUMENTOS IRMAOS:
- [operational-intelligence-ml-layer.md](operational-intelligence-ml-layer.md)
- [../reference/lead-attribution-ml-foundation.md](../reference/lead-attribution-ml-foundation.md)

QUANDO USAR:
- quando a duvida for como o OctoBox deve estruturar uma frente de crescimento comercial para boxes
- quando a duvida for onde outbound, playbook de vendas, follow-up e priorizacao por ML devem morar sem contaminar o core transacional
- quando a duvida for qual e o momento certo para ativar essa frente dentro da maturidade do produto

POR QUE ELE EXISTE:
- transforma a ambicao comercial de medio e longo prazo do OctoBox em arquitetura de produto e operacao, nao em discurso solto.
- impede que a frente de crescimento nasca como improviso em CRM generico, planilha ou automacao rasa.
- formaliza a separacao entre captacao de leads, execucao comercial humana, intelligence layer e verdade transacional do box.
- registra que essa frente so deve entrar quando o produto tiver escala e fundacao suficientes.

O QUE ESTE ARQUIVO FAZ:
1. define a tese do growth engine do OctoBox.
2. separa aquisicao, qualificacao, execucao comercial, fechamento e expansao de capacidade.
3. estabelece guardrails para ML, reputacao e operacao humana intensiva.
4. organiza a ordem de implantacao dessa frente em fases seguras.

PONTOS CRITICOS:
- promessa comercial sem base operacional vira ruido e frustracao.
- ML nao pode decidir sozinho quem e descartado ou qual verdade comercial passa a ser canonica.
- essa frente nao deve nascer acoplada a WhatsApp automation, nem depender de uma unica origem de lead.
- esta iniciativa nao deve entrar antes da maturidade de produto e do preparo para multitenancy.
-->

# OctoBox Growth Engine

## Tese central

O OctoBox pode evoluir de sistema operacional de box para `growth engine especializado para boxes`.

A ideia central e simples:

1. o software nao apenas registra leads
2. o software organiza uma operacao comercial humana de alta intensidade
3. o software ajuda cada box a fechar mais alunos com processo, disciplina e priorizacao inteligente

Em linguagem curta:

1. marketing encontra o minerio
2. o motor de growth lapida o diamante
3. o box recebe alunos convertidos, recorrencia e pressao positiva de crescimento

## Declaracao de posicionamento

Nesta iniciativa, o OctoBox passa a sustentar uma frente especializada em crescimento comercial para o mercado fitness.

Nao como automacao fria.

Nao como disparo cego por WhatsApp.

Mas como uma `estrutura de growth comercial disciplinada e orientada por dados`, onde cada box pode operar com:

1. setor comercial especializado
2. playbooks de cold call
3. cadencias de follow-up
4. tecnicas de conversao
5. roteiros de indicacao
6. reativacao de leads quentes
7. leitura de capacidade do box e necessidade de expansao

## Horizonte e momento correto

Esta frente nao e prioridade de curto prazo.

Ela fica registrada como `iniciativa de medio e longo prazo`.

Regra de ativacao:

1. so deve entrar quando o OctoBox tiver aproximadamente `80 a 100 clientes`
2. so deve entrar quando a base estiver pronta para `multitenancy`
3. so deve entrar quando os contratos atuais de core, operacao e observabilidade estiverem estaveis
4. so deve entrar depois de validacao com `early adopters`

Traducao simples:

1. nao vamos colocar motor de foguete em bicicleta
2. primeiro a bicicleta vira carro confiavel
3. depois instalamos a turbina

## O problema que essa frente resolve

Muitos boxes ate geram interesse, mas perdem dinheiro entre a curiosidade do lead e a matricula.

O vazamento costuma acontecer assim:

1. lead entra
2. ninguem responde com ritmo
3. nao existe dono claro da oportunidade
4. nao existe cadencia de contato
5. nao existe argumento comercial ajustado ao perfil
6. nao existe priorizacao real do que merece ligacao agora

Resultado:

1. o box acha que falta lead
2. mas muitas vezes falta `estrutura de conversao`

Metafora simples:

1. gerar lead sem operacao comercial e como encher um balde furado
2. parece que falta agua
3. mas o problema real e o furo

## Regra-mestra

No OctoBox Growth Engine:

1. `o fechamento continua humano`
2. `o sistema organiza prioridade, contexto e proxima melhor acao`
3. `ML recomenda, mas nao substitui o vendedor`
4. `a promessa comercial deve ficar levemente acima do limite, mas ainda dentro do crivel`

Traducao pratica:

1. o produto ajuda o vendedor a mirar no peixe maior
2. mas o arpao ainda e humano

## Tese de promessa comercial

O OctoBox nao deve vender milagre.

Tambem nao deve vender uma promessa timida demais.

A faixa correta e:

1. promessa ousada
2. linguagem forte
3. base defensavel
4. compromisso operacional claro

Regra:

1. a promessa pode ficar levemente acima do limite
2. mas nao pode atravessar a linha da fantasia

Exemplos de territorio seguro:

1. mais previsibilidade comercial
2. melhor velocidade de resposta
3. mais disciplina de follow-up
4. melhor conversao da operacao
5. leitura mais clara do momento de expandir

## Nao-objetivos desta frente

Para evitar desvio de arquitetura, esta frente nao nasce para:

1. virar ferramenta de spam
2. automatizar WhatsApp como motor principal
3. disparar promessa de saude de forma irresponsavel
4. tratar persuasao como manipulacao sem contexto
5. transformar score em desculpa para ignorar auditoria e operacao
6. virar uma feature principal antes de a base SaaS estar pronta

## Estrutura conceitual da maquina de growth

O Growth Engine deve crescer em seis blocos.

### 1. Lead Acquisition Layer

Responsavel por:

1. consolidar leads de Instagram, site, landing pages, formularios, indicacao, parceria B2C e captura manual
2. registrar origem declarada e origem operacional
3. medir qualidade de entrada por canal

Pergunta que responde:

1. de onde veio a oportunidade?

### 2. Qualification and Enrichment Layer

Responsavel por:

1. enriquecer lead com contexto do interesse
2. registrar perfil, objetivo, faixa de horario, friccoes e urgencia
3. separar sinal cru de dado confirmado

Pergunta que responde:

1. esse lead parece promissor, para qual argumento e para qual oferta?

### 3. Human Outbound Execution Layer

Responsavel por:

1. organizar cold call
2. organizar follow-up por vendedor
3. definir cadencias e proximas tarefas
4. registrar objecoes, respostas e avancos reais

Pergunta que responde:

1. quem precisa agir agora, com quem, por qual canal e com qual discurso?

### 4. Conversion Layer

Responsavel por:

1. mover oportunidade para aula experimental, visita, oferta, fechamento e matricula
2. conectar promessa comercial com plano, onboarding e pagamento
3. registrar razoes de ganho e perda

Pergunta que responde:

1. o lead virou aluno ou escapou? por que?

### 5. Capacity and Expansion Layer

Responsavel por:

1. medir ocupacao do box
2. relacionar performance comercial com capacidade operacional
3. sinalizar quando a unidade esta enchendo e precisa abrir nova estrutura, horario ou frente

Pergunta que responde:

1. estamos vendendo abaixo da capacidade ou empurrando o box para expandir?

### 6. Commercial Intelligence and ML Layer

Responsavel por:

1. priorizar leads
2. sugerir proxima melhor acao
3. prever chance de conversao
4. medir produtividade comercial por origem, perfil e argumento
5. captar nuances finas do lead para aumentar precisao comercial

Pergunta que responde:

1. onde esta o ouro mais facil de escavar agora?

## Onde essa frente mora no predio

A leitura arquitetural correta fica assim:

### Core transacional

Responsavel por:

1. lead intake
2. cadastro oficial
3. aluno
4. plano
5. matricula
6. pagamento

### Growth Engine

Responsavel por:

1. oportunidade comercial
2. pipeline
3. tarefa de follow-up
4. cadencia
5. contato comercial
6. script e argumento
7. motivo de perda
8. razao de ganho

### ML Layer

Responsavel por:

1. score de conversao
2. score de prioridade
3. propensao de resposta
4. confianca do perfil
5. recomendacao operacional

Regra:

1. o core guarda a verdade oficial
2. o Growth Engine guarda a guerra comercial organizada
3. o ML Layer ajuda a mirar melhor

## Entidades que precisam existir

Para essa frente nao virar logica espalhada em anotacao, comentario e planilha, o produto deve crescer com entidades claras.

### Lead

Representa:

1. a pessoa ou oportunidade em fase pre-comercial ou comercial

Campos principais:

1. identificadores basicos
2. origem operacional
3. origem comercial declarada
4. perfil inicial
5. status de qualificacao
6. score atual
7. nuances comportamentais e contextuais

### Sales Opportunity

Representa:

1. a oportunidade comercial viva

Campos principais:

1. stage atual
2. owner comercial
3. temperatura
4. ultima acao
5. proxima acao
6. deadline da proxima acao
7. razao principal de interesse

### Sales Activity

Representa:

1. cada toque comercial real

Campos principais:

1. tipo da acao
2. canal
3. outcome
4. resumo da conversa
5. objecoes
6. proximo passo

### Sales Cadence

Representa:

1. o plano tatico de tentativa por janela temporal

Campos principais:

1. tipo de cadencia
2. numero maximo de tentativas
3. espacamento
4. gatilhos de pausa
5. gatilhos de encerramento

### Sales Playbook

Representa:

1. o roteiro operacional para determinado perfil ou objecao

Campos principais:

1. publico-alvo
2. script de abertura
3. perguntas de descoberta
4. objecoes mapeadas
5. provas de valor
6. CTA final

### Sales Outcome

Representa:

1. o fechamento, perda ou congelamento da oportunidade

Campos principais:

1. ganho ou perda
2. motivo
3. plano vendido
4. valor
5. tempo ate conversao
6. quem fechou

## Pipeline comercial recomendado

O pipeline inicial pode nascer assim:

1. `new`
2. `qualified`
3. `contacting`
4. `conversation_open`
5. `trial_scheduled`
6. `trial_completed`
7. `offer_presented`
8. `closing`
9. `won`
10. `lost`
11. `recycle`

Regra:

1. stage precisa refletir estado comercial observavel
2. stage nao pode virar poesia ou campo subjetivo demais

## Cadencias humanas oficiais

Como a tese nao depende de WhatsApp automation, a cadencia inicial deve ser `human-first`.

Exemplos de canais permitidos nessa fase:

1. cold call
2. ligacao de follow-up
3. mensagem manual
4. indicacao pedida ativamente
5. abordagem de retorno para lead parado
6. convite para aula experimental

Regra:

1. toda tentativa precisa virar dado
2. contato sem registro e como treino sem anotacao: voce sua muito, mas nao aprende o padrao

## Camada de playbooks e metodologia

O sistema nao deve guardar apenas nomes e telefones.

Ele deve guardar `metodologia operacional de conversao`.

Isso significa suportar:

1. scripts por perfil de lead
2. argumentacao por objetivo do aluno
3. tratamento de objecoes
4. roteiros de indicacao
5. gatilhos de urgencia legitimos
6. provas sociais e resultados reais
7. proposta comercial adequada ao momento do lead

Exemplos de perfis:

1. emagrecimento
2. performance
3. saude e qualidade de vida
4. retorno a atividade fisica
5. aluno que parou e pode voltar
6. lead vindo de indicacao

## Especialista humano como camada de metodo

Quando essa frente for ativada, o desenho operacional deve incluir um `expert humano de vendas`.

Papel desse especialista:

1. desenhar treinamento
2. calibrar playbooks
3. revisar objecoes
4. orientar a metodologia inicial
5. ajudar a transformar pratica de campo em processo reproduzivel

Regra:

1. o especialista entra para cristalizar metodo
2. o especialista nao deve virar gargalo operacional permanente

Traducao simples:

1. ele ajuda a escrever a partitura
2. depois a orquestra precisa conseguir tocar sem depender dele em cada nota

## Papel do machine learning

O ML entra como `arma de foco`, nao como arma de substituicao humana.

Primeiras saidas seguras:

1. `conversion_propensity_score`
2. `follow_up_priority_score`
3. `contact_window_recommendation`
4. `lead_quality_score`
5. `reason_codes`

Perguntas que o modelo pode responder:

1. quais leads parecem mais prontos para fechar?
2. quais leads precisam de resposta imediata?
3. quais perfis historicamente fecham melhor para cada tipo de box?
4. quais canais entregam mais conversa util, nao apenas volume?
5. quais nuances de comportamento, origem, timing e objecao se repetem nos melhores fechamentos?

Regra:

1. o score ajuda a ordenar a fila
2. ele nao autoriza tratar gente como lixo nem abandonar auditoria

### Nuances que o ML deve aprender

O valor do ML aqui nao esta em parecer magico.

O valor esta em enxergar detalhes que o olho humano isolado perde quando a fila cresce.

Exemplos:

1. horario de resposta com maior taxa de retorno
2. combinacao entre origem e objetivo do lead
3. objecoes mais frequentes por perfil
4. probabilidade de comparecer a aula experimental
5. probabilidade de fechar apos determinado tipo de abordagem
6. diferenca entre lead curioso e lead pronto para decisao

Regra:

1. nuance boa vira prioridade melhor
2. prioridade melhor vira energia comercial melhor alocada

## Data products que precisam nascer

Antes de treinar modelo serio, o OctoBox precisa consolidar produtos de dado reproduziveis.

### Lead Performance Snapshot

1. volume por canal
2. taxa de contato
3. taxa de resposta
4. taxa de visita
5. taxa de fechamento

### Sales Productivity Snapshot

1. atividades por vendedor
2. tentativas por lead
3. tempo medio ate primeiro contato
4. tempo medio ate fechamento
5. ganho e perda por motivo

### Conversion Journey Snapshot

1. tempo entre lead e trial
2. tempo entre trial e oferta
3. tempo entre oferta e pagamento
4. gargalos por stage

### Capacity Pressure Snapshot

1. ocupacao atual
2. slots restantes
3. pressao comercial por horario
4. momento de expansao sugerido

## Ponte futura com expansion intelligence

No medio e longo prazo, o Growth Engine deve se conectar a uma camada complementar de `expansion intelligence`.

Essa camada futura deve responder:

1. quando o box esta perto de saturacao saudavel
2. quando vale abrir novos horarios
3. quando vale abrir nova unidade
4. quais regioes mostram melhor relacao entre demanda e viabilidade
5. como conectar expansao com parceiros, credito e tese financeira

Importante:

1. isso e uma frente futura
2. ela nao deve ser misturada com a primeira implantacao do Growth Engine
3. a ponte existe, mas a execucao deve ser faseada

## Superficies de produto

Essa frente deve aparecer no produto em telas muito claras.

### 1. Growth Command Center

Para:

1. leitura executiva
2. fila priorizada
3. indicadores por box
4. gargalos do funil

### 2. Opportunity Workspace

Para:

1. trabalhar um lead individual
2. ver historico de contatos
3. registrar objecoes
4. escolher proximo passo

### 3. Cadence Board

Para:

1. listar tarefas vencidas
2. listar follow-ups do dia
3. medir disciplina comercial

### 4. Playbook Console

Para:

1. manter scripts
2. testar argumentos
3. comparar taxa de conversao por abordagem

### 5. Expansion Radar

Para:

1. relacionar vendas, ocupacao e necessidade de nova unidade ou horario

## Integracoes esperadas

Essa frente deve aceitar sinais de:

1. Instagram ads e landing pages
2. site institucional
3. formularios internos
4. parceiros B2C
5. captacao manual da recepcao ou do time comercial

Importante:

1. a frente pode registrar mensagem manual enviada por WhatsApp
2. mas `nao deve depender de automacao por WhatsApp` como pilar da arquitetura inicial

## Guardrails de reputacao e controle operacional

Uma operacao comercial de alta energia precisa nascer com controle, mesmo quando o publico ja demonstra interesse previo em atividade fisica.

Por isso, o Growth Engine deve nascer com:

1. limite de tentativas por janela
2. opt-out claro
3. bloqueio de contato abusivo
4. trilha de auditoria por vendedor
5. script review por playbook
6. motivos de perda e reclamacao registrados

Metafora simples:

1. um carro de corrida sem freio nao e mais rapido
2. ele so bate mais cedo

## Riscos arquiteturais

### 1. Confundir growth engine com CRM glorificado

Risco:

1. registrar dado sem gerar disciplina operacional

Correcao:

1. priorizar fila, tarefa, proxima acao e ownership

### 2. Acoplar score ao core cedo demais

Risco:

1. inferencia virar verdade transacional escondida

Correcao:

1. manter score em camada explicita, versionada e auditavel

### 3. Focar so em lead volume

Risco:

1. o box compra trafego, mas nao compra conversao

Correcao:

1. medir jornada completa ate matricula e pagamento

### 4. Nascer dependente de um canal

Risco:

1. qualquer mudanca externa mata a captacao

Correcao:

1. manter arquitetura multicanal desde o inicio

### 5. Vendedor forte sem metodo reproduzivel

Risco:

1. performance fica presa em talento individual e nao vira sistema

Correcao:

1. transformar tecnica em playbook versionado

### 6. Entrar cedo demais

Risco:

1. criar uma frente sofisticada antes de o SaaS estar pronto para escalar

Correcao:

1. travar a iniciativa atras do marco de `80-100 clientes` e preparo para `multitenancy`

## Ordem de implantacao recomendada

### Fase 0: Maturidade de base

Precondicoes:

1. OctoBox operando com aproximadamente `80-100 clientes`
2. observabilidade de produto estabilizada
3. contratos de dados mais confiaveis
4. caminho de multitenancy preparado
5. early adopters selecionados para validacao desta frente

Objetivo:

1. ativar essa trilha na hora certa, nao cedo demais

### Fase 1: Fundacao comercial

Entregas:

1. modelo de oportunidade
2. registro de atividades comerciais
3. pipeline minimo
4. fila de follow-up
5. motivos de ganho e perda

Objetivo:

1. sair do improviso e criar disciplina

### Fase 2: Playbooks e cadencias

Entregas:

1. scripts por perfil
2. cadencias por tipo de lead
3. workspace de objecoes
4. metricas de produtividade comercial

Objetivo:

1. transformar talento em metodo

### Fase 3: Priorizacao inteligente

Entregas:

1. snapshots consolidados
2. regras heuristicas de prioridade
3. janela recomendada de contato
4. ranking operacional de oportunidades

Objetivo:

1. fazer o time gastar energia onde ha mais chance de retorno

### Fase 4: ML supervisionado

Entregas:

1. score de conversao
2. score de follow-up
3. reason codes
4. comparacao entre vendedor, canal e perfil

Objetivo:

1. transformar historico em mira mais precisa

### Fase 5: Expansion intelligence

Entregas:

1. radar de capacidade
2. previsao de saturacao
3. gatilhos de abertura de nova operacao

Objetivo:

1. usar a venda para empurrar crescimento real do box, nao apenas inflar vaidade comercial

## Regra final de produto

O OctoBox Growth Engine nao deve ser lido como "mais um CRM".

Ele deve ser lido como:

1. captacao organizada
2. operacao comercial humana de elite
3. metodo reproduzivel
4. inteligencia assistida por ML
5. crescimento com leitura de capacidade

Resumo final:

1. leads entram
2. vendedores atacam com metodo
3. o sistema prioriza
4. o box converte
5. a lotacao sobe
6. a expansao deixa de ser sonho e vira necessidade operacional mensuravel
