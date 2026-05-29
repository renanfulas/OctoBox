<!--
ARQUIVO: C.O.R.D.A. da Sprint 0 do plano mestre de performance front-end.

TIPO DE DOCUMENTO:
- registro de sprint, baseline e inventario tecnico

AUTORIDADE:
- alta para a execucao da Sprint 0 da frente de performance front-end

DOCUMENTO PAI:
- [front-end-performance-master-plan.md](front-end-performance-master-plan.md)

DOCUMENTOS IRMAOS:
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)
- [catalog-page-payload-presenter-blueprint.md](catalog-page-payload-presenter-blueprint.md)
- [../reference/front-end-ownership-map.md](../reference/front-end-ownership-map.md)
- [../experience/css-guide.md](../experience/css-guide.md)

QUANDO USAR:
- antes de iniciar a Sprint 1
- quando for comparar melhorias de LCP, CSS no head, scripts globais ou fonte critica
- quando for justificar por que a primeira correcao deve atacar fonte/hero antes de consolidacao ampla de CSS

POR QUE ELE EXISTE:
- transforma a Sprint 0 em evidencia, nao opiniao.
- registra o estado inicial do caminho critico de front-end antes de otimizacoes.
- cria a base de comparacao para as proximas sprints.

O QUE ESTE ARQUIVO FAZ:
1. registra o C.O.R.D.A. da Sprint 0.
2. lista os arquivos investigados e pontos de conexao.
3. documenta os numeros iniciais de CSS e JS.
4. identifica riscos e dividas descobertas.
5. define a recomendacao para a Sprint 1.

PONTOS CRITICOS:
- os numeros deste arquivo sao baseline local de desenvolvimento e devem ser tratados como direcao tecnica, nao como medicao final de campo.
- Lighthouse, WebPageTest ou trace real de navegador ainda devem complementar este inventario quando houver ambiente estavel.
- este arquivo nao autoriza edicoes de runtime por si so; ele prepara a Sprint 1.
-->

# Sprint 0: baseline e inventario C.O.R.D.A.

Data de referencia: 2026-04-15.

## C - Contexto

A frente de performance front-end comecou pelo plano mestre em [front-end-performance-master-plan.md](front-end-performance-master-plan.md).

A Sprint 0 nao corrige runtime.

Ela cria o raio-x inicial para que as proximas sprints nao virem otimizacao por impulso.

O problema observado:

1. a shell carrega uma base ampla de CSS em toda pagina autenticada
2. paginas centrais somam CSS adicional via manifestos expandidos
3. a fonte Inter externa ainda esta no head do layout base
4. `dynamic-visuals.js`, `search.js` e `shell.js` entram globalmente
5. a busca da topbar existe no contrato global antes de qualquer intencao do usuario
6. o hero canonico e candidato natural de LCP nas telas de operacao, especialmente alunos

Metafora simples:

1. antes a pagina parecia uma loja tentando abrir a porta carregando vitrine, estoque, caixa de som e fogos juntos
2. esta sprint mede o peso de cada coisa antes de decidir o que sai primeiro

## O - Objetivo

Objetivo desta sprint:

1. medir CSS inicial por tela central
2. medir scripts globais e scripts locais relevantes
3. localizar fonte externa critica
4. mapear arquivos de ownership para as proximas sprints
5. registrar riscos e dividas tecnicas
6. recomendar a primeira sprint de correcao com menor risco e maior impacto percebido

Criterios de pronto:

1. baseline de CSS registrado
2. baseline de JS registrado
3. arquivos de conexao registrados
4. riscos documentados
5. proxima sprint recomendada

## R - Riscos

Riscos identificados:

1. consolidar CSS agora pode esconder o problema em um bundle opaco
2. remover efeitos visuais sem camada progressiva pode empobrecer a assinatura Luxo Futurista 2050
3. dividir `shell.js` sem inventario pode quebrar sidebar, tema, profile menu, atalhos ou acessibilidade
4. lazy-load da busca sem fallback pode quebrar busca server-side ou experiencia de teclado
5. mexer no hero apenas em `students.css` criaria excecao local e enfraqueceria o host canonico
6. deixar `data-max-lines` sem contrato real aumenta instabilidade visual entre viewports

Risco extra encontrado durante leitura:

1. [../experience/css-guide.md](../experience/css-guide.md) contem marcadores de conflito Git em uma secao do mapa CSS
2. isso nao bloqueia a Sprint 1, mas e uma divida documental que pode confundir futuras decisoes de ownership

## D - Direcao

Direcao recomendada:

1. executar Sprint 1 antes de qualquer consolidacao de CSS
2. atacar fonte critica e contrato do hero primeiro
3. manter a correcao no host canonico do hero e nos tokens, nao em remendo local
4. depois atacar busca global e shell JS
5. deixar consolidacao CSS para depois da separacao entre critical, page e enhancement

Alternativas rejeitadas nesta sprint:

1. consolidar todos os CSS agora: rejeitado porque reduz contagem visivel, mas nao separa criticidade
2. apagar efeitos premium: rejeitado porque melhora metrica de forma pobre e prejudica identidade
3. reescrever shell inteiro: rejeitado porque e amplo demais para primeiro passo seguro
4. trocar toda tipografia do sistema: rejeitado porque a dor inicial esta no heading critico e no caminho de LCP

## A - Acoes executadas

Arquivos e docs lidos:

1. `docs/plans/front-end-performance-master-plan.md`
2. `docs/reference/front-end-ownership-map.md`
3. `docs/experience/css-guide.md`
4. `.agents/skills/performance_architect/SKILL.md`
5. `.agents/skills/css_front_end_architect/SKILL.md`
6. `templates/layouts/base.html`
7. `access/context_processors.py`
8. `shared_support/page_payloads.py`
9. `shared_support/static_assets.py`
10. `shared_support/shell_payloads.py`
11. `catalog/presentation/student_directory_page.py`
12. `catalog/presentation/finance_center_page.py`
13. `dashboard/presentation.py`
14. `static/css/design-system.css`

Busca executada:

1. `rg` foi tentado primeiro, mas o ambiente retornou `Access is denied`
2. a busca foi feita com `Get-ChildItem` e `Select-String`
3. foram pesquisados `fonts.googleapis`, `fonts.gstatic`, `current_page_assets`, `dynamic-visuals`, `search.js`, `shell.js`, `build_page_assets`, `attach_page_payload`, `operation-hero`, `page_hero`, `data-max-lines` e eventos JavaScript relevantes

## Baseline de CSS no head

Medicao feita usando `resolve_runtime_css_paths(...)`, incluindo:

1. shell core resolvido a partir de `css/design-system.css`
2. `css/design-system/components/topbar_profile_menu.css`, que e carregado diretamente no `base.html`
3. assets de pagina conhecidos por presenter

| Tela | Links CSS no head | CSS shell | CSS de pagina | Peso aproximado |
|---|---:|---:|---:|---:|
| `shell_only` | 26 | 25 | 0 | 210.1KB |
| `students` | 44 | 25 | 18 | 319.0KB |
| `finance` | 48 | 25 | 22 | 411.7KB |
| `class_grid` | 43 | 25 | 17 | 303.3KB |
| `operations` | 51 | 25 | 25 | 402.4KB |
| `dashboard` | 53 | 25 | 27 | 429.7KB |

Leitura:

1. `dashboard` e a tela mais pesada em CSS inicial entre as medidas
2. `finance` e a segunda mais pesada
3. `students` nao e a maior em CSS, mas ainda paga 44 links e 319.0KB no head
4. todas as telas autenticadas ja comecam com 26 links CSS por causa da shell e do profile menu

## Maiores arquivos CSS encontrados

Top arquivos CSS por tamanho:

| Arquivo | Peso aproximado |
|---|---:|
| `static/css/catalog/finance/_boards.css` | 72.0KB |
| `static/css/catalog/shared/student-financial.css` | 54.2KB |
| `static/css/catalog/shared/student-page-shell.css` | 52.9KB |
| `static/css/onboarding/intakes.css` | 38.8KB |
| `static/css/design-system/topbar.css` | 32.6KB |
| `static/css/catalog/student_form_stepper.css` | 31.6KB |
| `static/css/design-system/components/cards.css` | 27.0KB |
| `static/css/catalog/students/quick-panel.css` | 25.7KB |
| `static/css/design-system/operations/reception/command.css` | 22.2KB |
| `static/css/design-system/dashboard.css` | 21.7KB |
| `static/css/design-system/components/dashboard/side.css` | 21.5KB |
| `static/css/design-system/operations/reception/payment.css` | 19.8KB |
| `static/css/catalog/class-grid/calendar.css` | 18.4KB |
| `static/css/access/overview.css` | 17.5KB |
| `static/css/design-system/operations/dev-coach/coach.css` | 17.3KB |

