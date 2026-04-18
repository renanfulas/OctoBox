<!--
ARQUIVO: C.O.R.D.A. do fluxo de WOD com autoria do coach e aprovacao mestre de owner ou manager.

TIPO DE DOCUMENTO:
- plano arquitetural e operacional
- trilho de execucao por ondas

AUTORIDADE:
- alta para a evolucao do editor de WOD do coach e da aprovacao operacional do box

DOCUMENTOS PAIS:
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [student-app-grade-wod-rm-corda.md](student-app-grade-wod-rm-corda.md)
- [wod-post-publication-operational-loop.md](wod-post-publication-operational-loop.md)
- [operations-workspace-views-refactor-corda.md](operations-workspace-views-refactor-corda.md)

QUANDO USAR:
- quando a duvida for como evoluir o fluxo de WOD do coach sem misturar autoria, aprovacao e publicacao
- quando precisarmos alinhar o papel de coach, manager e owner no treino do box
- quando quisermos implementar inline edit, duplicacao e aprovacao sem criar debito tecnico de permissao

POR QUE ELE EXISTE:
- evita que o WOD publicado para alunos nasca sem trilha de aprovacao
- separa autoria do treino de governanca de publicacao
- protege o app do aluno contra exibicao acidental de rascunhos
- organiza a implementacao em ondas pequenas e testaveis

O QUE ESTE ARQUIVO FAZ:
1. formaliza o contrato de autoria e aprovacao do WOD
2. define estados, permissoes e eventos minimos
3. lista riscos e esquecimentos que poderiam virar debito tecnico
4. organiza a execucao por ondas com checks objetivos

PONTOS CRITICOS:
- `is_published` sozinho nao e suficiente para representar o ciclo de vida do WOD
- duplicacao nao pode copiar trilha de aprovacao antiga
- o app do aluno so deve enxergar WOD em estado oficial de publicacao
- aprovacao unica precisa funcionar mesmo em box sem manager
-->

# C.O.R.D.A. - Coach monta o WOD, owner ou manager aprovam

## C - Contexto

O OctoBox ja possui uma base funcional importante para a trilha de treino:

1. `SessionWorkout`
2. `SessionWorkoutBlock`
3. `SessionWorkoutMovement`
4. tela operacional minima do coach para montar o WOD
5. app do aluno capaz de renderizar o WOD publicado do dia
6. recomendacao de carga por `% RM` quando existe `StudentExerciseMax`

Hoje, porem, ainda existe uma simplificacao que serve para o prototipo, mas nao serve bem para governanca operacional:

1. o modelo usa `is_published`
2. o coach consegue montar o treino
3. ainda nao existe uma fronteira clara entre `rascunho`, `treino aguardando aprovacao` e `treino oficial do box`

Na pratica, isso cria uma pergunta de produto e arquitetura:

1. como deixar o coach com velocidade para montar treino?
2. como impedir que qualquer ajuste dele ja entre no app do aluno sem filtro?
3. como permitir boxes pequenos sem manager operarem normalmente?

### Tese de produto

O coach deve ser o autor do treino.

O owner ou manager devem ser a aprovacao mestre.

Em linguagem simples:

1. o coach escreve a receita
2. o owner ou manager provam
3. so depois o prato vai para a mesa do aluno

### Tese de arquitetura

O fluxo de WOD precisa separar tres coisas que parecem proximas, mas sao diferentes:

1. autoria
2. aprovacao
3. publicacao

Se essas tres camadas ficarem espremidas em um unico booleano ou em um unico botao:

1. a permissao fica turva
2. a auditoria fica fraca
3. o debug fica caro
4. o app do aluno pode consumir estado errado

## O - Objetivo

Construir a proxima fase do editor de WOD para que:

1. o coach possa editar o treino com velocidade real
2. blocos e movimentos possam ser editados inline
3. um WOD possa ser duplicado para outra aula
4. a publicacao para alunos dependa de aprovacao unica de `owner` ou `manager`
5. o app do aluno enxergue apenas versoes oficiais
6. a trilha inteira fique auditavel e previsivel

### Sucesso significa

1. o coach monta e envia sem entrar no admin bruto
2. o manager ou owner aprovam com um clique consciente
3. o aluno nunca ve rascunho sem querer
4. o codigo nao mistura permissao de coach com permissao de publicacao
5. a duplicacao acelera o dia a dia sem copiar lixo de governanca

## R - Riscos

