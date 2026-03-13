## Objetivo

Comparar, dominio por dominio, quatro coisas diferentes:

- onde o model concreto realmente e definido
- onde a aplicacao deve importar esse model hoje
- onde o estado historico do Django ainda esta ancorado
- qual o proximo tipo de corte seguro para cada dominio

## Leitura correta desta matriz

Ownership de codigo nao e a mesma coisa que ownership de estado.

- ownership de codigo: onde a classe concreta ou a implementacao real mora hoje
- ownership de estado: qual app label, migrations e app config ainda sustentam o model no Django

Um dominio so esta realmente fora de boxcore quando as duas coisas tiverem saído dele.

## Matriz por dominio

### Students

- superficie publica atual: students/models.py
- definicao concreta atual: students/model_definitions.py
- ownership de estado atual: boxcore
- situacao: codigo concreto fora de boxcore, mas estado ainda historico
- leitura tecnica: Student ja nao e implementado em boxcore, mas app label e migrations continuam ancorados no estado legado
- proximo corte seguro: nenhum corte estrutural local isolado; so faz sentido dentro de um plano de split de estado por dominio

### Finance

- superficie publica atual: finance/models.py
- definicao concreta atual: finance/model_definitions.py
- ownership de estado atual: boxcore
- situacao: codigo concreto fora de boxcore, mas estado ainda historico
- leitura tecnica: Enrollment, MembershipPlan e Payment ja nao sao implementados em boxcore, mas app label, relacionamentos historicos e migrations continuam ancorados no estado legado
- proximo corte seguro: manter a superficie atual e evitar reintroduzir imports diretos de boxcore.models.finance

### Operations

- superficie publica atual: operations/models.py
- definicao concreta atual: operations/model_definitions.py
- ownership de estado atual: boxcore
- situacao: codigo concreto fora de boxcore, mas estado ainda historico
- leitura tecnica: ClassSession, Attendance e BehaviorNote ja nao sao implementados em boxcore, mas app label, relacionamentos historicos e migrations continuam ancorados no estado legado
- proximo corte seguro: continuar movendo runtime e comportamento, nao o estado dos models

### Auditing

- superficie publica atual: auditing/models.py
- definicao concreta atual: auditing/model_definitions.py
- ownership de estado atual: boxcore
- situacao: codigo concreto fora de boxcore, mas estado ainda historico
- leitura tecnica: AuditEvent ja nao e implementado em boxcore, mas o app label e o estado do Django continuam ancorados nele
- proximo corte seguro: nenhum corte estrutural local; a prioridade continua sendo nao reacoplar codigo novo ao exportador central boxcore.models

### Onboarding

- superficie publica atual: onboarding/models.py
- definicao concreta atual: onboarding/model_definitions.py
- ownership de estado atual: boxcore
- situacao: codigo concreto fora de boxcore, mas estado ainda historico
- leitura tecnica: StudentIntake ja nao e implementado em boxcore, mas o app label e o relacionamento historico com Student continuam ancorados no estado legado
- proximo corte seguro: manter onboarding.models como contrato canonico da aplicacao

### Communications

- superficie publica atual: communications/models.py
- definicao concreta atual: communications/model_definitions/whatsapp.py
- ownership de estado atual: boxcore
- situacao: dominio mais avancado da transicao
- leitura tecnica: aqui ja houve separacao entre ownership de codigo e ownership de estado; a implementacao real saiu de boxcore, mas o model concreto ainda preserva app_label e relacionamentos historicos para manter schema e migrations
- proximo corte seguro: nao mexer no app label ainda; usar communications como referencia do padrao de transicao para outros dominios quando houver justificativa real

### Bases abstratas compartilhadas

- superficie publica atual: model_support/base.py
- definicao concreta atual: model_support/base.py
- ownership de estado atual: neutro, sem schema proprio
- situacao: corte concluido
- leitura tecnica: TimeStampedModel ja saiu com sucesso do namespace historico porque era uma base abstrata sem impacto de schema
- proximo corte seguro: repetir esse padrao apenas para estruturas neutras equivalentes

## Conclusao comparativa

Hoje existem tres niveis diferentes de maturidade na transicao:

### Nivel 1. Superficie publica separada, mas model concreto ainda em boxcore

- students

### Nivel 2. Codigo concreto fora de boxcore, mas estado ainda historico

- finance
- students
- operations
- auditing
- onboarding
- communications

### Nivel 3. Totalmente neutro e fora de boxcore sem custo de schema

- model_support.base.TimeStampedModel

## Leitura estrategica

Isso mostra que o projeto nao esta travado. Ele ja tem um padrao comprovado de transicao:

1. primeiro separar superficie publica de importacao
2. depois, quando fizer sentido, separar ownership de codigo
3. por ultimo, so com plano proprio, separar ownership de estado

O erro agora seria pular do nivel 1 direto para o nivel 3 em dominios concretos sem um projeto explicito de migrations e app label.

Observacao complementar:

- o exportador central boxcore/models/__init__.py ja nao e mais necessario para o runtime atual
- ele permanece apenas como camada de compatibilidade para imports historicos ainda tolerados durante a transicao

## Proximo corte seguro recomendado

Em vez de tentar mover models concretos de students, finance, operations, auditing ou onboarding agora, o proximo corte seguro e consolidar ainda mais a regra:

1. codigo de aplicacao importa de superficies de dominio
2. codigo novo nao deve nascer em boxcore.models
3. boxcore.models fica cada vez mais como ancora historica e nao como API publica central

## Quando reabrir o assunto de split real de estado

Vale reabrir esse assunto apenas se uma destas condicoes aparecer:

- necessidade operacional real de separar migrations por dominio
- necessidade de distribuir apps de forma independente
- custo recorrente de manter app label historico maior do que o risco de migra-lo
- necessidade de tornar um dominio reutilizavel fora deste produto