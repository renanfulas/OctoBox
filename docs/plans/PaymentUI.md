<!--
ARQUIVO: plano mestre da refatoracao da pagina financeira do aluno com foco em coerencia operacional e clareza cognitiva.

POR QUE ELE EXISTE:
- transforma a refatoracao da superficie financeira do aluno em uma frente guiada, iterativa e auditavel.
- fixa o filtro de baixa carga cognitiva para impedir que a pagina continue exigindo interpretacao demais da recepcao.
- organiza a implementacao por ondas sem incentivar rewrite destrutivo ou simplificacao burra.

O QUE ESTE ARQUIVO FAZ:
1. define a tese central da Payment UI do aluno.
2. registra o perfil cognitivo do usuario-alvo e a passagem visual operacional.
3. mapeia dores atuais do runtime sem separar UI de estado e regra de negocio.
4. estrutura as ondas de implementacao e os criterios de pronto.

PONTOS CRITICOS:
- simplificar a experiencia nao pode destruir contexto financeiro importante.
- clareza de balcao nao significa esconder risco operacional ou estado real.
- nenhuma mudanca deve gerar botao placebo, KPI mentiroso ou acao sensivel sem protecao proporcional.
-->

# PaymentUI

## Tese central

A pagina financeira do aluno no OctoBOX deve operar como um cockpit coerente e legivel, nao como uma colagem de blocos que exigem interpretacao do operador.

Os dois eixos inseparaveis deste plano sao:

1. coerencia entre interface, estado e regra de negocio
2. clareza operacional extrema sob a lente de uma recepcionista com baixa carga cognitiva

Em linguagem simples:

1. se a tela manda clicar e nada conversa depois, ela esta quebrada
2. se a tela exige pensar demais antes de agir, ela ainda nao esta pronta
3. se o operador precisa adivinhar o que aconteceu, a pagina falhou

## Norte operacional

Esta superficie deve obedecer a estas verdades:

1. o proximo passo precisa ficar obvio em poucos segundos
2. cada botao precisa ter efeito previsivel e retorno confiavel
3. pagamento, atraso, plano e matricula devem parecer partes do mesmo sistema
4. a recepcao nao pode carregar o peso mental de um modulo financeiro completo
5. simplificacao so entra quando preserva seguranca, contexto e rastreabilidade

## Perfil cognitivo do usuario-alvo

Toda avaliacao desta pagina deve assumir o seguinte perfil operacional:

1. recepcionista cansada
2. atendimento interrompido
3. pressa
4. leitura superficial
5. pouca margem para interpretar estados ambiguos
6. pouca paciencia para multiplas acoes paralelas

Traducao pratica:

1. a tela precisa orientar sem exigir raciocinio longo
2. o proximo passo precisa estar obvio
3. o sistema nao pode depender de entendimento implicito
4. se houver duvida entre dois botoes, a pagina ainda esta confusa

Filtro oficial de qualidade:

`isso funciona no balcao para alguem com baixa carga cognitiva?`

Filtro complementar:

`uma recepcionista de 80 de QI entende o que fazer em poucos segundos?`

## Passagem visual operacional

Antes de considerar qualquer rodada como boa, a superficie precisa passar por uma leitura operacional simulada.

Cada rodada deve responder explicitamente:

1. onde o olho bate primeiro
2. o que parece acao principal
3. existe mais de um botao parecendo principal
4. existe texto que obriga a pensar demais
5. existe card que informa, mas nao ajuda a agir
6. existe alguma acao cujo efeito nao e previsivel
7. existe alguma decisao que o sistema poderia tomar pela recepcionista
8. existe algum ponto em que a pagina parece esperta demais para o contexto de balcao

Cada rodada deve terminar com um laudo curto:

1. `CONFUSO`
2. `ACEITAVEL`
3. `CLARO`
4. `CLIMAX OPERACIONAL`

Em linguagem simples:

esse laudo funciona como semaforo. Se nao estiver verde, ainda nao chegamos no ponto certo.

## Mapa de dores atuais do runtime

O runtime atual ja mostra sinais claros de desconexao entre superficie, estado e logica.

### Dores confirmadas

1. ha botoes que existem na interface, mas nao entregam fluxo completo
2. ha acoes sensiveis que ainda dependem de `prompt`, `alert` ou submit direto sem protecao proporcional
3. cards e KPIs pedem leituras que o snapshot nem sempre calcula de forma completa
4. drawers e acoes rapidas nem sempre abrem com o contexto correto do item
5. algumas mutacoes ainda dependem de `reload` em vez de contrato claro de recomposicao
6. `Cobrar agora` e `Gestao ampliada` ja foram separados visualmente, mas ainda nao leem do mesmo circuito com maturidade suficiente

### Classificacao das dores

#### Botao placebo ou incompleto

1. qualquer acao que pareca pronta, mas ainda dependa de placeholder ou comportamento parcial

#### Atualizacao mentirosa

1. qualquer card, KPI ou bloco visual que continue desatualizado depois de uma mutacao relevante

#### Protecao insuficiente

1. qualquer acao sensivel sem confirmacao proporcional ao risco

#### Contexto quebrado

1. qualquer drawer ou fluxo que abra sem carregar o objeto certo

#### Excesso cognitivo

1. qualquer ponto em que a pagina peca mais leitura, memoria ou comparacao do que o balcao suporta

## Guardrails de seguranca e contexto

Estas regras nao podem ser rompidas:

