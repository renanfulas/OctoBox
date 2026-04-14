<!--
ARQUIVO: raio-x forense da superficie /operacao/owner/.

POR QUE ELE EXISTE:
- registra o ownership real da tela do owner.
- evita que legado visual do tema notion volte a ser tratado como runtime vivo.
- deixa explicito o que esta ativo, o que esta sobrando e o que ainda precisa prova extra.

O QUE ESTE ARQUIVO FAZ:
1. mapeia view -> presenter -> template -> includes -> CSS.
2. classifica achados principais da superficie do owner.
3. registra o corte seguro aplicado no manifesto CSS.
4. aponta o que ainda nao deve ser apagado sem prova adicional.

PONTOS CRITICOS:
- este documento nao autoriza apagar includes ou payload so por intuicao.
- runtime real vence memoria, ghost audit antigo ou historia de fase anterior.
-->

# Auditoria forense da superficie owner

## Ownership real

Trilho vivo da tela:

1. view: [../../operations/workspace_views.py](../../operations/workspace_views.py)
2. presenter/payload: [../../operations/presentation.py](../../operations/presentation.py)
3. snapshot: [../../operations/queries.py](../../operations/queries.py)
4. template principal: [../../templates/operations/owner.html](../../templates/operations/owner.html)
5. includes realmente carregados:
   - [../../templates/operations/includes/owner/owner_command_lane.html](../../templates/operations/includes/owner/owner_command_lane.html)
   - [../../templates/operations/includes/owner/owner_sessions_panel.html](../../templates/operations/includes/owner/owner_sessions_panel.html)
   - [../../templates/operations/includes/owner/owner_metrics_section.html](../../templates/operations/includes/owner/owner_metrics_section.html)
6. manifesto CSS carregado pela pagina:
   - [../../static/css/design-system/operations.css](../../static/css/design-system/operations.css)
   - [../../static/css/design-system/operations/owner.css](../../static/css/design-system/operations/owner.css)
   - [../../static/css/design-system/operations/refinements/owner-simple.css](../../static/css/design-system/operations/refinements/owner-simple.css)

## Achados classificados

### 1. `owner-notion` sem consumidor vivo no runtime principal

Classificacao:

1. `dead`

Evidencia:

1. a pagina real usa `owner-simple-shell` em [../../templates/operations/owner.html](../../templates/operations/owner.html)
2. a busca em `templates/operations`, `operations` e `static/js` nao encontrou `owner-notion-shell`
3. os seletores do tema notion sao todos escopados por `.owner-notion-shell` em:
   - [../../static/css/design-system/operations/owner/notion/scene.css](../../static/css/design-system/operations/owner/notion/scene.css)
   - [../../static/css/design-system/operations/owner/notion/narrative.css](../../static/css/design-system/operations/owner/notion/narrative.css)
   - [../../static/css/design-system/operations/owner/notion/panels.css](../../static/css/design-system/operations/owner/notion/panels.css)
   - [../../static/css/design-system/operations/owner/notion/dark.css](../../static/css/design-system/operations/owner/notion/dark.css)
   - [../../static/css/design-system/operations/owner/notion/responsive.css](../../static/css/design-system/operations/owner/notion/responsive.css)

Acao aplicada:

1. removido `@import url("./owner/notion.css");` de [../../static/css/design-system/operations/owner.css](../../static/css/design-system/operations/owner.css)

Traducao simples:

1. a sala real esta decorada em modo `simple`
2. o caminhão ainda trazia um segundo jogo de moveis `notion`
3. o corte aplicado foi parar de entregar moveis que nao entram em casa nenhuma

### 2. includes do owner fora da composicao atual

Classificacao:

1. `dead`

Arquivos:

1. [../../templates/operations/includes/owner/owner_primary_panel.html](../../templates/operations/includes/owner/owner_primary_panel.html)
2. [../../templates/operations/includes/owner/owner_status_panel.html](../../templates/operations/includes/owner/owner_status_panel.html)
3. [../../templates/operations/includes/owner/owner_structure_panel.html](../../templates/operations/includes/owner/owner_structure_panel.html)
4. [../../templates/operations/includes/owner/owner_sequence_panel.html](../../templates/operations/includes/owner/owner_sequence_panel.html)

Evidencia:

1. a composicao atual em [../../templates/operations/owner.html](../../templates/operations/owner.html) nao inclui esses arquivos
2. a busca em `templates/operations` e `operations` nao encontrou consumidores vivos por nome
3. a unica lembranca restante apareceu em spec historica de onda anterior, nao em runtime vivo
4. o CSS local correspondente em `owner/simple/panels.css`, `owner/simple/dark.css` e `refinements/owner-simple.css` tambem ficou sem corpo no DOM atual

