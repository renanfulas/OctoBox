<!--
ARQUIVO: blueprint pragmatico para reduzir a dependencia de Django no core do produto.

POR QUE ELE EXISTE:
- Define como tirar regra de negocio do boxcore e do ciclo HTTP sem reescrever o produto.
- Traduz a ideia de "nao depender do Django" em passos pequenos, verificaveis e financeiramente viaveis.

O QUE ESTE ARQUIVO FAZ:
1. Define a arquitetura alvo de dominio, aplicacao e adapters.
2. Explica o que continua em Django e o que precisa sair dele.
3. Prioriza a primeira trilha de execucao com o que a base ja tem hoje.

PONTOS CRITICOS:
- O objetivo nao e remover Django do projeto agora; e impedir que ele continue sendo o dono do negocio.
- Models historicos, admin e migrations continuam em Django por bastante tempo durante a transicao.
-->

# Blueprint de desacoplamento de Django

## Tese

A forma inteligente de desenrolar boxcore nao e trocar de framework nem tentar arrancar o ORM do projeto de uma vez.

O caminho certo e este:

1. deixar Django como casca de entrega
2. mover regra de negocio para casos de uso e servicos puros
3. esconder ORM, admin, auth e HTTP atras de adapters
4. fazer o dominio conversar com portas, nao com `ModelForm`, `TemplateView` e `QuerySet`

Em resumo:

1. Django continua como runtime web e ORM historico
2. o negocio para de depender diretamente dele

## O que significa "nao depender do Django"

Na pratica, significa que estas decisoes deixam de morar em classes e APIs do framework:

1. validacao de regra de negocio
2. orquestracao de fluxo principal
3. decisao de integracao externa
4. montagem de payload de caso de uso
5. contrato de entrada e saida entre dominios

E passam a morar em:

1. entidades e regras puras
2. comandos e resultados explicitos
3. use cases
4. portas de repositorio e integracao
5. adapters Django que so traduzem entrada e persistencia

## O que fica em Django

Django ainda e bom e barato para manter estes blocos:

1. settings, urls e boot do projeto
2. admin interno
3. auth, sessao e permissao web
4. templates e pages server-rendered
5. models historicos e migrations enquanto houver alto risco de mover estado
6. adapters ORM temporarios

Ou seja: Django deixa de ser o core, mas continua sendo a plataforma de entrega por bastante tempo.

## Arquitetura alvo

Cada dominio deve caminhar para quatro camadas.

### 1. Domain

Camada sem Django.

Responsavel por:

1. regras invariantes
2. entidades leves do dominio
3. enums de negocio
4. regras de decisao

Nao deve importar:

1. `django.*`
2. `QuerySet`
3. `ModelForm`
4. `HttpRequest`
5. `messages`

### 2. Application

Camada sem HTTP e sem template.

Responsavel por:

1. comandos de entrada
2. resultados de saida
3. casos de uso
4. orchestration entre repositorios e integracoes

Pode conhecer:

1. portas de persistencia
2. portas de auditoria
3. portas de mensageria

Nao deve conhecer:

1. ORM concreto
2. view concreta
3. admin

### 3. Infrastructure / Django adapters

Camada que fala com Django de verdade.

Responsavel por:

1. models ORM
2. implementacao concreta de repositorios
3. adapters para auditoria
4. adapters de integracao
5. mapeamento de models para objetos de aplicacao

### 4. Delivery

Camada HTTP e interface.

Responsavel por:

1. views
2. forms HTTP
3. serializacao de request
4. mensagens de sucesso e erro
5. redirect e response

Regra:

1. entrega chama caso de uso
2. entrega nao decide regra de negocio

## Tradução para a base atual

Hoje a base ja tem um meio caminho importante:

1. existe separacao entre views, queries e services
2. existe fronteira real de `communications`, `integrations`, `access`, `auditing`, `api` e `jobs`
3. existem workflows como [boxcore/catalog/services/student_workflows.py](boxcore/catalog/services/student_workflows.py)