### 1. Risco de `is_published` virar um semaforo de brinquedo

Se mantivermos tudo em `True` ou `False`:

1. nao sabemos se o treino esta em rascunho
2. nao sabemos se ja foi enviado para aprovacao
3. nao sabemos quem aprovou
4. nao sabemos se houve rejeicao

### 2. Risco de o coach publicar sem trilha

Se o coach puder mudar o treino e isso ja refletir no app do aluno:

1. perdemos governanca
2. o box pode reclamar de treino errado no ar
3. fica dificil reconstruir o que aconteceu

### 3. Risco de duplicacao copiar mais do que deveria

Ao duplicar um WOD, nao podemos copiar:

1. aprovador antigo
2. horario de aprovacao antigo
3. estado final antigo
4. motivo de rejeicao antigo

Se copiar isso, o novo treino nasce com identidade falsa.

### 4. Risco de manager e owner nao terem a mesma leitura do fluxo

Se a UI nao deixar claro o que esta sendo aprovado:

1. o aprovador vira um clicador de botao
2. aumenta o risco de publicar treino incompleto
3. o processo vira teatro de governanca

### 5. Risco de sobrescrever publicacao ativa sem protecao

Se o coach altera um WOD ja publicado:

1. precisamos decidir se a edicao volta para `draft`
2. ou se nasce uma nova versao pendente

Se isso nao for decidido, o sistema pode mostrar mudanca parcial para o aluno.

### 6. Risco de esquecimento de ownership por box

Mesmo sem multiunidade completa na interface, o contrato precisa assumir que:

1. aprovacao e publicacao pertencem ao box
2. o aprovador so deve aprovar treino do box que controla

### 7. Risco de app do aluno continuar lendo o campo errado

Quando o modelo migrar de `is_published` para `status`:

1. qualquer query antiga pode continuar olhando para o booleano
2. isso gera regressao silenciosa

## D - Direcao

### Tese central

Evoluir o fluxo atual sem reescrever a base, trocando o booleano de publicacao por um ciclo de vida pequeno, claro e auditavel.

### Regra-mestra

1. `coach` cria e edita
2. `coach` envia para aprovacao
3. `owner` ou `manager` aprovam sozinhos
4. so estado `published` aparece para o aluno

### Estado oficial do WOD

Substituir `is_published` por um status explicito.

Estados minimos:

1. `draft`
2. `pending_approval`
3. `published`
4. `rejected`

Observacao:

`approved` separado de `published` so vale a pena se existir uma janela de publicacao posterior. Como o objetivo atual e aprovacao mestre simples, `published` ja incorpora a aprovacao.

### Regras de transicao

#### `draft -> pending_approval`

Quando:

1. o coach envia para aprovacao

Contrato:

1. grava `submitted_by`
2. grava `submitted_at`
3. limpa `rejection_reason`

#### `pending_approval -> published`

Quando:

1. owner ou manager aprovam

Contrato:

1. grava `approved_by`
2. grava `approved_at`
3. publica para leitura do aluno

#### `pending_approval -> rejected`

Quando:

1. owner ou manager rejeitam

Contrato:

1. grava `rejected_by`
2. grava `rejected_at`
3. grava `rejection_reason`
4. impede exibicao ao aluno

#### `rejected -> draft`

Quando:

1. coach volta a editar para corrigir

Contrato:

1. mantem historico de rejeicao
2. reabre o trabalho sem reaproveitar aprovacao antiga

#### `published -> draft`

Quando:

1. coach edita o treino ja publicado

Contrato recomendado:

1. a mudanca nova nao entra no ar imediatamente
2. o treino volta para `draft`
3. precisa de nova aprovacao para republicar

Analogia:

o cardapio ja impresso continua valendo ate a cozinha mandar uma versao revisada e o gerente autorizar de novo.

### Permissoes oficiais

#### Coach

Pode:

1. criar WOD
2. editar cabecalho
3. editar bloco inline
4. editar movimento inline
5. deletar bloco
6. deletar movimento
7. duplicar WOD para outra aula
8. enviar para aprovacao

Nao pode:

1. publicar para aluno
2. aprovar o proprio WOD
3. rejeitar com efeito oficial

#### Manager

Pode:

1. revisar WOD pendente
2. aprovar
3. rejeitar
4. visualizar historico minimo da submissao

#### Owner

Pode:

1. tudo que o manager pode no fluxo de aprovacao
2. agir como aprovador unico em box sem manager

