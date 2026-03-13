<!--
ARQUIVO: guia interno de leitura e depuracao da base.

POR QUE ELE EXISTE:
- Orienta a leitura do projeto por camadas e dominios sem depender de exploracao aleatoria.

O QUE ESTE ARQUIVO FAZ:
1. Define uma ordem pragmatica de estudo do sistema.
2. Mapeia os pontos de entrada mais sensiveis por assunto.
3. Ajuda a localizar bugs com menos ida e volta entre modulos.

TIPO DE DOCUMENTO:
- guia tecnico de navegacao e depuracao

AUTORIDADE:
- alta para leitura do codigo, baixa para direcao de produto

DOCUMENTO PAI:
- [../../README.md](../../README.md)

QUANDO USAR:
- quando a duvida for por onde ler o codigo, onde procurar um bug ou qual arquivo abre primeiro numa investigacao tecnica

PONTOS CRITICOS:
- Este guia precisa acompanhar renomeacoes de arquivo e mudancas arquiteturais.
- Links quebrados aqui reduzem muito a utilidade pedagogica do documento.
- Este guia nao deve redefinir a tese do produto nem competir com os documentos de direcao.
-->

# Guia de leitura do projeto

Este guia acompanha a arquitetura atual do OctoBox Control. A base deixou de concentrar comportamento em modulos genericos e passou a separar melhor cada dominio em views HTTP, queries de leitura e actions ou workflows de regra.

Regra de uso deste documento:

1. o [../../README.md](../../README.md) explica o produto e a direcao geral do repositorio
2. este arquivo entra depois, quando a necessidade passa a ser leitura tecnica, depuracao e localizacao de ownership no codigo
3. se houver conflito entre uma tese de produto e um atalho tecnico daqui, a tese oficial deve vencer e este guia precisa ser atualizado

Leitura estrutural importante para esta fase:

1. `boxcore` nao e mais a raiz canonica do runtime
2. `boxcore` agora deve ser lido como app legado de estado, compatibilidade e migrations historicas
3. ao navegar pela base, prefira primeiro os apps reais promovidos e so depois as fachadas historicas

Para a direcao de medio e longo prazo da arquitetura, leia tambem [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md).

Se o foco for preparar a quebra do atual boxcore em apps Django reais com baixo risco, leia tambem [../architecture/app-split-plan.md](../architecture/app-split-plan.md).

Se o foco for evitar regressao de imports historicos e saber qual caminho canonico usar no runtime atual, leia tambem [../architecture/promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md).

Se o foco for reduzir a dependencia do negocio em Django sem reescrever o produto, leia tambem [../architecture/django-decoupling-blueprint.md](../architecture/django-decoupling-blueprint.md).

Se o foco for transformar essa direcao em estrategia operacional por ondas, guardrails e criterio de pronto, leia tambem [../architecture/django-core-strategy.md](../architecture/django-core-strategy.md).

Se o foco for entender, em linguagem oficial do projeto, o que passa a ser o centro do sistema e por que Django deixa de ser o core conceitual, leia tambem [../architecture/octobox-conceptual-core.md](../architecture/octobox-conceptual-core.md).

Se o foco for entender o novo andar de comunicacao entre acesso e nucleo interno, leia tambem [../architecture/center-layer.md](../architecture/center-layer.md).

Se o foco for entender a malha transversal de sinais, integracoes, envelopes e observabilidade ao lado do CENTER, leia tambem [../architecture/signal-mesh.md](../architecture/signal-mesh.md).

Se o foco for entender o que e temporario na obra arquitetural e como retirar os agentes de transicao quando o predio ficar pronto, leia tambem [../architecture/scaffold-agents.md](../architecture/scaffold-agents.md).

Se o foco for entender a grande fachada frontal do produto, onde a experiencia visivel precisa permanecer limpa mesmo com obra lateral, leia tambem [../experience/front-display-wall.md](../experience/front-display-wall.md).

Se o foco for entender a camada superior de emissao visivel, alerta e projeção externa confiavel do sistema, leia tambem [../architecture/red-beacon.md](../architecture/red-beacon.md).

Se o foco for entender a escalada maxima de visibilidade e o sistema sonoro de mobilizacao defensiva do predio, leia tambem [../architecture/vertical-sky-beam.md](../architecture/vertical-sky-beam.md) e [../architecture/alert-siren.md](../architecture/alert-siren.md).

Se o foco for transformar a leitura extraordinaria do Beam em um plano real de convergencia entre front, UX, Center e desacoplamento de `boxcore`, leia tambem [../plans/vertical-sky-beam-readiness-guide.md](../plans/vertical-sky-beam-readiness-guide.md).

