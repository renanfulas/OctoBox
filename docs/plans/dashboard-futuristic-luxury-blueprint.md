<!--
ARQUIVO: blueprint pratico do dashboard OctoBox no estilo Futuristic Luxury.

TIPO DE DOCUMENTO:
- plano de interface e implementacao visual

AUTORIDADE:
- media para execucao de dashboard; subordinado ao themeOctoBox para conflitos de tema

DOCUMENTO PAI:
- [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md)

QUANDO USAR:
- quando for desenhar, evoluir ou revisar o dashboard principal
- quando for transformar direcao estetica em layout e CSS implementavel

POR QUE ELE EXISTE:
- traduz o tema Luxo Futurista 2050 para um plano de dashboard executavel
- evita design generico e evita brilho sem hierarquia
- reduz retrabalho entre produto, front-end e UX

O QUE ESTE ARQUIVO FAZ:
1. define a proposta visual e funcional do dashboard.
2. mapeia os blocos para leitura operacional rapida.
3. especifica tokens, composicao, motion e responsividade.
4. oferece um roteiro de implementacao em baixo risco tecnico.

PONTOS CRITICOS:
- este blueprint nao substitui o tema oficial; ele aplica o tema ao dashboard.
- se houver conflito com themeOctoBox, themeOctoBox vence.
- evitar criar novos tokens globais sem reutilizacao clara.
-->

# Dashboard OctoBox Futuristic Luxury Blueprint

## Tese da tela

O dashboard deve parecer um cockpit premium-tech: forte no primeiro olhar, simples na leitura de acao e confortavel para uso continuo.

Em linguagem direta:

1. o usuario precisa descobrir o que fazer em ate 3 segundos.
2. a assinatura visual precisa ser memoravel sem virar barulho.
3. o brilho precisa guiar prioridade, nunca competir com conteudo.

Metafora:

Pense no painel de um aviao moderno. Luzes existem para orientar decisao, nao para enfeitar.

## Mapa de composicao (estrutura real)

A composicao recomendada para o dashboard atual:

1. Hero de comando (abertura)
2. Reading list (narrativa curta e foco do dia)
3. Toolbar de organizacao (controle de layout)
4. Workspace principal em duas faixas:
5. `main_primary` para decisao
6. `right_rail` para fila de apoio e contexto

Leitura ideal em Z:

1. topo: direcao e CTA
2. centro esquerdo: metricas e decisoes criticas
3. lateral direita: agenda, alertas, acompanhamentos
4. base: contexto adicional e historico util

## Hierarquia de blocos

### Bloco A: Hero de comando

Objetivo:

1. responder "como esta o box hoje?"
2. destacar 1 CTA dominante

Regras:

1. titulo com presenca forte
2. subtitulo curto e humano
3. 1 acao primaria e no maximo 1 secundaria
4. glow localizado apenas no CTA primario

### Bloco B: Pulso rapido (topline KPI)

Objetivo:

1. mostrar temperatura operacional em segundos

Regras:

1. 3 cards no desktop, 1 coluna no mobile
2. diferenciar claramente card lider vs cards de apoio
3. usar cor semantica apenas para status (critico, atencao, estavel)

### Bloco C: Cluster de metricas

Objetivo:

1. aprofundar leitura sem perder escaneabilidade

Regras:

1. primeira linha: metricas lideres
2. segunda linha: metricas de sustentacao
3. manter ritmo de espacamento consistente

### Bloco D: Right rail operacional

Objetivo:

1. mostrar fila de acao, agenda e sinais de risco

Regras:

1. trilho sempre mais silencioso que a coluna principal
2. cards menores com acao objetiva
3. chips e labels devem orientar, nao chamar mais atencao que o main

## Blueprint de tokens visuais (dark protagonista)

Use tokens existentes como base e ajuste por escopo do dashboard.

Paleta direcional:

1. base: grafite profundo e azul noturno
2. acento principal: cyan
3. acento de apoio: azul celestial
4. assinatura premium: magenta neon em baixa area de cobertura
5. semantica de status: ruby, ambar, esmeralda

