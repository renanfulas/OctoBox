<!--
ARQUIVO: matriz operacional de ownership funcional e circuitos criticos.

POR QUE ELE EXISTE:
- transforma a regra de ownership por funcionalidade em um mapa operacional de manutencao.
- reduz risco de alterar uma tela local e esquecer a comunicacao cruzada com o shell e outras paginas.
- aponta rapidamente quais testes devem subir quando um circuito funcional for tocado.

O QUE ESTE ARQUIVO FAZ:
1. define o dono local de cada funcionalidade relevante do beta.
2. registra os contratos compartilhados que propagam comunicacao entre telas.
3. lista o minimo de testes obrigatorios por circuito critico.

TIPO DE DOCUMENTO:
- referencia operacional de manutencao e revisao de impacto.

AUTORIDADE:
- alta para ownership tecnico e regressao funcional do beta.

DOCUMENTO PAI:
- [front-end-ownership-map.md](front-end-ownership-map.md)

QUANDO USAR:
- antes de alterar uma funcionalidade relevante.
- antes de fechar PR de comportamento entre paginas.
- quando precisarmos saber rapidamente quais suites sobem para validar um circuito.

PONTOS CRITICOS:
- se um ownership mudar, esta matriz precisa mudar junto.
- esta matriz nao substitui testes; ela define o minimo que nao pode ser esquecido.
- links quebrados aqui comprometem a manutencao cruzada do produto.
-->

# Matriz de funcionalidades e circuitos criticos

## Como usar

Leia cada funcionalidade por quatro lentes:

1. dono local: onde a funcionalidade realmente mora e deve ser alterada primeiro
2. contratos compartilhados: por onde a mudanca comunica prioridade, alerta, hero, assets ou navegacao para o resto do produto
3. testes obrigatorios: quais suites sobem no minimo para evitar regressao silenciosa
4. circuito critico: quais outras paginas precisam continuar coerentes depois da alteracao

Regra pratica:

1. se a mudanca for local, altere o dono local primeiro
2. se a mudanca muda leitura cruzada, revise tambem os contratos compartilhados
3. se a funcionalidade muda fila, CTA, ancora, alerta ou prioridade, rode o circuito completo

## Contratos compartilhados centrais

Antes da matriz por funcionalidade, estes tres pontos continuam sendo a espinha dorsal da comunicacao transversal:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [access/context_processors.py](../../access/context_processors.py)
3. [access/shell_actions.py](../../access/shell_actions.py)

Testes-base desses contratos:

1. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
2. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

Checklist complementar para revisao:

1. [pr-circuit-checklist.md](pr-circuit-checklist.md)

Agenda manual por papel:

1. [../rollout/beta-role-test-agenda.md](../rollout/beta-role-test-agenda.md)

## Matriz por funcionalidade

### Dashboard

Dono local:

1. [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)
2. [dashboard/presentation.py](../../dashboard/presentation.py)
3. [templates/dashboard/index.html](../../templates/dashboard/index.html)
4. [static/css/design-system/dashboard.css](../../static/css/design-system/dashboard.css)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py) para hero, assets e behavior da tela
2. [access/context_processors.py](../../access/context_processors.py) para alertas do topo e navegacao global
3. [access/shell_actions.py](../../access/shell_actions.py) para prioridade operacional por papel

Circuito critico:

1. dashboard precisa continuar apontando corretamente para Alunos, Financeiro e Operacao por papel
2. alteracoes em CTAs ou alertas do dashboard exigem revisar links cruzados do topo e pulse chips

Testes obrigatorios:

1. [boxcore/tests/test_dashboard.py](../../boxcore/tests/test_dashboard.py)
2. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

### Alunos

Dono local:

1. [catalog/views/student_views.py](../../catalog/views/student_views.py)
2. [catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)
3. [catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)
4. [templates/catalog/students.html](../../templates/catalog/students.html)
5. [templates/catalog/student-form.html](../../templates/catalog/student-form.html)
6. [static/css/catalog/students.css](../../static/css/catalog/students.css)
7. [static/js/pages/student-form.js](../../static/js/pages/student-form.js)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py) para payload semantico da listagem e ficha
2. [access/context_processors.py](../../access/context_processors.py) para alertas de intake e leitura cruzada no shell
3. [access/shell_actions.py](../../access/shell_actions.py) para atalhos ligados a intake, pagamento e proximas acoes

Circuito critico:

1. alunos precisa continuar coerente com Dashboard e Recepcao quando existir intake pendente
2. mudancas em pagamento ou matricula afetam Financeiro e filas operacionais

Testes obrigatorios:

1. [boxcore/tests/test_catalog.py](../../boxcore/tests/test_catalog.py)
2. [boxcore/tests/test_students_domain.py](../../boxcore/tests/test_students_domain.py)
3. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
4. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

### Financeiro

Dono local:

1. [catalog/views/finance_views.py](../../catalog/views/finance_views.py)
2. [catalog/presentation/finance_center_page.py](../../catalog/presentation/finance_center_page.py)
3. [templates/catalog/finance.html](../../templates/catalog/finance.html)
4. [templates/catalog/finance-plan-form.html](../../templates/catalog/finance-plan-form.html)
5. [../../static/css/catalog/finance/](../../static/css/catalog/finance/)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py) para hero e assets da central financeira
2. [access/context_processors.py](../../access/context_processors.py) para alertas financeiros no topo
3. [access/shell_actions.py](../../access/shell_actions.py) para filas e CTA de cobranca

Circuito critico:

1. financeiro precisa continuar coerente com Dashboard e Recepcao para inadimplencia e cobranca
2. alteracoes em comunicacao financeira exigem revisar logica de mensagem e fila operacional

Testes obrigatorios:

1. [boxcore/tests/test_finance.py](../../boxcore/tests/test_finance.py)
2. [boxcore/tests/test_catalog_services.py](../../boxcore/tests/test_catalog_services.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

### Grade de aulas

Dono local:

1. [catalog/views/class_grid_views.py](../../catalog/views/class_grid_views.py)
2. [catalog/presentation/class_grid_page.py](../../catalog/presentation/class_grid_page.py)
3. [templates/catalog/class-grid.html](../../templates/catalog/class-grid.html)
4. [static/css/catalog/class-grid.css](../../static/css/catalog/class-grid.css)
5. [static/js/pages/class-grid.js](../../static/js/pages/class-grid.js)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py) para behavior e assets da grade
2. [access/context_processors.py](../../access/context_processors.py) para contexto global do shell
3. [access/shell_actions.py](../../access/shell_actions.py) para prioridade visivel quando a grade for relevante no papel atual

Circuito critico:

1. grade precisa continuar coerente com Dashboard e operacao quando a leitura de ocupacao e agenda afetar o dia
2. mudancas estruturais da grade exigem revisar JS local e payload semantico antes de tocar shell

Testes obrigatorios:

1. [boxcore/tests/test_catalog.py](../../boxcore/tests/test_catalog.py)
2. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py) quando a mudanca alterar prioridade, alerta ou CTA global

### Recepcao

Dono local:

1. [operations/workspace_views.py](../../operations/workspace_views.py)
2. [operations/presentation.py](../../operations/presentation.py)
3. [templates/operations/reception.html](../../templates/operations/reception.html)
4. [operations/action_views.py](../../operations/action_views.py)
5. [operations/forms.py](../../operations/forms.py)
6. [static/css/design-system/operations.css](../../static/css/design-system/operations.css)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py) para hero e comportamento do workspace
2. [access/context_processors.py](../../access/context_processors.py) para topo e leitura cruzada de alertas
3. [access/shell_actions.py](../../access/shell_actions.py) para filas de intake e pagamento da recepcao

Circuito critico:

1. recepcao precisa continuar coerente com Dashboard e Alunos para intake pendente
2. recepcao precisa continuar coerente com Financeiro para cobranca e pagamento pendente
3. alteracoes de ancora no workspace exigem revisar dashboard, topo e testes de href estrutural

Testes obrigatorios:

1. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
2. [boxcore/tests/test_operations_services.py](../../boxcore/tests/test_operations_services.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

### Coach

Dono local:

1. [operations/workspace_views.py](../../operations/workspace_views.py)
2. [operations/presentation.py](../../operations/presentation.py)
3. [templates/operations/coach.html](../../templates/operations/coach.html)
4. [operations/action_views.py](../../operations/action_views.py)
5. [operations/forms.py](../../operations/forms.py)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [access/context_processors.py](../../access/context_processors.py)
3. [access/shell_actions.py](../../access/shell_actions.py)

Circuito critico:

1. coach precisa continuar coerente com Dashboard quando houver ocorrencias tecnicas ou comportamentais
2. mudancas nas actions do coach exigem revisar formulario, validacao e reflexo operacional no shell

Testes obrigatorios:

1. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
2. [boxcore/tests/test_operations_domain.py](../../boxcore/tests/test_operations_domain.py)
3. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py) quando a alteracao subir prioridade para o shell

### Gerente

Dono local:

1. [operations/workspace_views.py](../../operations/workspace_views.py)
2. [operations/presentation.py](../../operations/presentation.py)
3. [templates/operations/manager.html](../../templates/operations/manager.html)
4. [static/css/design-system/operations.css](../../static/css/design-system/operations.css)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [access/context_processors.py](../../access/context_processors.py)
3. [access/shell_actions.py](../../access/shell_actions.py)

Circuito critico:

1. gerente concentra leitura transversal, entao qualquer alteracao de cards, contadores ou CTA deve preservar coerencia com dashboard e workspaces por papel

Testes obrigatorios:

1. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
2. [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)
3. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py) quando a alteracao tocar hero, assets ou behavior

### Guia

Dono local:

1. [guide/views.py](../../guide/views.py)
2. [guide/presentation.py](../../guide/presentation.py)
3. [templates/guide/system-map.html](../../templates/guide/system-map.html)

Contratos compartilhados:

1. [shared_support/page_payloads.py](../../shared_support/page_payloads.py)
2. [access/context_processors.py](../../access/context_processors.py)

Circuito critico:

1. guia nao costuma puxar prioridade operacional, mas precisa continuar coerente com shell, hero e navegacao global

Testes obrigatorios:

1. [boxcore/tests/test_guide.py](../../boxcore/tests/test_guide.py)
2. [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)

### API publica

Dono local:

1. [api/urls.py](../../api/urls.py)
2. [api/views.py](../../api/views.py)
3. [api/v1/urls.py](../../api/v1/urls.py)
4. [api/v1/views.py](../../api/v1/views.py)

Contratos compartilhados:

1. versionamento da fronteira em [api/urls.py](../../api/urls.py)
2. manifesto e saude publica em [api/v1/views.py](../../api/v1/views.py)
3. autenticacao e busca operacional de alunos no endpoint de autocomplete em [api/v1/views.py](../../api/v1/views.py)

Circuito critico:

1. a API precisa continuar previsivel para mobile e integracoes futuras
2. alteracoes no autocomplete precisam continuar coerentes com autenticacao, limite de resultados e rota de edicao de aluno
3. alteracoes de contrato publico exigem revisar impacto na documentacao e em clientes futuros

Testes obrigatorios:

1. [boxcore/tests/test_api.py](../../boxcore/tests/test_api.py)
2. [boxcore/tests/test_security_guards.py](../../boxcore/tests/test_security_guards.py) quando a mudanca tocar autenticacao, throttling ou autocomplete
3. [boxcore/tests/test_catalog.py](../../boxcore/tests/test_catalog.py) quando a alteracao impactar o fluxo que consome busca de alunos

### Integracao WhatsApp

Dono local:

1. [integrations/whatsapp/contracts.py](../../integrations/whatsapp/contracts.py)
2. [integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
3. [integrations/whatsapp/identity.py](../../integrations/whatsapp/identity.py)
4. [integrations/whatsapp/payloads.py](../../integrations/whatsapp/payloads.py)

Contratos compartilhados:

1. fachada publica do registro inbound em [integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
2. identidade de canal e reconciliacao com aluno ou intake em [integrations/whatsapp/identity.py](../../integrations/whatsapp/identity.py)
3. logs e modelos da comunicacao persistida exercitados por [boxcore/tests/test_integrations.py](../../boxcore/tests/test_integrations.py)

Circuito critico:

1. a integracao precisa continuar idempotente por external_message_id
2. o vinculo entre contato, aluno e intake nao pode regredir
3. saneamento de payload sensivel precisa continuar antes de persistir log
4. se a integracao gerar efeito visivel para financeiro ou recepcao, revisar tambem o circuito funcional afetado

Testes obrigatorios:

1. [boxcore/tests/test_integrations.py](../../boxcore/tests/test_integrations.py)
2. [boxcore/tests/test_finance.py](../../boxcore/tests/test_finance.py) quando a alteracao tocar cobranca ou comunicacao financeira
3. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py) quando a alteracao impactar intake, atendimento ou fila operacional

### Jobs assincronos

Dono local:

1. [jobs/base.py](../../jobs/base.py)
2. consumers concretos futuros no proprio dominio dono do comportamento

Contratos compartilhados:

1. contrato minimo de execucao em [jobs/base.py](../../jobs/base.py)
2. fronteira externa consumidora em API, integracoes ou comandos de dominio, conforme o caso

Circuito critico:

1. job nao deve concentrar regra de HTTP ou template
2. job deve ser idempotente e reexecutavel sempre que possivel
3. quando um job passar a existir de forma concreta, ele precisa nascer com suite propria do dominio dono

Testes obrigatorios:

1. hoje nao existe suite dedicada para jobs concretos nesta branch
2. ao introduzir job real, criar cobertura no dominio dono no mesmo pacote da mudanca
3. se o job tocar integracao externa, subir tambem [boxcore/tests/test_integrations.py](../../boxcore/tests/test_integrations.py)
4. se o job tocar mutacao operacional ou catalogo, subir tambem a suite local correspondente

## Pacotes minimos por tipo de mudanca

Se a alteracao for de payload semantico da tela:

1. rode [boxcore/tests/test_page_payloads.py](../../boxcore/tests/test_page_payloads.py)
2. rode a suite local da funcionalidade

Se a alteracao for de prioridade, alerta, CTA global ou ancora cruzada:

1. rode [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)
2. rode a suite local da funcionalidade
3. rode a suite da tela vizinha impactada pelo circuito

Se a alteracao for de action, workflow ou mutacao:

1. rode a suite local HTTP
2. rode a suite de dominio ou service relacionada
3. se a mutacao mudar fila ou contagem, rode tambem [boxcore/tests/test_shell_hints.py](../../boxcore/tests/test_shell_hints.py)

## Fechamento obrigatorio antes de considerar pronto

1. a funcionalidade continua com dono local claro
2. os contratos compartilhados afetados foram revisados no mesmo pacote
3. os testes obrigatorios do circuito rodaram
4. se houver ancora ou link cruzado, o href estrutural continua valido na pagina de destino
5. se a mudanca for visivel para mais de um papel, o shell continua coerente para cada papel afetado