### Contrato minimo de dados

Adicionar em `SessionWorkout`:

1. `status`
2. `created_by`
3. `submitted_by`
4. `submitted_at`
5. `approved_by`
6. `approved_at`
7. `rejected_by`
8. `rejected_at`
9. `rejection_reason`
10. `version`

#### Por que `version` entra agora

Mesmo que o diff visual venha depois, `version` ja prepara:

1. auditoria
2. logs claros
3. invalida cache de leitura
4. comparacao futura de revisoes

### Contrato minimo de leitura do app do aluno

O app do aluno deve ler somente:

1. WOD do `active_box`
2. WOD da aula certa
3. WOD com status `published`

Nao deve ler:

1. `draft`
2. `pending_approval`
3. `rejected`

### Contrato de duplicacao

Duplicar WOD deve copiar:

1. titulo
2. coach_notes
3. blocos
4. movimentos
5. ordem de blocos e movimentos

Duplicar WOD nao deve copiar:

1. status anterior
2. aprovador anterior
3. timestamps de aprovacao
4. motivo de rejeicao
5. versao anterior

Resultado oficial da duplicacao:

1. o novo WOD nasce em `draft`
2. com `version = 1`
3. sem aprovacao

### Contrato de edicao inline

Editar inline significa:

1. alterar dados de bloco e movimento na propria tela
2. reduzir voltas de formulario
3. preservar validacao do backend

Nao significa:

1. deixar estado inconsistente no frontend
2. aceitar mutacao sem feedback
3. salvar parcialmente sem contrato claro

Recomendacao tecnica:

1. manter POSTs pequenos por intencao
2. usar intents explicitas
3. so considerar AJAX/HTMX depois que o contrato funcional estiver estavel

Isso evita um frontend mais bonito do que seguro.

## A - Arquitetura-alvo

### 1. Dominio

`student_app.models.SessionWorkout` continua sendo a verdade do treino da aula nesta fase.

Responsabilidades:

1. guardar o ciclo de vida do WOD
2. guardar autoria e aprovacao
3. guardar a estrutura do treino

Nao entra agora:

1. versionamento historico completo por tabela separada
2. branching de treino
3. biblioteca global de templates de WOD

### 2. Nivel 1 de acesso externo

#### Coach corridor

Continuar em `operations/workspace_views.py` ou mover para modulo dedicado quando crescer mais.

Responsavel por:

1. editor do coach
2. intents de salvar
3. duplicacao
4. envio para aprovacao

#### Manager and owner corridor

Criar uma board curta de aprovacao operacional.

Responsavel por:

1. listar WODs pendentes
2. revisar resumo
3. aprovar ou rejeitar

### 3. Center Layer recomendado

Mesmo que a primeira entrega possa nascer direto na camada HTTP, a direcao correta e preparar comandos claros para:

1. `save_session_workout_draft`
2. `submit_session_workout_for_approval`
3. `approve_session_workout`
4. `reject_session_workout`
5. `duplicate_session_workout`

Motivo:

isso reduz risco de logica de permissao ficar espalhada entre views.

### 4. Auditoria

Cada transicao relevante deve deixar trilha:

1. rascunho criado
2. enviado para aprovacao
3. aprovado
4. rejeitado
5. duplicado

Payload minimo recomendado:

1. `session_id`
2. `workout_id`
3. `box_id` quando aplicavel
4. `actor_id`
5. `from_status`
6. `to_status`
7. `version`

### 5. UI minima por papel

#### Coach

Precisa ver:

1. status atual
2. versao atual
3. ultima decisao
4. motivo da rejeicao, quando houver
5. CTA claro de `Enviar para aprovacao`
6. CTA de `Duplicar WOD`

#### Manager/Owner

Precisa ver:

1. fila de WODs pendentes
2. aula
3. coach autor
4. quando foi enviado
5. resumo do treino
6. aprovar
7. rejeitar com motivo

## Esquecimentos provaveis que vale amarrar agora

### 1. Quem pode editar depois de enviado para aprovacao?

Regra recomendada:

1. `pending_approval` nao deve ser editavel livremente
2. se o coach quiser mudar, o sistema deve devolver para `draft`

### 2. O que acontece com treino ja publicado se uma nova versao esta em rascunho?

Regra recomendada:

1. o aluno continua vendo a ultima versao `published`
2. a nova revisao fica invisivel ate nova aprovacao

