<!--
ARQUIVO: guia de metodologia e organizacao viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de metodologia
- guia de organizacao

AUTORIDADE:
- media para onboard e rotina de trabalho

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [../reference/reading-guide.md](../reference/reading-guide.md)
- [../../.specs/codebase/CONVENTIONS.md](../../.specs/codebase/CONVENTIONS.md)
- [../history/v1-retrospective.md](../history/v1-retrospective.md)

QUANDO USAR:
- quando a duvida for como o time organiza pensamento, codigo e docs hoje
- quando for explicar a maturidade do projeto alem do codigo
- quando for evitar repeticao de caos que costuma aparecer em projetos que crescem rapido
-->

# Guia de metodologia e organizacao

## A mudanca mais importante

O projeto ficou mais eficiente nao apenas porque o codigo melhorou.

Ele ficou mais eficiente porque hoje existe menos improviso na forma de pensar, registrar, localizar e revisar.

Em linguagem simples:

1. antes voce tinha um atleta talentoso correndo muito
2. agora voce tem esse atleta com mapa, relogio, treino e quadro tatico

## O que o projeto passou a usar de forma recorrente

### 1. Precedencia documental

Hoje a documentacao nao e mais um monte de arquivos soltos.

Existe uma hierarquia clara:

1. runtime real e testes
2. README
3. architecture
4. plans
5. reference
6. rollout
7. experience
8. diagnostics e reports
9. history

Isso e valioso porque impede tratar:

1. retrospectiva como regra viva
2. plano antigo como mandato eterno
3. doc inspiracional como contrato tecnico

### 2. C.O.R.D.A.

O projeto hoje pensa melhor em frentes porque usa uma forma de diagnostico mais consciente:

1. `Contexto`
2. `Objetivo`
3. `Riscos`
4. `Direcao`
5. `Acoes`

Esse metodo ficou mais eficiente que o inicio porque ajuda a evitar o erro classico de polir superficie antes de resolver a estrutura.

### 3. Autodocumentacao de arquivo

Os cabecalhos de arquivo ajudam muito porque:

1. reduzem o custo de retorno ao codigo
2. deixam o motivo da existencia mais explicito
3. tornam a base mais ensinavel para quem esta chegando

### 4. Ownership mais claro

O projeto amadureceu em organizacao porque hoje a pergunta "quem cuida disso?" esta menos nebulosa.

Exemplos:

1. docs de ownership no frontend
2. promoted facades map para imports
3. reading guide para navegacao do runtime
4. separacao mais clara entre apps reais e ancora historica

## O que ficou melhor em relacao ao inicio

### Metodologia

Antes:

1. o projeto ja tinha boa intuicao arquitetural
2. mas ainda dependia mais do contexto recente de quem estava trabalhando

Agora:

1. existe um sistema melhor para orientar decisoes
2. existe trilha de leitura
3. existe mapa de autoridade
4. existe plano por frente
5. existe criterio melhor para saber se um documento e tese, execucao, referencia ou historia

### Organizacao de codigo

Antes:

1. a separacao por dominio ja era boa
2. mas varias partes ainda eram explicadas pelo legado

Agora:

1. o runtime novo ja promove caminhos canonicos
2. o codigo novo tem menos desculpa para nascer no lugar errado
3. a separacao entre leitura, mutacao e apresentacao esta mais visivel

### Organizacao de frontend

Antes:

1. havia boas telas
2. mas ainda com risco de virar mosaico

Agora:

1. existe mapa de cidade
2. existe padrao oficial de organizacao
3. existe plano de reestruturacao
4. existe plano mestre de performance

### Organizacao operacional

Antes:

1. a base era forte
2. mas a operacao ainda tinha menos protocolos institucionais

Agora:

1. existem runbooks
2. existem smoke checklists
3. existem check commands
4. existem docs de backup, restore, rollback e deploy

## Regras simples para manter a organizacao boa

1. documento profundo nao deve competir com documento-guia
2. view HTTP nao deve virar deposito de regra
3. app historico nao deve voltar a ser resposta automatica para codigo novo
4. CSS local nao deve resolver problema global no grito
5. plano ativo manda na frente; retrospectiva ensina, mas nao governa

## Sinais de que estamos melhor do que no inicio

1. ha menos conhecimento escondido so na cabeca de quem editou por ultimo
2. ha mais caminhos canonicos para leitura e escrita
3. ha mais infraestrutura de medicao e observacao
4. ha mais guardrails contra abuso, regressao e drift
5. ha menos necessidade de "caça ao tesouro" para entender ownership

## Sinais de perigo

1. criar novo doc sem dizer se ele e tese, plano, referencia ou historia
2. escrever novo codigo direto no legado quando ja existe corredor promovido
3. fazer ajuste rapido que esconde acoplamento em vez de resolver ownership
4. deixar a documentacao-guia envelhecer enquanto os docs profundos mudam

## Regra pedagógica do projeto

Quando algo ficar complexo, explique em duas camadas:

1. a camada infantil
   "o que isso faz no predio?"
2. a camada tecnica
   "qual e o contrato, a fronteira e o ownership?"

Esse jeito de explicar virou uma vantagem real do projeto porque ajuda onboarding sem sacrificar rigor.
