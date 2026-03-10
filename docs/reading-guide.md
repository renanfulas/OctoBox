# Guia de leitura do projeto

Este guia foi atualizado para refletir o produto atual, que ja nao e so uma base administrativa inicial. Hoje existe uma camada visual forte para alunos e financeiro, com costura entre intake, matricula e cobranca.

## Objetivo deste guia

Use este roteiro para responder quatro perguntas:

1. por onde comecar a leitura
2. onde mora a logica de negocio mais sensivel
3. onde procurar quando surgir um bug
4. como navegar pela base sem se perder

## Ordem recomendada de leitura

### Etapa 1: entender a entrada do sistema

Comece por:

1. [manage.py](../manage.py)
2. [config/settings.py](../config/settings.py)
3. [config/urls.py](../config/urls.py)
4. [boxcore/urls.py](../boxcore/urls.py)

Aqui voce entende:

1. como o Django sobe
2. onde as configuracoes principais vivem
3. como as rotas sao distribuidas
4. quais modulos entram primeiro no fluxo

Se houver bug de inicializacao, app nao carregando, template nao encontrado ou rota quebrada, comece aqui.

### Etapa 2: entender acesso, login e papeis

Depois leia:

1. [boxcore/access/urls.py](../boxcore/access/urls.py)
2. [boxcore/access/views.py](../boxcore/access/views.py)
3. [boxcore/access/context_processors.py](../boxcore/access/context_processors.py)
4. [boxcore/access/roles/base.py](../boxcore/access/roles/base.py)
5. [boxcore/access/roles/owner.py](../boxcore/access/roles/owner.py)
6. [boxcore/access/roles/dev.py](../boxcore/access/roles/dev.py)
7. [boxcore/access/roles/manager.py](../boxcore/access/roles/manager.py)
8. [boxcore/access/roles/coach.py](../boxcore/access/roles/coach.py)
9. [boxcore/access/roles/__init__.py](../boxcore/access/roles/__init__.py)
10. [boxcore/management/commands/bootstrap_roles.py](../boxcore/management/commands/bootstrap_roles.py)

Aqui voce entende:

1. como o sistema decide quem e owner, dev, manager ou coach
2. como o login entra no fluxo
3. como a navegacao e filtrada pelo papel
4. como os grupos base sao preparados

Se o problema for permissao, redirecionamento, papel errado ou menu incorreto, a raiz normalmente esta aqui.

### Etapa 3: entender os dados do negocio

Depois leia os modelos:

1. [boxcore/models/base.py](../boxcore/models/base.py)
2. [boxcore/models/students.py](../boxcore/models/students.py)
3. [boxcore/models/finance.py](../boxcore/models/finance.py)
4. [boxcore/models/onboarding.py](../boxcore/models/onboarding.py)
5. [boxcore/models/operations.py](../boxcore/models/operations.py)
6. [boxcore/models/communications.py](../boxcore/models/communications.py)
7. [boxcore/models/audit.py](../boxcore/models/audit.py)
8. [boxcore/models/__init__.py](../boxcore/models/__init__.py)

Esta camada explica a estrutura real do produto.

Aqui voce entende:

1. o que e um aluno para o sistema
2. como intake e aluno definitivo se conectam
3. como funcionam plano, matricula e pagamento
4. como recorrencia e parcelamento sao representados
5. como aula, presenca e ocorrencia sao salvas
6. como auditoria registra rastreabilidade

Se o bug for de banco, relacionamento, status, relatorio ou regra comercial, comece aqui.

### Etapa 4: entender a camada visual de catalogo

Esta etapa agora e central para o produto.

Leia nesta ordem:

1. [boxcore/catalog/urls.py](../boxcore/catalog/urls.py)
2. [boxcore/catalog/forms.py](../boxcore/catalog/forms.py)
3. [boxcore/catalog/views.py](../boxcore/catalog/views.py)
4. [templates/catalog/students.html](../templates/catalog/students.html)
5. [templates/catalog/student-form.html](../templates/catalog/student-form.html)
6. [templates/catalog/finance.html](../templates/catalog/finance.html)
7. [templates/catalog/finance-plan-form.html](../templates/catalog/finance-plan-form.html)

Aqui voce entende:

1. como a base de alunos virou tambem um funil comercial
2. como um intake pode ser convertido em aluno definitivo
3. como o fluxo leve cria matricula e cobranca inicial
4. como pagamentos podem ser unicos, parcelados ou recorrentes
5. como a ficha do aluno permite acoes diretas de cobranca e matricula
6. como o financeiro filtra metricas, portfolio e alertas

Se o bug estiver em alunos, conversao, cobranca, filtros comerciais ou tela financeira, normalmente e aqui.

### Etapa 5: entender a operacao por papel

Depois leia:

1. [boxcore/operations/urls.py](../boxcore/operations/urls.py)
2. [boxcore/operations/views.py](../boxcore/operations/views.py)
3. [templates/operations/owner.html](../templates/operations/owner.html)
4. [templates/operations/dev.html](../templates/operations/dev.html)
5. [templates/operations/manager.html](../templates/operations/manager.html)
6. [templates/operations/coach.html](../templates/operations/coach.html)

Aqui voce entende:

1. como o usuario e enviado para a area correta
2. quais acoes pertencem a cada papel
3. onde termina a operacao administrativa e comeca a tecnica

Se houver bug de acao bloqueada, permissao funcional ou tela errada por papel, investigue aqui.

### Etapa 6: entender auditoria

Depois leia:

1. [boxcore/auditing/services.py](../boxcore/auditing/services.py)
2. [boxcore/models/audit.py](../boxcore/models/audit.py)
3. [boxcore/admin/audit.py](../boxcore/admin/audit.py)

