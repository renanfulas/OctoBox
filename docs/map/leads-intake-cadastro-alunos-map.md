<!--
ARQUIVO: mapa operacional de leads, intake e cadastro de alunos.

POR QUE ELE EXISTE:
- junta em um unico trilho a entrada comercial, a triagem operacional e a conversao em aluno.
- reduz ida e volta entre onboarding, catalog, students e finance quando a pergunta for "onde isso acontece de verdade?".

O QUE ESTE ARQUIVO FAZ:
1. define a ordem curta de leitura do funil leads -> intake -> cadastro -> matricula.
2. aponta ownership tecnico de cada etapa.
3. registra onde investigar quando houver fila travada, conversao errada ou cadastro inconsistente.

PONTOS CRITICOS:
- este mapa depende de arquivos reais; se rotas, workflows ou models mudarem, ele precisa ser revisado.
- onboarding e students ja tem ownership de codigo fora de boxcore, mas o estado historico ainda preserva app label legado.
- este documento nao substitui o runtime nem os testes; ele organiza a leitura operacional do circuito.
-->

# Mapa de leads, intake e cadastro de alunos

Este documento explica o trilho comercial principal do OctoBox:

1. um contato entra como lead ou conversa provisoria
2. essa entrada vive na Central de Intake
3. quando fizer sentido, ela vira cadastro de aluno
4. o cadastro pode sair da mesma ficha ja com plano, matricula e cobranca inicial

Pense assim:

1. `StudentIntake` e a porta da frente
2. `Student` e a identidade consolidada
3. `catalog` e a ponte visual e operacional entre os dois

## Ordem curta de leitura

Se a pergunta for "como esse funil funciona?", leia nesta ordem:

1. [../../README.md](../../README.md)
2. [documentation-authority-map.md](documentation-authority-map.md)
3. [../../onboarding/model_definitions.py](../../onboarding/model_definitions.py)
4. [../../onboarding/queries.py](../../onboarding/queries.py)
5. [../../onboarding/facade.py](../../onboarding/facade.py)
6. [../../onboarding/views.py](../../onboarding/views.py)
7. [../../catalog/views/student_views.py](../../catalog/views/student_views.py)
8. [../../catalog/services/student_workflows.py](../../catalog/services/student_workflows.py)
9. [../../students/model_definitions.py](../../students/model_definitions.py)
10. [../../catalog/services/enrollments.py](../../catalog/services/enrollments.py)
11. [../../catalog/student_queries.py](../../catalog/student_queries.py)
12. [../reference/lead-attribution-ml-foundation.md](../reference/lead-attribution-ml-foundation.md)

## Mapa mental rapido

Hoje o circuito principal funciona assim:

1. a Central de Intake cria ou filtra entradas provisórias em [../../onboarding/views.py](../../onboarding/views.py)
2. essas entradas sao salvas como `StudentIntake` em [../../onboarding/model_definitions.py](../../onboarding/model_definitions.py)
3. a leitura operacional da fila nasce em [../../onboarding/queries.py](../../onboarding/queries.py)
4. a semantica da fila e as acoes de triagem vivem em [../../onboarding/facade.py](../../onboarding/facade.py)
5. a ficha de aluno recebe um `intake` opcional em [../../catalog/views/student_views.py](../../catalog/views/student_views.py)
6. a conversao para `Student` acontece pelos workflows em [../../catalog/services/student_workflows.py](../../catalog/services/student_workflows.py)
7. o model final do aluno vive em [../../students/model_definitions.py](../../students/model_definitions.py)
8. se houver plano e cobranca, a sincronizacao de matricula sai por [../../catalog/services/enrollments.py](../../catalog/services/enrollments.py)

## Ownership por etapa

### 1. Entrada comercial: lead ou conversa

Arquivos principais:

1. [../../onboarding/views.py](../../onboarding/views.py)
2. [../../onboarding/forms.py](../../onboarding/forms.py)
3. [../../templates/onboarding/intake_center.html](../../templates/onboarding/intake_center.html)

Aqui mora:

1. criacao rapida de `lead` ou `intake`
2. permissao por papel para recepcao, manager e owner
3. destino canonico da central de entradas

Regra importante:

1. o `entry_kind` entra no `raw_payload`
2. o status inicial nasce como `new`
3. a tela aceita consulta por `dev`, mas `dev` nao executa a fila nem cria entrada por essa interface

### 2. Estado provisório: intake

Arquivos principais:

1. [../../onboarding/model_definitions.py](../../onboarding/model_definitions.py)
2. [../../boxcore/models/onboarding.py](../../boxcore/models/onboarding.py)

Aqui mora:

1. o model `StudentIntake`
2. status como `new`, `reviewing`, `matched`, `approved` e `rejected`
3. origem da entrada como `manual`, `csv`, `whatsapp` e `import`
4. vinculo opcional com `linked_student`

Leitura pratica:

1. `StudentIntake` e como uma ficha temporaria na recepcao
2. ela guarda o primeiro contato antes de o sistema assumir "isso ja e um aluno consolidado"

### 3. Triagem e fila de conversao

Arquivos principais:

1. [../../onboarding/queries.py](../../onboarding/queries.py)
2. [../../onboarding/facade.py](../../onboarding/facade.py)
3. [../../onboarding/domain/intake_semantics.py](../../onboarding/domain/intake_semantics.py)

Aqui mora:

1. contagem de pendentes
2. fila de conversao
3. cards de KPI e radar por origem
4. separacao entre origem operacional e canal comercial de captacao
5. decisao operacional como mover para conversa ou rejeitar intake

Heuristica:

1. se o numero da fila parece errado, comece em `queries.py`
2. se a acao da fila esta liberando ou bloqueando na hora errada, olhe `facade.py` e `domain/intake_semantics.py`

### 4. Conversao para aluno

Arquivos principais:

1. [../../catalog/views/student_views.py](../../catalog/views/student_views.py)
2. [../../catalog/services/student_workflows.py](../../catalog/services/student_workflows.py)
3. [../../catalog/services/intakes.py](../../catalog/services/intakes.py)

Aqui mora:

1. prefill da ficha de aluno quando existe `intake`
2. criacao e atualizacao rapida do aluno
3. sincronizacao do intake com o cadastro final
4. emissao de eventos para manager stream e student stream

Regra pratica:

1. a view monta a casca HTTP
2. o workflow faz a conversao real
3. o intake nao deveria ser "copiado na mao" em outro ponto; o caminho oficial passa por esse workflow

### 5. Cadastro consolidado do aluno

Arquivos principais:

1. [../../students/model_definitions.py](../../students/model_definitions.py)
2. [../../boxcore/models/students.py](../../boxcore/models/students.py)
3. [../../catalog/presentation/student_form_page.py](../../catalog/presentation/student_form_page.py)
4. [../../templates/catalog/student-form.html](../../templates/catalog/student-form.html)

Aqui mora:

1. o model `Student`
2. status como `lead`, `active`, `paused` e `inactive`
3. dados essenciais de cadastro
4. a ficha visual que conduz perfil, saude, plano e cobranca

Observacao importante:

1. o ownership de codigo do aluno ja esta em `students`
2. o app label historico ainda fica em `boxcore`
3. isso evita quebrar schema e migrations durante a transicao

### 6. Matricula e cobranca inicial

Arquivos principais:

1. [../../catalog/services/enrollments.py](../../catalog/services/enrollments.py)
2. [../../catalog/services/student_enrollment_actions.py](../../catalog/services/student_enrollment_actions.py)
3. [../../catalog/services/student_payment_actions.py](../../catalog/services/student_payment_actions.py)
4. [../../catalog/student_queries.py](../../catalog/student_queries.py)

Aqui mora:

1. sincronizacao entre aluno, plano, matricula e pagamento
2. leitura financeira da ficha
3. proximos passos depois da conversao do lead em aluno

Traducao simples:

1. intake responde "quem entrou"
2. cadastro responde "quem essa pessoa e"
3. matricula e cobranca respondem "como ela passa a operar dentro do box"

## Fluxo ponta a ponta

Leia o fluxo oficial assim:

1. a recepcao ou a gestao cria uma entrada na Central de Intake
2. o sistema salva isso como `StudentIntake`
3. a fila mostra o item como `new` ou `reviewing`
4. ao abrir a ficha de aluno com `?intake=<id>`, o cadastro pode nascer pre-preenchido
5. o workflow cria ou atualiza `Student`
6. se houver plano escolhido, o mesmo fluxo pode sincronizar matricula e primeira cobranca
7. o intake passa a apontar para o aluno consolidado

## Onde procurar bugs por assunto

Use esta trilha:

1. lead nao aparece na central: [../../onboarding/views.py](../../onboarding/views.py), [../../onboarding/forms.py](../../onboarding/forms.py) e [../../onboarding/model_definitions.py](../../onboarding/model_definitions.py)
2. contador de pendentes errado: [../../onboarding/queries.py](../../onboarding/queries.py)
3. acao da fila bloqueada ou permissao estranha: [../../onboarding/facade.py](../../onboarding/facade.py) e [../../onboarding/domain/intake_semantics.py](../../onboarding/domain/intake_semantics.py)
4. intake nao preenche a ficha do aluno: [../../catalog/views/student_views.py](../../catalog/views/student_views.py)
5. intake nao vira aluno corretamente: [../../catalog/services/student_workflows.py](../../catalog/services/student_workflows.py) e [../../catalog/services/intakes.py](../../catalog/services/intakes.py)
6. aluno criado sem consistencia de telefone ou duplicado: [../../students/model_definitions.py](../../students/model_definitions.py)
7. aluno criado mas sem matricula ou cobranca: [../../catalog/services/enrollments.py](../../catalog/services/student_enrollment_actions.py) e [../../catalog/services/student_payment_actions.py](../../catalog/services/student_payment_actions.py)
8. diretório de alunos nao reflete o funil comercial: [../../catalog/student_queries.py](../../catalog/student_queries.py) e [../../catalog/presentation/student_directory_page.py](../../catalog/presentation/student_directory_page.py)

## Riscos e guardrails

Existem tres cuidados que valem ouro aqui:

1. nao trate `StudentIntake` e `Student` como a mesma coisa
2. nao pule o workflow oficial de conversao so para salvar mais rapido
3. nao mova implementacao de volta para `boxcore`, porque isso recria debito tecnico historico

Traducao para uma crianca de 6 anos:

1. o lead e o nome escrito no caderno da recepcao
2. o intake e a ficha provisoria em cima do balcao
3. o aluno e a pasta oficial no armario
4. se misturarmos tudo, depois ninguem sabe qual papel vale de verdade

## Regra final de manutencao

Se mexer nesse circuito, revise nesta ordem:

1. model de intake
2. leitura da fila
3. acoes da central
4. ficha de aluno
5. workflow de conversao
6. matricula e cobranca
7. diretorio e snapshots de leitura

Se uma mudanca tocar duas ou mais dessas etapas, o risco de debito tecnico sobe e os testes do circuito de catalogo e onboarding devem ser revisados no mesmo pacote.
