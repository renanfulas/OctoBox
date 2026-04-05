<!--
ARQUIVO: arquitetura visual oficial do tema do OctoBox.

TIPO DE DOCUMENTO:
- arquitetura visual e manifesto canonico de tema

AUTORIDADE:
- alta para linguagem visual, precedencia de tema e criterio de assinatura do produto

DOCUMENTO PAI:
- [octobox-architecture-model.md](octobox-architecture-model.md)

QUANDO USAR:
- quando a duvida for qual e o tema oficial do produto
- quando houver conflito entre direcao visual antiga e nova
- quando for preciso decidir paleta, glow, contraste, superficie e assinatura visual

POR QUE ELE EXISTE:
- transforma a linguagem visual do OctoBox em arquitetura explicita
- evita concorrencia entre fases esteticamente validas, mas temporalmente diferentes
- registra o tema oficial que deve guiar tokens, shell, hero, cards e CTA

O QUE ESTE ARQUIVO FAZ:
1. define o tema oficial do OctoBox
2. registra a tese central do Luxo Futurista 2050
3. estabelece a gramatica visual canonica do produto
4. fixa a precedencia sobre direcoes visuais anteriores quando houver conflito

PONTOS CRITICOS:
- este arquivo nao substitui o plano pratico de implantacao
- se a linguagem visual mudar de fase, este documento precisa ser atualizado junto
- experiencia historica continua valida como contexto, mas nao como soberania quando conflitar com este tema
-->

# Theme OctoBox

## Tese central

O tema oficial do OctoBox passa a ser **Luxo Futurista 2050**.

Em linguagem direta:

1. o produto deve acolher sem parecer antigo
2. o produto deve parecer moderno sem ficar hostil
3. o produto deve usar neon com controle, nao com agressao
4. o produto deve parecer premium-tech, nao gamer
5. o produto deve gerar desejo de uso sem cansar a vista

Esse tema nasce para resolver uma tensao real do produto:

1. a base ja nao precisa parecer prototipo
2. a base tambem nao deve parecer painel neutro e frio
3. o sistema precisa ter assinatura propria, memoravel e contemporanea
4. essa assinatura precisa continuar legivel para operacao real

## O que o tema oficial significa

Luxo Futurista 2050 nao e uma fantasia cyberpunk solta.

Ele significa:

1. atmosfera de futuro proximo
2. energia visual controlada
3. contraste premium
4. profundidade limpa
5. brilho orientando o olho
6. superfices tecnicas com calor humano suficiente para acolher

Metafora curta:

1. nao e boate neon
2. nao e terminal hacker
3. e cockpit de um SaaS premium do futuro, onde tudo parece caro, preciso e convidativo

## Principios fixos do tema

### 1. Neon medio e localizado

O neon e permitido e desejado.

Mas ele so entra para:

1. orientar prioridade
2. reforcar CTA
3. marcar foco
4. sustentar assinatura visual

Ele nao entra para:

1. preencher todos os blocos
2. competir com texto
3. virar barulho de fundo
4. cansar o usuario no uso continuo

### 2. Luxo premium-tech, nao gamer

O tema deve parecer produto de alto valor, nao interface de jogo.

Isso exige:

1. superfices bem controladas
2. bordas com brilho curto
3. sombras profundas, mas disciplinadas
4. saturacao forte so nos pontos certos
5. ritmo visual limpo

### 3. Acolhimento com energia futurista

O produto deve parecer vivo e moderno, mas nao frio.

Isso pede:

1. copy humana
2. hierarquia clara
3. glow que convida e nao expulsa
4. composicao com respiro
5. contraste que ajuda a decisao

### 4. Brilho guiando hierarquia

Glow, halo, orb e stroke luminoso so existem se ajudarem a leitura.

Regra dura:

1. se o brilho aparece antes do conteudo, ele passou do ponto
2. se o brilho nao ajuda a priorizar, ele esta sobrando
3. se duas areas pedem atencao ao mesmo tempo, a assinatura falhou

## Estrategia de tema

### Dark protagonista

O modo dark e a referencia principal do tema.

Ele deve concentrar:

1. a assinatura mais forte do produto
2. a experiencia mais memoravel
3. a leitura mais nitida de profundidade
4. a vitrine principal do Luxo Futurista 2050

Base esperada do dark:

1. grafite profundo
2. azul noturno
3. superficies minerais escuras
4. acentos luminosos em cyan, azul celestial e magenta neon

### Light companion

O modo light nao e um segundo tema.

Ele e a mesma identidade em uma atmosfera mais suave.

Isso significa:

1. mesma linguagem
2. mesma hierarquia
3. mesmo edificio visual
4. menos glow
5. mais ar
6. superficies claras sem virar branco morto

## Criterio de entrada para tela premium com escopo

Nem toda tela deve receber a assinatura 2050 forte.

Regra de arquitetura:

1. tokens globais formam a base estavel do produto
2. escopo premium existe para concentrar assinatura, nao para espalhar efeito
3. uma tela so entra no escopo premium quando precisa vender valor, orientar decisao ou sustentar percepcao de produto

Metafora curta:

1. a base global e o predio inteiro bem construido
2. o escopo premium e a iluminacao cenica da vitrine
3. nem todo corredor precisa virar vitrine

### Quando uma tela pode entrar no escopo premium

Uma superficie pode receber escopo premium quando cumpre pelo menos dois destes papeis:

1. e fachada principal do produto para o papel do usuario
2. concentra decisao operacional importante logo no primeiro olhar
3. sustenta percepcao comercial de valor do OctoBox
4. agrupa CTA dominante, hero ou leitura executiva que precisa parecer memoravel
5. aparece com alta frequencia na rotina e influencia sensacao geral de qualidade

