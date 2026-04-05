<!--
ARQUIVO: plano final de implantacao do tema visual oficial do OctoBox.

TIPO DE DOCUMENTO:
- plano operacional de implantacao visual

AUTORIDADE:
- alta para execucao pratica da implantacao do tema

DOCUMENTO PAI:
- [../architecture/themeOctoBox.md](../architecture/themeOctoBox.md)

QUANDO USAR:
- quando a duvida for como implantar o tema oficial sem abrir obra estrutural
- quando for preciso saber ordem, risco e criterio de pronto por onda
- quando o time precisar executar a mudanca visual de forma disciplinada

POR QUE ELE EXISTE:
- transforma a arquitetura visual oficial em sequencia pratica de trabalho
- evita retrabalho e polimento aleatorio sem criterio unico
- protege a fase final do produto contra mudancas de medio e alto risco

O QUE ESTE ARQUIVO FAZ:
1. define o objetivo operacional da implantacao
2. organiza a execucao em ondas curtas
3. registra checklist por camada e criterio de aceite
4. fixa a validacao final pela persona Maria

PONTOS CRITICOS:
- este plano e de implantacao visual, nao de reestruturacao arquitetural
- qualquer mudanca que exija mexer forte em templates, views ou payloads sai do escopo desta rodada
- se uma onda gerar barulho visual ou regressao de leitura, ela falhou mesmo que tenha ficado mais chamativa
-->

# Theme Implementation Final

## Objetivo operacional

Implantar o tema **Luxo Futurista 2050** no OctoBox com baixo risco e alto retorno visual.

O alvo pratico e este:

1. deixar o produto mais magnetico
2. manter a tela facil de localizar
3. reforcar a sensacao de SaaS premium-tech
4. preservar clareza e orientacao de acao
5. evitar reestruturacao media ou alta

## Regra de execucao

Toda implantacao desta rodada deve obedecer:

1. primeiro docs e criterio
2. depois design system
3. depois vitrines centrais
4. depois harmonizacao lateral
5. por ultimo smoke final

Regra de protecao:

1. nada de cirurgia em views, payloads ou JS sem necessidade real
2. nada de reabrir layout-base do produto como se fosse uma nova fase
3. tudo que entrar precisa sair mais bonito e mais claro ao mesmo tempo

## Gate de promocao para escopo premium

Antes de aplicar assinatura forte em uma nova tela, passar por este gate.

### A tela entra no escopo premium quando

1. representa fachada importante do produto para aquele papel
2. precisa vender valor percebido do OctoBox logo no primeiro olhar
3. concentra decisao, hero, CTA dominante ou leitura executiva
4. aparece com frequencia suficiente para moldar a sensacao geral do produto

### A tela fica so na base global quando

1. e formulario utilitario
2. e fluxo intermediario
3. precisa mais de silencio do que de presenca cenica
4. ainda esta com hierarquia visual imatura

### Checklist de promocao

1. a estrutura da tela ja esta clara sem glow
2. a assinatura premium melhora a orientacao de acao
3. o conteudo importante ainda vence em ate 3 segundos
4. dark e light continuam coerentes
5. nao foi preciso inventar token global novo por vaidade local

### Regra de rollback

Se a tela ficar mais chamativa do que clara:

1. remover escopo premium local
2. voltar para a base global
3. corrigir hierarquia antes de tentar promover de novo

## Onda 1: Docs + Design System Base

### Objetivo

Tornar a nova direcao visual oficial e preparar a fundacao que sera herdada pelas telas.

### Arquivos-alvo

1. `docs/architecture/themeOctoBox.md`
2. `docs/plans/theme-implementation-final.md`
3. `README.md`
4. `docs/reference/documentation-authority-map.md`
5. `docs/reference/reading-guide.md`
6. `static/css/design-system/tokens.css`

### Tipo de mudanca permitida

1. documentacao canonica
2. tokens semanticos
3. calibracao de stage, surface, border, shadow e accent

### Risco

1. baixo para docs
2. medio para tokens globais porque respingam em varias telas

### Done criteria

1. a rota oficial de leitura aponta para o novo tema
2. o mapa de autoridade reflete a nova precedencia
3. os tokens base ja falam a lingua do Luxo Futurista 2050
4. dark e light passam a ter o mesmo edificio visual, com intensidades diferentes
5. o gate de promocao para escopo premium esta documentado

## Onda 2: Hero, Cards, Actions, Topbar e Shell

### Objetivo

Aplicar a nova assinatura nos componentes compartilhados que vendem o produto antes mesmo do conteudo detalhado.

### Arquivos-alvo

1. `static/css/design-system/components/hero.css`
2. `static/css/design-system/components/cards.css`
3. `static/css/design-system/components/card-variants.css`
4. `static/css/design-system/components/actions.css`
5. `static/css/design-system/topbar.css`
6. shell compartilhado relevante carregado pelo design system

### Tipo de mudanca permitida

1. glow
2. halo
3. superficie
4. borda
5. sombra
6. CTA
7. quick actions
8. chips e alertas
9. criacao de escopo premium apenas para superfices aprovadas no gate

### Risco

1. medio

### Done criteria

1. hero parece portal de comando premium-tech
2. cards parecem mais modernos e mais coerentes entre si
3. CTA principal chama mais o olhar do que a secundaria
4. topbar e shell parecem sofisticados sem excesso
5. o brilho ficou medio e localizado
6. nenhuma tela fora do gate recebeu assinatura premium forte

