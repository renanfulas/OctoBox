<!--
ARQUIVO: mapa dos contratos vivos e aposentados de data-action no runtime principal.

POR QUE ELE EXISTE:
- fecha a trilha forense de limpeza de `data-action` com uma referencia operacional unica.
- separa o que ainda aciona JS do que apenas estrutura componente ou ja foi removido.
- evita que a equipe volte a tratar `data-action` como magia ou cole novos atributos sem dono.

O QUE ESTE ARQUIVO FAZ:
1. lista as familias de `data-action` ainda vivas por JS.
2. registra os contratos que continuam vivos por papel estrutural.
3. documenta os contratos aposentados na trilha de limpeza.
4. define a regra de decisao para futuras auditorias.

PONTOS CRITICOS:
- este mapa descreve o runtime principal em `templates/` + `static/`.
- `data-action` nao deve ser mantido por habito; precisa ter dono comprovado.
- ausencia de listener JS nao significa remocao automatica: ainda pode ser contrato estrutural.
-->

# Mapa dos contratos de `data-action`

Este documento responde a pergunta:

1. "quais `data-action` ainda vivem de verdade no OctoBOX e quais ja foram aposentados?"

Metafora curta:

1. alguns `data-action` ainda sao botoes ligados na tomada
2. alguns sao etiquetas da planta eletrica
3. outros eram adesivos colados em botoes que ja funcionavam sem eles

## Regra-mestra

Antes de remover qualquer `data-action`, responda nesta ordem:

1. quem emite?
2. onde o HTML expoe?
3. quem consome?
4. o efeito real vem de JS, de contrato estrutural ou do proprio browser?

Classifique sempre em uma destas caixas:

1. `vivo por JS`
2. `vivo por contrato estrutural`
3. `aposentado`

## Fontes de verdade

Leia nesta ordem:

1. [../../README.md](../../README.md)
2. [documentation-authority-map.md](documentation-authority-map.md)
3. [front-end-ownership-map.md](front-end-ownership-map.md)
4. [front-end-data-action-debug-checklist.md](front-end-data-action-debug-checklist.md)
5. [front-end-dashboard-action-contract-map.md](front-end-dashboard-action-contract-map.md) para familias do dashboard
6. [front-end-neon-contract-map.md](front-end-neon-contract-map.md) para `blink-*`
7. runtime real em `templates/`, `static/js/`, `static/css/`

## 1. Vivo por JS

Estes contratos continuam ativos porque ha listener real no runtime.

### Tabs genericas

Familia:

1. `open-tab-*`

Dono:

1. [../../static/js/pages/interactive_tabs.js](../../static/js/pages/interactive_tabs.js)

Exemplos:

1. `open-tab-students-directory`
2. `open-tab-students-active`
3. `open-tab-finance-queue`
4. `open-tab-finance-movements`
5. `open-tab-finance-portfolio`
6. `open-tab-intake-queue`

Leitura simples:

1. aqui o `data-action` e o proprio comando de abrir painel

### Shell global

Familias:

1. `blink-topbar-*`
2. `blink-board-*`
3. `blink-sidebar-*`

Dono:

1. [../../static/js/core/shell.js](../../static/js/core/shell.js)

Leitura simples:

1. o shell escuta o prefixo e resolve alvo por `data-ui`, `id` ou `data-nav-key`

### Grade

Contratos:

1. `open-monthly-calendar`
2. `open-weekly-modal-full`
3. `toggle-weekly-day-overflow`

Dono:

1. [../../static/js/pages/class-grid/class-grid.js](../../static/js/pages/class-grid/class-grid.js)

### Financeiro do aluno

Contratos:

1. `toggle-financial-workspace`
2. `open-drawer`
3. `close-drawers`
4. `submit-stripe`
5. `edit-payment`
6. `vacation-freeze`
7. `cancel-payment-confirm`

Dono:

1. [../../static/js/pages/finance/student-financial-workspace.js](../../static/js/pages/finance/student-financial-workspace.js)

### Trilha financeira

Contratos:

1. `finance-priority-prev`
2. `finance-priority-next`
3. `open-finance-whatsapp`

Dono:

1. [../../static/js/pages/finance/finance-priority-carousel.js](../../static/js/pages/finance/finance-priority-carousel.js)

### Ficha e diretorio de alunos

Contratos:

1. `toggle-student-profile-edit`
2. `submit-student-form`
3. `next-step`
4. `prev-step`

Donos:

1. [../../static/js/pages/students/student-form.js](../../static/js/pages/students/student-form.js)
2. [../../static/js/pages/students/student-form-stepper.js](../../static/js/pages/students/student-form-stepper.js)
3. [../../static/js/pages/students/student-directory.js](../../static/js/pages/students/student-directory.js)

### Recepcao

Contratos:

1. `manage-reception-payment`
2. `launch-reception-whatsapp`

Dono:

1. [../../static/js/pages/operations/reception-payment-card.js](../../static/js/pages/operations/reception-payment-card.js)

## 2. Vivo por contrato estrutural

Estes contratos nao devem ser removidos automaticamente so porque nao ha listener direto no mesmo ponto.

### Payload interativo de KPI e cards

Locais:

1. [../../templates/catalog/includes/student/student_metric_card.html](../../templates/catalog/includes/student/student_metric_card.html)
2. [../../templates/includes/ui/shared/interactive_kpi_card.html](../../templates/includes/ui/shared/interactive_kpi_card.html)
3. [../../templates/includes/ui/shared/metric_card.html](../../templates/includes/ui/shared/metric_card.html)