Observacao:

essa regra e a mais segura, mas pode exigir historico de snapshot publicado numa fase seguinte.

Para a fase atual, como o modelo ainda e simples, a recomendacao pragmatica e:

1. bloquear edicao destrutiva de WOD `published`
2. ou converter para `draft` assumindo que o treino sai do ar ate nova aprovacao

Escolha mais barata nesta fase:

1. converter para `draft`
2. avisar o time que uma edicao em treino publicado retira ele do ar ate nova aprovacao

### 3. Pode existir aula sem coach definido?

Se sim:

1. owner ou manager ainda podem aprovar
2. mas a autoria inicial do WOD precisa continuar clara

### 4. Rejeicao precisa obrigar motivo?

Recomendacao:

1. sim
2. sem motivo, a rejeicao vira porta batendo sem explicar por que

### 5. Duplicar para qual escopo?

Nesta fase:

1. duplicar apenas para outra `ClassSession`
2. do mesmo box

Nao fazer ainda:

1. biblioteca global entre boxes
2. clonagem em massa

### 6. O que acontece se owner e manager aprovarem ao mesmo tempo?

Mesmo com baixa chance, o contrato precisa ser idempotente:

1. so a primeira aprovacao muda o estado
2. a segunda recebe retorno neutro

### 7. Quais testes sobem obrigatoriamente?

1. coach nao publica diretamente
2. owner publica
3. manager publica
4. rejeicao exige motivo
5. duplicacao nasce em `draft`
6. app do aluno ignora `draft`
7. app do aluno ignora `pending_approval`
8. edicao de WOD publicado pede nova aprovacao

## Acoes por ondas

### Onda 1 - Fundacao de estado e permissao

Objetivo:

1. trocar `is_published` por `status`
2. incluir trilha minima de autoria e aprovacao
3. ajustar queries do aluno para ler so `published`

Entregas:

1. migration de `SessionWorkout`
2. enums de status
3. adaptacao do editor atual
4. testes de leitura do aluno

Check de pronto:

1. nenhum caminho do aluno depende mais de `is_published`
2. coach nao consegue mais publicar direto

### Onda 2 - Ergonomia do coach

Objetivo:

1. acelerar montagem do treino

Entregas:

1. edicao inline de blocos
2. edicao inline de movimentos
3. feedback visual de status
4. CTA de enviar para aprovacao

Check de pronto:

1. coach monta um treino completo sem fluxo quebrado
2. `pending_approval` fica visivel e claro

### Onda 3 - Duplicacao segura

Objetivo:

1. acelerar reaproveitamento sem copiar governanca errada

Entregas:

1. duplicar WOD para outra aula
2. reset de status e trilhas
3. testes de copia estrutural

Check de pronto:

1. estrutura copia corretamente
2. governanca antiga nao vaza

### Onda 4 - Board de aprovacao mestre

Objetivo:

1. criar o corredor curto de aprovacao para owner e manager

Entregas:

1. lista de WODs pendentes
2. aprovacao por owner
3. aprovacao por manager
4. rejeicao com motivo obrigatorio

Check de pronto:

1. boxes sem manager continuam operando
2. boxes com manager ganham fila clara de aprovacao

### Onda 5 - Auditoria e endurecimento

Objetivo:

1. fechar a malha de rastreabilidade

Entregas:

1. eventos de auditoria
2. idempotencia de aprovacao
3. mensagens de erro e estado
4. smoke manual por papel

Check de pronto:

1. conseguimos responder quem criou, quem enviou, quem aprovou e quando

## Fora do escopo agora

1. dupla aprovacao
2. biblioteca global de templates
3. historico completo de diffs entre versoes
4. publicacao agendada
5. aprovacao multi-etapa
6. WOD compartilhado entre boxes

## Decisao executiva recomendada

Fazer agora:

1. status explicito
2. aprovacao unica de owner ou manager
3. edicao inline
4. duplicacao segura
5. board curta de aprovacao

Nao fazer agora:

1. sistema complexo de workflow
2. versionamento historico pesado
3. governanca teatral que desacelera box pequeno

## Resumo em linguagem simples

Hoje o sistema ja tem o caderno e o lapis.

O que falta agora e:

1. deixar o coach escrever mais rapido
2. deixar o manager ou owner carimbar
3. garantir que o aluno so veja o que ja recebeu carimbo oficial

Esse plano e barato porque mexe no corredor certo sem derrubar o predio.