## Onda 3: Dashboard e Financeiro

### Objetivo

Levar a nova linguagem para as vitrines centrais do produto.

### Arquivos-alvo

1. `static/css/design-system/dashboard.css`
2. `templates/dashboard/index.html` apenas se houver ajuste pequeno e seguro de classe
3. `static/css/catalog/finance/_shell.css`
4. `static/css/catalog/finance/_signature.css`
5. `templates/catalog/finance.html` apenas se houver ajuste pequeno e seguro de classe

### Tipo de mudanca permitida

1. hierarquia visual
2. assinatura do hero
3. contraste entre cards lideres e cards de apoio
4. identidade do financeiro convergida ao tema novo

### Risco

1. medio

### Done criteria

1. dashboard parece a fachada oficial do OctoBox 2050
2. financeiro parece premium-tech e nao paralelo ao restante do produto
3. prioridade, pressao e proxima acao ficam mais faceis de perceber
4. nada parece mais chamativo do que o conteudo importante

## Onda 4: Students, Class Grid, Recepcao e Superficies Secundarias

### Objetivo

Espalhar a consistencia do tema para o restante das superfices visiveis sem reabrir arquitetura.

### Arquivos-alvo

1. CSS local de students
   diretorio e ficha do aluno nao podem compartilhar hierarquia por acidente
2. CSS local de class-grid
3. CSS operacional de recepcao e personas que herdarem a linguagem
4. templates dessas telas apenas para classes pequenas, se necessario

### Tipo de mudanca permitida

1. ajuste de superficie local
2. refino de contraste
3. polimento de densidade
4. harmonizacao de estados

### Risco

1. baixo a medio

### Done criteria

1. students parece parte do mesmo predio visual
   diretorio de alunos e ficha do aluno continuam da mesma familia, mas com hierarquias independentes
2. class-grid parece futurista sem perder leitura operacional
3. recepcao continua acolhedora e fica mais desejavel
4. nenhuma tela secundaria parece de outro produto

## Onda 5: Consistencia Dark/Light + Smoke Final

### Objetivo

Fechar a implantacao com verificacao de coerencia, responsividade e aprovacao funcional.

### Arquivos-alvo

1. o conjunto dos CSS e templates tocados nas ondas anteriores

### Tipo de mudanca permitida

1. microajustes de contraste
2. microajustes de glow
3. microajustes de spacing
4. correcao de excesso ou falta de assinatura

### Risco

1. baixo

### Done criteria

1. dark protagonista esta consistente
2. light companion parece a mesma familia visual
3. nao existe um ponto destoando como tema paralelo
4. a implantacao fecha sem regressao visual aparente

## Checklist de implementacao por camada

### Documentacao

1. o tema oficial esta explicito
2. a precedencia esta clara
3. a direcao antiga ficou como contexto historico quando conflitar

### Tokens

1. stage conversa com a nova atmosfera
2. accent principal usa cyan, azul celestial e magenta neon
3. semantica critica usa ruby, ambar e esmeralda
4. sombras e glow estao calibrados para intensidade media
5. tokens globais continuam seguros para telas fora de escopo premium

### Componentes compartilhados

1. hero tem presenca
2. cards tem familia coerente
3. CTA primaria lidera
4. CTA secundaria apoia
5. chips e alertas nao berram

### Telas centrais

1. dashboard vende o produto
2. financeiro parece parte da mesma identidade
3. alunos, grade e recepcao nao destoam

### Promocao de escopo premium

1. a promocao foi justificada por papel de negocio e nao por gosto
2. a tela aprovada entrou com `data-shell-scope` ou cena premium explicita
3. a tela nao aprovada continuou usando a base global sem perda de clareza

## Criterios de aceitacao visuais e funcionais

### Visuais

1. o produto parece mais moderno
2. o produto parece mais premium
3. o produto continua facil de usar
4. o neon e percebido como assinatura, nao como agressao
5. dark e light parecem versoes do mesmo tema

### Funcionais

1. a tela carrega sem erro
2. as classes novas nao quebram layout
3. a hierarquia continua clara em desktop e mobile
4. nenhum fluxo principal perde legibilidade

## Sequencia de rollout

1. fechar docs e precedencia
2. ajustar tokens
3. ajustar componentes compartilhados
4. ajustar dashboard e financeiro
5. ajustar superfices secundarias
6. rodar smoke visual e funcional
7. consolidar pequenos refinamentos finais

## Criterio de aprovacao pela Maria

Persona de validacao:

1. Maria
2. recepcionista
3. leitura pratica
4. pouco apetite para interface cansativa

Maria aprova quando sentir:

1. isso ficou mais bonito
2. isso parece mais moderno
3. isso continua facil de achar
4. isso nao cansou minha vista
5. isso parece produto caro e bom de mexer

Maria reprova quando sentir:

1. muito brilho
2. muita confusao
3. muito barulho visual
4. mais dificuldade para localizar a acao

## Regra final

Se uma mudanca deixar o produto mais chamativo, mas menos claro, ela nao entra.

Se deixar mais claro, mas sem identidade, ela ainda esta incompleta.

O ponto de chegada desta implantacao e:

1. clareza
2. magnetismo
3. modernidade
4. baixo risco
5. vontade de usar