Razao:

1. `card.data_action` ainda e o fio entre payload e componente interativo
2. alguns hosts apenas repassam o atributo; o consumidor real mora em outra camada

### Selecao e estado de KPI

Locais:

1. [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)
2. [../../catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. [../../catalog/finance_snapshot/metrics.py](../../catalog/finance_snapshot/metrics.py)

Razao:

1. `default_action` ainda participa da selecao e da leitura inicial de cards
2. remover isso sem migracao pode quebrar destaque, estado inicial ou leitura de recorte

### Hosts compartilhados de leitura e hero

Locais:

1. [../../templates/includes/ui/layout/hero_stat_panel.html](../../templates/includes/ui/layout/hero_stat_panel.html)
2. [../../templates/includes/ui/layout/dashboard_reading_list.html](../../templates/includes/ui/layout/dashboard_reading_list.html)
3. [../../templates/includes/ui/layout/page_reading_list.html](../../templates/includes/ui/layout/page_reading_list.html)
4. [../../templates/includes/ui/layout/page_reading_panel.html](../../templates/includes/ui/layout/page_reading_panel.html)

Razao:

1. ainda aceitam `item.data_action` ou `action.data_action` como parte do contrato compartilhado
2. nao devem ser "limpos" em lote sem revisar cada surface que os consome

### Topbar por `data-ui`

Local:

1. [../../templates/includes/ui/layout/topbar/topbar_alerts.html](../../templates/includes/ui/layout/topbar/topbar_alerts.html)

Razao:

1. o contrato real de alvo da topbar hoje passa por `data-ui`
2. o `data-action` antigo ja foi podado onde era sobra, mas o alvo estrutural continua vivo

## 3. Aposentado

Estes contratos foram removidos porque:

1. existia emissor em payload ou template
2. nao havia consumidor em JS
3. nao havia hook em CSS ou teste
4. o comportamento real ja vinha de `href`, `form` ou `submit`

### Contratos de navegacao e atalhos aposentados

1. `open-tab-student-form-essential`
2. `open-tab-student-form-financial`
3. `jump-report-commercial`
4. `jump-report-finance`
5. `jump-reception-class-grid`
6. `open-student-intake-center`
7. `open-student-create`
8. `open-priority-student-form`
9. `open-priority-student-admin`
10. `open-finance-alerts`
11. `open-intake-alerts`
12. `open-intake-center`
13. `open-intake-center-from-preview`
14. `open-student-registration`
15. `open-intake-registration`
16. `open-students-directory`
17. `open-class-grid`
18. `open-full-class-grid`
19. `open-student-financial-overview`
20. `open-report-focus`
21. `open-class-grid-session-edit`
22. `open-student-quick-create-from-intake`
23. `open-student-quick-create-from-intake-handoff`
24. `open-quick-action`

### Contratos de formulario aposentados

1. `submit-login`
2. `confirm-login`
3. `filter-finance`
4. `apply-finance-filters`
5. `clear-finance-filters`
6. `filter-intakes`
7. `apply-intake-filters`
8. `clear-intake-filters`
9. `class-grid-panel-button`
10. `delete-class-grid-session`
11. `confirm-class-grid-session-delete`
12. `confirm-reception-payment`
13. `save-reception-payment-update`

## 4. Regra pratica para futuras auditorias

### Pode remover rapido quando:

1. o nome aparece so em template ou payload
2. nao existe listener em `static/js`
3. nao existe hook em `static/css`
4. nao existe teste cobrindo o atributo
5. `href`, `form` ou `submit` ja sustentam o comportamento

### Preserve e documente quando:

1. o contrato usa prefixo conhecido do shell
2. o contrato alimenta tabs genericas
3. o include compartilhado ainda aceita `data_action` dinamico
4. o payload usa `default_action` para selecao, estado inicial ou leitura interativa

### Nao trate como morto so porque:

1. nao houve `closest('[data-action=\"nome\"]')` no grep
2. o contrato pode ser consumido por prefixo, host compartilhado ou payload estrutural

## 5. Proxima inspecao recomendada

Se a trilha continuar no futuro, as proximas perguntas maduras nao sao:

1. "qual `data-action` eu ainda posso apagar?"

E sim:

1. "quais hosts compartilhados ainda deveriam aceitar `data_action`?"
2. "quais contratos vivos merecem migrar para `target_panel`, `data-ui` ou `data-role`?"
3. "onde ainda existe host generico demais para superficie especifica demais?"

Alvos naturais de inspeção futura:

1. [../../templates/includes/ui/layout/hero_stat_panel.html](../../templates/includes/ui/layout/hero_stat_panel.html)
2. [../../templates/includes/ui/layout/dashboard_reading_list.html](../../templates/includes/ui/layout/dashboard_reading_list.html)
3. [../../templates/includes/ui/layout/page_reading_list.html](../../templates/includes/ui/layout/page_reading_list.html)
4. [../../templates/includes/ui/layout/page_reading_panel.html](../../templates/includes/ui/layout/page_reading_panel.html)

## Fechamento

Leitura curta:

1. o OctoBOX ainda usa `data-action`
2. mas agora ele esta muito menos espalhado por supersticao
3. o que ficou tem dono mais claro
4. o que saiu era peso morto

Em linguagem simples:

1. antes havia botoes, etiquetas e fios misturados na mesma caixa
2. agora a caixa esta separada em:
   - fio vivo
   - etiqueta da planta
   - adesivo velho jogado fora
