<!--
ARQUIVO: mapa forense de payload, presenter e contrato de tela do OctoBox.

POR QUE ELE EXISTE:
- transforma bugs de "backend visual" em trilho curto de investigacao.
- ajuda a descobrir quando a tela esta errada por contrato fraco, presenter torto ou contexto vazando.
- reduz o vicio de culpar CSS quando o problema nasceu antes de o HTML existir.

O QUE ESTE ARQUIVO FAZ:
1. aponta onde o contrato de tela nasce.
2. lista sintomas tipicos de payload, presenter e shell context quebrados.
3. mostra onde olhar primeiro por tipo de falha.
4. sugere correcoes que fortalecem o contrato sem inflar a view.

PONTOS CRITICOS:
- este documento nao pede reescrever todas as views.
- ele nao autoriza empurrar regra de negocio para presenter.
- se o dado estiver errado na origem de dominio, query, facade ou workflow ainda vencem como suspeitos anteriores.
-->

# Mapa forense de payload, presenter e contrato de tela

Este documento existe para responder a pergunta:

1. a UI esta errada porque o CSS falhou ou porque a tela nasceu errada antes de renderizar?

Metafora curta:

1. o CSS veste a pessoa
2. o template monta a vitrine
3. o payload decide o que entrou na loja
4. o presenter organiza as caixas antes de elas chegarem na vitrine

Se a vitrine esta confusa, nem sempre o problema e a roupa.
As vezes as caixas ja chegaram trocadas.

## Ordem curta de leitura

Se a suspeita for de payload, presenter, shell context ou contrato de tela, leia nesta ordem:

1. [../../README.md](../../README.md)
2. [documentation-authority-map.md](documentation-authority-map.md)
3. [front-end-ownership-map.md](front-end-ownership-map.md)
4. [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
5. [../plans/catalog-page-payload-presenter-blueprint.md](../plans/catalog-page-payload-presenter-blueprint.md)
6. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
7. [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py)
8. [../../operations/presentation.py](../../operations/presentation.py)
9. [../../access/context_processors.py](../../access/context_processors.py)
10. [../../access/shell_actions.py](../../access/shell_actions.py)

Regra pratica:

1. se o HTML parece organizado mas mostra conteudo incoerente, suspeite do payload
2. se a pagina perdeu hero, assets, behavior ou shell info ao mesmo tempo, suspeite da montagem do page payload
3. se varias telas sofrem a mesma incoerencia de leitura, suspeite do contexto global do shell

## Onde o contrato de tela nasce

No estado atual do OctoBox, a montagem visual do backend passa principalmente por estes pontos:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py) para shape canonico, hero, reading panel, assets e bridge legado
2. [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py) para helpers do catalogo
3. presenters do catalogo em [../../catalog/presentation](../../catalog/presentation)
4. [../../operations/presentation.py](../../operations/presentation.py) para workspaces operacionais
5. [../../access/context_processors.py](../../access/context_processors.py) para shell global, navegacao, alertas e asset version
6. [../../access/shell_actions.py](../../access/shell_actions.py) para scope do shell e counts globais

## Heuristica-mestra

Pergunte nesta ordem:

1. a view esta curta ou esta montando contexto demais?
2. o payload esta namespaced ou cheio de chaves soltas?
3. o presenter esta organizando a tela ou tomando decisoes de negocio que nao pertencem a ele?
4. o template esta renderizando o contrato ou inventando regra por conta propria?
5. o JS esta lendo `behavior` e `data-*` ou redescobrindo estado pelo DOM?

## Padroes principais, pistas e correcoes

### 1. Dado certo no dominio, errado na tela

Sinais na cena:

1. query ou model mostram uma coisa
2. a pagina mostra resumo, badge, hero ou CTA incoerente
3. o erro aparece na leitura consolidada, nao no registro cru

Leitura provavel:

1. o problema costuma morar no presenter, page builder ou bridge de contexto

Onde olhar primeiro:

1. presenter da pagina
2. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
3. template principal da tela

Correcao que costuma funcionar:

1. ajustar a traducao do dado para a linguagem da tela
2. manter a view curta
3. nao empurrar esse ajuste para CSS ou JS quando o problema e semantico

### 2. Template fazendo trabalho de presenter

Sinais na cena:

1. muitos `if`, `elif`, flags espalhadas ou copy duplicada
2. template decidindo estado operacional, prioridade ou CTA
3. pequenas mudancas exigem editar HTML em muitos pontos

Leitura provavel:

1. o contrato da tela esta fraco
2. o presenter nao organizou contexto suficiente

Onde olhar primeiro:

1. presenter da tela
2. [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py)
3. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)

Correcao que costuma funcionar:

1. mover composicao semantica para o presenter
2. deixar o template renderizar blocos e `data-*`
3. nao criar mini framework de presenter so para fugir de alguns `if`

### 3. View HTTP virando buraco negro de contexto

Sinais na cena:

1. a view monta muitas listas, flags, urls, copy e assets manualmente
2. o contrato da pagina existe, mas esta espalhado
3. mexer na view parece mexer na tela inteira

Leitura provavel:

1. a view passou a agir como presenter improvisado

Onde olhar primeiro:

1. view do dominio
2. presenter correspondente
3. blueprint em [../plans/catalog-page-payload-presenter-blueprint.md](../plans/catalog-page-payload-presenter-blueprint.md)

Correcao que costuma funcionar:

1. empurrar a montagem da tela para presenter ou builder pequeno
2. deixar a view cuidar de request, auth, chamada e response
3. reduzir chaves soltas no contexto

### 4. Hero, reading panel ou shell vindo incoerentes

Sinais na cena:

1. hero sem CTA correto
2. reading panel sem prioridade certa
3. shell scope, eyebrow ou titulo desalinhados com a pagina

Leitura provavel:

1. o contrato de hero ou shell context foi montado errado

Onde olhar primeiro:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [../../operations/presentation.py](../../operations/presentation.py)
3. [../../access/context_processors.py](../../access/context_processors.py)
4. [../../access/shell_actions.py](../../access/shell_actions.py)

Correcao que costuma funcionar:

1. usar `build_page_hero(...)` e `build_page_reading_panel(...)` como host canonico
2. corrigir `resolve_shell_scope(...)` quando o scope esta errado
3. nao hardcodar hero no template se o contrato canonico ja existe

### 5. Assets da tela somem, duplicam ou nao aplicam

Sinais na cena:

1. a pagina nao carrega CSS ou JS esperado
2. o comportamento da tela falha mesmo com markup certo
3. a mudanca em arquivo local nao aparece onde deveria

Leitura provavel:

1. o payload nao anexou assets corretamente
2. `attach_page_payload(...)` ou `build_page_assets(...)` nao recebeu a lista certa

Onde olhar primeiro:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py)
3. presenter da tela

Correcao que costuma funcionar:

1. declarar assets no payload da tela
2. evitar injetar CSS e JS por fora do contrato
3. checar `current_page_assets`, `page_assets` e aliases de attach

### 6. JS redescobrindo estado pelo DOM

Sinais na cena:

1. o script precisa ler texto, classe ou markup para entender estado
2. pequenas mudancas de template quebram o comportamento
3. a pagina parece "funcionar por coincidencia"

Leitura provavel:

1. `behavior` ou `json_blocks` do payload estao fracos
2. faltam `data-*` estaveis

Onde olhar primeiro:

1. `behavior` do payload
2. template principal da tela
3. JS local da pagina

Correcao que costuma funcionar:

1. mandar o que o JS precisa via payload
2. usar `data-page`, `data-slot`, `data-panel`, `data-ui` e `data-action`
3. nao deixar o JS inferir negocio pelo HTML quando o backend pode declarar o estado

### 7. Shell counts, alertas ou foco global errados

Sinais na cena:

1. topbar com contagem estranha
2. alerta global incoerente com o estado real
3. uma pagina local muda e o shell inteiro parece fora do tom

Leitura provavel:

1. a falha esta no shell global, nao na tela local

Onde olhar primeiro:

1. [../../access/shell_actions.py](../../access/shell_actions.py)
2. [../../access/context_processors.py](../../access/context_processors.py)

Correcao que costuma funcionar:

1. revisar `get_shell_counts(...)`
2. revisar `resolve_shell_scope(...)`
3. nao "corrigir" o shell duplicando count local em template de pagina

### 8. Papel, menu ou navegacao errados

Sinais na cena:

1. menu ativo errado
2. papel ve CTA que nao deveria
3. topbar ou sidebar parecem de outra area

Leitura provavel:

1. a navegacao global ou o contract de rota esta desalinhado

Onde olhar primeiro:

1. [../../access/context_processors.py](../../access/context_processors.py)
2. `get_navigation_contract(...)`
3. role da view atual

Correcao que costuma funcionar:

1. alinhar nav key, scope e role gating
2. nao mascarar erro de navegacao com if local no template

### 9. Payload inflado com cosmetica redundante

Sinais na cena:

1. o mesmo dado chega em varias chaves so para sustentar layout
2. presenter produz copy cosmetica demais
3. alterar layout exige tocar backend sem necessidade real

Leitura provavel:

1. o contrato semantico enxuto foi quebrado

Onde olhar primeiro:

1. presenter da pagina
2. [../plans/catalog-page-payload-presenter-blueprint.md](../plans/catalog-page-payload-presenter-blueprint.md)
3. [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)

Correcao que costuma funcionar:

1. backend entrega dado real, acesso, estado e acao
2. frontend organiza repeticao e distribuicao visual
3. remover duplicacao cosmetica do payload

### 10. Contexto namespaced e alias legado se atropelando

Sinais na cena:

1. a pagina usa `page_payload` e tambem depende de chaves planas antigas
2. uma mudanca aparentemente inocente quebra template legado
3. o contexto parece ter duas linguas ao mesmo tempo

Leitura provavel:

1. a bridge de compatibilidade esta viva e precisa ser tratada com cuidado

Onde olhar primeiro:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. `attach_page_payload(...)`
3. includes antigos da tela

Correcao que costuma funcionar:

1. usar aliases de forma centralizada
2. nao repetir bridge legado em varias views
3. migrar tela por tela, sem explodir tudo de uma vez

## Suspeitos recorrentes da base

Se a falha parecer nascer antes do CSS, estes arquivos merecem lupa primeiro:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py)
3. [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)
4. [../../catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)
5. [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
6. [../../catalog/presentation/class_grid_page.py](../../catalog/presentation/class_grid_page.py)
7. [../../operations/presentation.py](../../operations/presentation.py)
8. [../../access/context_processors.py](../../access/context_processors.py)
9. [../../access/shell_actions.py](../../access/shell_actions.py)

## Veredito pratico

Quando a UI parece quebrada, nao culpe o CSS cedo demais.

No OctoBox, muitas falhas visiveis nascem daqui:

1. payload mal montado
2. presenter fazendo pouco ou demais
3. view carregando contexto demais
4. shell global contaminando a leitura local
5. template improvisando regra que deveria vir pronta

Em linguagem curta:

1. se a roupa ficou torta, pode ser o corte
2. mas as vezes o problema foi a pessoa entrar no provador com a roupa errada