Acao aplicada:

1. removidos os templates antigos:
   - [../../templates/operations/includes/owner/owner_primary_panel.html](../../templates/operations/includes/owner/owner_primary_panel.html)
   - [../../templates/operations/includes/owner/owner_status_panel.html](../../templates/operations/includes/owner/owner_status_panel.html)
   - [../../templates/operations/includes/owner/owner_structure_panel.html](../../templates/operations/includes/owner/owner_structure_panel.html)
   - [../../templates/operations/includes/owner/owner_sequence_panel.html](../../templates/operations/includes/owner/owner_sequence_panel.html)
2. removidas as regras CSS orfas correspondentes em:
   - [../../static/css/design-system/operations/owner/simple/panels.css](../../static/css/design-system/operations/owner/simple/panels.css)
   - [../../static/css/design-system/operations/owner/simple/dark.css](../../static/css/design-system/operations/owner/simple/dark.css)
   - [../../static/css/design-system/operations/refinements/owner-simple.css](../../static/css/design-system/operations/refinements/owner-simple.css)

### 3. snapshot mais rico que a tela atual

Classificacao:

1. `legacy-bridge`

Evidencia:

1. [../../operations/queries.py](../../operations/queries.py) ainda retorna contexto de decisao e prioridade mais amplo do que os 3 includes atuais exibem
2. isso nao e bug por si so, mas indica heranca de uma fase editorial anterior

Acao segura recomendada:

1. medir quais chaves do snapshot alimentam hero e command lane de verdade
2. so depois reduzir payload

## Mapa de consumo do payload do owner

Tabela curta de "quem ainda bebe desse copo":

1. `headline_metrics`
   - consumido em [../../operations/presentation.py](../../operations/presentation.py) para montar o hero do owner
   - tambem alimenta a montagem interna de `owner_operational_focus` em [../../operations/queries.py](../../operations/queries.py)
   - status: `structural-do-not-touch`

2. `owner_operational_focus`
   - consumido em [../../operations/presentation.py](../../operations/presentation.py) para hero e reading panel
   - renderizado em [../../templates/operations/includes/owner/owner_command_lane.html](../../templates/operations/includes/owner/owner_command_lane.html)
   - status: `structural-do-not-touch`

3. `owner_priority_context`
   - consumido apenas para `pill_label` e `pill_class` fixos no reading panel
   - status anterior: `legacy-bridge`
   - acao aplicada: removido do snapshot; o presenter agora deriva `Agora` + `accent` localmente

4. `owner_decision_entry_context`
   - consumido em [../../operations/presentation.py](../../operations/presentation.py) para as acoes do hero e o `primary_href` do reading panel
   - status: `structural-do-not-touch`

5. `owner_priority_surface`
   - consumido em [../../templates/operations/owner.html](../../templates/operations/owner.html) como `data-owner-priority`
   - status: `structural-do-not-touch`

6. `overdue_amount_label`
   - consumido em [../../templates/operations/owner.html](../../templates/operations/owner.html) no bloco `visually-hidden`
   - status: `structural-do-not-touch`

7. `owner_upcoming_sessions`
   - consumido em [../../templates/operations/includes/owner/owner_sessions_panel.html](../../templates/operations/includes/owner/owner_sessions_panel.html)
   - status: `structural-do-not-touch`

8. `owner_upcoming_sessions_total_label`
   - consumido em [../../templates/operations/includes/owner/owner_sessions_panel.html](../../templates/operations/includes/owner/owner_sessions_panel.html)
   - status: `structural-do-not-touch`

9. `metric_cards`
   - consumido em [../../templates/operations/includes/owner/owner_metrics_section.html](../../templates/operations/includes/owner/owner_metrics_section.html)
   - status: `structural-do-not-touch`

10. `classes_today`
   - nenhum consumidor vivo encontrado em `templates`, `operations` ou `static/js`
   - status: `dead`
   - acao aplicada: removido do retorno do snapshot

11. `owner_secondary_focus`
   - so aparecia em [../../templates/operations/includes/owner/owner_primary_panel.html](../../templates/operations/includes/owner/owner_primary_panel.html), removido nesta onda
   - status: `dead` no runtime principal
   - acao aplicada: removido do retorno do snapshot