Leitura:

1. alguns arquivos grandes sao locais e aceitaveis quando entram apenas na pagina certa
2. o risco maior e quando CSS de dashboard, operations ou componentes pesados entram pela shell global
3. `topbar.css` e parte do caminho de toda pagina autenticada e merece revisao futura cuidadosa

## Baseline de JavaScript

Scripts globais carregados por `templates/layouts/base.html`:

| Script global | Peso aproximado | Observacao |
|---|---:|---|
| `static/js/core/dynamic-visuals.js` | 1.5KB | efeito visual global antes de saber se a pagina precisa |
| `static/js/core/search.js` | 6.2KB | busca global carregada antes da intencao |
| `static/js/core/shell.js` | 14.6KB | comportamento amplo da shell |
| Total global | 22.2KB | executado em toda pagina autenticada |

Scripts locais relevantes:

| Tela | Script | Peso aproximado |
|---|---|---:|
| `students` | `static/js/pages/students/student-directory.js` | 101.6KB |
| `class_grid` | `static/js/pages/class-grid/class-grid.js` | 13.3KB |
| `dashboard` | `static/js/pages/dashboard/dashboard-layout-controller.js` | 16.1KB |
| `dashboard` | `static/js/pages/dashboard/dashboard.js` | 1.4KB |
| `operations_owner` | `static/js/pages/operations/owner-workspace.js` | 3.5KB |
| `operations_manager` | `static/js/pages/operations/manager-boards.js` | 13.2KB |

Top arquivos JS por tamanho:

| Arquivo | Peso aproximado |
|---|---:|
| `static/js/pages/students/student-directory.js` | 101.6KB |
| `static/js/pages/finance/student-financial-workspace.js` | 18.1KB |
| `static/js/pages/students/student-form.js` | 17.6KB |
| `static/js/pages/dashboard/dashboard-layout-controller.js` | 16.1KB |
| `static/js/pages/onboarding/intake-center.js` | 15.1KB |
| `static/js/core/shell.js` | 14.6KB |
| `static/js/pages/class-grid/class-grid.js` | 13.3KB |
| `static/js/pages/operations/manager-boards.js` | 13.2KB |
| `static/js/pages/operations/reception-payment-card.js` | 10.3KB |
| `static/js/catalog/student_form_lock.js` | 8.2KB |
| `static/js/pages/finance/finance-priority-carousel.js` | 7.8KB |
| `static/js/pages/students/student-form-stepper.js` | 7.2KB |
| `static/js/core/forms.js` | 6.9KB |
| `static/js/core/search.js` | 6.2KB |
| `static/js/pages/finance/billing_console.js` | 5.9KB |

Leitura:

1. o custo global de JS nao e enorme em bytes, mas e global e executa antes de intencao
2. `students` tem um script local grande, mas a Sprint 1 ainda deve focar fonte/hero por ser o caminho mais seguro para LCP
3. `search.js` e candidato perfeito para lazy-load por intencao na Sprint 2
4. `shell.js` deve ser dividido com cuidado na Sprint 3

## Fonte critica

`templates/layouts/base.html` carrega no head:

1. `https://fonts.googleapis.com`
2. `https://fonts.gstatic.com`
3. `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap`

Leitura:

1. isso cria dependencia externa no caminho inicial
2. mesmo com `display=swap`, a folha da fonte ainda participa do head
3. o heading do hero deve ter uma fonte critica local/sistema na Sprint 1

## Hero e candidato de LCP

Arquivos de contrato:

1. `shared_support/page_payloads.py`
2. `templates/includes/ui/layout/page_hero.html`
3. `static/css/design-system/components/hero.css`
4. `static/css/design-system/operations/refinements/hero.css`

Alunos:

1. `catalog/presentation/student_directory_page.py` monta o hero com `heading_level='h1'`
2. o titulo atual e `O que pede cuidado na sua base hoje.`
3. o hero usa classe variante `student-hero`

Leitura:

1. o `h1` do hero e candidato natural de LCP porque aparece acima da dobra e tem grande area visual
2. o LCP atribuido ao hero pode ser causado por fonte, CSS, layout ou JS anterior, nao necessariamente pelo texto em si
3. a Sprint 1 deve corrigir fonte critica e contrato de linhas no host canonico

## Contrato de assets atual

Arquivos de contrato:

1. `shared_support/page_payloads.py`
2. `catalog/presentation/shared.py`
3. `shared_support/static_assets.py`
4. `templates/layouts/base.html`

Comportamento atual:

1. `build_page_assets(css=[...], js=[...])` recebe listas simples
2. `attach_page_payload(...)` adiciona `current_page_assets`
3. `resolve_runtime_css_paths(...)` expande `@import` para `css_runtime`
4. `base.html` renderiza todo `css_runtime` no head

Leitura:

1. o contrato atual sabe quais assets a pagina precisa
2. ele ainda nao sabe prioridade de asset
3. a Sprint 4 deve evoluir o shape para `critical`, `page`, `deferred` e `enhancement`, mantendo compatibilidade

## Pontos de conexao por sprint futura

Sprint 1:

1. `templates/layouts/base.html`
2. `templates/includes/ui/layout/page_hero.html`
3. `shared_support/page_payloads.py`
4. `catalog/presentation/student_directory_page.py`
5. `static/css/design-system/tokens.css`
6. `static/css/design-system/components/hero.css`
7. `static/css/design-system/operations/refinements/hero.css`

Sprint 2:

1. `templates/includes/ui/layout/topbar/topbar_search.html`
2. `templates/layouts/base.html`
3. `static/js/core/search.js`
4. `static/js/core/shell.js`
5. `shared_support/shell_payloads.py`
6. `access/context_processors.py`

Sprint 3:

1. `static/js/core/shell.js`
2. `static/js/core/dynamic-visuals.js`
3. `templates/layouts/base.html`
4. `templates/includes/ui/layout/topbar/*.html`
5. `templates/includes/ui/layout/shell_sidebar.html`

Sprint 4:

1. `shared_support/page_payloads.py`
2. `shared_support/static_assets.py`
3. `templates/layouts/base.html`
4. presenters de catalogo, dashboard e operations
5. testes de page payload

## Recomendacao para a Sprint 1

Executar a Sprint 1 com foco estreito:

1. remover a dependencia da fonte externa para o heading critico
2. criar ou confirmar token `--font-display-critical`
3. aplicar o token no hero canonico
4. garantir que `data-max-lines` realmente tenha suporte visual ou remover a promessa quando nao for contrato real
5. nao mexer ainda em consolidacao ampla de CSS

Motivo:

1. e o menor corte com maior chance de melhorar LCP percebido em alunos
2. reduz dependencia externa
3. melhora previsibilidade visual
4. prepara o terreno para Sprint 2 e Sprint 3

## Comandos de referencia

Medir CSS resolvido:

```powershell
@'
from django.conf import settings
from shared_support.static_assets import resolve_runtime_css_paths
static_root = settings.BASE_DIR / 'static'
pages = {
    'students': ['css/design-system.css','css/design-system/catalog-operation-contract.css','css/catalog/shared.css','css/catalog/students.css'],
    'finance': ['css/design-system.css','css/design-system/catalog-operation-contract.css','css/catalog/shared.css','css/catalog/finance.css','css/design-system/financial.css'],
}
for name, assets in pages.items():
    resolved = resolve_runtime_css_paths(assets)
    total = sum((static_root / path).stat().st_size for path in resolved if (static_root / path).exists())
    print(name, len(resolved), round(total / 1024, 1))
'@ | .\.venv\Scripts\python.exe manage.py shell -c "import sys; exec(sys.stdin.read())"
```

Buscar pontos de conexao quando `rg` estiver disponivel:

```powershell
rg "operation-hero|page_hero|data-max-lines" templates static catalog shared_support
rg "current_page_assets|css_runtime|build_page_assets|attach_page_payload" .
rg "dynamic-visuals|search.js|shell.js" templates static
```

Fallback quando `rg` falhar:

```powershell
Get-ChildItem -Path templates,static,shared_support,access,catalog,dashboard,operations -Recurse -File |
  Select-String -Pattern 'operation-hero','page_hero','data-max-lines','current_page_assets','dynamic-visuals','search.js','shell.js'
```