1. nenhum botao importante pode ser placebo
2. nenhuma acao sensivel pode acontecer sem confirmacao quando houver risco real
3. nenhum KPI ou card pode continuar mostrando dado desatualizado apos mutacao relevante
4. `Cobrar agora` e `Gestao ampliada` devem continuar separados, mas lendo do mesmo estado real
5. simplificacao agressiva que destrua contexto e proibida
6. mudança cosmetica que esconda problema de logica e proibida
7. refactor que aumente debito tecnico ou risco operacional e proibido

Guardrails visuais:

1. o CTA principal deve ser encontrado sem esforco
2. o status do aluno precisa ser legivel rapidamente
3. o atraso precisa ficar claro sem dramatizacao decorativa
4. cards devem orientar decisao, nao enfeitar a tela

## Ondas de implementacao

## Onda 1

### Foco

remover friccao obvia, placebo e risco

### O que muda

1. acoes fake ou incompletas
2. confirmacao de acoes sensiveis
3. botoes com semantica fraca
4. pontos de ambiguidade imediata

### Criterio de pronto

1. nenhuma acao importante parece vazia
2. nenhuma acao sensivel parece perigosa ou impulsiva
3. o operador entende o que cada botao faz antes de clicar

## Onda 2

### Foco

fazer o estado conversar com a superficie

### O que muda

1. KPIs inconsistentes
2. recomposicao apos mutacao
3. contratos de retorno entre backend e frontend
4. atualizacao visual coerente de cards, ledger, vinculo e proxima acao

### Criterio de pronto

1. a pagina reflete o que realmente aconteceu
2. o operador nao precisa recarregar mentalmente a tela depois da acao
3. o circuito entre persistencia e leitura visual fica confiavel

## Onda 3

### Foco

reduzir esforco mental da leitura

### O que muda

1. hierarquia
2. peso dos CTAs
3. excesso de escolhas
4. microcopy operacional
5. competicao visual entre blocos

### Criterio de pronto

1. a recepcionista entende o fluxo sem parar para interpretar
2. o proximo passo aparece antes do excesso
3. a tela deixa de parecer inteligente demais e passa a parecer prestativa

## Onda 4

### Foco

passagem visual iterativa ate o climax operacional

### O que muda

1. ajustes finos de leitura
2. simplificacao saudavel
3. corte de ruido residual
4. alinhamento entre balcao rapido e gestao ampliada

### Criterio de pronto

1. o fluxo parece natural, seguro e quase autoexplicativo
2. nao existe medo de clicar no botao errado
3. a pagina chega ao estado `CLIMAX OPERACIONAL`

## Criterio de climax operacional

A pagina atinge o climax operacional quando:

1. o proximo passo fica obvio sem esforco
2. nao existe medo de clicar no botao errado
3. acoes sensiveis tem protecao proporcional
4. pagamento, plano, matricula e atraso parecem partes do mesmo sistema
5. KPIs nao sao decoracao; ajudam a agir
6. a recepcionista consegue explicar o que fazer agora em uma frase curta
7. nao ha sensacao de `preciso pensar para usar`

Em linguagem simples:

chegamos no climax quando a tela para de pedir interpretacao e comeca a conduzir com tranquilidade.

## Contrato de output por onda

Toda rodada futura desta frente deve usar este painel no topo:

```md
Status:
- Onda:
- Foco:
- Decisao central:
- Principal risco:
- Proximo passo:
```

Depois responder nestes blocos:

1. `Passagem visual`
2. `O que esta confuso`
3. `O que melhora nesta rodada`
4. `Riscos`
5. `Validacao`
6. `Resultado da rodada`

### Limite de resposta

1. cada onda deve ter no maximo 800 palavras
2. pode usar menos quando a decisao estiver clara
3. se faltar espaco, cortar ornamentacao antes de cortar decisao

## Testes e cenarios

### Leitura em 3 segundos

1. qual e a acao principal
2. qual e o status do aluno
3. existe atraso
4. da para cobrar agora

### Previsibilidade

1. o que acontece ao clicar
2. o retorno e claro
3. o drawer abre no item certo

### Seguranca

1. congelamento
2. cancelamento
3. reativacao
4. outras acoes com impacto real

### Atualizacao de estado

1. cards
2. KPIs
3. ledger
4. vinculo
5. proxima acao

### Carga cognitiva

1. quantas decisoes a recepcionista precisa tomar para concluir uma cobranca
2. quantos elementos competem pela atencao
3. ha texto demais para o contexto
4. ha mais de um caminho parecendo principal

## Criterio de pronto final

Esta frente estara pronta quando:

1. cada botao importante tiver efeito real e previsivel
2. cada acao sensivel tiver confirmacao adequada
3. pagamento, atraso, plano e matricula atualizarem a leitura visual correta
4. KPIs e cards refletirem o estado persistido
5. drawers abrirem no contexto certo
6. a pagina nao depender de adivinhacao do operador
7. `Cobrar agora` e `Gestao ampliada` parecerem partes do mesmo sistema
8. a passagem visual final terminar em `CLIMAX OPERACIONAL`

## Assumptions e defaults

1. este documento vive em `docs/plans/PaymentUI.md`
2. `RefactorPayment.md` continua como baseline geral de pagamentos
3. `PaymentUI.md` e o plano especifico da pagina financeira do aluno
4. a estrategia desta frente e iterativa e conservadora
5. a regra final e melhorar sem quebrar, simplificar sem amputar e integrar sem reescrever tudo
