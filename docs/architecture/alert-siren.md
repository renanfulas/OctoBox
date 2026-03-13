<!--
ARQUIVO: formalizacao da Alert Siren como sistema de mudanca de postura defensiva e mobilizacao estrutural do predio.

POR QUE ELE EXISTE:
- transforma a ideia do sinal sonoro de aviso em uma peça arquitetural de mudanca de modo do sistema.
- separa emissao de alerta do comportamento interno de preparacao e protecao.

O QUE ESTE ARQUIVO FAZ:
1. define o que e a Alert Siren.
2. explica como ela muda a postura do predio em situacoes de risco.
3. estabelece o papel dela em relacao ao Red Beacon, Vertical Sky Beam e Signal Mesh.

PONTOS CRITICOS:
- a Alert Siren nao e decoracao e nao pode virar ruido permanente.
- se ela tocar demais, perde forca; se tocar pouco demais, perde capacidade de preparacao.
TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [octobox-architecture-model.md](octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for como o sistema reage a risco critico e como escalar postura defensiva sem caos


# Alert Siren

## Tese central

O predio nao apenas mostra estado. Ele tambem precisa mudar de postura quando algo errado acontece.

Essa mudanca de postura foi formalizada como `Alert Siren`.

Em linguagem simples:

1. a Alert Siren e o sinal sonoro do predio
2. ela indica que o sistema saiu do repouso e entrou em estado de alerta
3. ela prepara as estruturas para impacto, contencao, degradacao e protecao

## O que a Alert Siren faz

Ela existe para:

1. marcar a transicao entre estado estavel e estado de alerta
2. acionar postura defensiva do sistema
3. coordenar preparacao estrutural para possivel impacto
4. avisar que o predio entrou em modo de protecao

## Estado estavel

Quando nao ha nada acontecendo de relevante:

1. o predio permanece estavel
2. a Siren fica silenciosa ou em nivel basal sem alarme
3. o sistema opera em baseline seguro

## Estado de alerta

Quando o risco sobe:

1. a Siren entra em alerta
2. a estrutura se prepara para possivel problema
3. corredores podem ser isolados
4. a Signal Mesh pode entrar em contencao
5. prioridades mudam para proteger o nucleo e os canais criticos

## O que a Alert Siren pode acionar

Ela pode ser o gatilho arquitetural para:

1. degradacao controlada
2. isolamento de corredores
3. congelamento de entradas nao essenciais
4. retração da Signal Mesh para baseline seguro
5. aumento de observabilidade e registro de incidente
6. reforco de circuit breaker e backpressure
7. protecao reforcada de canais criticos

## Diferenca entre Siren, Beacon e Beam

### Red Beacon

1. projeta o estado consolidado do predio

### Vertical Sky Beam

1. escala a visibilidade ao nivel maximo em estado extraordinario
2. pode acompanhar crise severa ou declarar prontidao estrutural suprema

### Alert Siren

1. muda a postura operacional e defensiva do predio

Resumo:

1. o Beacon mostra
2. o Beam expõe no nivel maximo
3. a Siren mobiliza

Regra de fronteira:

1. se a pergunta for sobre emergencia, protecao, contencao ou resposta defensiva, a dona da mudanca e a Siren
2. se a pergunta for sobre visibilidade maxima de um estado extraordinario, a peca correta e o Beam

## Regras duras

1. a Siren nao pode tocar por ruido pequeno
2. a Siren precisa estar ligada a mudanca real de postura
3. a Siren deve ter niveis ou estados claros de ativacao
4. a Siren precisa ter criterio de retorno ao estado normal

## Possiveis niveis da Siren

Exemplo conceitual:

1. silenciosa = operacao normal
2. baixa = alerta leve e observacao reforcada
3. media = degradacao controlada e preparacao
4. alta = incidente relevante e modo defensivo forte

## Critério de retorno

A Siren deve recuar quando:

1. o risco diminuir de forma sustentada
2. a estrutura voltar ao baseline ou a uma degradacao controlada menor
3. os canais criticos estiverem protegidos
4. o Vertical Sky Beam, se ativo, ja nao for mais necessario

## Riscos reais

### Risco 1: sirene cronicamente ligada

Sintoma:

1. alerta constante
2. equipe e sistema deixam de levar a serio

Mitigacao:

1. criterios de disparo claros
2. niveis de ativacao diferenciados
3. retorno obrigatorio quando o risco cair

### Risco 2: sirene sem efeito estrutural

Sintoma:

1. ela toca, mas nada muda internamente

Mitigacao:

1. ligar a Siren a politicas concretas de defesa
2. documentar quais mecanismos a ativacao destrava

### Risco 3: sirene sem proporcionalidade

Sintoma:

1. tudo vira alerta alto

Mitigacao:

1. usar niveis ou degraus de ativacao
2. calibrar por risco consolidado e nao por sinal isolado

## Estado atual

Neste momento, a Alert Siren e um conceito arquitetural formalizado.

Isso e o estado correto.

Ela so deve ganhar implementacao quando houver uma tabela pequena, objetiva e confiavel de estados de risco e de mudancas defensivas correspondentes.