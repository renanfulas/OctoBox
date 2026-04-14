<!--
ARQUIVO: auditoria da Onda 1 do hotspot compartilhado do catalogo.

POR QUE ELE EXISTE:
- transforma a primeira varredura forense do `catalog/shared` em mapa de execucao.
- separa regra viva, ponte legada, alias protegido e morto provavel antes de qualquer limpeza.
- evita exclusao impulsiva em camada compartilhada carregada por varias telas.

O QUE ESTE ARQUIVO FAZ:
1. mapeia ownership e consumo real de `shared.css`.
2. resume os principais sinais de override, legado e autoridade falsa.
3. classifica os achados por risco e acao recomendada.
4. define a ordem segura para a fase de correcao.

PONTOS CRITICOS:
- este documento nao autoriza apagar `catalog/shared` inteiro.
- `note-panel*` e `legacy-copy*` seguem protegidos.
- nomes legados como `glass-panel*` ainda sustentam telas reais e exigem migracao antes de exclusao.
-->

# Onda 1: auditoria do hotspot `catalog/shared`

## Escopo

Esta Onda 1 cobre:

1. [../../static/css/catalog/shared.css](../../static/css/catalog/shared.css)
2. [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
3. modulos importados pelo manifesto compartilhado
4. telas do catalogo que carregam `include_catalog_shared=True`

O objetivo aqui nao e "limpar porque parece velho".

O objetivo e descobrir qual fio ainda conduz energia antes de encostar no alicate.

## C.O.R.D.A.

### Contexto

O arquivo [../../static/css/catalog/shared.css](../../static/css/catalog/shared.css) hoje funciona como manifesto e trilho de cascade. Ele importa, nesta ordem:

1. `scene.css`
2. `student-financial.css`
3. `utilities.css`
4. `student-financial-foundations.css`
5. `responsive.css`
6. `lock-banner.css`

Esse pacote compartilhado sobe em pelo menos cinco superficies do catalogo por meio de [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py):

1. [../../catalog/presentation/class_grid_page.py](../../catalog/presentation/class_grid_page.py)
2. [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. [../../catalog/presentation/membership_plan_page.py](../../catalog/presentation/membership_plan_page.py)
4. [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)
5. [../../catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)

Traduzindo em linguagem simples: `shared.css` nao e um comodo isolado, e o corredor central. Se a gente puxar um fio errado aqui, apaga varias salas ao mesmo tempo.

### Objetivo

Sair desta onda com quatro caixas separadas:

1. o que pode morrer com baixo risco
2. o que parece morto, mas ainda precisa prova
3. o que e ponte legada viva
4. o que esta protegido por contrato e nao pode ser tratado como sujeira

### Riscos

Os riscos principais desta camada sao:

1. apagar ponte viva como `glass-panel` ou `finance-glass-panel`
2. tratar `note-panel*` como legado morto, quando ele hoje e host canonizado em [design-system/components/states.css](design-system-contract.md)
3. confundir `legacy-copy` com variavel descartavel, quando ele ainda participa da malha tipografica compartilhada
4. atacar helpers com `!important` sem primeiro localizar quem esta brigando por autoridade
5. misturar arvore ativa com arvore espelho em `OctoBox/` e gerar falso positivo

### Direcao

A direcao correta aqui e:

1. classificar antes de deletar
2. reduzir autoridade falsa antes de reescrever naming
3. migrar ponte legada antes de aposentar host historico
4. manter `shared.css` como manifesto ate que a divisao de ownership esteja mais limpa

### Acoes

1. congelar exclusao em `catalog/shared` ate fechar classificacao
2. priorizar `utilities.css`, porque ele concentra helper neutro, semantica local e engine utilitaria no mesmo arquivo
3. isolar o bloco `ENGINE DE UTILITARIOS AAA` como hotspot de override
4. mapear `glass-panel*` e `finance-glass-panel*` por superficie antes de propor substituicao
5. tratar `note-panel*` e `legacy-copy*` como protegidos

## Cadeia de ownership

### Dono de carregamento

O ownership de carregamento vem de [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py), pela funcao `build_catalog_assets(...)`.

Quando `include_catalog_shared=True`, o pacote compartilhado entra na tela.

### Dono de tema e estado

Algumas familias ja mudaram de dono:

1. `note-panel*` deixou de ser autoridade local e hoje mora em [../../static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)
2. `utilities.css` ainda pode complementar layout, mas nao deve redefinir tema de `note-panel`

### Dono de sintoma

Hoje `utilities.css` esta exercendo tres papeis ao mesmo tempo:

1. helper neutro
2. componente compartilhado de catalogo
3. area de escape com utilitarios de alta autoridade via `!important`

Esse acoplamento e o principal cheiro de risco da Onda 1.

## Evidencias principais

O scanner forense reportou nesta base:

1. `113` regras com `!important`
2. `1570` duplicacoes de seletor
3. `990` hotspots de override
4. `295` candidatos a seletor sem uso
5. `106` ocorrencias de familias legadas monitoradas

No recorte da Onda 1, os sinais mais fortes sao:

1. [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css) mistura semantica real com engine utilitaria de alta autoridade
2. `plan-card.is-selected-plan` usa `!important` em borda, background e sombra
3. estados `[hidden]` usam `display: none !important`
4. o bloco `ENGINE DE UTILITARIOS AAA` injeta margem, padding, gap, flex e tipografia com `!important`
5. `legacy-copy` aparece em `scene.css`, `student-financial.css`, `student-page-shell.css` e `utilities.css`
6. `note-panel*` aparece em templates e JS reais, inclusive em [../../static/js/pages/students/student-directory.js](../../static/js/pages/students/student-directory.js)

## Classificacao dos achados

### `canonical-alias`

Familias protegidas que parecem legado, mas ainda sao contrato vivo:

1. `note-panel*`

Pistas:

1. aparece em templates reais de formulario, financeiro, student page e operacoes
2. ha comentario explicito em [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css) informando que a autoridade saiu dali
3. o host canonico esta em [../../static/css/design-system/components/states.css](../../static/css/design-system/components/states.css)

Acao recomendada:

1. nao apagar
2. evitar redefinir tema localmente
3. permitir apenas complemento de layout por contexto

### `structural-do-not-touch`

Contrato estrutural que ainda atravessa a base:

1. `legacy-copy`

Pistas:

1. a token aparece em varios modulos compartilhados do catalogo
2. a malha de texto secundario ainda depende dela

Acao recomendada:

1. nao renomear nem substituir em massa nesta onda
2. registrar futura estrategia de migracao para token mais canonico so depois de medir impacto

### `legacy-bridge`

Pontes legadas ainda vivas:

1. `glass-panel`
2. `finance-glass-panel`

Pistas:

1. o scanner marcou ambas como `legacy-bridge`
2. aparecem em templates reais de financeiro, class-grid, onboarding e diretorio estudantil na arvore espelho `OctoBox/`
3. o guia de CSS ja reconhece essa familia como base compartilhada historica

Leitura tecnica:

Essas classes sao como andaime de obra. Sao feias para deixar para sempre, mas tirar antes da parede curar derruba a fachada.

Acao recomendada:

1. mapear superficie por superficie
2. criar equivalente canonico por contexto antes da retirada
3. remover por ondas, nunca por busca textual isolada

### `override-hotspot`

Pontos onde a cascata esta sendo vencida no grito:

1. `plan-card.is-selected-plan` em [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
2. estados `[hidden]` em [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
3. bloco `ENGINE DE UTILITARIOS AAA` em [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css)
4. trechos de [../../static/css/catalog/shared/student-page-shell.css](../../static/css/catalog/shared/student-page-shell.css) com reset via `!important`

Pistas:

1. margem, padding, flex e tipografia com `!important` transformam helper em arma de override
2. isso torna previsao de cascata mais cara e empurra a base para remendo

Acao recomendada:

1. separar utilitario neutro de componente semantico
2. reduzir `!important` apenas depois de descobrir o competidor da cascata
3. tratar cada grupo como disputa de ownership, nao como simples linter issue

### `dead`

Mortos provaveis com sinal forte:

1. `elite-glass-card`
2. `glass-panel-elite`
3. `ui-card`
4. [../../static/css/design-system/components/dashboard/summary.css.bkp](../../static/css/design-system/components/dashboard/summary.css.bkp)

Pistas:

1. scanner marcou essas familias com `hits: 0`
2. o arquivo `.bkp` e residual evidente

Acao recomendada:

1. remover em pacote proprio de baixo risco
2. fazer smoke rapido depois da exclusao
3. se o nome aparecer apenas em specs, relatarios ou arvore historica, tratar como quarentena documental e nao como runtime vivo

### `candidate-unused`

Sinais que pedem prova antes de exclusao:

1. `secondary-glow`
2. seletores compartilhados classificados pelo scanner como possivelmente sem uso

Pistas:

1. `secondary-glow` apareceu na arvore `OctoBox/templates/catalog/students.html` e na CSS espelho
2. nao houve evidencia forte de consumo na arvore principal `templates/`

Acao recomendada:

1. confirmar se `OctoBox/` e runtime ativo, espelho ou historico
2. so depois decidir entre migrar, manter ou remover

## Diagnostico do arquivo `utilities.css`

O arquivo [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css) hoje esta fazendo trabalho de tres arquivos diferentes:

1. biblioteca de utilitarios
2. kit compartilhado de componentes simples do catalogo
3. deposito de remendos com `!important`

Principais grupos internos:

1. base util e legitima
   Exemplos: `field-grid-*`, `mix-bar-*`, `chart-*`, `timeline-*`
2. semantica compartilhada de catalogo
   Exemplos: `plan-card`, `intake-card`, `history-entry`, `disclosure-panel`, `installment-shell`
3. engine utilitaria de alta autoridade
   Exemplos: `.mt-*`, `.mb-*`, `.p-*`, `.gap-*`, `.flex-*`, `.text-*`

Leitura pratica:

Hoje esse arquivo esta como uma gaveta onde moram talher, chave de fenda e fio desencapado. A Onda 1 nao pede jogar tudo fora. Pede separar por bandeja para parar de cortar a mao quando abrir.

## Ordem segura de correcao

### Fase 1: congelamento de exclusao

Nao apagar nada de `catalog/shared` antes de fechar consumo de:

1. `glass-panel*`
2. `finance-glass-panel*`
3. `secondary-glow`
4. grupos utilitarios com `!important`

### Fase 2: pacote de baixo arrependimento

Pode entrar cedo:

1. remover [../../static/css/design-system/components/dashboard/summary.css.bkp](../../static/css/design-system/components/dashboard/summary.css.bkp)
2. preparar retirada de familias sem `hits`, como `elite-glass-card`, `glass-panel-elite` e `ui-card`, se nenhuma arvore ativa referenciar
3. manter esses nomes em observacao se aparecerem apenas em specs, ghost reports ou arvores espelho

### Fase 3: reordem interna de `utilities.css`

Separar por ownership:

1. utilitarios neutros
2. componentes compartilhados do catalogo
3. hotspots temporarios de override

Objetivo:

1. facilitar leitura
2. reduzir conflitos futuros
3. preparar remocao gradual de `!important`

### Fase 4: migracao das pontes legadas

Para cada superficie que usa `glass-panel*`:

1. identificar qual equivalente canonico deve receber a responsabilidade
2. adaptar template e CSS local
3. remover ponte so depois do smoke da tela

### Fase 5: limpeza assistida por evidencias

Usar o scanner de novo depois de cada pacote para verificar:

1. queda de `!important`
2. queda de familias legadas
3. ausencia de regressao em classes protegidas

## Recomendações objetivas da Onda 1

### Fazer agora

1. criar pacote proprio para mortos evidentes
2. abrir refactor de estrutura de `utilities.css`
3. documentar `glass-panel*` como ponte viva por superficie

## Status de execucao do Pacote A

Executado nesta fase:

1. remocao do residual [../../static/css/design-system/components/dashboard/summary.css.bkp](../../static/css/design-system/components/dashboard/summary.css.bkp)
2. reorganizacao documental de [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css) por ownership, sem alterar comportamento visual

Mantido em quarentena documental:

1. `elite-glass-card`
2. `glass-panel-elite`
3. `ui-card`

Motivo:

1. nao houve evidencia na arvore principal de runtime consultada
2. ainda existem referencias em specs, inventarios e relatorios antigos
3. sem confirmar se toda arvore espelho esta fora do runtime, a exclusao nominal ainda seria precipitada

Resultado do Pacote B:

1. `utilities.css` agora separa explicitamente helpers, surfaces compartilhadas, metricas, disclosure, engine de compatibilidade e adaptacoes de tema escuro
2. os hotspots de `!important` ficaram demarcados como area de compatibilidade e nao como modelo para novas regras
3. a cascata foi preservada, porque a reorganizacao desta fase foi apenas semantica e documental

## Status parcial da Onda 2

Executado nesta fase:

1. remocao do `style=""` fixo em [../../templates/catalog/student-source-capture.html](../../templates/catalog/student-source-capture.html)
2. introducao do modificador estrutural [../../static/css/design-system/components/layout-blocks.css](../../static/css/design-system/components/layout-blocks.css) com `.layout-panel--narrow-center`

Decisao de ownership:

1. largura limitada e centralizacao sao estrutura, nao tema local, entao a correcao foi promovida para `layout-blocks.css`
2. o template ativo passou a consumir classe oficial em vez de carregar decisao visual inline

Mantido por enquanto:

1. usos de `style="--bar-width: ..."` e `style="--bar-height: ..."` na arvore `OctoBox/`, porque ali o inline esta servindo como passagem de dado dinamico para CSS
2. qualquer `<style>` encontrado apenas na arvore espelho, ate confirmacao final de runtime

Veredito posterior:

1. [front-end-runtime-boundary-map.md](front-end-runtime-boundary-map.md) confirmou que `OctoBox/` deve ser tratado como arvore espelho no runtime atual
2. com isso, esses achados deixam de bloquear a limpeza do runtime principal e passam a ser classificados como drift de referencia historica

### Nao fazer agora

1. apagar `note-panel*`
2. renomear `legacy-copy` em massa
3. retirar `glass-panel*` sem migracao
4. trocar todos os `!important` por uma vez so

## Proximo passo recomendado

Encerrar a Onda 1 com dois pacotes separados:

1. `Pacote A`: remocao de mortos evidentes e residuais
2. `Pacote B`: reorganizacao de [../../static/css/catalog/shared/utilities.css](../../static/css/catalog/shared/utilities.css) sem alterar comportamento visual

Depois disso, a Onda 2 pode entrar com mais seguranca nos inline styles e na autoridade visual falsa, porque a casa ja vai estar mapeada e com menos fio cruzado.
