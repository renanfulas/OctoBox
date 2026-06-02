<!--
ARQUIVO: auditoria da Onda 4 na trilha contratual do front-end.

POR QUE ELE EXISTE:
- registra o raio-x do contrato entre payload, presenter, shell e template.
- separa bug visual verdadeiro de bug nascido no backend visual.
- cria uma lista curta de riscos e correcoes seguras antes de qualquer refatoracao maior.

O QUE ESTE ARQUIVO FAZ:
1. resume o papel de `page_payloads.py`, presenters do catalogo e shell.
2. classifica os principais achados desta onda.
3. indica o que e bug real, o que e risco controlado e o que e ponte estrutural.

PONTOS CRITICOS:
- o objetivo aqui nao e "mudar tudo", e descobrir onde o contrato esta forte ou fraco.
- parte do sistema usa namespacing saudavel; parte ainda convive com aliases e bridges por compatibilidade.
- mexer em assets compartilhados ou no shape de `behavior` sem prova pode espalhar regressao em varias telas.
-->

# Onda 4: auditoria da trilha contratual

Este documento responde a pergunta:

1. "quais problemas do front parecem CSS, mas na verdade nascem no contrato entre presenter, payload, shell e template?"

Em linguagem simples:

1. antes a gente limpou a tinta e os fios aparentes da casa
2. agora abrimos o quadro de energia para ver se a corrente chega certa em cada comodo
3. a boa noticia e que a casa ja tem uma fiação melhor do que parecia
4. a ma noticia e que ainda existem algumas emendas antigas e um fio errado de verdade

## Leitura geral da arquitetura

O desenho atual da trilha contratual do catalogo esta assim:

1. `shared_support/page_payloads.py` define o shape canonico do payload
2. `catalog/presentation/shared.py` especializa esse shape para o catalogo
3. os presenters de tela preenchem `context`, `data`, `actions`, `behavior`, `capabilities` e `assets`
4. `attach_page_payload()` injeta aliases necessarios no contexto do template
5. `templates/layouts/base.html` carrega assets e serializa `current_page_behavior` para o JS

Leitura tecnica:

1. existe um contrato namespaced relativamente limpo
2. existe uma ponte de compatibilidade para templates e shell
3. o sistema ainda convive com alguma autoridade duplicada entre server-render, template e JS

## Veredito curto

O contrato esta melhor do que parecia.

Os principais problemas desta onda nao sao "payload caotico".

Eles sao:

1. um bug real de shape na ficha do aluno
2. um acoplamento compartilhado de assets entre catalogo e operations
3. uma ponte de aliases que ainda funciona, mas pede disciplina
4. um contrato de tabs com autoridade dividida entre server-render e JS

## Achados classificados

## 1. Bug real: template do aluno le um caminho antigo de `behavior`

Classificacao:

1. `contract-bug`

Camada dona:

1. template da pagina canonica do aluno

Evidencia:

1. o presenter de [student_form_page.py](../../catalog/presentation/student_form_page.py) entrega `behavior.student_browser_snapshot`
2. o template [student_page_profile_panel.html](../../templates/includes/catalog/student_page/student_page_profile_panel.html) tenta ler `page.behavior.student_form.browser_snapshot.profile_version`
3. esse ramo `student_form.browser_snapshot` nao existe no payload atual

Risco:

1. o campo oculto `profile_version` fica vazio por padrao
2. isso enfraquece qualquer protecao baseada em versao de perfil na ficha canonica

Leitura simples:

1. o template esta procurando a chave no bolso velho do casaco
2. mas o presenter ja mudou a chave para um bolso novo

Correcao segura:

1. alinhar o template para `page.behavior.student_browser_snapshot.profile_version`
2. depois revisar se existe mais algum template usando o shape legado `page.behavior.student_form.*`

## 2. Hotspot contratual: `build_catalog_assets()` injeta `operations.css` por padrao

Classificacao:

1. `override-hotspot`

Camada dona:

1. helper compartilhado de presentation do catalogo

Evidencia:

1. [catalog/presentation/shared.py](../../catalog/presentation/shared.py) define `include_operations=True` por padrao
2. isso faz catalogo carregar `css/design-system/operations.css` mesmo em telas como alunos, financeiro e planos
3. os presenters do catalogo usam `build_catalog_assets(...)` sem desligar esse default

Risco:

1. vazamento visual de uma camada operacional para telas de catalogo
2. mais peso de CSS em paginas que nao precisariam dessa autoridade
3. debugging mais caro, porque um bug local pode nascer num arquivo compartilhado inesperado

Leitura simples:

1. e como ligar o sistema de som da quadra em toda sala de aula so porque um corredor passa perto

Correcao segura:

1. mapear quais telas do catalogo realmente precisam de `operations.css`
2. inverter o default no futuro so depois de prova de carregamento
3. enquanto isso, classificar `operations.css` como suspeito primario quando um bug do catalogo parecer "sem dono"

## 3. Ponte estrutural viva: `attach_page_payload()` mistura namespace com aliases de contexto

Classificacao:

1. `legacy-bridge`

Camada dona:

1. `shared_support/page_payloads.py`

Evidencia:

1. `attach_page_payload()` anexa o payload namespaced por `payload_key`
2. depois faz `context.update()` das secoes `context` e `shell`
3. isso deixa coexistirem `page.context.title` e aliases planos como `page_title`, `page_subtitle` e chaves de shell no contexto geral

Risco:

1. drift de template: um include pode ler o valor namespaced, outro o alias plano
2. debugging mais confuso quando docs e templates nao deixam claro qual camada e a fonte de verdade

Leitura simples:

1. a casa tem o endereco oficial e tambem varios apelidos pintados no muro
2. funciona, mas pode confundir o entregador

Correcao segura:

1. manter a ponte por enquanto
2. em novas telas, preferir consumir o payload namespaced
3. usar os aliases planos so quando o shell ou templates legados realmente precisarem

## 4. Contrato hibrido de tabs: estado inicial vem do template e a interacao vem do JS

Classificacao:

1. `structural-do-not-touch`

Camada dona:

1. presenters + templates de catalogo + `interactive_tabs.js`

Evidencia:

1. telas como [students.html](../../templates/catalog/students.html) e [finance.html](../../templates/catalog/finance.html) rendem `is-tab-active` no server com base em `page.behavior.default_panel`
2. o mesmo `default_panel` tambem e exposto em `data-default-panel`
3. [interactive_tabs.js](../../static/js/pages/interactive_tabs.js) reativa o painel no cliente e gerencia as trocas futuras

Risco:

1. existe autoridade duplicada aparente
2. mas ela tambem oferece progressive enhancement e estado inicial coerente sem depender do JS

Leitura simples:

1. parece que dois adultos estao segurando a mesma bicicleta
2. mas aqui um segura na largada e o outro assume quando a bicicleta comeca a andar

Correcao segura:

1. nao mexer nisso por reflexo
2. tratar como contrato hibrido intencional ate prova contraria
3. se houver refatoracao futura, fazer de forma planejada e em lote

## 5. `behavior` esta forte quando alimenta JS real, mas deve ser vigiado quando alimenta template diretamente

Classificacao:

1. `contract-watch`

Camada dona:

1. presenters do catalogo

Evidencia:

1. [student-directory.js](../../static/js/pages/students/student-directory.js) consome `student_prefetch` e `directory_search`
2. [student-form.js](../../static/js/pages/students/student-form.js) consome `plan_price_map`, `student_browser_snapshot` e `focus_sections`
3. templates tambem consomem partes de `behavior`, como `default_panel` e `student_form_initial_step`

Risco:

1. quando `behavior` serve a JS e template ao mesmo tempo, o shape fica mais sensivel a drift
2. pequenas mudancas de nome podem quebrar sem erro gritante

Correcao segura:

1. para novos contratos, preferir uma das duas trilhas por campo:
2. ou o campo existe para JS
3. ou o campo existe para template
4. se precisar servir aos dois, documentar o shape como contrato formal

## O que esta saudavel e nao merece cirurgia agora

Estes pontos parecem bons:

1. `build_page_payload()` tem shape claro e previsivel
2. `build_page_assets()` e a resolucao de runtime CSS em `attach_page_payload()` ajudam a evitar drift entre caminho logico e caminho real servido
3. `current_page_behavior|json_script` no [base.html](../../templates/layouts/base.html) e uma ponte limpa para JS
4. `capabilities` esta sendo usado de forma semantica e enxuta nos templates

## Prioridade pratica

Se eu fosse continuar essa onda por ordem de retorno:

1. corrigir o bug real de `student_page_profile_panel.html`
2. mapear uso real de `operations.css` nas telas do catalogo
3. catalogar quais campos de `behavior` servem a JS, template ou ambos
4. deixar a ponte de aliases sob observacao, sem reescrever agora

Evolucao desta trilha:

1. o mapa de dependencia e o primeiro corte seguro desta frente ficaram registrados em [front-end-wave4-operations-dependency-map.md](front-end-wave4-operations-dependency-map.md)

## Regra de ouro que saiu desta onda

Antes de culpar o CSS, pergunte:

1. esse dado veio certo?
2. esse shape ainda e o mesmo que o template espera?
3. essa tela esta carregando uma camada compartilhada que nem deveria estar aqui?

Se a resposta for "nao", o bug ja chegou torto antes da pintura.