12. seletores residuais de `owner/simple`
   - `owner-workspace`, `owner-panel-grid`, `owner-support-grid`, `owner-panel`, `owner-step-card`, `owner-next-steps-title`, `owner-step-number` e `owner-step-body`
   - nenhum consumidor vivo encontrado no DOM ativo do owner
   - status: `dead`
   - acao aplicada: removidos dos arquivos [../../static/css/design-system/operations/owner/simple/scene.css](../../static/css/design-system/operations/owner/simple/scene.css), [../../static/css/design-system/operations/owner/simple/panels.css](../../static/css/design-system/operations/owner/simple/panels.css) e [../../static/css/design-system/operations/owner/simple/dark.css](../../static/css/design-system/operations/owner/simple/dark.css)

## Corte aplicado nesta onda

Aplicado agora:

1. remoção do import `owner/notion.css` do manifesto vivo do owner
2. remocao de `classes_today` do snapshot do owner
3. remocao de `owner_secondary_focus` do snapshot do owner
4. remocao dos includes antigos do owner
5. remocao do CSS orfao ligado a esses includes
6. remocao de `owner_priority_context` do snapshot do owner
7. remocao dos ultimos seletores residuais sem consumidor em `owner/simple`

Nao aplicado ainda:

1. reducao adicional do snapshot do owner
2. reescrita dos refinamentos do owner

## Proximo passo sugerido

1. considerar esta frente pronta para commit proprio
2. depois voltar para a correcao separada dos KPIs de alunos em `student_queries.py`

## Padroes visuais encontrados na command lane

1. `semantica parcial de variante`
   - sintoma: `chip`, `count` ou ponto visual mudam de cor, mas a casca externa do card continua neutra
   - causa raiz: a variante controla apenas descendentes e deixa `background`, `border-color` e `box-shadow` no host base
   - traducao simples: e como trocar o volante e o banco do carro, mas deixar a lataria cinza
   - regra segura: quando uma lane usar variantes como `entries`, `billing` e `structure`, a cor precisa fechar no host e nos filhos

2. `payload semantico brigando com variante local`
   - sintoma: `owner-command-card--billing` continua puxando vermelho por causa de `.is-danger`
   - causa raiz: a classe do payload carrega uma semantica antiga que pode vencer ou confundir a variante nova
   - traducao simples: a etiqueta velha da caixa ainda fala mais alto que a etiqueta nova
   - regra segura: a variante local do owner deve ser a autoridade final para shell, chip, count e ponto visual

3. `shell de agenda com decoracao vazando`
   - sintoma: painel de agenda ganha orelhas, brilho sobrando no canto ou cara de caixa dupla no dark
   - causa raiz: `table-card::after` continua ativo no host local e o painel deixa `overflow` aberto demais
   - traducao simples: o card esta certo, mas o brilho do abajur passa para fora da cúpula
   - regra segura: em shells de agenda como `owner-sessions-panel`, o wrapper deve prender o brilho com `overflow: hidden` e desligar a decoracao extra quando ela competir com o tema local

4. `trilha interna com largura magica`
   - sintoma: barra de ocupacao parece curta demais ou nao acompanha a largura util do card
   - causa raiz: a progress bar nasce com `width: min(...px, 100%)` e deixa de seguir o espaco real do container
   - traducao simples: a regua da barra para antes do fim da mesa
   - regra segura: em cards operacionais, a trilha deve usar `width: 100%` e esticar dentro do padding util do card

5. `state-empty sem branch dark proprio`
   - sintoma: o estado vazio parece um bloco estranho ou claro demais dentro de um painel dark bem resolvido
   - causa raiz: o host compartilhado `state-empty` fica neutro demais e o contexto local tenta compensar no painel em volta
   - traducao simples: a sala esta escura e elegante, mas a placa de "nada aqui" ainda veio impressa no papel do turno da manha
   - regra segura: primeiro fechar um dark mode canonico em `states.css`; depois, se necessario, aplicar apenas um sotaque local no shell do owner

6. `override local perdendo para host compartilhado`
   - sintoma: o arquivo local parece correto, mas padding, altura, tipografia ou alinhamento continuam iguais no runtime
   - causa raiz: o host canonico entra com seletor mais especifico, como `.operation-shell .page-reading-list .fdw-focus-card`, e o modulo local tenta responder com seletor mais curto
   - traducao simples: o gerente da loja deu a ordem certa, mas o aviso da matriz estava pendurado maior bem na frente
   - regra segura: em lanes derivadas de `fdw-focus-card`, subir a especificidade do modulo local para o mesmo nivel do host antes de pensar em `!important`