Se o foco for ver o modelo inteiro consolidado em uma referencia unica, leia tambem [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md).

Se o foco for estudar o criterio por tras das decisoes, leia tambem [personal-architecture-framework.md](personal-architecture-framework.md), [architecture-terms-glossary.md](architecture-terms-glossary.md) e [personal-growth-roadmap.md](personal-growth-roadmap.md).

## Objetivo deste guia

Use este roteiro para responder quatro perguntas:

1. Por onde comecar a leitura.
2. Onde mora a regra de negocio mais sensivel.
3. Onde procurar quando surgir um bug.
4. Como navegar pela base sem se perder depois das refatoracoes recentes.

## Mapa mental rapido

Hoje vale pensar o sistema em cinco blocos:

1. Entrada e configuracao do Django.
2. Acesso, papeis e navegacao global.
3. Modelos centrais do negocio.
4. Camadas de produto por dominio: catalogo, operacao por papel e dashboard.
5. Fronteiras de API, integracoes e jobs.
6. Auditoria, admin, comandos internos e testes.

Observacao de transicao:

1. `api`, `integrations`, `jobs`, `access`, `auditing` e `communications` ja existem como apps reais.
2. em alguns casos, especialmente em models historicos, o dono tecnico do comportamento ja mudou antes do app label mudar.

## Ordem recomendada de leitura

### Etapa 1: entender como o projeto sobe

Comece por:

1. [manage.py](../../manage.py)
2. [config/settings/base.py](../../config/settings/base.py)
3. [config/settings/development.py](../../config/settings/development.py)
4. [config/settings/production.py](../../config/settings/production.py)
5. [config/urls.py](../../config/urls.py)
6. [boxcore/urls.py](../../boxcore/urls.py)

Aqui voce entende:

1. Como o Django sobe.
2. Como o ambiente muda entre desenvolvimento e producao.
3. Como as rotas principais sao distribuidas.
4. Quais apps entram primeiro no fluxo.
5. Por que `config/urls.py` e a raiz HTTP canonica e `boxcore/urls.py` ficou como compatibilidade.

Se houver bug de inicializacao, app nao carregando, template nao encontrado ou rota principal quebrada, comece aqui.

### Etapa 1.5: entender a fronteira externa do produto

Leia:

1. [api/urls.py](../../api/urls.py)
2. [api/views.py](../../api/views.py)
3. [api/v1/urls.py](../../api/v1/urls.py)
4. [api/v1/views.py](../../api/v1/views.py)
5. [integrations/whatsapp/contracts.py](../../integrations/whatsapp/contracts.py)
6. [jobs/base.py](../../jobs/base.py)

Aqui voce entende:

1. onde a API publica do produto deve nascer
2. onde contratos externos devem ficar
3. onde jobs futuros devem entrar sem contaminar a interface web

Se o problema for contrato externo, expansao para mobile, webhook ou automacao futura, comece aqui.

### Etapa 2: entender acesso, login e papeis

Depois leia:

1. [access/urls.py](../../access/urls.py)
2. [access/views.py](../../access/views.py)
3. [access/context_processors.py](../../access/context_processors.py)
4. [access/permissions/mixins.py](../../access/permissions/mixins.py)
5. [access/roles/base.py](../../access/roles/base.py)
6. [access/roles/owner.py](../../access/roles/owner.py)
7. [access/roles/dev.py](../../access/roles/dev.py)
8. [access/roles/manager.py](../../access/roles/manager.py)
9. [access/roles/coach.py](../../access/roles/coach.py)
10. [access/roles/__init__.py](../../access/roles/__init__.py)
11. [boxcore/management/commands/bootstrap_roles.py](../../boxcore/management/commands/bootstrap_roles.py)

Aqui voce entende:

1. Como o sistema decide quem e owner, dev, manager ou coach.
2. Como o login entra no fluxo.
3. Como a navegacao e filtrada por papel.
4. Como as permissoes declarativas chegam nas views.

Se o problema for permissao, redirecionamento, papel errado ou menu incorreto, a raiz normalmente esta aqui.

### Etapa 3: entender os dados do negocio

Depois leia os modelos:

1. [boxcore/models/base.py](../../boxcore/models/base.py)
2. [boxcore/models/students.py](../../boxcore/models/students.py)
3. [boxcore/models/finance.py](../../boxcore/models/finance.py)
4. [boxcore/models/onboarding.py](../../boxcore/models/onboarding.py)
5. [boxcore/models/operations.py](../../boxcore/models/operations.py)
6. [boxcore/models/communications.py](../../boxcore/models/communications.py)
7. [boxcore/models/audit.py](../../boxcore/models/audit.py)
8. [boxcore/models/__init__.py](../../boxcore/models/__init__.py)