Distribuicao pratica:

1. 70% superficie/base
2. 20% contraste e suporte
3. 10% acentos de orientacao

Regras de contraste:

1. texto principal com contraste alto constante
2. texto secundario com contraste medio controlado
3. acento nunca deve reduzir legibilidade de dado numerico

## Typography system (diretriz)

Objetivo:

1. manter cara premium e leitura de dados excelente

Direcao:

1. fonte de destaque: expressiva e tecnica para titulos
2. fonte de corpo: neutra e resistente para uso continuo
3. numeros de KPI com peso alto e espacamento claro

Regra dura:

1. evitar stack generica sem motivo estrutural do produto
2. nao trocar tipografia global sem plano de rollout

## Motion blueprint

Motion recomendado:

1. entrada em cascata no carregamento do dashboard
2. hover curto em cards de decisao
3. feedback claro de foco para acessibilidade

Duracao:

1. 180ms a 260ms para hover
2. 420ms a 700ms para entrada de cena

Regra de ouro:

1. se todos os elementos animam, a hierarquia morre
2. priorizar uma coreografia principal por tela

## Responsividade (desktop -> mobile)

### Desktop (>960px)

1. duas trilhas: `main_primary` e `right_rail`
2. hero com area de presenca ampla
3. cards de topline em 3 colunas

### Tablet (720px a 960px)

1. reduzir densidade de bloco
2. empilhar alguns cards de apoio
3. manter CTA principal sempre visivel sem scroll longo

### Mobile (<720px)

1. uma coluna priorizada
2. hero compacto com CTA full-width quando necessario
3. right rail desce para depois dos blocos criticos
4. reduzir glow e ornamento para preservar performance e leitura

## Checklist anti-slop (antes de subir PR)

1. o dashboard parece OctoBox, e nao template generico?
2. existe uma assinatura memoravel unica?
3. em 3 segundos eu sei qual acao fazer?
4. o brilho esta ajudando hierarquia ou roubando atencao?
5. mobile continua elegante e rapido?

## Riscos tecnicos e como evitar divida tecnica

Risco 1: criar excecao visual demais no CSS local

1. efeito: dashboard bonito hoje, inconsistente amanha
2. mitigacao: preferir tokens e componentes canonicos antes de override local

Risco 2: inventar novos tokens globais sem necessidade

1. efeito: contamina outras telas
2. mitigacao: aplicar assinatura forte por escopo (`data-shell-scope="dashboard"`)

Risco 3: motion excessivo

1. efeito: cansaco e queda de foco operacional
2. mitigacao: uma animacao principal + microinteracoes minimas

## Roteiro de implementacao sugerido (baixo risco)

1. Revisar hero e topline no `dashboard.css` com foco em hierarquia e contraste.
2. Consolidar estilo de cards lideres e de suporte no cluster de metricas.
3. Refinar right rail para silencio visual controlado.
4. Validar dark e light como mesma familia visual.
5. Rodar smoke visual em desktop/tablet/mobile e ajuste fino final.

## Mapeamento para arquivos atuais

Template principal:

- `templates/dashboard/index.html`

Blocos principais:

- `templates/dashboard/blocks/hero.html`
- `templates/dashboard/blocks/metrics_cluster.html`

CSS de shell da pagina:

- `static/css/design-system/dashboard.css`

Componentes base:

- `static/css/design-system/components/hero.css`
- `static/css/design-system/components/cards.css`
- `static/css/design-system/components/actions.css`
- `static/css/design-system/components/states.css`

Tokens:

- `static/css/design-system/tokens.css`

## Criterio de pronto

O dashboard Futuristic Luxury esta pronto quando:

1. comunica prioridade em ate 3 segundos
2. parece premium-tech sem visual gamer
3. mantem legibilidade e conforto de uso continuo
4. nao cria divida tecnica por excesso de excepcao local
5. deixa uma memoria visual clara de marca OctoBox
