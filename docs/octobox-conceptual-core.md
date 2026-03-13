<!--
ARQUIVO: documento-mae do core conceitual do OctoBox.

POR QUE ELE EXISTE:
- formaliza, em linguagem direta, que o centro do sistema nao e Django nem o app legado boxcore.
- reorganiza a leitura do produto por capacidades de dominio, casos de uso, fachadas publicas e snapshots.

O QUE ESTE ARQUIVO FAZ:
1. define o que e o core conceitual do OctoBox.
2. separa centro conceitual, casca operacional e legado historico.
3. traduz essa definicao para criterio pratico de leitura e evolucao.

PONTOS CRITICOS:
- este documento precisa continuar coerente com o codigo real; se virar slogan, perde valor.
- ele nao elimina Django do projeto; ele rebaixa Django ao papel correto.
-->

# OctoBox Conceptual Core

## Tese central

O OctoBox nao deve mais ser explicado como um conjunto de apps Django e models historicos.

Ele deve ser explicado como um sistema de capacidades de dominio, executado por casos de uso, exposto por fachadas publicas e lido por snapshots estaveis.

Em linguagem curta:

1. o centro do sistema nao e Django
2. o centro do sistema nao e boxcore
3. o centro do sistema e comportamento de negocio organizado por capacidade

## O que e core conceitual do OctoBox

O core conceitual do OctoBox e formado por quatro camadas de sentido que juntas definem o produto:

1. dominio
2. use cases
3. facades publicas
4. snapshots publicos

### Dominio

Dominio e o conjunto de regras, invariantes, estados e decisoes que definem o comportamento do produto.

Exemplos:

1. quando uma matricula pode ser ativada, cancelada ou reativada
2. como uma aula muda de estado ao longo do tempo real
3. como uma cobranca inicial nasce a partir da ficha do aluno
4. como um contato de WhatsApp e reconciliado com uma pessoa real

### Use cases

Use case e a orquestracao explicita de uma intencao do sistema.

Exemplos:

1. cadastrar aluno com intake e cobranca inicial
2. vincular pagamento a matricula ativa
3. aplicar check-in, check-out ou falta na operacao
4. processar toque operacional de comunicacao

### Facades publicas

Facade publica e a porta oficial de entrada de uma capacidade do produto.

Ela existe para que web, API, job, admin ou integracao chamem o mesmo corredor oficial sem depender do miolo inteiro.

Exemplos atuais:

1. operations/facade/workspace.py
2. operations/facade/class_grid.py
3. students/facade/student_lifecycle.py
4. communications/facade/messaging.py
5. catalog/services/

### Snapshots publicos

Snapshot publico e a leitura consolidada entregue para cima de forma estavel.

Ele permite que telas, exportacoes e visoes executivas consumam estado sem depender de QuerySet cru como lingua oficial do produto.

Exemplos atuais:

1. catalog/student_queries.py
2. catalog/finance_queries.py
3. catalog/class_grid_queries.py
4. operations/session_snapshots.py
5. dashboard/dashboard_snapshot_queries.py

## O que nao e core conceitual

As pecas abaixo sao importantes, mas nao sao o centro conceitual do sistema:

1. views Django
2. forms Django
3. urls Django
4. admin do Django
5. migrations historicas
6. models historicos enquanto representacao concreta de persistencia
7. boxcore como namespace de compatibilidade

Essas pecas podem continuar existindo. O erro seria tratá-las como a linguagem principal do produto.

## A formula oficial do projeto

A formula arquitetural oficial do OctoBox passa a ser esta:

1. capacidades de dominio definem o que o produto sabe fazer
2. use cases definem como cada intencao e executada
3. facades publicas definem por onde cada capacidade e chamada
4. snapshots publicos definem como o estado e lido para cima
5. Django entrega HTTP, admin, autenticacao, sessao e persistencia concreta

Em frase unica:

O core conceitual do OctoBox e formado por dominio, use cases, facades publicas e snapshots publicos. Django e apenas a casca operacional de entrega, autenticacao, administracao e persistencia historica.

## Como explicar o sistema a partir de agora

Em vez de dizer:

1. isso mora no app Django tal
2. isso sai do model tal
3. isso passa por uma view Django e pronto

Devemos preferir esta leitura:

1. esta capacidade pertence ao dominio de alunos, financeiro, operacao, comunicacao ou leitura executiva
2. esta intencao entra por uma facade publica ou por um service canonico
3. este comportamento e decidido por um use case ou por regra de dominio
4. esta tela consome um snapshot publico

Em outras palavras:

1. primeiro capacidade
2. depois corredor oficial
3. depois caso de uso
4. por ultimo framework e detalhe tecnico

## Capacidades de dominio do OctoBox

Hoje o produto pode ser explicado melhor pelas capacidades abaixo.

### 1. Acesso e identidade operacional

Pergunta:

1. quem esta entrando e o que essa pessoa pode operar?

Aqui entram login, papel, navegacao por papel e permissao funcional.

