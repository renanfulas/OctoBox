<!--
ARQUIVO: arquitetura estrategica da rede OctoPASS para acesso, autorizacao e liquidacao.

TIPO DE DOCUMENTO:
- direcao arquitetural

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [architecture-growth-plan.md](architecture-growth-plan.md)

QUANDO USAR:
- quando a duvida for como o OctoBox pode evoluir de software operacional para trilho de acesso e liquidacao conectado a bancos, wallets e parceiros B2B

POR QUE ELE EXISTE:
- registra a visao do OctoPASS antes da implementacao para impedir que a ideia se perca ou nasca de forma confusa.
- separa claramente tese de produto, tese economica, fronteiras regulatorias e arquitetura futura.

O QUE ESTE ARQUIVO FAZ:
1. define o OctoPASS como camada futura de check-in, autorizacao e liquidacao.
2. explica por que o modelo pode competir com Wellhub e TotalPass por uma via diferente.
3. organiza os atores, fluxos e ganhos do ecossistema.
4. registra os riscos regulatorios, operacionais e tecnicos.
5. propoe uma ordem de maturacao para validar a tese sem misturar isso com o PWA atual.

PONTOS CRITICOS:
- OctoPASS nao e uma feature pequena; e uma nova camada de negocio e infraestrutura.
- pagamentos, beneficios e check-in por wallet tocam regulacao, compliance, antifraude e integracao bancaria real.
- o OctoBox nao deve tentar virar banco; deve ocupar a camada de orquestracao, identidade, presenca e reconciliacao.
-->

# OctoPASS

## Tese

O OctoPASS e a visao do OctoBox para transformar presenca validada em um evento economico confiavel usando wallet, NFC, trilha bancaria e parceiros B2B.

Em vez de depender de check-in manual em aplicativo e repasses lentos de intermediarios, o OctoPASS busca conectar:

1. identidade do aluno
2. presenca fisica no box ou academia
3. autorizacao do convenio ou beneficio
4. liquidacao financeira

O objetivo nao e construir um banco.

O objetivo e usar a infraestrutura do banco e dos parceiros para que o OctoBox ocupe a camada mais valiosa de orquestracao operacional.

## Nome operacional

OctoPASS e o nome da trilha futura de:

1. acesso
2. check-in
3. autorizacao
4. liquidacao
5. reconciliacao

## O problema que o OctoPASS quer resolver

Hoje, no modelo tradicional de convenios fitness:

1. o check-in depende de fluxo proprio do intermediario
2. a academia ou box depende do repasse de outra plataforma
3. ha espaco para fraude, atraso, divergencia e friccao
4. a margem do operador local e pressionada por taxas e tempo de espera

O OctoPASS nasce para inverter esse desenho.

## Tese de produto

O aluno nao precisa abrir um aplicativo e procurar um botao de check-in.

Ele chega ao box, apresenta sua credencial via wallet ou NFC, aproxima no terminal homologado e gera um evento de presenca validada.

Esse evento pode ser processado sobre a trilha do parceiro financeiro, enquanto o OctoBox registra:

1. quem chegou
2. em que box
3. em que janela
4. sob qual regra de elegibilidade
5. com qual efeito operacional e financeiro

## Tese competitiva

O OctoPASS nao tenta copiar Wellhub ou TotalPass na superficie.

Ele tenta atacar a estrutura do problema por outro angulo:

1. menos friccao no check-in
2. menos dependencia de repasse
3. menos fraude
4. mais proximidade entre presenca e liquidacao
5. mais alinhamento entre banco, box e plataforma

## Tese economica

Se 100 mil alunos movimentarem uma mensalidade media de R$ 200 por mes, o volume mensal de referencia e de R$ 20 milhoes.

Se o ecossistema chegar a 1 milhao de alunos com a mesma media, o volume mensal de referencia sobe para R$ 200 milhoes.

Esses numeros nao sao previsao contratual.

Eles sao a ilustracao do motivo economico pelo qual um banco, adquirente ou parceiro B2B pode se interessar pelo OctoPASS:

1. volume recorrente
2. previsibilidade
3. transacao frequente
4. relacao direta com ecossistema de saude e fitness

## Tese de ecossistema

O OctoPASS so faz sentido se todos os lados ganharem.

### Aluno

1. check-in mais simples
2. menos friccao
3. experiencia mais proxima de um passe nativo do celular

### Box ou academia

1. menos fraude
2. menos espera de repasse
3. mais previsibilidade de caixa
4. menos dependencia de intermediario classico

### Banco ou parceiro financeiro

1. mais dinheiro circulando dentro do proprio ecossistema
2. mais relacionamento com o segmento fitness
3. possibilidade de precificacao mais competitiva
4. maior volume recorrente

### OctoBox

1. deixa de ser apenas software interno
2. vira camada estrategica de conexao entre presenca e liquidacao
3. aumenta relevancia no fluxo economico do box
4. cria moat de produto e infraestrutura

## Definicao arquitetural

O OctoPASS deve ser tratado como uma rede composta por quatro camadas.

### 1. Credencial

