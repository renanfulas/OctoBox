# Corda Plan

## Contexto

O OctoBOX ja tem um contrato canonico de tema, mas o darkmode ainda sofre com vazamentos de autoridade visual em arquivos locais e em alguns componentes que nasceram com mentalidade light-first.

Hoje o resultado nao e um darkmode quebrado por completo.
O problema e mais sutil e mais perigoso: ele funciona, mas em varios pontos ainda nao parece um sistema unico.

Agora tambem temos uma direcao visual explicitamente escolhida em `docs/architecture/design-guideless.md`:

1. dark premium com fundo navy quase preto
2. light mode completo com linguagem iOS-inspired
3. neons com papel semantico claro
4. glassmorphism nos cards principais
5. scrollbar discreta e moderna

## Objetivo

Endurecer a estrutura do darkmode para que cards, tipografia, notices, topbar e superficies locais respondam ao mesmo conjunto de tokens e ao mesmo contrato visual.

Ao mesmo tempo, vamos incorporar ao contrato canonico a paleta aprovada:

1. vermelho `#ff0844` para urgente e critico
2. amarelo `#ffb020` para warning e pendencia
3. verde `#00ff88` para sucesso e meta
4. azul `#00d4ff` para primary e info
5. roxo `#af52de` para accent e premium

Sem redesenhar a casa inteira.
So mudancas leves de estrutura e cor.

Em termos simples:

1. parar de apagar incendio tela por tela
2. fortalecer o encanamento central do tema
3. deixar a manutencao futura mais barata e previsivel

## Riscos

1. corrigir sintomas locais sem tocar os tokens certos
2. aumentar o numero de excecoes `body[data-theme="dark"]` e criar outra camada de divida
3. mexer em componentes compartilhados sem mapear onde CSS local ainda depende do comportamento antigo
4. misturar "melhorar darkmode" com "redesenhar o produto inteiro"
5. usar glow neon demais e transformar leitura operacional em poluicao visual

## Direcao

Vamos seguir a escada oficial do projeto:

1. tokens semanticos
2. primitivas canonicas
3. composicao local
4. alias temporario apenas quando necessario

E vamos traduzir o `design-guideless.md` assim:

1. a paleta vai para tokens
2. o glassmorphism vai para surfaces canonicas
3. o scrollbar vai para camada global discreta
4. o neon vira linguagem de estado e destaque, nao decoracao espalhada

Traducao de crianca de 6 anos:
primeiro arrumamos a caixa d'agua, depois os canos principais, e so depois as torneiras.
Se comecarmos pelas torneiras, a agua continua saindo errada no resto da casa.

## Acoes iniciais

### Onda 1 - Auditoria focada do darkmode

1. inventariar onde o darkmode ainda depende de cor fixa, gradiente fixo ou contraste manual
2. separar o que e problema de token, de componente compartilhado, e de CSS local
3. registrar quais arquivos podem ser tratados por migracao segura e quais exigem cuidado especial

### Onda 2 - Hardening do contrato canonico

1. ampliar tokens semanticos para superficies, copy, borda, overlay, scrollbar e estados
2. alinhar os tokens de acento com a paleta aprovada do guideline
3. refinar `cards.css`, `hero.css`, `states.css` e `topbar.css` para consumir esse contrato com menos decisao local embutida
4. reduzir a necessidade de overrides por pagina

### Onda 3 - Limpeza das ilhas locais

1. atacar os arquivos locais com maior cheiro de light-first
2. migrar hardcodes relevantes para tokens ou variantes canonicas
3. aplicar ajustes leves de estrutura onde o darkmode estiver pesado, lavado ou com contraste ruim
4. validar contraste, leitura e continuidade visual nas telas mais usadas
