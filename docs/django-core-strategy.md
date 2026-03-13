<!--
ARQUIVO: estrategia operacional para fazer o negocio parar de depender de Django como core.

POR QUE ELE EXISTE:
- Traduz a ambicao de "Django fora do core" em trilha pratica, incremental e verificavel.
- Evita que a decisao vire uma abstracao bonita sem impacto real no codigo.

O QUE ESTE ARQUIVO FAZ:
1. Define a meta tecnica real da transicao.
2. Explica as estrategias que o projeto vai usar.
3. Organiza a execucao por ondas, guardrails e criterios de pronto.

PONTOS CRITICOS:
- O objetivo nao e remover Django do projeto agora.
- O objetivo e fazer Django deixar de ser dono da regra de negocio, do contrato de fluxo e da orquestracao central.
-->

# Estrategia para Django deixar de ser o core

## Tese central

O OctoBox nao vai deixar de depender de Django trocando framework.

Vai deixar de depender de Django quando estas tres coisas forem verdadeiras:

1. a regra de negocio principal morar em camadas puras e estaveis
2. os fluxos principais do produto puderem ser chamados por web, API, job ou integracao sem reescrever regra
3. Django ficar restrito a entrega, persistencia historica e adaptadores concretos

Em linguagem direta:

1. Django continua como plataforma
2. Django deixa de ser o cerebro

## Meta tecnica real

O alvo nao e este:

- apagar models Django
- remover admin
- abandonar templates
- reescrever o produto como microservicos

O alvo e este:

- o core de decisao nao importar `django.*`
- os contratos dos fluxos nao dependerem de `HttpRequest`, `ModelForm`, `QuerySet` ou `messages`
- os casos de uso poderem ser reutilizados fora da web server-rendered
- a persistencia concreta ficar atras de portas pequenas

## O que ja existe hoje

O projeto ja abriu a trilha certa em varios pontos:

1. `students/application/*` ja concentra commands, results, ports e use cases
2. `communications/application/*` ja separa casos de uso das implementacoes concretas
3. `operations/application/*` ja concentra policy, dispatcher e casos de uso operacionais
4. `students/infrastructure/*`, `communications/infrastructure/*` e `operations/infrastructure/*` ja funcionam como adapters Django
5. o runtime HTTP ja comecou a sair de `boxcore`

Ou seja:

1. a base nao vai comecar do zero
2. a estrategia agora e consolidar padrao, reduzir vazamentos e ampliar cobertura

## Estrategias que vamos usar

## 1. Command e Result como contrato oficial de fluxo

Todo fluxo principal deve nascer e terminar por objetos explicitos.

Entradas:

1. command de caso de uso
2. tipos simples, enums de negocio e ids explicitos

Saidas:

1. result estavel
2. records simples e serializaveis

Nao usar como contrato de fluxo:

1. `cleaned_data`
2. `request.POST`
3. `QuerySet`
4. instancia ORM como saida publica da aplicacao

Regra:

1. view, API, job e webhook montam command
2. view, API, job e webhook traduzem result

## 2. Use case puro para orquestracao

Toda orquestracao que decide negocio deve ficar em `application/use_cases.py` ou modulo equivalente.

Essa camada pode:

1. coordenar portas
2. decidir sequencia do fluxo
3. validar precondicoes de negocio
4. devolver resultado final do caso de uso

Essa camada nao pode:

1. abrir transacao Django diretamente
2. consultar `Model.objects` diretamente
3. usar `messages`, `redirect`, `render` ou `HttpResponse`

## 3. Portas pequenas e orientadas ao fluxo

O projeto nao deve criar um mega repositorio generico por dominio.

Deve criar portas pequenas, focadas no fluxo real.

Exemplos corretos:

1. `StudentWriterPort`
2. `StudentQuickAuditPort`
3. `InboundWhatsAppMessagePort`
4. `OperationalQueueSnapshotPort`
5. `UnitOfWorkPort`

Regra:

1. cada porta existe porque um caso de uso precisa dela
2. a porta nao e criada para satisfazer pureza academica

## 4. Django restrito a adapter e delivery

Tudo o que for concreto de framework deve ficar em dois lugares:

1. `infrastructure/`
2. casca HTTP, admin, management command, API ou job

Pode usar Django livremente:

1. `transaction.atomic`
2. `QuerySet`
3. ORM concreto
4. `timezone`
5. `messages`
6. `HttpRequest`

Mas so abaixo da fronteira de aplicacao.

## 5. Read side separado do write side

O projeto ja tem um bom inicio com queries e snapshots.

Vamos manter esta regra:

1. leituras para tela podem continuar usando ORM
2. mas o contrato entregue para cima deve ser snapshot, DTO ou estrutura simples
3. a view nao deve montar regra sensivel em cima de `QuerySet` cru

Em outras palavras:

1. QuerySet pode continuar existindo
2. QuerySet nao pode virar lingua oficial do negocio

## 6. Politicas e regras puras saem antes dos models

O erro comum seria atacar models primeiro.

Nao vamos por esse caminho.

Vamos mover antes:

1. policy
2. templates de mensagem
3. regras de decisao
4. validacoes invariantes
5. montagem de comandos e resultados

Motivo:

1. isso reduz dependencia real de Django com risco muito menor
2. prepara API, jobs e integracoes antes de encostar no estado historico

## 7. Entradas diferentes devem chamar o mesmo core

Quando um fluxo existir em mais de uma interface, a regra deve ser unica.

Exemplos-alvo:

1. web interna chama o mesmo caso de uso que a futura API
2. job chama o mesmo caso de uso que a acao manual
3. webhook chama o mesmo core que um processamento posterior de reprocessamento

Se cada interface tiver sua propria regra, Django continua sendo o core na pratica.

## 8. Teste do core sem precisar subir a casca web

Toda vez que um caso de uso for promovido de verdade, ele deve ganhar teste com dependencias fake ou stub.

Sinal de maturidade:

1. testar fluxo de negocio sem request HTTP
2. testar sem template
3. testar com fake port quando fizer sentido

Nao precisamos eliminar teste com banco.

Precisamos parar de depender so dele para validar regra.

## Guardrails arquiteturais

Para nao regredir, vamos adotar estas regras.

### Em `application/` e `domain/`

Nao pode entrar:

1. `django.*`
2. `Model`
3. `QuerySet`
4. `HttpRequest`
5. `messages`
6. `redirect`, `render`, `reverse`

### Em `infrastructure/`

Pode entrar:

1. ORM
2. transacao
3. models historicos
4. auditoria concreta
5. chamadas de integracao concreta

Mas esta camada nao deve decidir regra central sozinha.

### Em `views`, `admin`, `commands`, `api` e `jobs`

Regra:

1. traduzir entrada
2. chamar caso de uso
3. traduzir saida

## Ondas de execucao

## Onda A: blindar a camada de aplicacao que ja existe

Objetivo:

1. transformar o que hoje e padrao parcial em regra oficial

Entregas:

1. revisar `students/application/*`, `communications/application/*`, `operations/application/*` e `finance/application/*`
2. remover vazamentos de framework da camada de aplicacao
3. explicitar guardrails na documentacao

Resultado esperado:

1. o projeto passa a ter um nucleo de aplicacao confiavel e repetivel

## Onda B: extrair regras puras para `domain/`

Objetivo:

1. separar orquestracao de aplicacao das regras invariantes e politicas puras

Entradas candidatas:

1. regras comerciais de aluno e matricula
2. politicas de grade e agenda
3. montagem de mensagens operacionais
4. reconciliacao de identidade de canal

Resultado esperado:

1. `application` orquestra
2. `domain` decide

## Onda C: unificar pontos de entrada no mesmo core

Objetivo:

1. fazer web, API, integracoes e jobs chamarem o mesmo fluxo central

Entregas:

1. views HTTP viram tradutoras finas
2. management commands deixam de embutir regra de negocio
3. jobs futuros nascem chamando use cases existentes
4. API nova nasce como casca sobre os mesmos contracts

Resultado esperado:

1. trocar interface nao exige reescrever negocio

## Onda D: isolar servicos tecnicos transversais

Objetivo:

1. tirar dependencias tecnicas difusas do core

Portas candidatas:

1. clock
2. audit logger
3. unit of work
4. idempotency checker
5. channel identity resolver

Resultado esperado:

1. o core conhece comportamento, nao implementacao concreta

## Onda E: discutir split real de state

So depois das ondas anteriores.

Motivo:

1. antes disso, atacar app label e migrations seria operar identidade formal sem precisar
2. depois disso, a migracao de estado passa a ter beneficio real e fronteira bem definida

## Prioridade por dominio

### 1. Students

Motivo:

1. ja tem o melhor embriao de commands, ports, results e use cases
2. conecta intake, matricula, pagamento e auditoria
3. serve como padrao para o resto do projeto

### 2. Communications

Motivo:

1. sera a fronteira mais pressionada por webhook, provedores, automacao e jobs
2. precisa aprender a falar com integracao sem deixar ORM virar lingua do fluxo

### 3. Operations

Motivo:

1. ja tem policy e dispatcher fora da view
2. pode consolidar bastante regra pura de operacao

### 4. Finance

Motivo:

1. precisa evoluir com mais cuidado porque toca historico, cobranca e agenda de pagamento
2. deve herdar padroes dos dominios anteriores antes de expandir

## Criterio de pronto para dizer que Django saiu do core de um fluxo

Um fluxo so pode ser considerado desacoplado quando:

1. existe command e result explicitos
2. existe use case reutilizavel
3. existe porta pequena para persistencia ou servico tecnico
4. a view ou integracao apenas traduz entrada e saida
5. a regra principal do fluxo nao importa `django.*`
6. o fluxo pode ser chamado por outro entrypoint sem duplicar regra

## O que nao vamos fazer

1. reescrever tudo para FastAPI ou outro framework so para parecer moderno
2. quebrar models historicos cedo demais
3. inventar microservicos
4. criar repositorios gigantes e abstracoes vazias
5. transformar o projeto em arquitetura academicamente bonita e operacionalmente pior

## Proximo passo pratico

Nos proximos ciclos, a trilha recomendada e esta:

1. revisar e endurecer os limites de `application` nos dominios ja iniciados
2. escolher um fluxo de `communications` para promover de adapter Django para caso de uso mais puro
3. criar a primeira extracao explicita de regra pura para `domain/`
4. so depois expandir esse padrao para novas interfaces como API e jobs

## Formula de leitura daqui para frente

Sempre que surgir uma feature nova, a pergunta nao sera:

- em qual view Django isso entra?

Vai ser esta:

1. qual e o command?
2. qual e o result?
3. qual e o use case?
4. quais portas esse fluxo precisa?
5. qual adapter Django vai atender essas portas?

Quando essa for a pergunta padrao do time, Django tera deixado de ser o core na pratica.