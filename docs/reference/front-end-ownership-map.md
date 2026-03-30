<!--
ARQUIVO: mapa curto de ownership do front-end.

POR QUE ELE EXISTE:
- reduz busca cega quando precisarmos localizar elementos, ownership e pontos de mudanca.
- serve como entrada rapida para manutencao, refatoracao e automacao futura.

O QUE ESTE ARQUIVO FAZ:
1. aponta onde mora o shell global.
2. aponta onde mora o contrato de page payload.
3. aponta onde moram as paginas principais do produto.
4. registra a convencao de hooks estruturais do DOM.

PONTOS CRITICOS:
- este mapa precisa continuar curto, operacional e atualizado.
- ele nao substitui o guia estrutural; ele acelera a navegacao real pelo codigo.
-->

# Mapa curto de ownership do front-end

## Para onde olhar primeiro

Se a duvida for sobre estrutura, comece por esta ordem:

1. shell global
2. payload da tela
3. template principal da pagina
4. includes da pagina
5. CSS da area
6. JS da area

## Shell global

Casca autenticada principal:

1. [../../templates/layouts/base.html](../../templates/layouts/base.html)

Comportamento universal do shell:

1. [../../static/js/core/shell.js](../../static/js/core/shell.js)
2. [../../static/js/core/search.js](../../static/js/core/search.js)
3. [../../static/js/core/forms.js](../../static/js/core/forms.js)

CSS estrutural do shell:

1. [../../static/css/design-system/tokens.css](../../static/css/design-system/tokens.css)
2. [../../static/css/design-system/shell.css](../../static/css/design-system/shell.css)
3. [../../static/css/design-system/sidebar/sidebar.css](../../static/css/design-system/sidebar/sidebar.css)
4. [../../static/css/design-system/topbar.css](../../static/css/design-system/topbar.css)
5. [../../static/css/design-system/compass.css](../../static/css/design-system/compass.css)
6. [../../static/css/design-system/spacing.css](../../static/css/design-system/spacing.css)
7. [../../static/css/design-system/responsiveness.css](../../static/css/design-system/responsiveness.css)

Contrato rapido do design system:

1. [design-system-contract.md](design-system-contract.md)

## Contrato de tela

Heuristica curta do contrato semantico enxuto:

1. backend entrega o minimo semantico necessario: dado real, permissao, estado, contexto e acao possivel
2. frontend organiza hierarquia, composicao, repeticao visual e experiencia
3. se o mesmo valor vai aparecer em varios cards, o contrato deve continuar semantico e unico
4. se a mudanca for apenas cosmetica ou distributiva, desconfie de qualquer novo peso no payload

Helper generico do page payload:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py)

Bridge do catalogo:

1. [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py)

Guia estrutural oficial:

1. [../plans/front-end-restructuring-guide.md](../plans/front-end-restructuring-guide.md)
2. [functional-circuits-matrix.md](functional-circuits-matrix.md)

## Paginas principais e ownership

## Regra por funcionalidade

Cada funcionalidade relevante do produto deve conseguir ser localizada por um trilho curto e previsivel.

Estrutura esperada por funcionalidade:

1. entrada HTTP em `views` do dominio
2. montagem semantica em `presentation` ou builder equivalente
3. regra e mutacao em `services`, `workflows` ou `actions`
4. template principal da funcionalidade
5. includes locais da funcionalidade
6. CSS local da funcionalidade
7. JS local da funcionalidade, quando houver comportamento proprio
8. testes do contrato funcional e da comunicacao compartilhada

Regra pratica:

1. a funcionalidade deve ter dono local claro
2. a comunicacao com o resto do produto deve subir por contrato compartilhado, nao por improviso em template
3. quando uma funcionalidade mudar, o impacto no shell, nos atalhos e na leitura cruzada deve ser revisado no mesmo pacote

Matriz operacional desta regra:

1. [functional-circuits-matrix.md](functional-circuits-matrix.md)

## Comunicacao transversal

No estado atual do OctoBox, a comunicacao entre funcionalidades e outras paginas passa principalmente por estes pontos:

1. [../../shared_support/page_payloads.py](../../shared_support/page_payloads.py) para contexto, shell, behavior e assets da tela
2. [../../access/context_processors.py](../../access/context_processors.py) para shell global, topbar, alertas e contexto da navegacao
3. [../../access/shell_actions.py](../../access/shell_actions.py) para prioridade, pendente e proxima acao entre paginas