Aqui voce entende:

1. O que e um aluno para o sistema.
2. Como intake e aluno definitivo se conectam.
3. Como funcionam plano, matricula e pagamento.
4. Como aula, presenca e ocorrencia sao salvas.
5. Como auditoria registra rastreabilidade.

Se o bug for de banco, relacionamento, status, agregacao ou regra comercial, comece aqui.

### Etapa 3.5: entender communications sem mexer ainda no app label dos modelos

Leia:

1. [communications/models.py](../../communications/models.py)
2. [communications/queries.py](../../communications/queries.py)
3. [communications/services.py](../../communications/services.py)
4. [integrations/whatsapp/identity.py](../../integrations/whatsapp/identity.py)
5. [integrations/whatsapp/services.py](../../integrations/whatsapp/services.py)
6. [boxcore/models/communications.py](../../boxcore/models/communications.py)
7. [boxcore/models/onboarding.py](../../boxcore/models/onboarding.py)

Aqui voce entende:

1. Como o dominio de comunicacao passou a ter services e queries proprios.
2. Como o WhatsApp ja conversa com a superficie publica de `communications`.
3. Por que os modelos ainda continuam em `boxcore` nesta fase da migracao.

Se o problema for fila de entrada, vinculo de contato, log de mensagem ou toque operacional de WhatsApp, comece aqui.

### Etapa 4: entender o catalogo visual

Esta etapa hoje e central para o produto. O catalogo passou a ser organizado por dominio.

Leia nesta ordem:

1. [catalog/urls.py](../../catalog/urls.py)
2. [catalog/forms.py](../../catalog/forms.py)
3. [catalog/views/catalog_base_views.py](../../catalog/views/catalog_base_views.py)
4. [catalog/views/student_views.py](../../catalog/views/student_views.py)
5. [catalog/student_queries.py](../../catalog/student_queries.py)
6. [catalog/services/student_workflows.py](../../catalog/services/student_workflows.py)
7. [catalog/services/student_enrollment_actions.py](../../catalog/services/student_enrollment_actions.py)
8. [catalog/services/student_payment_actions.py](../../catalog/services/student_payment_actions.py)
9. [catalog/views/finance_views.py](../../catalog/views/finance_views.py)
10. [catalog/finance_queries.py](../../catalog/finance_queries.py)
11. [catalog/services/finance_communication_actions.py](../../catalog/services/finance_communication_actions.py)
12. [catalog/services/membership_plan_workflows.py](../../catalog/services/membership_plan_workflows.py)
13. [catalog/services/operational_queue.py](../../catalog/services/operational_queue.py)
14. [catalog/views/class_grid_views.py](../../catalog/views/class_grid_views.py)
15. [catalog/class_grid_queries.py](../../catalog/class_grid_queries.py)
16. [boxcore/catalog/report_builders.py](../../boxcore/catalog/report_builders.py)
17. [templates/catalog/students.html](../../templates/catalog/students.html)
18. [templates/catalog/student-form.html](../../templates/catalog/student-form.html)
19. [templates/catalog/finance.html](../../templates/catalog/finance.html)
20. [templates/catalog/finance-plan-form.html](../../templates/catalog/finance-plan-form.html)

Aqui voce entende:

1. Como a base de alunos tambem funciona como funil comercial.
2. Como um intake pode virar aluno definitivo.
3. Como a ficha do aluno dispara acoes de cobranca e matricula.
4. Como a camada HTTP ficou separada das leituras e da regra de negocio.
5. Como o financeiro visual monta metricas, carteira e fila operacional.

Se o bug estiver em alunos, conversao, cobranca, filtros comerciais, exportacao ou tela financeira, normalmente e aqui.

### Etapa 5: entender a operacao por papel

Operations tambem foi separado entre views base, workspaces, actions HTTP e queries de snapshot.

Leia nesta ordem:

1. [operations/urls.py](../../operations/urls.py)
2. [operations/base_views.py](../../operations/base_views.py)
3. [operations/workspace_views.py](../../operations/workspace_views.py)
4. [boxcore/operations/workspace_snapshot_queries.py](../../boxcore/operations/workspace_snapshot_queries.py)
5. [operations/action_views.py](../../operations/action_views.py)
6. [operations/actions.py](../../operations/actions.py)
7. [templates/operations/owner.html](../../templates/operations/owner.html)
8. [templates/operations/dev.html](../../templates/operations/dev.html)
9. [templates/operations/manager.html](../../templates/operations/manager.html)
10. [templates/operations/coach.html](../../templates/operations/coach.html)