Aqui voce entende:

1. como login, logout e mudancas administrativas sao auditados
2. como a camada visual de alunos e financeiro registra eventos sensiveis
3. por que chamadas de auditoria precisam usar assinatura consistente

Se houver bug de rastreabilidade ou ausencia de eventos, olhe aqui e depois quem chamou o servico.

### Etapa 7: entender painel e navegacao global

Agora leia:

1. [boxcore/dashboard/urls.py](../boxcore/dashboard/urls.py)
2. [boxcore/dashboard/views.py](../boxcore/dashboard/views.py)
3. [templates/dashboard/index.html](../templates/dashboard/index.html)
4. [templates/layouts/base.html](../templates/layouts/base.html)

Aqui voce entende:

1. como as metricas chegam na tela
2. como a navegacao global e montada
3. como o layout e reaproveitado entre as areas

Se o problema for visual, contexto ausente, card vazio ou navegacao quebrada, comece aqui.

### Etapa 8: entender importacao e automacoes internas

Leia:

1. [boxcore/management/commands/import_students_csv.py](../boxcore/management/commands/import_students_csv.py)
2. [docs/new-file-template.md](new-file-template.md)

Aqui voce entende:

1. como a base inicial de alunos entra por CSV
2. como o WhatsApp e usado para deduplicacao
3. como o projeto padroniza cabecalhos e comentarios

Se o bug vier de planilha, carga inicial ou dados massivos, comece aqui.

### Etapa 9: entender o admin do Django

Depois leia:

1. [boxcore/admin/students.py](../boxcore/admin/students.py)
2. [boxcore/admin/finance.py](../boxcore/admin/finance.py)
3. [boxcore/admin/operations.py](../boxcore/admin/operations.py)
4. [boxcore/admin/onboarding.py](../boxcore/admin/onboarding.py)
5. [boxcore/admin/__init__.py](../boxcore/admin/__init__.py)

Aqui voce entende:

1. como os dados aparecem no backoffice
2. quais filtros, buscas e autocompletes existem
3. como campos tecnicos ficam escondidos quando nao sao uteis para operacao manual

Se o sistema estiver funcional, mas o admin estiver ruim de usar ou quebrando submit, revise aqui.

### Etapa 10: fechar com testes

Feche a leitura com:

1. [boxcore/tests/test_access.py](../boxcore/tests/test_access.py)
2. [boxcore/tests/test_catalog.py](../boxcore/tests/test_catalog.py)
3. [boxcore/tests/test_dashboard.py](../boxcore/tests/test_dashboard.py)
4. [boxcore/tests/test_finance.py](../boxcore/tests/test_finance.py)
5. [boxcore/tests/test_guide.py](../boxcore/tests/test_guide.py)
6. [boxcore/tests/test_import_students.py](../boxcore/tests/test_import_students.py)
7. [boxcore/tests/test_operations.py](../boxcore/tests/test_operations.py)

Aqui voce entende:

1. quais fluxos o projeto considera essenciais
2. quais telas e acoes estao protegidas contra regressao
3. onde uma alteracao recente ja quebrou antes e passou a ter cobertura

## Como procurar bugs por assunto

Use esta heuristica:

1. bug de login, papel ou menu: access/
2. bug de rota principal: config/urls.py, [boxcore/urls.py](../boxcore/urls.py) ou urls do modulo afetado
3. bug de aluno ou intake: [boxcore/models/students.py](../boxcore/models/students.py), [boxcore/models/onboarding.py](../boxcore/models/onboarding.py) ou [boxcore/catalog/views.py](../boxcore/catalog/views.py)
4. bug de matricula, plano ou pagamento: [boxcore/models/finance.py](../boxcore/models/finance.py), [boxcore/catalog/views.py](../boxcore/catalog/views.py) ou [boxcore/admin/finance.py](../boxcore/admin/finance.py)
5. bug de filtros financeiros ou funil: [boxcore/catalog/forms.py](../boxcore/catalog/forms.py) e [boxcore/catalog/views.py](../boxcore/catalog/views.py)
6. bug de aula, presenca ou falta: [boxcore/models/operations.py](../boxcore/models/operations.py) e operations/
7. bug de auditoria: [boxcore/auditing/services.py](../boxcore/auditing/services.py) e [boxcore/models/audit.py](../boxcore/models/audit.py)
8. bug de importacao: [boxcore/management/commands/import_students_csv.py](../boxcore/management/commands/import_students_csv.py)
9. bug visual: templates/ e view correspondente

## Como fazer engenharia reversa sem travar

Quando abrir um arquivo novo:

1. leia o cabecalho
2. resuma com suas palavras o que ele faz
3. identifique quais classes e funcoes carregam a regra principal
4. veja quem chama esse arquivo ou quem depende dele
5. so depois altere alguma coisa

## Fluxo mental do sistema hoje

Pense no produto assim:

1. o Django sobe por [manage.py](../manage.py)
2. acesso define quem entrou e qual papel essa pessoa tem
3. a navegacao global mostra apenas o que faz sentido para o papel
4. catalogo visual cuida da rotina leve de alunos e financeiro
5. operacao por papel cuida das rotinas dedicadas de owner, dev, manager e coach
6. modelos sustentam tudo com status, relacionamentos e historico
7. auditoria registra o que nao pode desaparecer sem rastro
8. admin e comandos internos apoiam manutencao e operacao profunda

## Regra de estudo

Quando surgir duvida, faca esta pergunta antes de abrir arquivos aleatorios:

1. estou tentando entender acesso?
2. estou tentando entender dados?
3. estou tentando entender a tela leve de negocio?
4. estou tentando entender operacao por papel?
5. estou tentando entender automacao ou importacao?

Depois va direto para a pasta do assunto.