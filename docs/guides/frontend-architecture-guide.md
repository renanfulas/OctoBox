<!--
ARQUIVO: guia de arquitetura frontend viva do OctoBox.

TIPO DE DOCUMENTO:
- guia de frontend

AUTORIDADE:
- media para orientacao de frontend

DOCUMENTO PAI:
- [README.md](./README.md)

DOCUMENTOS IRMAOS:
- [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
- [../reference/front-end-city-map.md](../reference/front-end-city-map.md)
- [../reference/front-end-octobox-organization-standard.md](../reference/front-end-octobox-organization-standard.md)
- [../experience/front-display-wall.md](../experience/front-display-wall.md)
-->

# Guia de arquitetura frontend

## Tese frontend atual

O frontend do OctoBox deixou de ser apenas "templates Django com estilo".

Hoje ele esta mais eficiente quando funciona como:

1. uma fachada unica do produto
2. alimentada por contratos claros
3. organizada por superficies, personas e componentes
4. preparada para crescer sem exigir reescrever o backend inteiro

## O que melhorou em relacao ao inicio

### 1. A tela ficou menos dependente de improviso

No inicio a grande vitoria foi ter interfaces operacionais reais.

Agora a vitoria adicional e esta:

1. a tela recebeu um `page payload` mais explicito
2. `presentation` ganhou mais protagonismo
3. assets criticos, diferidos e de enhancement passaram a ser declarados com mais intencao

### 2. O frontend conversa melhor com o backend

Hoje a relacao correta esta mais clara:

1. backend entrega verdade, permissao, estado e acoes possiveis
2. frontend organiza hierarquia visual, repeticao de leitura e fluxo da experiencia

Isso e melhor do que no inicio porque reduz:

1. copy redundante no backend
2. deducao de regra no HTML
3. acoplamento casual a IDs e estruturas nao canonicas

### 3. A fachada ganhou ownership

Os docs atuais ja tratam o front como cidade com bairros, nao como terreno vazio.

Isso ficou mais eficiente porque:

1. sabemos onde procurar
2. sabemos quem e dono local
3. sabemos quando algo e global, de superficie ou local

## Contrato de tela atual

Hoje a forma mais madura de pensar uma pagina rica no OctoBox e:

1. `context`
2. `shell`
3. `data`
4. `actions`
5. `behavior`
6. `capabilities`
7. `assets`

Metafora simples:

1. o backend entrega a caixa organizada
2. o frontend abre cada divisoria no lugar certo
3. a tela para de catar objeto solto no porta-malas

## Regra viva do frontend

### O backend deve entregar

1. dados reais
2. estado
3. acesso
4. links e acoes possiveis
5. declaracao de assets e comportamento quando necessario

### O frontend deve decidir

1. distribuicao visual
2. repeticao de leitura
3. composicao de cards, trilhas e apoios visuais
4. progressao de interacao

## O que isso muda no dia a dia

Quando uma tela nova for nascer:

1. primeiro pense na capacidade e na leitura que ela precisa
2. depois monte o `page payload`
3. depois componha template, CSS e JS orbitando esse contrato
4. evite espalhar a mesma verdade em dez chaves planas so para facilitar um pedaço local de marcação

## Estrutura mais saudavel para telas ricas

1. `view` coordena
2. `query` ou `snapshot` monta leitura
3. `presentation` monta hero, painéis, comportamento e assets
4. `template` compoe
5. `CSS` organiza a anatomia visual
6. `JS` reage a contratos declarados, nao a adivinhacao de DOM

## O que ja esta aparecendo bem no runtime

1. `catalog/presentation/*` como camada de montagem de paginas
2. `shared_support/page_payloads.py` como shape canonico de tela
3. `current_page_assets` e grupos de assets para caminho critico e enhancement
4. docs de city map, ownership e standard para o front

## Riscos de divida tecnica no frontend

1. template assumir regra de negocio demais
2. JS depender de texto ou classe visual em vez de contrato
3. backend enviar duplicacao cosmetica so para evitar interpolacao simples
4. tela nova nascer fora da superficie correta

## Quando abrir docs profundos

1. se a duvida for estrutural de longo prazo, use [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
2. se a duvida for ownership local, use [../reference/front-end-city-map.md](../reference/front-end-city-map.md)
3. se a duvida for onde a feature nova deve nascer, use [../reference/front-end-octobox-organization-standard.md](../reference/front-end-octobox-organization-standard.md)