### 2. Jornada comercial do aluno

Pergunta:

1. como um contato vira aluno com contexto comercial e operacional coerente?

Aqui entram intake, cadastro leve, ficha comercial, vinculo com plano e transicao entre estados.

### 3. Matricula, cobranca e leitura financeira

Pergunta:

1. como o sistema cria, acompanha e interpreta receita, atraso, carteira e churn?

Aqui entram matricula, pagamento, plano, fila de cobranca, comunicacao financeira e snapshot do financeiro.

### 4. Grade e operacao ao vivo

Pergunta:

1. como o box planeja, executa e atualiza a rotina real de aulas e presencas?

Aqui entram grade, sessao, ocupacao, check-in, check-out, faltas e ocorrencias.

### 5. Comunicacao e identidade de canal

Pergunta:

1. como sinais de canal chegam, sao reconciliados e geram acao operacional correta?

Aqui entram contatos de WhatsApp, inbound, reconciliacao e toques operacionais ou financeiros.

### 6. Leitura executiva da operacao

Pergunta:

1. como o estado do box e projetado para decisao rapida e confiavel?

Aqui entram dashboard, metricas, alertas e snapshots executivos.

### 7. Auditoria e rastreabilidade

Pergunta:

1. como o sistema prova o que aconteceu e quando aconteceu?

Aqui entram eventos sensiveis, trilha administrativa e integridade de manutencao.

## O papel correto do Django

Django continua no projeto, mas em papel rebaixado e explicito.

Ele fica responsavel por:

1. urls e delivery HTTP
2. views, templates e forms como adaptadores de interface
3. admin
4. autenticacao e sessao
5. ORM e persistencia concreta
6. management commands
7. bootstrap do runtime

Isso significa:

1. Django continua sendo plataforma
2. Django deixa de ser explicacao principal do produto

## O papel correto do boxcore

boxcore tambem muda de status conceitual.

Ele deixa de ser lido como centro do sistema e passa a ser lido principalmente como:

1. app legado de estado historico do Django
2. ancora de migrations
3. superficie de compatibilidade temporaria
4. residuo estrutural ainda nao promovido

Regra de leitura:

1. primeiro ler apps reais promovidos
2. depois ler facades publicas
3. so entao consultar boxcore quando a trilha historica realmente importar

## Guardrails de linguagem arquitetural

Para manter esse centro conceitual vivo, o projeto passa a adotar estes guardrails de linguagem:

1. nao explicar fluxo novo por model Django quando a capacidade puder ser nomeada
2. nao apresentar boxcore como dono de comportamento quando ele for apenas compatibilidade
3. nao tratar QuerySet como contrato oficial do produto
4. nao explicar regra por tela quando existir use case ou snapshot oficial
5. nao deixar facade publica virar so apelido de import; ela precisa ser corredor oficial de verdade

## Como saber se o centro conceitual esta sendo respeitado

O projeto esta no caminho certo quando:

1. uma feature nova e descrita primeiro pela capacidade de dominio afetada
2. a entrada oficial dela passa por facade, service canonico ou caso de uso explicito
3. a view so traduz entrada e saida
4. a leitura de tela vem de snapshot publico
5. Django aparece como mecanismo, nao como explicacao do negocio

O projeto esta regredindo quando:

1. a regra nasce em view, form ou admin
2. a explicacao padrao volta a ser um app Django ou model historico
3. a fronteira publica depende de boxcore sem necessidade
4. QuerySet cru sobe para a camada de decisao

## Traducoes praticas para o repositorio atual

Hoje, em leitura pragmatica, a conversa arquitetural deveria ficar assim:

1. catalog organiza a jornada comercial e as leituras publicas do aluno, do financeiro e da grade
2. operations concentra a rotina operacional viva, os workspaces por papel e as actions oficiais
3. students concentra lifecycle e fluxos do aluno
4. communications concentra identidade de canal e toque operacional de mensagem
5. dashboard concentra leitura executiva consolidada
6. guide concentra a camada pedagogica interna de leitura do sistema
7. boxcore guarda estado historico, compatibilidade e residuos ainda nao promovidos

## Relacao com o predio arquitetural maior

Este documento nao substitui o modelo maior do predio do OctoBox.

Ele o aterrissa.

O predio maior explica:

1. CENTER
2. Signal Mesh
3. Scaffold Agents
4. Red Beacon
5. Vertical Sky Beam
6. Alert Siren

Este documento explica uma pergunta mais dura e mais operacional:

1. afinal, o que o projeto considera seu centro conceitual?

Resposta oficial:

1. dominio
2. use cases
3. facades publicas
4. snapshots publicos

## Regra final

Quando houver disputa entre explicar o OctoBox por framework ou por capacidade, a capacidade vence.

Quando houver disputa entre explicar o sistema por namespace historico ou por corredor oficial atual, o corredor oficial vence.

Quando houver disputa entre detalhe tecnico e sentido do produto, o sentido do produto vence.