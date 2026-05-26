<!--
ARQUIVO: C.O.R.D.A. da Sprint 3 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, desenho de camadas e validacao de runtime

AUTORIDADE:
- alta para a Sprint 3 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
- [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
- [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)

QUANDO USAR:
- antes de alterar `shell.js`, topbar, sidebar, profile, blink actions, hash reveal ou celebracoes
- antes de mover efeitos globais para Sprint 6
- quando for validar o contrato de scripts globais do shell

POR QUE ELE EXISTE:
- registra a separacao entre comportamento essencial, interativo e cosmetico.
- evita que o shell volte a virar monolito.
- protege tema, sidebar e perfil como comportamento imediato.

O QUE ESTE ARQUIVO FAZ:
1. aplica C.O.R.D.A. para a Sprint 3.
2. mapeia responsabilidades de `shell.js`.
3. define a divisao em camadas.
4. registra riscos e validacoes.
5. prepara a Sprint 4.

PONTOS CRITICOS:
- tema, sidebar e perfil precisam continuar imediatos.
- hash reveal e blink actions podem viver em camada interativa, mas ainda precisam carregar no fluxo normal.
- celebracoes sao cosmeticas e devem acordar em idle.
-->

# Sprint 3: shell JavaScript em camadas C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A Sprint 0 mostrou que `shell.js` tinha aproximadamente `14.6KB` e era carregado em toda pagina autenticada.

A Sprint 2 ja tirou `search.js` do carregamento direto.

Agora o gargalo nao e apenas byte:

1. `shell.js` mistura comportamento essencial com interacoes e efeitos
2. qualquer mudanca nele pode quebrar o shell inteiro
3. celebracoes e blinks nao precisam morar no nucleo de tema/sidebar/perfil
4. separar responsabilidade reduz risco e prepara loaders futuros

Metafora simples:

1. antes a chave da porta, a campainha e os fogos ficavam no mesmo molho
2. agora a chave da porta fica separada para abrir a loja rapido

## O - Objetivo

Objetivos da sprint:

1. manter `shell.js` como camada essencial
2. mover hash reveal, topbar scroll e blink actions para camada interativa
3. mover celebracoes de contagem para camada cosmetica
4. carregar celebracoes em idle
5. proteger o contrato de scripts globais por teste
6. nao mexer ainda em `dynamic-visuals.js`, que pertence a Sprint 6

Criterios de pronto:

1. tema, sidebar e profile continuam em `shell.js`
2. `shell-interactions.js` existe e e carregado no base
3. `shell-effects-loader.js` existe e e carregado no base
4. `shell-effects.js` nao e carregado diretamente no HTML inicial
5. testes focados passam

## R - Riscos

Riscos considerados:

1. Escape parar de fechar sidebar ou profile
2. hash reveal parar de abrir `#dashboard`
3. blink actions deixarem de funcionar em cards do dashboard
4. celebracao carregar tarde demais e perder comparacao de contagens
5. aumento de numero de scripts parecer regressao

Mitigacoes:

1. `shell.js` preserva acessibilidade imediata de tema, sidebar, profile, Escape e resize
2. `shell-interactions.js` ainda carrega no fluxo normal do base
3. `shell-effects-loader.js` carrega `shell-effects.js` em idle, depois que DOM e contagens existem
4. teste protege nomes dos scripts esperados
5. a separacao prepara Sprint 4 de asset priority e Sprint 6 de efeitos sob demanda

## D - Direcao

Direcao escolhida:

1. reduzir `static/js/core/shell.js` ao essencial
2. criar `static/js/core/shell-interactions.js`
3. criar `static/js/core/shell-effects.js`
4. criar `static/js/core/shell-effects-loader.js`
5. atualizar `templates/layouts/base.html`
6. atualizar teste de renderizacao de alunos

Alternativas rejeitadas:

1. manter tudo em `shell.js`: rejeitado porque perpetua monolito
2. carregar tudo por idle: rejeitado porque hash reveal e blink actions sao interativos demais para atrasar indiscriminadamente
3. transformar tudo em ES modules agora: rejeitado por escopo maior e risco desnecessario
4. mexer em `dynamic-visuals.js` agora: rejeitado porque pertence a Sprint 6

## A - Acoes executadas

Arquivos investigados:

1. `static/js/core/shell.js`
2. `templates/layouts/base.html`
3. `static/css/design-system/topbar.css`
4. `boxcore/tests/test_dashboard.py`
5. `boxcore/tests/test_catalog.py`

Arquivos alterados:

1. `static/js/core/shell.js`
2. `static/js/core/shell-interactions.js`
3. `static/js/core/shell-effects.js`
4. `static/js/core/shell-effects-loader.js`
5. `templates/layouts/base.html`
6. `boxcore/tests/test_catalog.py`
7. `docs/plans/front-end-performance-master-plan.md`

Mudancas:

1. `static/js/core/shell.js` ficou responsavel apenas por tema, sidebar, profile, Escape e resize
2. `static/js/core/shell-interactions.js` passou a concentrar topbar scroll, hash reveal e blink actions
3. `static/js/core/shell-effects.js` passou a concentrar celebracoes de contagem e confetti DOM
4. `static/js/core/shell-effects-loader.js` passou a carregar os efeitos em idle ou timeout curto
5. `templates/layouts/base.html` passou a carregar `shell-interactions.js` e `shell-effects-loader.js`
6. `boxcore/tests/test_catalog.py` passou a proteger o contrato de scripts globais do shell

Validacao planejada:

1. renderizacao de alunos
2. page payload bridge
3. dashboard tests que protegem `blink-topbar-finance`
4. checagem de scripts no HTML inicial

Validacao executada:

```powershell
node --check static\js\core\shell.js; node --check static\js\core\shell-interactions.js; node --check static\js\core\shell-effects-loader.js; node --check static\js\core\shell-effects.js
```

Resultado:

1. sintaxe dos `4` arquivos JS validada
2. status `OK`

```powershell
.\.venv\Scripts\python.exe manage.py test boxcore.tests.test_catalog.CatalogViewTests.test_student_directory_renders boxcore.tests.test_page_payloads.PagePayloadBridgeContractTests boxcore.tests.test_dashboard.DashboardViewTests.test_dashboard_support_metric_cards_keep_neon_actions_without_navigation boxcore.tests.test_dashboard.DashboardViewTests.test_dashboard_overdue_metric_card_keeps_only_neon_when_clean boxcore.tests.test_dashboard.DashboardViewTests.test_dashboard_overdue_metric_card_restores_click_to_go_when_there_is_pressure --verbosity 1
```

Resultado:

1. `8` testes executados
2. status `OK`

Observacao:

1. uma execucao ampla de `DashboardViewTests` encontrou falha preexistente/externa ao split em `test_dashboard_keeps_routine_session_out_of_emergency_card`
2. a falha procurava o texto `Tudo tranquilo na reten`
3. a falha nao envolve os scripts do shell e deve ser tratada fora da Sprint 3

## Mapa de responsabilidades

`shell.js` essencial:

1. tema
2. sidebar
3. profile menu
4. Escape
5. resize mobile da sidebar
6. helpers seguros de storage

Peso apos split:

1. `shell.js`: aproximadamente `4.6KB`
2. `shell-interactions.js`: aproximadamente `5.6KB`
3. `shell-effects-loader.js`: aproximadamente `1.0KB`
4. `shell-effects.js`: aproximadamente `4.1KB`, carregado em idle

`shell-interactions.js`:

1. topbar scroll-to-top
2. hash reveal
3. legado `#dashboard` para `#dashboard-sessions-board`
4. blink actions de topbar
5. blink actions de board
6. blink actions de sidebar

`shell-effects.js`:

1. leitura de contagens do shell
2. comparacao com sessionStorage
3. toast de celebracao
4. confetti DOM

`shell-effects-loader.js`:

1. espera idle ou timeout curto
2. injeta `shell-effects.js`
3. falha silenciosamente se nao houver body/script

## Proxima sprint recomendada

Sprint 4: asset priority no page payload.

Antes de editar:

1. reler Sprints 0-3
2. mapear `build_page_assets`, `attach_page_payload`, `resolve_runtime_css_paths` e `base.html`
3. desenhar compatibilidade com `css` e `js` legados