A credencial do aluno vive na wallet do dispositivo ou em meio equivalente homologado.

Ela representa:

1. identidade
2. elegibilidade
3. vinculo com plano, beneficio ou convenio

### 2. Evento de presenca

Ao aproximar a credencial no terminal:

1. o terminal captura o evento
2. a trilha do parceiro valida a operacao
3. o OctoBox recebe ou reconcilia o evento autorizado

### 3. Autorizacao

A autorizacao decide:

1. se aquele aluno pode usar aquele box
2. em qual contexto
3. sob qual regra comercial ou de convenio
4. com qual efeito financeiro

### 4. Liquidacao

A liquidacao financeira usa a trilha do parceiro bancario ou B2B.

O OctoBox nao vira banco.

O OctoBox vira:

1. orquestrador
2. conciliador
3. observador confiavel do evento
4. camada de regra operacional do box

## O que o OctoPASS nao deve tentar ser

1. um banco proprio
2. um core de adquirencia feito do zero
3. um emissor completo sem parceiro
4. uma gambiarra de pagamento disfarcada de check-in

## Formatos possiveis de credencial

O desenho futuro pode usar uma ou mais formas:

1. Apple Wallet pass
2. Google Wallet pass
3. credencial NFC
4. tokenizacao equivalente homologada por parceiro

O formato final deve ser decidido pelo parceiro, pela regulacao e pela melhor ergonomia operacional.

## Fluxo conceitual

### Fluxo normal

1. aluno chega ao box
2. ativa ou apresenta sua credencial wallet/NFC
3. aproxima no terminal homologado
4. parceiro processa o evento
5. OctoBox recebe a confirmacao ou reconcilia a operacao
6. a presenca e registrada
7. o efeito financeiro e reconhecido no fluxo correto

### Resultado ideal

1. check-in validado
2. fraude reduzida
3. dinheiro menos preso em repasse de terceiro
4. box com leitura mais imediata do proprio caixa

## Vantagem contra fraude

O check-in por OctoPASS e mais forte do que um clique manual isolado porque:

1. exige presenca fisica com credencial
2. pode depender de trilha homologada
3. reduz check-in fantasma
4. reduz abuso de fluxo manual ou declaratorio

Fraude nao desaparece por magica.

Mas a superficie de fraude fica menor quando presenca e autorizacao se aproximam do evento fisico validado.

## Papel do WhatsApp, PWA e app mobile

OctoPASS nao substitui o PWA mobile.

O PWA mobile continua sendo a camada de:

1. acesso recorrente
2. leitura da grade
3. operacao humana
4. configuracao

O OctoPASS ocupa outro andar:

1. presenca
2. autorizacao
3. validacao de uso
4. liquidacao conectada

## Riscos e fronteiras

### 1. Regulacao

Pagamentos, beneficios, wallet e liquidacao tocam:

1. compliance
2. LGPD
3. antifraude
4. contrato com banco e B2B
5. possivel regulacao de arranjo ou credencial financeira

### 2. Dependencia de parceiro

Sem parceiro forte, OctoPASS nao se sustenta.

### 3. Operacao fisica

Terminal, wallet e NFC precisam funcionar de forma confiavel no mundo real.

### 4. Fallback

Se a trilha principal falhar, o box precisa continuar operando por rota controlada.

## Regra de posicionamento

O OctoBox nao deve competir tentando carregar no proprio colo o peso que o banco ja sabe carregar melhor.

O OctoBox deve competir onde o banco nao tem contexto suficiente:

1. identidade do aluno
2. regra do box
3. presenca operacional
4. conciliacao de uso
5. visao de produto do ecossistema fitness

## Ordem de maturacao recomendada

### Fase 0: tese registrada

1. documentar a visao
2. mapear parceiros potenciais
3. entender trilhas regulatorias

### Fase 1: prova de infraestrutura

1. validar modelo wallet
2. validar captura de evento
3. validar reconciliacao com o OctoBox

### Fase 2: prova de uso

1. pequeno piloto com boxes parceiros
2. medir friccao, fraude e confiabilidade

### Fase 3: prova economica

1. validar ganho de caixa para o box
2. validar modelo de receita do OctoBox
3. validar apetite real de banco e B2B

### Fase 4: trilha oficial

1. formalizar parceiros
2. endurecer compliance
3. escalar operacao

## Hipoteses que precisam ser validadas

1. o aluno aceita usar wallet como passe de entrada
2. o box confia no fluxo como substituto real de check-in tradicional
3. o banco ve incentivo economico suficiente
4. a trilha reduz fraude sem aumentar friccao
5. a liquidacao mais rapida melhora proposta de valor o bastante para mudar mercado

## Decisao arquitetural final

OctoPASS e uma tese estrategica oficial do OctoBox.

Ele deve ser tratado como um futuro trilho de acesso, autorizacao e liquidacao conectado a wallet, NFC e parceiros financeiros.

O OctoBox nao deve construir o banco.

O OctoBox deve construir a camada que faz presenca, elegibilidade, operacao e dinheiro conversarem de forma mais inteligente do que no modelo atual de convenios fitness.