### Quando uma tela nao deve entrar no escopo premium

Uma superficie nao deve receber escopo premium quando:

1. e apenas fluxo intermediario ou formulario utilitario
2. depende mais de silencio do que de assinatura
3. ainda nao tem hierarquia madura de conteudo
4. corre risco de competir com telas mais importantes
5. usa linguagem local experimental que ainda nao foi consolidada

### Checklist obrigatorio antes de promover uma tela

Antes de aplicar `data-shell-scope` ou uma cena premium, validar:

1. a tela tem hero, trilho, card lider ou CTA principal claramente definidos
2. o conteudo importante continua vencendo o brilho em ate 3 segundos
3. a assinatura forte melhora orientacao, nao apenas decoracao
4. dark e light continuam sendo a mesma familia visual
5. a mudanca nao obriga criar tokens globais novos sem reutilizacao clara

### Regra de saida

Se a tela precisar de excecoes demais para ficar bonita, ela nao merece escopo premium ainda.

Nesse caso, o caminho correto e:

1. manter base global estavel
2. corrigir hierarquia local
3. promover depois, quando a tela estiver pronta para sustentar assinatura

### Precedencia pratica

Quando houver duvida entre impacto global e brilho local:

1. preferir ajuste local por escopo
2. evitar subir saturacao no token global
3. preservar a seguranca da base antes de ampliar a vitrine

## Paleta canonica

### Paleta principal

1. cyan como sinal primario de foco e tecnologia
2. azul celestial como apoio de profundidade e navegacao
3. neon magenta como assinatura premium de energia e contraste

### Semantica operacional

1. critico = ruby
2. atencao = ambar
3. estavel ou positivo = esmeralda

Regra:

1. semantica operacional nunca deve disputar com a assinatura principal
2. cyan, azul celestial e magenta constroem identidade
3. ruby, ambar e esmeralda constroem leitura de estado

## Gramatica visual oficial

### Fundo

O fundo deve parecer ambiente, nao chapa lisa.

Direcao:

1. stage com gradiente controlado
2. profundidade atmosferica sutil
3. grid ou textura apenas se muito leve

### Superficie

A superficie deve parecer material premium-tech.

Direcao:

1. glass controlado
2. mineralidade limpa
3. opacidade suficiente para leitura longa
4. contraste nitido entre bloco dominante e bloco de apoio

### Borda

Borda nao e contorno burocratico.

Ela deve:

1. separar camada
2. sugerir material
3. receber energia curta quando houver foco ou prioridade

### Glow e halo

Glow e halo sao instrumentos de composicao.

Uso correto:

1. CTA principal
2. hero dominante
3. card prioritario
4. foco ativo
5. sinais importantes de estado

Uso incorreto:

1. toda a pagina brilhando
2. todos os cards com o mesmo peso
3. alertas virando outdoor

### Sombra

A sombra deve dar profundidade e luxo.

Ela nao deve:

1. escurecer demais
2. parecer pesada
3. substituir hierarquia ruim

### Hero

O hero deve parecer portal de comando do produto.

Ele deve ter:

1. presenca forte
2. assinatura luminosa contida
3. CTA principal muito clara
4. painel lateral vivo, mas subordinado

### Card

Os cards devem parecer familia unica.

Eles precisam:

1. carregar a mesma linguagem material
2. variar intensidade por papel
3. separar decisao, fila, contexto e apoio
4. manter leitura rapida

### CTA

CTA principal:

1. energizada
2. evidente
3. futurista
4. premium

CTA secundaria:

1. mais fria
2. mais silenciosa
3. sem competir com a primaria

### Chips, trilhos e alertas

Esses elementos precisam parecer instrumentos de orientacao, nao brinquedos visuais.

Regra:

1. chips informam
2. trilhos organizam
3. alertas destacam risco
4. nenhum deles sequestra a fachada inteira

## Anti-padroes proibidos

1. neon agressivo
2. visual gaming
3. glow excessivo
4. superficies berrando juntas
5. tema claro sem identidade propria
6. dark excessivamente saturado
7. multiplas linguagens visuais concorrentes
8. assinatura quente e fria brigando sem criterio

## Regra de precedencia

Este documento passa a ser a referencia oficial para tema visual do OctoBox.

Quando houver conflito com direcoes visuais anteriores:

1. `themeOctoBox.md` vence em tema, atmosfera, paleta, glow, superficie e assinatura
2. guias anteriores continuam valendo em estrutura, clareza, hierarquia e disciplina de UX quando nao houver conflito
3. calibracoes como `Luxo Discreto` e `O Silencio Que Acolhe` passam a ser leitura historica de evolucao, nao autoridade soberana

Traducao pratica:

1. a historia continua ensinando
2. o tema oficial agora manda

## Relacao com os outros docs

Use este documento para:

1. decidir a linguagem visual oficial
2. resolver conflito de tema
3. orientar tokens, hero, cards, CTA, shell e alertas

Use [../plans/theme-implementation-final.md](../plans/theme-implementation-final.md) para a implantacao pratica por ondas.

Use [../experience/front-display-wall.md](../experience/front-display-wall.md) para a metafora maior da fachada.

Use [../experience/layout-decision-guide.md](../experience/layout-decision-guide.md) para composicao, hierarquia e cena da tela.

Use [../experience/css-guide.md](../experience/css-guide.md) para ownership e disciplina de CSS.

## Regra final

Se uma tela parecer futurista, mas cansativa, ela falhou.

Se parecer acolhedora, mas sem assinatura, ela falhou.

O ponto certo do OctoBox e este:

1. futuro proximo
2. valor percebido alto
3. clareza operacional
4. energia controlada
5. vontade imediata de mexer