Aqui voce entende:

1. Como o usuario e enviado para a area correta.
2. Como cada papel recebe um snapshot proprio.
3. Quais endpoints realmente mutam estado operacional.
4. Onde termina a camada HTTP e comeca a regra operacional.

Se houver bug de acao bloqueada, permissao funcional, workspace errado ou mutacao operacional com efeito colateral inesperado, investigue aqui.

### Etapa 6: entender o dashboard

O dashboard tambem foi simplificado em view HTTP e snapshot de leitura.

Leia:

1. [dashboard/urls.py](../../dashboard/urls.py)
2. [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)
3. [dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py)
4. [templates/dashboard/index.html](../../templates/dashboard/index.html)
5. [templates/layouts/base.html](../../templates/layouts/base.html)

Aqui voce entende:

1. Como o papel atual do usuario chega ao painel.
2. Como as metricas, alertas e listas sao agregadas.
3. Como a navegacao global e reaproveitada entre as areas.

Se o problema for card vazio, numero inconsistente, contexto ausente ou navegacao quebrada, comece aqui.

### Etapa 7: entender auditoria

Depois leia:

1. [auditing/services.py](../../auditing/services.py)
2. [boxcore/models/audit.py](../../boxcore/models/audit.py)
3. [boxcore/admin/audit.py](../../boxcore/admin/audit.py)

Aqui voce entende:

1. Como login, logout e mudancas administrativas sao auditados.
2. Como a camada visual de alunos e financeiro registra eventos sensiveis.
3. Por que chamadas de auditoria precisam manter assinatura consistente.

Se houver bug de rastreabilidade ou ausencia de eventos, olhe aqui e depois quem chamou o servico.

### Etapa 8: entender importacao e automacoes internas

Leia:

1. [boxcore/management/commands/import_students_csv.py](../../boxcore/management/commands/import_students_csv.py)
2. [new-file-template.md](new-file-template.md)

Aqui voce entende:

1. Como a base inicial de alunos entra por CSV.
2. Como o WhatsApp e usado para deduplicacao.
3. Como o projeto padroniza cabecalhos e comentarios.

Se o bug vier de planilha, carga inicial ou dados massivos, comece aqui.

### Etapa 9: entender o admin do Django

Depois leia:

1. [boxcore/admin/students.py](../../boxcore/admin/students.py)
2. [boxcore/admin/finance.py](../../boxcore/admin/finance.py)
3. [boxcore/admin/operations.py](../../boxcore/admin/operations.py)
4. [boxcore/admin/onboarding.py](../../boxcore/admin/onboarding.py)
5. [boxcore/admin/__init__.py](../../boxcore/admin/__init__.py)

Aqui voce entende:

1. Como os dados aparecem no backoffice.
2. Quais filtros, buscas e autocompletes existem.
3. Como campos tecnicos ficam escondidos quando nao sao uteis para operacao manual.

Se o sistema estiver funcional, mas o admin estiver ruim de usar ou quebrando submit, revise aqui.

### Etapa 10: fechar com testes

Observacao importante:

1. `api`, `integrations`, `access` e `auditing` ja tem dono tecnico fora de `boxcore`.
2. Os testes continuam fisicamente em `boxcore/tests` por compatibilidade de descoberta e labels legados.
3. Durante a transicao, leia o teste junto com o app real dono do comportamento.

Feche a leitura com:

1. [boxcore/tests/test_access.py](../../boxcore/tests/test_access.py)
2. [boxcore/tests/test_api.py](../../boxcore/tests/test_api.py)
3. [boxcore/tests/test_catalog.py](../../boxcore/tests/test_catalog.py)
4. [boxcore/tests/test_catalog_services.py](../../boxcore/tests/test_catalog_services.py)
5. [boxcore/tests/test_dashboard.py](../../boxcore/tests/test_dashboard.py)
6. [boxcore/tests/test_finance.py](../../boxcore/tests/test_finance.py)
7. [boxcore/tests/test_guide.py](../../boxcore/tests/test_guide.py)
8. [boxcore/tests/test_import_students.py](../../boxcore/tests/test_import_students.py)
9. [boxcore/tests/test_operations.py](../../boxcore/tests/test_operations.py)
10. [boxcore/tests/test_operations_services.py](../../boxcore/tests/test_operations_services.py)

Aqui voce entende:

1. Quais fluxos o projeto considera essenciais.
2. Quais telas e acoes estao protegidas contra regressao.
3. Onde uma alteracao recente ja quebrou antes e passou a ter cobertura.

## Como procurar bugs por assunto

Use esta heuristica:

1. Bug de login, papel ou menu: [access](../../access), com compatibilidade em [boxcore/access](../../boxcore/access).
2. Bug de rota principal: [config/urls.py](../../config/urls.py), [boxcore/urls.py](../../boxcore/urls.py) ou urls do modulo afetado.
3. Bug de aluno ou intake: [boxcore/models/students.py](../../boxcore/models/students.py), [boxcore/models/onboarding.py](../../boxcore/models/onboarding.py), [catalog/views/student_views.py](../../catalog/views/student_views.py) e [catalog/student_queries.py](../../catalog/student_queries.py).
4. Bug de matricula, plano ou pagamento: [boxcore/models/finance.py](../../boxcore/models/finance.py), [catalog/services/student_enrollment_actions.py](../../catalog/services/student_enrollment_actions.py), [catalog/services/student_payment_actions.py](../../catalog/services/student_payment_actions.py), [catalog/views/finance_views.py](../../catalog/views/finance_views.py) e [boxcore/admin/finance.py](../../boxcore/admin/finance.py).
5. Bug de filtros financeiros, relatorio ou fila operacional: [catalog/forms.py](../../catalog/forms.py), [catalog/finance_queries.py](../../catalog/finance_queries.py), [catalog/services/operational_queue.py](../../catalog/services/operational_queue.py), [boxcore/catalog/report_builders.py](../../boxcore/catalog/report_builders.py) e modelos financeiros em [boxcore/models/finance.py](../../boxcore/models/finance.py).
6. Bug de aula, presenca, ocorrencia ou workspace por papel: [boxcore/models/operations.py](../../boxcore/models/operations.py), [operations/workspace_views.py](../../operations/workspace_views.py), [operations/action_views.py](../../operations/action_views.py), [operations/actions.py](../../operations/actions.py) e [operations/facade/workspace.py](../../operations/facade/workspace.py).
7. Bug de dashboard: [dashboard/dashboard_views.py](../../dashboard/dashboard_views.py) e [dashboard/dashboard_snapshot_queries.py](../../dashboard/dashboard_snapshot_queries.py).
8. Bug de auditoria: [auditing/services.py](../../auditing/services.py), [auditing/signals.py](../../auditing/signals.py) e [boxcore/models/audit.py](../../boxcore/models/audit.py).
9. Bug de importacao: [boxcore/management/commands/import_students_csv.py](../../boxcore/management/commands/import_students_csv.py).
10. Bug visual: template da area mais a view correspondente.

## Fronteiras ja extraidas

Hoje o ownership tecnico ja esta assim:

1. API externa: [api](../../api)
2. Integracoes externas: [integrations](../../integrations)
3. Jobs e automacoes: [jobs](../../jobs)
4. Acesso, papeis e navegacao global: [access](../../access)
5. Auditoria e sinais transversais: [auditing](../../auditing)

Os namespaces equivalentes dentro de `boxcore` seguem existindo apenas como casca de compatibilidade.

## Como fazer engenharia reversa sem travar

Quando abrir um arquivo novo:

1. Leia o cabecalho.
2. Resuma com suas palavras o que ele faz.
3. Identifique quais classes e funcoes carregam a regra principal.
4. Veja quem chama esse arquivo ou quem depende dele.
5. So depois altere alguma coisa.

## Fluxo mental do sistema hoje

Pense no produto assim:

1. O Django sobe por [manage.py](../../manage.py) e pelas settings em [config/settings](../../config/settings).
2. Access define quem entrou, qual papel essa pessoa tem e o que ela pode ver.
3. A navegacao global mostra apenas o que faz sentido para o papel.
4. Catalogo visual cuida da rotina leve de alunos, financeiro e grade de aulas.
5. Operations cuida das rotinas dedicadas de owner, dev, manager e coach.
6. Dashboard consolida a leitura rapida da operacao.
7. Modelos sustentam tudo com status, relacionamentos e historico.
8. Auditoria registra o que nao pode desaparecer sem rastro.
9. Admin e comandos internos apoiam manutencao e operacao profunda.

## Regra de estudo

Quando surgir duvida, faca esta pergunta antes de abrir arquivos aleatorios:

1. Estou tentando entender acesso.
2. Estou tentando entender dados.
3. Estou tentando entender a tela leve de negocio.
4. Estou tentando entender operacao por papel.
5. Estou tentando entender painel, automacao ou importacao.

Depois va direto para a pasta do assunto.