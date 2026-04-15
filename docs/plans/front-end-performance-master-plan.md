<!--
ARQUIVO: plano mestre de performance front-end do OctoBox.

TIPO DE DOCUMENTO:
- plano estrutural de performance, entrega visual e governanca de sprints

AUTORIDADE:
- alta para a frente de performance front-end

DOCUMENTO PAI:
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)

DOCUMENTOS IRMAOS:
- [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)
- [../experience/css-guide.md](../experience/css-guide.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- antes de qualquer sprint de performance front-end
- antes de alterar fonte critica, hero, CSS no head, shell JavaScript, busca global, efeitos visuais ou page assets
- quando uma otimizacao parecer simples demais e puder esconder divida tecnica

POR QUE ELE EXISTE:
- evita otimizacao por impulso.
- cria uma rota unica para reduzir LCP, INP, bytes iniciais e custo de pintura sem destruir a assinatura visual premium.
- obriga cada sprint a comecar por leitura real dos arquivos e pontos de conexao antes de editar codigo.
- preserva a coerencia entre performance, design system, page payload e experiencia percebida.

O QUE ESTE ARQUIVO FAZ:
1. declara o problema central de performance front-end.
2. define principios, riscos, dividas e nao-objetivos.
3. organiza a execucao em sprints.
4. define o ritual C.O.R.D.A. obrigatorio antes de cada sprint.
5. lista os arquivos e conexoes que precisam ser investigados por tema.
6. estabelece criterios de pronto e budgets contra regressao.

PONTOS CRITICOS:
- este plano nao substitui evidencia do runtime, testes, Lighthouse, traces ou leitura dos arquivos.
- este plano nao autoriza consolidar CSS antes de separar critico, page-level e enhancement.
- este plano nao autoriza remover identidade visual premium para ganhar performance artificial.
- se codigo real e este plano divergirem, o codigo vence e este plano deve ser atualizado.
-->

# Plano mestre de performance front-end

## Tese central

O OctoBox precisa carregar como produto premium de alta performance:

1. a primeira leitura precisa aparecer rapido
2. o hero nao pode pagar por fonte externa, CSS excessivo ou JavaScript que nao participa da primeira dobra
3. a shell precisa iniciar com o minimo essencial
4. busca, efeitos e interacoes ricas devem acordar por intencao do usuario ou por contrato explicito da pagina
5. a assinatura visual deve permanecer forte, mas nao pode bloquear o primeiro paint

Em linguagem simples:

1. primeiro acendemos a vitrine
2. depois abrimos as gavetas
3. depois ligamos os efeitos especiais

O erro que este plano evita e levar a loja inteira para a porta antes de deixar o cliente entrar.

## Regra de autoridade

Quando houver conflito, usar esta ordem:

1. runtime real, testes, traces e codigo atual
2. [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
3. [front-end-restructuring-guide.md](front-end-restructuring-guide.md)
4. [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)
5. [../experience/css-guide.md](../experience/css-guide.md)
6. este plano mestre
7. ideias, preferencias visuais e otimizacoes candidatas

Regra pratica:

1. se uma otimizacao melhora uma metrica mas quebra o contrato visual, ela nao esta pronta
2. se uma otimizacao deixa o codigo mais rapido mas menos localizavel, ela precisa de justificativa forte
3. se uma mudanca reduz bytes mas aumenta acoplamento, tratar como risco de divida tecnica

## Problema central

O front-end atual paga um imposto fixo alto antes da primeira leitura util.

Evidencias atuais conhecidas:

1. o shell base expande muitos CSS no head
2. paginas centrais somam dezenas de folhas CSS via manifestos
3. a fonte Inter externa ainda aparece no caminho critico do layout base
4. `dynamic-visuals.js`, `search.js` e `shell.js` entram globalmente
5. a busca da topbar existe como comportamento global mesmo quando o usuario nao vai buscar
6. efeitos atmosfericos podem competir com pintura, composicao e CPU inicial
7. alguns contratos visuais, como limite de linhas do hero, precisam ser garantidos pelo CSS real

Numeros de referencia medidos antes deste plano:

1. `shell_only`: 25 arquivos CSS resolvidos
2. `students`: 43 arquivos CSS resolvidos
3. `finance`: 47 arquivos CSS resolvidos
4. `class_grid`: 42 arquivos CSS resolvidos
5. `operations`: 50 arquivos CSS resolvidos
6. `dashboard`: 52 arquivos CSS resolvidos

Estes numeros nao significam automaticamente que cada arquivo e ruim.

Eles significam que a entrega inicial precisa ganhar prioridade, ordem e contrato.

## Objetivos

Objetivos principais:

1. reduzir LCP nas telas centrais, com prioridade inicial em alunos
2. reduzir CSS render-blocking no head
3. remover dependencia externa da fonte critica do heading principal
4. separar JavaScript essencial de interativo e cosmetico
5. carregar busca global apenas quando houver intencao
6. carregar efeitos visuais apenas quando a pagina declarar necessidade e quando o navegador estiver ocioso
7. deixar o contrato de assets mais explicito no `page payload`
8. criar budgets e testes para impedir regressao

Objetivos secundarios:

1. melhorar legibilidade de ownership do front
2. reduzir comportamento acoplado a classe visual
3. aumentar uso de `data-ui`, `data-slot`, `data-panel` e `data-action`
4. preservar a assinatura Luxo Futurista 2050 sem transformar visual em bloqueio de LCP

## Nao-objetivos

Este plano nao busca:

1. reescrever o front-end como SPA
2. remover Django templates
3. apagar o design premium do OctoBox
4. trocar todo CSS por utility-first
5. consolidar tudo em um unico arquivo CSS gigante
6. trocar medicao por opiniao
7. fazer micro-otimizacao antes de resolver caminho critico

## Principios de decisao

### 1. Medir antes de cortar

Toda sprint deve comecar com uma leitura de baseline.

Medir pelo menos:

1. arquivos CSS resolvidos
2. CSS critico no head
3. scripts globais carregados
4. fonte critica
5. LCP candidate esperado
6. tamanho aproximado de HTML e payloads de comportamento quando aplicavel

### 2. Primeiro caminho critico, depois acabamento

O caminho critico inclui:

1. HTML inicial
2. CSS necessario para shell, topbar, sidebar minima, layout e hero acima da dobra
3. fonte usada pelo heading LCP
4. JavaScript indispensavel para acessibilidade ou estado inicial

Todo o resto deve provar que precisa estar no carregamento inicial.

### 3. Visual premium progressivo

O OctoBox nao deve ficar pobre para ficar rapido.

Mas efeitos caros devem ser progressivos:

1. entram depois do primeiro paint
2. respeitam `prefers-reduced-motion`
3. dependem de declaracao explicita da pagina
4. nao bloqueiam leitura operacional

### 4. Backend entrega verdade, front organiza experiencia

O backend deve entregar:

1. dados reais
2. permissoes
3. estado
4. acoes possiveis
5. assets e behavior declarados

O frontend deve organizar:

1. hierarquia visual
2. repeticao de leitura
3. interacao progressiva
4. comportamento local

Anti-padrao:

1. JS deduzindo regra por texto ou classe visual
2. backend enviando duplicacao cosmetica do mesmo dado
3. template montando comportamento oculto sem contrato

### 5. CSS com casa certa

Regra de organizacao:

1. tokens globais moram em `tokens.css`
2. hero canonico mora no host compartilhado de hero
3. variantes recorrentes moram em camada oficial de variantes
4. pagina monta composicao local sem reinventar host
5. CSS local nao deve competir com `card`, `hero`, `notice-panel` ou `topbar`

## Dividas atuais a acompanhar

### Divida 1. CSS no head ainda e amplo demais

Sintoma:

1. manifestos expandem dezenas de CSS por pagina
2. o navegador precisa baixar e avaliar muita coisa antes da primeira pintura completa

Risco:

1. LCP alto
2. cascata dificil de depurar
3. incentivo a remendos locais para ganhar especificidade

Tratamento:

1. criar prioridade de asset
2. separar `critical`, `page` e `enhancement`
3. so consolidar depois de saber o que pertence a cada camada

### Divida 2. Fonte externa no caminho critico

Sintoma:

1. `base.html` carrega Google Fonts para Inter no head
2. o heading principal pode depender de resposta externa ou timing de fonte

Risco:

1. atraso de LCP
2. FOIT/FOUT mal controlado
3. dependencia externa desnecessaria para primeira dobra

Tratamento:

1. usar `--font-display-critical` com stack local para hero e headings LCP
2. opcionalmente self-host de fonte premium depois
3. remover ou adiar dependencia externa no caminho critico

### Divida 3. Shell JavaScript monolitico

Sintoma:

1. `shell.js` concentra varios comportamentos globais
2. parte do comportamento pode nao ser necessaria em toda pagina

Risco:

1. maior parse/execute inicial
2. listeners globais demais
3. maior custo de manutencao

Tratamento:

1. separar `shell-essential`
2. separar `shell-interactions`
3. separar `shell-effects`
4. carregar por necessidade declarada no payload

### Divida 4. Busca global sempre presente

Sintoma:

1. `search.js` e carregado globalmente
2. autocomplete e comportamento de busca entram mesmo sem intencao do usuario

Risco:

1. custo inicial desnecessario
2. risco de fetch antes da intencao
3. concorrencia com interacao inicial

Tratamento:

1. renderizar input visualmente
2. inicializar busca no primeiro `focus`, `pointerdown` ou atalho
3. usar import dinamico ou script diferido controlado
4. manter fallback server-side

### Divida 5. Efeitos atmosfericos no caminho inicial

Sintoma:

1. `dynamic-visuals.js` entra globalmente
2. efeitos premium podem competir com pintura inicial

Risco:

1. CPU inicial maior
2. composicao pesada
3. piora em maquinas fracas

Tratamento:

1. carregar por `data-atmosphere`
2. executar em idle
3. respeitar `prefers-reduced-motion`
4. garantir que ausencia do efeito nao quebra layout

### Divida 6. Contratos visuais incompletos

Sintoma:

1. atributos como `data-max-lines` declaram uma promessa visual
2. nem sempre o CSS garante a promessa de forma completa

Risco:

1. LCP instavel
2. quebra diferente por viewport
3. hero parecendo correto em uma tela e ruim em outra

Tratamento:

1. formalizar CSS do contrato no host canonico
2. documentar limite de linhas
3. testar viewports criticos
4. remover atributo quando nao for contrato real

### Divida 7. Falta de budgets automatizados

Sintoma:

1. performance depende de disciplina manual
2. um novo manifesto pode recolocar peso sem alarme

Risco:

1. regressao silenciosa
2. perda de confianca no front
3. custo alto para descobrir culpado depois

Tratamento:

1. testes de contagem de CSS critico
2. testes de scripts globais permitidos
3. teste contra fonte externa bloqueante
4. teste de contrato do hero

## Riscos de execucao

### Risco 1. Consolidar cedo demais

Consolidar CSS antes de classificar criticidade pode esconder o problema.

Mitigacao:

1. primeiro mapear
2. depois separar criticidade
3. por ultimo empacotar

### Risco 2. Perder assinatura visual

Remover efeitos sem criar camada progressiva pode deixar o produto generico.

Mitigacao:

1. preservar tokens e hosts canonicos
2. adiar efeitos, nao apagar a linguagem
3. comparar visual antes/depois

### Risco 3. Quebrar interacoes globais

Dividir `shell.js` pode quebrar topbar, sidebar, tema, perfil ou atalhos.

Mitigacao:

1. inventariar funcoes antes
2. separar por responsabilidade
3. manter smoke tests manuais e automatizados
4. trocar uma familia por vez

### Risco 4. Criar arquitetura excessiva

Separar demais pode virar mini-framework interno.

Mitigacao:

1. cada novo helper precisa remover repeticao real
2. contratos devem ser simples
3. leitura direta deve continuar possivel

### Risco 5. Lazy-load sem fallback

Busca ou efeitos carregados sob demanda podem falhar em rede ruim.

Mitigacao:

1. busca precisa ter submit server-side funcional
2. efeitos nao podem ser necessarios para operar
3. erros de import dinamico devem degradar em silencio seguro

## Ritual obrigatorio antes de cada sprint

Cada sprint desta frente deve comecar com C.O.R.D.A.

### C - Contexto

Responder:

1. qual problema da sprint estamos atacando
2. qual metrica ou risco justifica atacar agora
3. quais arquivos parecem envolvidos
4. quais docs mandam nesta decisao

### O - Objetivo

Responder:

1. qual resultado tecnico esperado
2. qual comportamento visual deve permanecer
3. qual budget ou teste deve proteger a mudanca
4. qual criterio define pronto

### R - Riscos

Responder:

1. o que pode quebrar
2. qual area pode sofrer regressao visual
3. qual contrato pode ficar mais acoplado
4. qual fallback precisa existir

### D - Direcao

Responder:

1. qual abordagem sera usada
2. quais alternativas foram rejeitadas e por que
3. qual parte sera deixada para outra sprint
4. qual trade-off estamos aceitando

### A - Acoes

Responder:

1. quais arquivos serao lidos primeiro
2. quais arquivos podem ser editados
3. quais testes serao rodados
4. como validar antes/depois

## Protocolo de busca minuciosa por sprint

Antes de editar qualquer arquivo, executar esta rotina mental e tecnica:

1. ler este plano mestre
2. ler o doc canonico mais especifico da area
3. localizar ownership pelo [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)
4. buscar arquivos por nome e por seletor
5. buscar imports, includes e uso de assets
6. buscar testes existentes relacionados
7. medir baseline local da area
8. escrever C.O.R.D.A. da sprint
9. so entao editar

Comandos uteis:

```powershell
rg "operation-hero|page_hero|data-max-lines" templates static catalog shared_support
rg "current_page_assets|css_runtime|build_page_assets|attach_page_payload" .
rg "dynamic-visuals|search.js|shell.js" templates static
rg "@import" static/css
```

## Sprints

## Sprint 0. Baseline e inventario

### Contexto

Antes de otimizar, precisamos saber exatamente o que cada tela paga no carregamento inicial.

### Objetivo

Criar uma fotografia confiavel de CSS, JS, fonte, payload e pontos de LCP esperados.

### Arquivos e conexoes para investigar

1. `templates/layouts/base.html`
2. `shared_support/static_assets.py`
3. `shared_support/page_payloads.py`
4. `access/context_processors.py`
5. `catalog/presentation/*`
6. `dashboard/*`
7. `operations/presentation.py`
8. `static/css/design-system.css`
9. `static/css/design-system/components.css`
10. `static/js/core/*.js`
11. testes de payload e catalogo

### Acoes

1. gerar tabela de CSS resolvido por pagina
2. listar scripts globais carregados por base
3. listar fontes externas no head
4. identificar candidatos de LCP por tela
5. registrar baseline no comentario da sprint ou em doc auxiliar se necessario

### Criterio de pronto

1. temos numeros antes/depois possiveis de comparar
2. sabemos quais telas sao mais caras
3. sabemos quais arquivos entram no caminho critico

## Sprint 1. Fonte critica e contrato do hero

### Contexto

O hero pode ser culpado pelo LCP mesmo quando o atraso vem de fonte, CSS ou layout.

### Objetivo

Fazer o heading critico renderizar sem depender de fonte externa e garantir que o contrato de linhas seja real.

### Arquivos e conexoes para investigar

1. `templates/layouts/base.html`
2. `templates/includes/ui/layout/page_hero.html`
3. `shared_support/page_payloads.py`
4. `catalog/presentation/student_directory_page.py`
5. `static/css/design-system/tokens.css`
6. `static/css/design-system/components/hero.css`
7. `static/css/design-system/operations/refinements/hero.css`
8. `static/css/catalog/students.css`
9. templates de dashboard, financeiro, grade e operations que usam hero

### Acoes

1. criar ou ajustar token de fonte critica
2. aplicar fonte critica ao hero canonico
3. remover dependencia da fonte externa para heading LCP
4. garantir `data-max-lines="2"` com CSS real ou remover atributo quando nao for verdadeiro
5. validar viewports mobile e desktop

### Criterio de pronto

1. hero carrega com fonte local/sistema no caminho critico
2. contrato de duas linhas e previsivel
3. outros heroes nao sofrem regressao visual
4. testes existentes passam

## Sprint 2. Topbar search sob demanda

### Contexto

Busca global e util, mas nao precisa cobrar custo antes da intencao do usuario.

### Objetivo

Renderizar a topbar normalmente, mas inicializar busca somente em foco, clique, pointer ou atalho.

### Arquivos e conexoes para investigar

1. `templates/includes/ui/layout/topbar/topbar_search.html`
2. `templates/layouts/base.html`
3. `static/js/core/search.js`
4. `static/js/core/shell.js`
5. `shared_support/shell_payloads.py`
6. `access/context_processors.py`
7. endpoints de busca/autocomplete
8. testes de shell e busca se existirem

### Acoes

1. inventariar responsabilidades atuais de `search.js`
2. separar boot leve de modulo completo se necessario
3. ativar busca no primeiro evento de intencao
4. manter submit server-side como fallback
5. impedir fetch antes da intencao

### Criterio de pronto

1. `search.js` completo nao executa no carregamento padrao
2. busca funciona apos foco/clique
3. fallback sem JS continua aceitavel
4. nenhum erro aparece quando topbar search nao existe para Coach

## Sprint 3. Shell JavaScript em camadas

### Contexto

O shell precisa existir em toda pagina, mas nem todo comportamento do shell e essencial para o primeiro paint.

### Objetivo

Separar JavaScript global em essencial, interativo e cosmetico.

### Arquivos e conexoes para investigar

1. `static/js/core/shell.js`
2. `static/js/core/dynamic-visuals.js`
3. `static/js/core/search.js`
4. `templates/layouts/base.html`
5. `templates/includes/ui/layout/shell_sidebar.html`
6. `templates/includes/ui/layout/topbar/*.html`
7. `shared_support/page_payloads.py`
8. `shared_support/shell_payloads.py`

### Acoes

1. mapear funcoes atuais de `shell.js`
2. classificar cada funcao como essencial, interativa ou cosmetica
3. criar arquivos menores apenas se a divisao reduzir custo e aumentar clareza
4. carregar interacoes por contrato ou defer
5. manter acessibilidade de sidebar, tema e perfil no essencial

### Criterio de pronto

1. tema, sidebar e perfil continuam funcionando imediatamente
2. comportamento nao essencial sai do caminho inicial
3. arquivos continuam legiveis sem mini-framework
4. smoke test manual da shell passa

## Sprint 4. Asset priority no page payload

### Contexto

Hoje `current_page_assets` lista CSS e JS, e `css_runtime` expande manifestos. Falta declarar prioridade.

### Objetivo

Evoluir o contrato de assets para separar critical, page, deferred e enhancement.

### Arquivos e conexoes para investigar

1. `shared_support/page_payloads.py`
2. `shared_support/static_assets.py`
3. `templates/layouts/base.html`
4. `catalog/presentation/shared.py`
5. `catalog/presentation/student_directory_page.py`
6. `catalog/presentation/finance_center_page.py`
7. `catalog/presentation/class_grid_page.py`
8. `dashboard/dashboard_views.py`
9. `operations/presentation.py`
10. testes de page payload

### Acoes

1. desenhar shape simples de assets priorizados
2. manter compatibilidade com `css` e `js` legados
3. renderizar critical no head
4. renderizar deferred/enhancement sem bloquear
5. ajustar testes de payload

### Criterio de pronto

1. assets antigos continuam funcionando
2. novas paginas podem declarar prioridade
3. `base.html` nao precisa conhecer detalhe de cada pagina
4. testes cobrem o contrato

## Sprint 5. CSS critico por tela

### Contexto

Depois de existir prioridade de assets, podemos separar o CSS por criticidade sem perder ownership.

### Objetivo

Reduzir CSS bloqueante nas telas centrais, comecando por alunos e financeiro.

### Arquivos e conexoes para investigar

1. `static/css/design-system.css`
2. `static/css/design-system/components.css`
3. `static/css/design-system/tokens.css`
4. `static/css/design-system/shell.css`
5. `static/css/design-system/topbar.css`
6. `static/css/design-system/sidebar/*`
7. `static/css/design-system/components/hero.css`
8. `static/css/catalog/shared.css`
9. `static/css/catalog/students.css`
10. `static/css/catalog/finance/*`
11. templates das telas alvo

### Acoes

1. identificar CSS necessario acima da dobra
2. criar camada critica minima sem duplicar tema
3. mover acabamento para enhancement quando seguro
4. validar responsividade
5. medir reducao de CSS bloqueante

### Criterio de pronto

1. alunos tem CSS critico menor
2. financeiro segue o mesmo padrao ou tem plano pronto
3. visual principal nao perde identidade
4. cascata continua rastreavel

## Sprint 6. Efeitos visuais sob demanda

### Contexto

Efeitos premium sao parte da marca, mas nao devem competir com a primeira leitura.

### Objetivo

Carregar e executar atmosfera premium apenas quando a pagina declarar necessidade e o navegador estiver pronto.

### Arquivos e conexoes para investigar

1. `static/js/core/dynamic-visuals.js`
2. `templates/layouts/base.html`
3. templates com efeitos especiais
4. CSS com glow, blur, mascaras, animacoes e layers atmosfericas
5. `shared_support/page_payloads.py`
6. presenters que declaram behavior/assets

### Acoes

1. criar flag de comportamento para atmosfera premium
2. carregar efeitos com idle ou defer seguro
3. respeitar `prefers-reduced-motion`
4. garantir fallback visual estatico
5. medir impacto de CPU inicial

### Criterio de pronto

1. efeitos nao rodam globalmente no carregamento padrao
2. paginas premium continuam com assinatura visual
3. usuarios com reducao de movimento nao recebem animacao pesada

## Sprint 7. Budgets e testes anti-regressao

### Contexto

Sem budget, toda melhoria pode ser perdida por uma mudanca futura inocente.

### Objetivo

Criar guardrails automatizados para performance front-end.

### Arquivos e conexoes para investigar

1. testes existentes de page payload
2. testes de catalogo
3. `shared_support/static_assets.py`
4. `templates/layouts/base.html`
5. manifests CSS
6. configuracao de CI se aplicavel

### Acoes

1. testar limite de CSS critico por tela
2. testar ausencia de fonte externa bloqueante no caminho critico
3. testar scripts globais permitidos
4. testar contrato do hero
5. documentar como atualizar budget com justificativa

### Criterio de pronto

1. CI falha quando alguem recoloca peso critico sem atualizar contrato
2. budgets sao compreensiveis
3. testes nao sao frageis por detalhe cosmetico

## Sprint 8. Consolidacao controlada

### Contexto

Somente depois de separar criticidade faz sentido consolidar ou gerar bundles.

### Objetivo

Reduzir fragmentacao operacional sem esconder ownership.

### Arquivos e conexoes para investigar

1. `shared_support/static_assets.py`
2. todos os manifestos CSS principais
3. `static/css/design-system.css`
4. `static/css/design-system/components.css`
5. `static/css/catalog/*`
6. pipeline de static/collectstatic
7. testes de drift de assets

### Acoes

1. decidir quais bundles fazem sentido
2. manter fonte de verdade modular
3. evitar arquivo gigante opaco
4. garantir cache/versionamento
5. medir antes/depois

### Criterio de pronto

1. menos requests ou menos bloqueio sem perder mapa mental
2. ownership continua nos arquivos modulares
3. build ou runtime nao fica fragil

## Budgets iniciais propostos

Estes budgets sao metas iniciais, nao verdades eternas.

Eles devem ser ajustados com evidencia.

1. fonte externa bloqueante para heading LCP: 0
2. fetch de autocomplete antes de intencao: 0
3. execucao de efeitos atmosfericos antes de idle: 0
4. scripts globais essenciais no carregamento: no maximo shell essencial
5. CSS critico de alunos: reduzir progressivamente ate ficar abaixo de 20 arquivos resolvidos ou equivalente empacotado
6. CSS critico de dashboard: reduzir progressivamente depois de alunos e financeiro
7. contrato `data-max-lines`: atributo so existe quando o CSS garante o comportamento

## Checklist de revisao antes de commit

Antes de fechar qualquer sprint:

1. rodar testes relevantes
2. comparar baseline antes/depois
3. validar que nao houve regressao visual obvia
4. confirmar que JS novo usa `data-*` quando busca elementos
5. confirmar que CSS novo tem casa certa
6. confirmar que page payload nao ganhou duplicacao cosmetica
7. confirmar que fallback existe para lazy-load
8. registrar trade-off se alguma meta nao foi atingida

## Como explicar a direcao para o time

Versao tecnica:

1. vamos reduzir critical path, separar assets por prioridade e transformar interacoes globais em ilhas progressivas
2. o backend declara o contrato de tela, o template renderiza a estrutura e o JS ativa comportamento por necessidade
3. a estetica premium continua, mas deixa de bloquear LCP

Versao simples:

1. primeiro fazemos a pagina aparecer
2. depois fazemos ela interagir
3. depois colocamos os fogos de artificio

Se tentarmos soltar os fogos antes da porta abrir, a crianca fica olhando a rua e acha que a loja esta lenta.

## Estado inicial deste plano

Status:

1. plano criado antes da execucao das sprints
2. Sprint 0 executada como baseline e inventario em [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
3. Sprint 1 executada para fonte critica e contrato do hero em [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
4. Sprint 2 executada para busca da topbar sob demanda em [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
5. Sprint 3 executada para camadas do shell em [front-end-performance-sprint-3-shell-layers-corda.md](front-end-performance-sprint-3-shell-layers-corda.md)
6. Sprint 4 executada para prioridade de assets no page payload em [front-end-performance-sprint-4-asset-priority-corda.md](front-end-performance-sprint-4-asset-priority-corda.md)
7. Sprint 5 iniciada por alunos e executada para reduzir CSS bloqueante da tela em [front-end-performance-sprint-5-students-critical-css-corda.md](front-end-performance-sprint-5-students-critical-css-corda.md)
8. Sprint 6 executada para `dynamic-visuals.js` sob demanda em [front-end-performance-sprint-6-dynamic-visuals-corda.md](front-end-performance-sprint-6-dynamic-visuals-corda.md)
9. Sprint 7 executada para budgets anti-regressao em [front-end-performance-sprint-7-budgets-corda.md](front-end-performance-sprint-7-budgets-corda.md)
10. Sprint 8 executada para consolidacao controlada de CSS progressivo em [front-end-performance-sprint-8-controlled-consolidation-corda.md](front-end-performance-sprint-8-controlled-consolidation-corda.md)
11. nenhuma sprint de correcao deve ser considerada concluida ate passar pelo ritual C.O.R.D.A. proprio

Proxima acao recomendada:

1. escolher a proxima frente: financeiro, validacao visual real ou Lighthouse/trace
2. reler [front-end-performance-sprint-0-baseline-corda.md](front-end-performance-sprint-0-baseline-corda.md)
3. reler [front-end-performance-sprint-1-font-hero-corda.md](front-end-performance-sprint-1-font-hero-corda.md)
4. reler [front-end-performance-sprint-2-topbar-search-corda.md](front-end-performance-sprint-2-topbar-search-corda.md)
5. reler [front-end-performance-sprint-3-shell-layers-corda.md](front-end-performance-sprint-3-shell-layers-corda.md)
6. reler [front-end-performance-sprint-4-asset-priority-corda.md](front-end-performance-sprint-4-asset-priority-corda.md)
7. reler [front-end-performance-sprint-5-students-critical-css-corda.md](front-end-performance-sprint-5-students-critical-css-corda.md)
8. reler [front-end-performance-sprint-6-dynamic-visuals-corda.md](front-end-performance-sprint-6-dynamic-visuals-corda.md)
9. reler [front-end-performance-sprint-7-budgets-corda.md](front-end-performance-sprint-7-budgets-corda.md)
10. reler [front-end-performance-sprint-8-controlled-consolidation-corda.md](front-end-performance-sprint-8-controlled-consolidation-corda.md)
11. nao ampliar `bundle:` para CSS critico sem nova medicao e budget proprio
