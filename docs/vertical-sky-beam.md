<!--
ARQUIVO: formalizacao do Vertical Sky Beam como escalada maxima de emissao visivel do Red Beacon para estados criticos.

POR QUE ELE EXISTE:
- transforma a imagem do feixe vertical extremo em uma peça arquitetural controlada e rara.
- separa a emissao extraordinaria de alerta critico da emissao normal do Red Beacon.

O QUE ESTE ARQUIVO FAZ:
1. define o que e o Vertical Sky Beam.
2. explica quando ele pode ser ativado.
3. estabelece limites para que ele nao vire ruido constante.

PONTOS CRITICOS:
- o Vertical Sky Beam e um modo de escalada excepcional, nao um estado rotineiro.
- se ele disparar com frequencia, perde sentido operacional e destrói a confiabilidade do topo do predio.
-->

# Vertical Sky Beam

## Tese central

O `Red Beacon` e a emissao visivel e confiavel do estado consolidado do predio.

Mas alguns estados raros exigem mais do que emissao normal. Exigem uma escalada extrema de visibilidade.

Essa escalada foi nomeada como `Vertical Sky Beam`.

Em linguagem simples:

1. o Red Beacon mostra o estado do predio
2. o Vertical Sky Beam rasga o ceu quando o estado critico precisa ser impossivel de ignorar

## O que o Vertical Sky Beam faz

Ele existe para:

1. declarar estado critico com visibilidade maxima
2. escalar o alerta do predio para muito acima do baseline
3. anunciar que a estrutura entrou em modo de protecao ou emergencia controlada
4. tornar explicitamente visivel que existe um risco relevante ou impacto em andamento

## O que ele nao faz

O Vertical Sky Beam nao deve:

1. substituir o Red Beacon cotidiano
2. substituir a Alert Siren
3. substituir observabilidade profunda
4. ser usado para qualquer alerta pequeno

Resumo:

1. o Vertical Sky Beam e excecao maxima
2. ele nao e telemetria cotidiana

## Relacao com o Red Beacon

O Vertical Sky Beam nao e uma estrutura separada do topo. Ele e um modo extraordinario do topo emissor do predio.

Relacao correta:

1. Red Beacon = emissao normal, consolidada e confiavel
2. Vertical Sky Beam = escalada extraordinaria dessa emissao quando a visibilidade precisa atingir o nivel maximo

## Gatilhos possiveis

Ele so deve ser ativado sob criterios duros.

Exemplos:

1. degradacao estrutural relevante
2. perda de corredores criticos do CENTER
3. falha severa em canais vitais da Signal Mesh
4. incidente operacional que exige declaracao imediata de estado critico
5. protecao defensiva do predio ja ativada em modo alto

## Regras duras

1. o Beam nao pode disparar por ruido pequeno
2. o Beam precisa depender de consolidacao de risco, nao de um unico sintoma fraco
3. o Beam deve ser raro o suficiente para continuar significativo
4. o Beam precisa ter criterio de desligamento tao claro quanto o criterio de disparo

## Critério de desligamento

O feixe deve ceder quando:

1. o risco critico for contido
2. o predio voltar do modo de crise para degradacao controlada ou baseline
3. a Signal Mesh recuperar capacidade suficiente
4. a Alert Siren deixar o estado alto de mobilizacao

## Riscos reais

### Risco 1: banalizacao do feixe

Sintoma:

1. ele dispara por eventos medianos
2. operadores se acostumam e deixam de reagir

Mitigacao:

1. regra de disparo muito restrita
2. uso apenas para eventos raros e realmente severos

### Risco 2: feixe desacoplado da realidade

Sintoma:

1. ele continua ativo depois que o problema passou
2. ele se apaga enquanto a crise continua

Mitigacao:

1. criterios claros de entrada e saida
2. consolidacao por sinais confiaveis do sistema

## Estado atual

Neste momento, o Vertical Sky Beam e um conceito arquitetural formalizado.

Isso e correto para esta fase.

Ele so deve ganhar implementacao concreta quando houver um modelo confiavel de escalada critica acima do Red Beacon, sem ruído e sem inflacao de alerta.