O problema atual e que muitos desses services ainda sao "services Django", nao "application services".

Exemplos claros:

1. [boxcore/catalog/views/student_views.py](boxcore/catalog/views/student_views.py) ainda monta o fluxo usando `FormView`, `messages`, `redirect` e models ORM diretos.
2. [boxcore/catalog/services/student_workflows.py](boxcore/catalog/services/student_workflows.py) ainda depende de `transaction`, `timezone`, enums do model e services que falam diretamente com ORM.
3. [integrations/whatsapp/services.py](integrations/whatsapp/services.py) ainda fala direto com model ORM e transacao Django.
4. varios snapshots de leitura ainda dependem diretamente de `QuerySet` e agregacoes do ORM como contrato de dominio.

## Solucao inteligente para o que ja existe

### Regra principal

Nao atacar os models primeiro.

Atacar primeiro os contratos e a orquestracao.

Motivo:

1. models historicos sao a parte mais cara e arriscada
2. o ganho arquitetural mais rapido vem de tirar o negocio de `View`, `ModelForm` e `QuerySet`
3. isso prepara uma futura API mobile e jobs sem nova explosao de acoplamento

## Padrão de transição recomendado

Cada dominio deve ser migrado neste formato:

### Etapa 1: Command e Result

Criar objetos explicitos de entrada e saida.

Exemplo conceitual:

1. `CreateStudentCommand`
2. `UpdateStudentCommand`
3. `RegisterInboundWhatsAppMessageCommand`
4. `StudentWorkflowResult`

Beneficio:

1. a regra deixa de depender de `cleaned_data` como contrato informal

### Etapa 2: Use Case puro

Criar um caso de uso por fluxo principal.

Exemplos prioritarios:

1. criar aluno rapido
2. atualizar aluno rapido
3. registrar mensagem inbound de WhatsApp
4. registrar toque operacional outbound

O caso de uso recebe:

1. command
2. repositorios por interface
3. portas auxiliares

O caso de uso devolve:

1. result simples e estavel

### Etapa 3: Repository port

Definir portas pequenas por agregado, nao um repositorio gigante.

Exemplos:

1. `StudentRepository`
2. `EnrollmentRepository`
3. `PaymentRepository`
4. `WhatsAppContactRepository`
5. `WhatsAppMessageLogRepository`

Primeiro contrato:

1. so metodos realmente usados pelo caso de uso

### Etapa 4: Django repository adapter

Implementar as portas em Django/ORM.

Exemplo:

1. `DjangoStudentRepository`
2. `DjangoWhatsAppContactRepository`

Regra:

1. aqui pode ter `select_for_update`, `QuerySet`, `transaction.atomic`, `timezone.now`
2. fora daqui, isso deve sumir aos poucos

### Etapa 5: View vira tradutora

As views passam a:

1. validar input HTTP
2. montar command
3. chamar caso de uso
4. traduzir result para template, redirect ou mensagem

Nao fazem mais:

1. abrir transacao
2. decidir regra de cobranca
3. reconciliar intake
4. registrar auditoria diretamente

## Onde começar de verdade

Se formos pragmáticos, a melhor primeira frente nao e o dominio inteiro. E um fluxo de alto valor e alto reaproveitamento.

### Primeira fatia recomendada

`student quick flow`

Arquivos de entrada hoje:

1. [boxcore/catalog/views/student_views.py](boxcore/catalog/views/student_views.py)
2. [boxcore/catalog/services/student_workflows.py](boxcore/catalog/services/student_workflows.py)
3. [boxcore/catalog/services/enrollments.py](boxcore/catalog/services/enrollments.py)
4. [boxcore/catalog/services/intakes.py](boxcore/catalog/services/intakes.py)

Por que comecar aqui:

1. e o fluxo central do produto
2. ja existe service separado da view
3. conversa com aluno, intake, matricula, pagamento e auditoria
4. se esse fluxo ficar desacoplado, a base aprende um padrao replicavel

### Como essa fatia deveria ficar

1. `students/application/commands.py`
2. `students/application/results.py`
3. `students/application/use_cases/create_student.py`
4. `students/application/use_cases/update_student.py`
5. `students/application/ports.py`
6. `students/infrastructure/django_repositories.py`
7. a view atual so monta command e exibe resultado

Observacao:

1. isso pode nascer dentro de `boxcore/catalog/` ou de um novo app `students/` em modo incremental
2. o importante e a fronteira conceitual, nao o nome da pasta no primeiro dia

## Segunda fatia recomendada

`communications + integrations whatsapp`

Arquivos de entrada hoje:

1. [integrations/whatsapp/services.py](integrations/whatsapp/services.py)
2. [integrations/whatsapp/identity.py](integrations/whatsapp/identity.py)
3. [communications/services.py](communications/services.py)
4. [communications/queries.py](communications/queries.py)

Por que vem logo depois:

1. esse dominio vai crescer para webhook real, fila, jobs e provedores
2. hoje ainda depende muito de ORM e transacao diretamente
3. e a melhor area para introduzir portas de integracao e repositorios menores

### Como deveria ficar

1. command inbound/outbound explicito
2. caso de uso de reconciliacao de canal
3. porta de repositorio para contato e log
4. porta de clock
5. porta de payload sanitizer ou adapter de provider

## O que nao fazer agora

1. tentar criar um "domain model puro" de todos os aggregates de uma vez
2. remover `ModelForm` do projeto inteiro numa tacada so
3. trocar todos os `QuerySet` por classes abstratas sem uso claro
4. abrir guerra contra Django admin
5. parar tudo para mover migrations historicas

## Meta de curto prazo

Em 2 a 4 ondas pequenas, a meta nao e ficar sem Django.

A meta e esta:

1. fluxos principais dependem de `Command -> UseCase -> Port`
2. Django vira adapter, nao dono do fluxo
3. a futura API mobile chama os mesmos casos de uso da web
4. job futuro chama os mesmos casos de uso da web
5. integracoes externas param de precisar conhecer templates e views

## Sinal de que estamos no caminho certo

Voce vai saber que a transicao esta funcionando quando:

1. um caso de uso puder ser testado sem `TestCase` de Django
2. a mesma regra puder ser chamada por view web, API e job
3. uma mudanca de UI nao exigir mudar regra comercial
4. trocar adapter de persistencia ou integracao virar viavel localmente

## Proposta objetiva de execucao

### Onda A

1. criar blueprint de `Command`, `Result` e `Port` para o fluxo de aluno rapido
2. mover `student_workflows` para um caso de uso com repositorios Django concretos
3. manter view e form atuais apenas como casca de entrada

### Onda B

1. repetir o mesmo padrao em `communications` e `integrations.whatsapp`
2. isolar reconciliacao de canal e registro de mensagem como caso de uso puro

### Onda C

1. aplicar o padrao em pagamentos e matricula
2. deixar snapshots de leitura com DTOs explicitos em vez de dicionarios soltos quando o custo compensar

### Onda D

1. so depois avaliar se parte dos models historicos merece migrar de estado
2. so depois avaliar se algum dominio merece sair parcialmente do ORM Django

## Decisao final

A solucao inteligente para o estado atual e esta:

1. nao lutar contra Django na borda
2. impedir que Django continue sendo o centro do negocio
3. usar o que a base ja tem de services e fronteiras reais para evoluir para `UseCase + Port + Adapter`

Se eu tivesse que escolher um unico primeiro corte tecnico, seria:

1. transformar o fluxo de aluno rapido no primeiro caso de uso realmente desacoplado do framework

Esse corte cria o padrao que depois reaplicamos em `communications`, `finance` e `operations` sem reescrever o produto inteiro.