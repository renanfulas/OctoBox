<!--
ARQUIVO: formalizacao do Red Beacon como camada superior de emissao visivel, alerta e projeção externa confiavel do estado do predio.

TIPO DE DOCUMENTO:
- direcao arquitetural satelite

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [octobox-architecture-model.md](octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for como sinalizar prontidao, estado consolidado e visibilidade superior sem ruido teatral

POR QUE ELE EXISTE:
- transforma a ideia da antena vermelha no topo em uma peça arquitetural clara e util.
- separa a emissao externa do sistema da captacao, roteamento e processamento interno.

O QUE ESTE ARQUIVO FAZ:
1. define o que e o Red Beacon na arquitetura do OctoBox.
2. explica sua relacao com Center Layer, Signal Mesh e Scaffold Agents.
3. estabelece regras para emissao externa segura, confiavel e legivel.

PONTOS CRITICOS:
- o Red Beacon nao pode vazar caos interno para fora.
- ele nao substitui observabilidade profunda, nem processamento, nem regra de negocio.
-->

# Red Beacon

## Tese central

Se o `Center Layer` e o hall de entrada, a `Signal Mesh` e a malha de sinais, os `Scaffold Agents` sao o andaime temporario da obra e a `Front Display Wall` e a grande fachada visual do produto, o sistema ainda precisa de uma peça superior de emissao.

Essa peca foi nomeada como `Red Beacon`.

Em linguagem simples:

1. o Red Beacon e a antena vermelha no topo do predio
2. ele projeta para fora o estado consolidado e confiavel do sistema
3. ele nao processa o caos interno; ele emite sinal legivel sobre o estado do predio

## O que o Red Beacon resolve

Sem uma camada de emissao externa clara, o sistema tende a misturar:

1. health check tecnico com estado operacional
2. telemetria bruta com sinal legivel
3. alerta interno com comunicacao externa
4. ruído de sistema com informacao realmente importante

O Red Beacon existe para separar isso.

Ele serve para:

1. emitir estado sintetizado
2. declarar alerta de forma confiavel
3. projetar para fora uma visao segura do predio
4. permitir leitura operacional rapida do estado do sistema

## Lugar do Red Beacon no predio

O modelo arquitetural agora pode ser lido assim:

1. Nivel 1 = acessos externos
2. Center Layer = hall oficial de entrada
3. Nivel 2 = nucleo interno encaixotado
4. Signal Mesh = malha permanente de sinais e elasticidade controlada
5. Scaffold Agents = suporte temporario de transicao
6. Front Display Wall = fachada frontal limpa da experiencia visivel
7. Red Beacon = emissao superior visivel do estado do predio

## Diferenca entre Front Display Wall e Red Beacon

### Front Display Wall

Serve para:

1. expor a face utilizavel do produto
2. sustentar a leitura humana principal da operacao
3. manter a frente do predio limpa mesmo com obra lateral

### Red Beacon

Serve para:

1. emitir estado consolidado acima da experiencia principal
2. declarar alerta e prontidao do predio
3. projetar um sinal superior e mais sintetizado

Resumo:

1. a Front Display Wall mostra o produto
2. o Red Beacon mostra o estado do predio acima do produto

## Diferenca entre Red Beacon e Signal Mesh

### Signal Mesh

Serve para:

1. captar sinais
2. normalizar envelopes
3. rotear e distribuir tecnicamente
4. observar e proteger a malha

Pergunta que a Signal Mesh responde:

1. como sinais entram, circulam e sao protegidos?

### Red Beacon

Serve para:

1. emitir sinal externo consolidado
2. declarar estado
3. anunciar alerta importante
4. tornar visivel a saude arquitetural e operacional do predio

Pergunta que o Red Beacon responde:

1. o que o predio precisa comunicar para fora, de forma clara, segura e visivel?

Resumo:

1. a Signal Mesh sente, distribui e protege
2. o Red Beacon declara, sinaliza e projeta

## O que o Red Beacon pode emitir

O Red Beacon pode emitir, entre outros, estes sinais:

1. estado operacional consolidado
2. modo degradado
3. alerta de risco estrutural contido
4. readiness real de capacidades importantes
5. health sintetizado de canais criticos
6. disponibilidade de corredores do CENTER
7. status de canais da Signal Mesh
8. sinalizacao de pressao operacional relevante

Regra:

1. o Red Beacon emite apenas sinal externo curado, consolidado e seguro

## O que o Red Beacon nao faz

O Red Beacon nao deve:

1. decidir regra de negocio
2. captar payload bruto
3. substituir monitoramento tecnico profundo
4. substituir observabilidade detalhada da Signal Mesh
5. virar endpoint generico de debug do sistema

Resumo:

1. o Red Beacon nao abre o predio para o mundo
2. ele apenas projeta o estado que o predio escolhe tornar visivel

## Fontes do Red Beacon

O Beacon pode ser alimentado por sinais vindos de:

1. Center Layer
2. Signal Mesh
3. observabilidade interna
4. indicadores de degradacao e contencao
5. health checks tecnicos resumidos
6. estados consolidados de capacidade

Regra:

1. o Red Beacon nunca deve depender de um unico ponto fragil
2. a emissao deve nascer de consolidacao confiavel e nao de leitura acidental de um componente isolado

## Semantica da luz vermelha

A cor vermelha, nesta arquitetura, nao e decoracao.

Ela significa:

1. alta visibilidade
2. presenca arquitetural
3. alerta quando necessario
4. vigilancia explicita do estado do predio

Ela pode assumir modos diferentes.

Exemplos conceituais:

1. vermelho estavel = sistema operacional e vigilante
2. vermelho pulsante = pressao controlada
3. vermelho intermitente forte = degradacao ou risco estrutural contido
4. vermelho reduzido = baseline seguro sem evento relevante

## Regras duras do Red Beacon

1. o Beacon nao pode emitir payload interno cru
2. o Beacon nao pode expor detalhes sensiveis da estrutura
3. o Beacon nao pode mentir sobre saude do sistema
4. o Beacon precisa preferir sinal consolidado a sinal instantaneo e ruidoso
5. o Beacon deve ser legivel para operacao humana e reutilizavel para integracoes seguras

## Riscos reais

### Risco 1: o Beacon virar vitrine de debug interno

Sintoma:

1. exposicao de detalhes demais
2. sinal externo confuso

Mitigacao:

1. expor apenas estado consolidado
2. esconder detalhes internos sensiveis
3. separar telemetria interna profunda da emissao publica do Beacon

### Risco 2: o Beacon emitir ruido demais

Sintoma:

1. alerta constante
2. estado mudando sem criterio

Mitigacao:

1. usar consolidacao e janela de estabilidade
2. evitar sinalizacao por oscilacao minima
3. preferir semantica operacional a ruído instantaneo

### Risco 3: o Beacon virar falso indicador de seguranca

Sintoma:

1. tudo parece bem porque o farol esta aceso
2. detalhes graves ficam escondidos sem politica clara

Mitigacao:

1. definir criterios explicitos de emissao
2. nao usar o Beacon como substituto de observabilidade interna
3. fazer o Beacon refletir consolidacao real, nao estetica arquitetural

### Risco 4: confusao entre Beacon e Signal Mesh

Sintoma:

1. a malha passa a emitir diretamente para fora sem consolidacao
2. o Beacon tenta rotear ou captar sinais

Mitigacao:

1. manter separacao de papeis
2. a malha sente e protege
3. o Beacon projeta estado confiavel

## Critério de boa implementacao

O Red Beacon esta bem implementado quando:

1. operadores entendem rapidamente o estado geral do predio
2. integracoes externas conseguem ler sinais seguros de saude e disponibilidade
3. o sistema nao vaza caos interno
4. o Beacon nao precisa conhecer o miolo do dominio para emitir estado

## Estado atual

Neste momento, o Red Beacon e um conceito arquitetural formalizado, nao uma camada implementada no codigo.

Isso e o estado correto.

Primeiro o predio precisava ganhar:

1. hall oficial
2. malha de sinais
3. andaime de transicao explicitamente removivel

Agora ele tambem ganhou sua camada superior de emissao visivel, acima da fachada principal formalizada em [../experience/front-display-wall.md](../experience/front-display-wall.md).

O passo futuro correto sera implementar o Beacon apenas quando houver um conjunto pequeno e confiavel de sinais consolidados para ele emitir.

Acima do Beacon normal, a escalada maxima de emissao foi formalizada em [vertical-sky-beam.md](vertical-sky-beam.md). A mudanca de postura defensiva do predio foi formalizada em [alert-siren.md](alert-siren.md).