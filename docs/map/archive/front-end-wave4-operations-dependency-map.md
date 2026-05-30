<!--
ARQUIVO: mapa do acoplamento entre telas do catalogo e `operations.css`.

POR QUE ELE EXISTE:
- documenta quais superficies do catalogo realmente dependem do manifesto operacional completo.
- separa dependencia estrutural legitima de carga excessiva.
- orienta a reducao segura do acoplamento sem apagar o chao visual da pagina.

O QUE ESTE ARQUIVO FAZ:
1. lista as telas do catalogo auditadas nesta trilha.
2. classifica cada uma como `full`, `contract-only` ou `pending`.
3. registra o primeiro corte seguro aplicado.
4. registra que o default do catalogo agora aponta para o contrato minimo.

PONTOS CRITICOS:
- `design-system.css` ja carrega a base geral do sistema.
- o problema aqui nao e remover toda heranca operacional; e parar de carregar o pacote inteiro quando a tela so usa a moldura.
- uma tela pode precisar de `operation-shell` e `operation-card-head` sem precisar de boards, personas e KPI grid de operations.
-->

# Onda 4.1: mapa de dependencia de `operations.css` no catalogo

Este documento responde a pergunta:

1. "quais telas do catalogo realmente precisam do manifesto operacional completo e quais ja podem usar um contrato menor?"

Em linguagem simples:

1. algumas telas precisam do caminhão de ferramentas inteiro
2. outras so precisam de uma maleta com tres chaves
3. carregar o caminhão onde bastava a maleta deixa a oficina mais pesada e mais barulhenta

## Regra de leitura

Use estas classes:

1. `full`: a tela ainda depende do manifesto `css/design-system/operations.css`
2. `contract-only`: a tela precisa so da moldura operacional minima
3. `pending`: a tela tem cheiro de corte futuro, mas ainda pede prova antes da troca

## Inventario atual

### 1. Finance center

Classificacao:

1. `contract-only`

Por que:

1. usa `operation-shell`
2. usa `operation-card-head`, `operation-card-title` e `operation-card-copy`
3. usa `operation-hero-action-rail` em pontos localizados
4. a identidade de KPI, boards, tabs e carteira ja vive majoritariamente no CSS local de `finance`
5. a auditoria nao mostrou dependencia viva de personas, `display-wall`, `sessions.css`, `focus.css` ou KPI grid operacional

Arquivos relevantes:

1. [../../templates/catalog/finance.html](../../templates/catalog/finance.html)
2. [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)

Corte aplicado:

1. a tela deixou de carregar `css/design-system/operations.css`
2. ela passou a carregar `css/design-system/catalog-operation-contract.css`

### 2. Student directory

Classificacao:

1. `contract-only`

Por que:

1. usa `operation-shell`
2. usa `operation_card_head.html` em pontos localizados de prioridade e intake
3. usa um trilho pontual `operation-hero-action-rail` no resumo financeiro rapido
4. a identidade de KPIs, tabs, triagem e quick panel ja vive majoritariamente no CSS local de `students`
5. a auditoria nao mostrou dependencia viva de personas, `display-wall`, KPI grid operacional, `sessions.css` ou `focus.css`

Arquivos relevantes:

1. [../../templates/catalog/students.html](../../templates/catalog/students.html)
2. [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)

Corte aplicado:

1. a tela deixou de carregar `css/design-system/operations.css`
2. ela passou a carregar `css/design-system/catalog-operation-contract.css`

### 3. Student form

Classificacao:

1. `contract-only`

Por que:

1. a tela usa `operation-shell`, hero operacional e varios contratos proprios do workspace do aluno
2. parte importante da identidade ja mora em CSS local do catalogo
3. os pontos operacionais vivos auditados ficaram concentrados em `operation-hero-action-rail` e `operation-table-wrap`
4. a superficie nao mostrou dependencia viva de personas, KPI grid operacional, `sessions.css` ou `focus.css`

Arquivos relevantes:

1. [../../templates/catalog/student-form.html](../../templates/catalog/student-form.html)
2. [../../catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)

Corte aplicado:

1. a tela deixou de carregar `css/design-system/operations.css`
2. ela passou a carregar `css/design-system/catalog-operation-contract.css`

### 4. Class grid

Classificacao:

1. `contract-only`

Por que:

1. usa `operation-shell` e `workspace-shell`
2. usa hero operacional via `page_hero.html`
3. usa `card-head`, `card-title` e `card-copy` em vez de boards por persona
4. a grade de metricas ja e local (`class-grid-metric-grid`), sem dependencia viva de `operation-metric-grid`

Arquivos relevantes:

1. [../../templates/catalog/class-grid.html](../../templates/catalog/class-grid.html)
2. [../../catalog/presentation/class_grid_page.py](../../catalog/presentation/class_grid_page.py)

Corte aplicado:

1. a tela deixou de carregar `css/design-system/operations.css`
2. ela passou a carregar `css/design-system/catalog-operation-contract.css`

### 5. Finance plan form

Classificacao:

1. `contract-only`

Por que:

1. usa `operation-shell`
2. usa hero operacional via `page_hero.html`
3. usa `operation-card-head` e `operation-card-title` no summary rail
4. nao usa boards por persona nem KPI grid operacional

Corte aplicado:

1. a tela deixou de carregar `css/design-system/operations.css`
2. ela passou a carregar `css/design-system/catalog-operation-contract.css`

Arquivos relevantes:

1. [../../catalog/presentation/membership_plan_page.py](../../catalog/presentation/membership_plan_page.py)
2. [../../static/css/design-system/catalog-operation-contract.css](../../static/css/design-system/catalog-operation-contract.css)
3. [../../templates/catalog/finance-plan-form.html](../../templates/catalog/finance-plan-form.html)

## O que entrou no contrato minimo

O manifesto [../../static/css/design-system/catalog-operation-contract.css](../../static/css/design-system/catalog-operation-contract.css) hoje importa:

1. `operations/core.css`
2. `operations/components/card-shell.css`
3. `operations/workspace/tables.css`
4. `operations/refinements/hero.css`

Leitura simples:

1. shell operacional minimo
2. cabecalho de card compartilhado
3. mesa responsiva operacional
4. hero operacional

Sem puxar:

1. KPI grid operacional
2. personas manager, reception, coach e owner
3. refinamentos de display wall

## Default atual do catalogo

Agora [../../catalog/presentation/shared.py](../../catalog/presentation/shared.py) trata:

1. `css/design-system/catalog-operation-contract.css` como default
2. `css/design-system/operations.css` completo como excecao explicita

Leitura simples:

1. antes todo mundo ganhava o caminhão por padrão
2. agora todo mundo recebe a maleta
3. só pega o caminhão quem realmente provar que precisa

## Regra de ouro desta subonda

Se uma tela do catalogo usar:

1. `operation-shell`
2. `operation-card-head`
3. `operation-hero`

isso nao quer dizer automaticamente que ela precisa do manifesto operacional inteiro.

Ela pode precisar apenas do contrato minimo.

## Proximo corte recomendado

Se formos seguir com baixo arrependimento:

1. confirmar com smoke visual as telas ja migradas para `contract-only`
2. se alguma nova superficie realmente precisar do manifesto completo, marcar isso de forma explicita no presenter

Checklist irmao:

1. [front-end-contract-only-visual-smoke-checklist.md](front-end-contract-only-visual-smoke-checklist.md)