Regra de alteracao:

1. se a mudanca altera leitura global, revisar `context_processors`
2. se a mudanca altera atalhos ou foco operacional, revisar `shell_actions`
3. se a mudanca altera hero, assets, behavior ou payload da tela, revisar `page_payloads`
4. se a mudanca for so local de layout, manter dentro da propria funcionalidade

## Checklist ao alterar uma funcionalidade

Antes de fechar uma alteracao funcional, revisar nesta ordem:

1. a view continua curta e a funcionalidade segue com ownership local claro
2. o payload da tela continua semantico e sem duplicacao cosmetica
3. o shell global ainda comunica prioridade, pendencia e proxima acao da forma certa
4. os alertas, atalhos ou links cruzados em outras paginas continuam coerentes
5. os testes de contrato da funcionalidade e da comunicacao compartilhada continuam verdes

Dashboard:

1. template principal: [../../templates/dashboard/index.html](../../templates/dashboard/index.html)
2. view e payload: [../../dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)
3. leitura base: [../../dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
4. CSS: [../../static/css/design-system/dashboard.css](../../static/css/design-system/dashboard.css)

Alunos:

1. listagem principal: [../../templates/catalog/students.html](../../templates/catalog/students.html)
2. ficha leve: [../../templates/catalog/student-form.html](../../templates/catalog/student-form.html)
3. views: [../../catalog/views/student_views.py](../../catalog/views/student_views.py)
4. presenters: [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py) e [../../catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)
5. CSS: [../../static/css/catalog/students.css](../../static/css/catalog/students.css)
6. JS da ficha: [../../static/js/pages/students/student-form.js](../../static/js/pages/students/student-form.js)
7. stepper da ficha: [../../static/js/pages/students/student-form-stepper.js](../../static/js/pages/students/student-form-stepper.js)

Financeiro:

1. central financeira: [../../templates/catalog/finance.html](../../templates/catalog/finance.html)
2. edicao de plano: [../../templates/catalog/finance-plan-form.html](../../templates/catalog/finance-plan-form.html)
3. views: [../../catalog/views/finance_views.py](../../catalog/views/finance_views.py)
4. presenter: [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
5. CSS: [../../static/css/catalog/finance/](../../static/css/catalog/finance/)

Grade de aulas:

1. template principal: [../../templates/catalog/class-grid.html](../../templates/catalog/class-grid.html)
2. view: [../../catalog/views/class_grid_views.py](../../catalog/views/class_grid_views.py)
3. presenter: [../../catalog/presentation/class_grid_page.py](../../catalog/presentation/class_grid_page.py)
4. CSS: [../../static/css/catalog/class-grid.css](../../static/css/catalog/class-grid.css)
5. JS: [../../static/js/pages/class-grid/class-grid.js](../../static/js/pages/class-grid/class-grid.js)

Operacao por papel:

1. views: [../../operations/workspace_views.py](../../operations/workspace_views.py)
2. payload: [../../operations/presentation.py](../../operations/presentation.py)
3. templates: [../../templates/operations](../../templates/operations)
4. CSS base visual: [../../static/css/design-system/operations.css](../../static/css/design-system/operations.css)

## Convencao de hooks estruturais

Use esta hierarquia:

1. classe para estilo
2. id para ancora, relacionamento ou acessibilidade
3. `data-*` para descoberta estavel de comportamento, automacao e manutencao

Hooks preferenciais:

1. `data-page` para identificar a tela
2. `data-slot` para identificar regioes estruturais da tela
3. `data-panel` para paineis e blocos operacionais relevantes
4. `data-ui` para elementos universais do shell e gatilhos de comportamento
5. `data-action` para botoes e links com papel de interacao claro

Regra de ouro:

1. JS novo deve preferir `data-ui` ou hook estrutural equivalente antes de cair em classe visual
2. testes e automacoes nao devem depender da cosmetica da interface
3. toda tela mexida deve sair com mais hooks estaveis do que entrou

## Heuristica rapida de manutencao

Se precisar mudar algo, pergunte nesta ordem:

1. isso e shell global ou tela local?
2. isso e contrato de payload ou composicao visual?
3. isso e include local ou componente compartilhado real?
4. isso e comportamento de JS ou so leitura de DOM?
5. o elemento ja tem hook estrutural ou ainda depende de classe visual?
