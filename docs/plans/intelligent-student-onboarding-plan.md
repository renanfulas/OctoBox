<!--
ARQUIVO: plano executivo do onboarding inteligente do aluno com identidade social, autocadastro guiado, intencao comercial e fundacao de inteligencia operacional.

TIPO DE DOCUMENTO:
- plano de execucao de produto + arquitetura + backend + UX + dados
- PRD operacional
- ADR consolidado

AUTORIDADE:
- alta para a evolucao do onboarding do aluno

DOCUMENTOS PAIS:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)
- [../architecture/operational-intelligence-ml-layer.md](../architecture/operational-intelligence-ml-layer.md)
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)

QUANDO USAR:
- quando a tarefa envolver convite do aluno, OAuth/Apple, autocadastro, primeira entrada no app, captacao de plano ou telemetria do onboarding
- quando precisarmos decidir a ordem certa de implementacao sem contaminar o core transacional com ML precoce
- quando quisermos alinhar produto, arquitetura e backlog do onboarding inteligente em uma unica referencia

POR QUE ELE EXISTE:
- evita que a visao do onboarding inteligente vire conversa solta sem trilho de execucao
- transforma a ideia de autocadastro e personalizacao em arquitetura segura, auditavel e incremental
- prepara o sistema para telemetria e inteligencia operacional sem confundir inferencia com verdade primaria

O QUE ESTE ARQUIVO FAZ:
1. define o problema e a oportunidade de produto do onboarding inteligente
2. formaliza a jornada alvo do aluno tela por tela
3. registra as decisoes arquiteturais principais em formato de ADR
4. organiza o plano tecnico por ownership real de arquivos
5. ordena a execucao em ondas pequenas, validaveis e de baixo risco

PONTOS CRITICOS:
- o convite contextualiza o box; OAuth/Apple prova identidade
- o email autenticado pode virar email canonico, mas a troca precisa ser auditavel
- onboarding nao deve ser confundido com matricula automatica
- ML observa, prioriza e recomenda; nao escreve verdade primaria
- dados sensiveis exigem necessidade real, acesso restrito e governanca forte
-->

# Plano - Intelligent Student Onboarding

## 1. Resumo executivo

O OctoBox tem uma oportunidade clara de mercado:

1. transformar onboarding de aluno em um corredor inteligente
2. reduzir digitacao manual da recepcao
3. elevar a qualidade do cadastro
4. capturar intencao comercial de forma estruturada
5. iniciar uma base de sinais comportamentais para personalizacao futura

Em linguagem curta:

1. o convite deixa de ser so um link
2. a autenticacao social deixa de ser so login
3. a primeira entrada vira autocadastro guiado
4. o sistema passa a enxergar o aluno como jornada, nao como formulario

## 2. C.O.R.D.A.

## C - Contexto

Hoje o runtime ja possui:

1. `StudentAppInvitation` para convites do app do aluno
2. `StudentIdentity` para identidade social separada da conta staff
3. callback OAuth para `Google` e `Apple`
4. `StudentBoxMembership` com estados formais
5. tela operacional de convites em `student_identity`
6. PWA do aluno com contexto de box e shell proprio

Hoje o gargalo principal ainda e este:

1. convite ainda conversa com e-mail manual demais
2. a primeira entrada ainda nao fecha um autocadastro completo
3. plano e dia preferido de pagamento ainda nao entram como intencao estruturada
4. nao existe uma camada formal de telemetria do onboarding
5. ainda nao existe fundacao consistente para personalizacao e ML do onboarding

## O - Objetivo

Implementar um onboarding inteligente do aluno com:

1. convite como porta de entrada do box
2. autenticacao social como prova de identidade
3. e-mail autenticado como referencia canonica atual
4. wizard de primeira entrada com autocadastro guiado
5. intencao comercial para plano e dia preferido de pagamento
6. telemetria pronta para inteligencia operacional

Sucesso significa:

1. o aluno consegue finalizar a maior parte da jornada sem ajuda humana
2. a recepcao so entra em excecoes reais
3. o sistema sabe exatamente em qual etapa o aluno esta
4. o cadastro final do aluno fica mais limpo que o cadastro importado
5. os sinais ja nascem prontos para analytics e modelos futuros

## R - Riscos

### 1. Risco de automatizar demais cedo demais

Se o sistema transformar selecao de plano em matricula e cobranca automatica logo no v1:

1. aumenta risco de erro comercial
2. aumenta atrito operacional para estorno e correcao
3. mistura onboarding com financeiro sensivel cedo demais

### 2. Risco de tratar inferencia como verdade

Se score futuro entrar no core transacional:

1. o sistema fica opaco
2. a operacao perde rastreabilidade
3. ML vira fonte de erro silencioso

### 3. Risco de trocar email sem trilha

Se o e-mail autenticado substituir o e-mail anterior sem auditoria:

1. suporte fica cego
2. reconciliacao futura fica fraca
3. troubleshooting fica mais caro

### 4. Risco de wizard longo demais

Se a primeira entrada exigir dados demais:

1. cai conversao
2. aumenta abandono
3. o ganho de automacao pode virar perda de ativacao

### 5. Risco de usar dados sensiveis para marketing precoce

Se CPF, saude ou sinais intimos entrarem em segmentacao agressiva:

1. cresce risco de LGPD
2. cresce risco reputacional
3. a vantagem competitiva vira fragilidade institucional

## D - Direcao

### Tese central

O onboarding inteligente do aluno deve obedecer esta ordem:

1. `invite` define contexto do box
2. `OAuth/Apple` prova identidade
3. `identity confirmation` limpa a transicao do cadastro importado para o cadastro autenticado
4. `profile onboarding` fecha o minimo operacional
5. `commercial intent` captura o interesse sem acionar financeiro pesado cedo demais
6. `telemetry` mede comportamento
7. `intelligence layer` recomenda e prioriza acima do core

### Frases de arquitetura

1. `Invite decide o corredor; OAuth decide quem entrou no corredor.`
2. `Onboarding fecha o cadastro; nao substitui a verdade financeira.`
3. `Intencao comercial prepara a venda; nao equivale a matricula automatica por padrao.`
4. `ML observa e recomenda; nao escreve verdade primaria.`
5. `Dado sensivel so entra quando a necessidade de negocio for clara e governada.`

## A - Acoes

1. remover o campo manual de e-mail do convite operacional
2. atualizar a regra de autenticacao para consolidar e-mail autenticado com auditoria
3. introduzir um estado formal de onboarding
4. criar o wizard de primeira entrada no `student_app`
5. introduzir uma camada de `commercial intent`
6. criar telemetria de onboarding e engajamento inicial
7. so depois disso subir heuristicas e modelos simples de score

## 3. PRD

## 3.1 Problema

Sistemas tradicionais de mercado ainda tratam onboarding como cadastro burocratico:

1. alguem importa uma lista
2. alguem liga ou manda mensagem
3. alguem corrige email, nome, telefone e plano manualmente
4. o sistema registra tarde e aprende pouco

Isso gera:

1. alto custo operacional
2. baixa qualidade de dado
3. baixa velocidade de ativacao
4. baixa fundacao para personalizacao futura

## 3.2 Oportunidade

O OctoBox pode tratar onboarding como produto:

1. mais autonomo
2. mais auditavel
3. mais rapido
4. mais preparado para segmentacao e personalizacao

## 3.3 Publico alvo

### Primario

1. alunos importados de listas externas
2. alunos convidados pelo box
3. alunos novos com identidade social validada

### Secundario

1. recepcao
2. owner
3. manager

## 3.4 Objetivos de negocio

1. reduzir trabalho manual de cadastro
2. aumentar taxa de conclusao do onboarding
3. aumentar taxa de ativacao do app
4. capturar intencao comercial de forma estruturada
5. construir base confiavel para personalizacao futura

## 3.5 Metricas de sucesso

### Produto

1. taxa de abertura de convite
2. taxa de autenticacao social
3. taxa de conclusao do onboarding
4. tempo medio entre convite e conclusao
5. abandono por etapa
6. taxa de selecao de plano
7. taxa de selecao de dia preferido de pagamento

### Operacao

1. cadastros finalizados sem intervencao humana
2. quantidade de excecoes por 100 convites
3. tempo economizado pela recepcao

### Dados

1. percentual de alunos com email autenticado canonico
2. percentual de alunos com perfil essencial completo
3. qualidade de reconciliacao entre nome/telefone importado e confirmado

## 3.6 Escopo funcional

### Entram no escopo

1. convite como entrada do fluxo
2. login social com `Google` e `Apple`
3. consolidacao de e-mail autenticado
4. wizard de primeira entrada
5. perfil essencial e complementar
6. intencao comercial de plano e dia preferido de pagamento
7. telemetria do onboarding

### Nao entram no primeiro corte

1. cobranca automatica sem revisao
2. uso de ML para decisao transacional
3. marketing automatizado agressivo em dados sensiveis
4. recomendacao de precificacao individual

## 3.7 Jornada tela por tela

### Tela 1 - Invite Landing

Objetivo:

1. contextualizar o box
2. reduzir ruido
3. levar para autenticacao

Campos:

1. nenhum campo de digitacao obrigatoria

CTAs:

1. `Continuar com Google`
2. `Continuar com Apple`

### Tela 2 - Callback / Identity Proof

Objetivo:

1. provar identidade
2. capturar e-mail autenticado e verificado

Resultado esperado:

1. `StudentIdentity` atualizado ou criado
2. trilha de auditoria registrada

### Tela 3 - Confirmacao de identidade

Objetivo:

1. limpar a diferenca entre cadastro importado e dado autenticado

Campos:

1. nome completo
2. WhatsApp
3. e-mail autenticado

### Tela 4 - Perfil essencial

Campos obrigatorios:

1. nome completo
2. WhatsApp
3. genero
4. data de nascimento

### Tela 5 - Perfil complementar

Campos opcionais:

1. CPF
2. observacoes de saude

### Tela 6 - Intencao comercial

Campos:

1. plano desejado
2. dia preferido de pagamento: `1`, `6`, `15`, `21`

### Tela 7 - Conclusao

Saidas:

1. `onboarding_completed`
2. `commercial_intent_created`
3. status final do acesso

## 4. ADR consolidado

## ADR 1 - O convite deixa de depender de email digitado manualmente

### Decisao

O fluxo operacional de convite do aluno deve remover o campo manual de e-mail e usar:

1. o e-mail ja cadastrado do aluno quando existir
2. a autenticacao social como fonte do e-mail canonico quando o cadastro inicial estiver incompleto

### Motivo

1. reduz erro humano
2. reduz divergencia entre convite e identidade autenticada
3. simplifica a operacao

### Trade-off

1. alunos antigos sem e-mail claro exigem fluxo de excecao mais bem tratado

## ADR 2 - O email autenticado vira o email canonico atual, com auditoria

### Decisao

O e-mail retornado por `Google` ou `Apple`, quando verificado e aceito pela regra do fluxo, passa a ser o e-mail canonico atual do aluno.

### Motivo

1. melhora qualidade de dado
2. reduz cadastro morto
3. cria base confiavel para comunicacao futura

### Guardrails

1. registrar trilha de auditoria
2. manter historico ou metadado de troca
3. nao fazer substituicao silenciosa sem rastreabilidade

## ADR 3 - Onboarding e uma camada propria, separada da identidade

### Decisao

A jornada de primeira entrada nao deve ficar espremida dentro de `StudentIdentity`.

### Motivo

1. identidade prova quem e a pessoa
2. onboarding registra o que ainda falta para o aluno ficar operacionalmente pronto

### Consequencia

Criar model proprio de onboarding ou session de onboarding.

## ADR 4 - Intencao comercial entra antes da matricula automatica

### Decisao

A escolha de plano e dia de pagamento gera uma `intencao comercial`, nao uma matricula financeira automatica por padrao no primeiro corte.

### Motivo

1. reduz risco comercial
2. permite revisao e automacao futura
3. evita acoplamento precoce com financeiro

## ADR 5 - Telemetria vem antes do ML

### Decisao

O sistema so deve subir modelos e score depois de:

1. estados formais
2. eventos rastreaveis
3. agregacoes reproduziveis

### Motivo

1. sem dado limpo, modelo aprende ruido
2. sem trilha auditavel, score vira opacidade

## 5. Modelo alvo

## 5.1 Entidades existentes reutilizadas

1. `student_identity.models.StudentAppInvitation`
2. `student_identity.models.StudentIdentity`
3. `student_identity.models.StudentBoxMembership`
4. `students.models.Student`

## 5.2 Novas entidades sugeridas

### `StudentOnboardingProfile`

Responsabilidade:

1. guardar progresso da primeira entrada
2. consolidar dados essenciais e complementares
3. separar onboarding de identidade

Campos sugeridos:

1. `student`
2. `identity`
3. `status`
4. `started_at`
5. `completed_at`
6. `full_name`
7. `whatsapp`
8. `gender`
9. `birth_date`
10. `cpf`
11. `health_notes`
12. `acquisition_source`
13. `acquisition_detail`
14. `profile_essential_completed_at`
15. `profile_complementary_completed_at`

### `StudentCommercialIntent`

Responsabilidade:

1. registrar intencao de compra e preferencia de cobranca

Campos sugeridos:

1. `student`
2. `identity`
3. `selected_plan`
4. `preferred_payment_day`
5. `source`
6. `status`
7. `created_at`
8. `updated_at`
9. `converted_at`

## 5.3 Estados formais

### `StudentOnboardingStatus`

1. `invited`
2. `authenticated`
3. `profile_pending`
4. `profile_completed`
5. `commercial_pending`
6. `ready_for_membership`
7. `completed`

### `StudentCommercialIntentStatus`

1. `draft`
2. `selected`
3. `pending_review`
4. `converted`
5. `discarded`

## 6. Regras de negocio

1. convite nao pede e-mail digitado manualmente no fluxo operacional alvo
2. autenticacao social validada atualiza o e-mail canonico atual
3. troca de e-mail exige trilha de auditoria
4. onboarding aparece ate os dados essenciais serem concluidos
5. plano escolhido gera intencao comercial, nao cobranca automatica por padrao
6. CPF e saude sao opcionais no primeiro corte
7. ML nao pode escrever verdade primaria

## 7. Telemetria e intelligence foundation

## 7.1 Eventos minimos

1. `invite_opened`
2. `oauth_started`
3. `oauth_completed`
4. `oauth_failed`
5. `identity_confirmed`
6. `onboarding_started`
7. `onboarding_step_viewed`
8. `onboarding_step_completed`
9. `onboarding_completed`
10. `plan_selected`
11. `payment_day_selected`
12. `app_opened`
13. `content_viewed`
14. `double_class_interest_clicked`

## 7.2 Payload minimo por evento

1. `student_id`
2. `box_root_slug`
3. `event_name`
4. `timestamp`
5. `screen`
6. `session_id`
7. `source`

## 7.3 Segmentos futuros

1. `nao_autenticou`
2. `autenticou_nao_completou_onboarding`
3. `conteudo_first`
4. `oferta_first`
5. `social_first`
6. `treino_first`
7. `alto_interesse_baixa_conversao`
8. `risco_abandono_onboarding`

## 7.4 Usos seguros

1. ordenar conteudo
2. recomendar proximo passo
3. priorizar fila operacional
4. detectar abandono de onboarding

## 7.5 Usos arriscados

1. segmentacao agressiva baseada em dado sensivel
2. decisao automatica importante sem revisao humana
3. usar pouca amostra para inferencia forte

## 7.6 Usos proibidos ou bloqueados no plano

1. vender dados dos alunos
2. usar CPF ou saude para marketing comum
3. sobrescrever verdade operacional por score

## 8. Plano tecnico por ownership de arquivos

## 8.1 `student_identity`

### Ownership

1. convite
2. autenticacao social
3. consolidacao de identidade
4. auditoria de troca de e-mail

### Arquivos principais

1. [student_identity/forms.py](../../student_identity/forms.py)
2. [student_identity/staff_views.py](../../student_identity/staff_views.py)
3. [student_identity/application/use_cases.py](../../student_identity/application/use_cases.py)
4. [student_identity/infrastructure/repositories.py](../../student_identity/infrastructure/repositories.py)
5. [student_identity/models.py](../../student_identity/models.py)
6. [student_identity/views.py](../../student_identity/views.py)
7. [templates/student_identity/operations_invites.html](../../templates/student_identity/operations_invites.html)

### Mudancas previstas

1. remover `invited_email` do fluxo operacional de convite
2. ajustar `CreateStudentInvitation`
3. ajustar `AuthenticateStudentWithProvider`
4. registrar auditoria da troca de e-mail
5. ligar o callback ao estado de onboarding

## 8.2 `student_app`

### Ownership

1. primeira entrada
2. wizard
3. telas mobile-first
4. retomada de onboarding incompleto

### Arquivos principais

1. [student_app/views.py](../../student_app/views.py)
2. [student_app/urls.py](../../student_app/urls.py)
3. [templates/student_app/](../../templates/student_app)

### Mudancas previstas

1. criar wizard de onboarding
2. bloquear ou redirecionar para onboarding quando perfil estiver incompleto
3. criar tela de conclusao

## 8.3 `students`

### Ownership

1. cadastro principal do aluno
2. consolidacao do e-mail canonico

### Arquivos principais

1. [students/models.py](../../students/models.py)

### Mudancas previstas

1. revisar impactos da troca de email
2. garantir que o cadastro principal reflita a identidade autenticada com seguranca

## 8.4 `catalog` / comercial

### Ownership

1. planos
2. selecao de plano
3. intencao comercial

### Arquivos provaveis

1. [catalog/](../../catalog)
2. [finance/](../../finance)

### Mudancas previstas

1. criar ponte de leitura para planos disponiveis
2. persistir `StudentCommercialIntent`

## 8.5 `auditing`

### Ownership

1. rastreabilidade de eventos sensiveis

### Mudancas previstas

1. novo evento para troca de email por autenticacao social
2. novo evento para conclusao de onboarding
3. novo evento para criacao de intencao comercial

## 8.6 `jobs` / intelligence layer

### Ownership

1. telemetria agregada
2. snapshots de onboarding
3. scores futuros

### Mudancas previstas

1. nao entram como bloqueador do v1
2. entram depois da fundacao de eventos

## 9. Backlog em ondas

## Onda 1 - Simplificacao do convite

### Objetivo

1. remover friccao manual

### Tarefas

1. remover `invited_email` da UI operacional
2. ajustar form e validacao
3. ajustar use case para confiar no cadastro atual ou no fluxo social
4. revisar mensagens de erro
5. revisar testes de convite

### Criterio de pronto

1. fluxo operacional nao pede e-mail manual
2. testes existentes continuam verdes

## Onda 2 - Consolidacao do email canonico

### Objetivo

1. transformar autenticacao social em limpador de cadastro

### Tarefas

1. registrar troca de e-mail por OAuth/Apple
2. atualizar `Student.email` com guardrails
3. preservar trilha de auditoria
4. revisar conflito com convites antigos

### Criterio de pronto

1. o e-mail autenticado passa a ser o atual
2. a trilha de mudanca fica auditavel

## Onda 3 - Estado formal de onboarding

### Objetivo

1. parar de inferir jornada por campos soltos

### Tarefas

1. criar model/status de onboarding
2. ligar identidade ao onboarding
3. inicializar onboarding no aceite do convite ou primeiro callback valido

### Criterio de pronto

1. cada aluno tem status formal de jornada

## Onda 4 - Wizard de primeira entrada

### Objetivo

1. aluno fecha o proprio cadastro

### Tarefas

1. criar telas do wizard
2. persistencia progressiva por etapa
3. retomada de onboarding incompleto
4. UX mobile-first

### Criterio de pronto

1. aluno consegue concluir perfil essencial sem ajuda humana

## Onda 5 - Intencao comercial

### Objetivo

1. capturar plano e preferencia de cobranca

### Tarefas

1. criar model `StudentCommercialIntent`
2. criar tela de selecao de plano
3. criar selecao do dia preferido
4. ligar conclusao do wizard a essa intencao

### Criterio de pronto

1. o sistema registra intencao comercial auditavel

## Onda 6 - Telemetria

### Objetivo

1. preparar analytics e intelligence layer

### Tarefas

1. definir taxonomia de eventos
2. instrumentar o onboarding
3. produzir agregados minimos
4. validar funil e abandono por etapa

### Criterio de pronto

1. o funil de onboarding passa a ser mensuravel

## Onda 7 - Heuristicas e score simples

### Objetivo

1. priorizar sem contaminar o core

### Tarefas

1. score heuristico de abandono
2. fila operacional de excecoes
3. recomendacao simples de proxima acao

### Criterio de pronto

1. a operacao enxerga onde atuar primeiro

## 10. Testes e validacao

## Testes obrigatorios

1. convite sem campo manual de e-mail
2. callback social atualiza e-mail canonico
3. auditoria da troca de e-mail
4. wizard persiste dados por etapa
5. retomada de onboarding incompleto
6. criacao de intencao comercial
7. eventos principais emitidos

## Smoke manual por papel

1. owner gera convite
2. aluno abre convite
3. aluno entra com Google ou Apple
4. aluno conclui onboarding
5. owner ou manager visualiza excecoes operacionais

## 11. Prompt de execucao

Use este prompt para orientar implementacao futura deste plano:

```text
Objetivo: implementar o onboarding inteligente do aluno no OctoBox de forma incremental, sem quebrar os fluxos atuais de convite, OAuth/Apple, membership e student app.

Contexto:
1. convite define o contexto do box
2. autenticacao social prova identidade
3. onboarding fecha o cadastro essencial
4. intencao comercial captura plano e dia preferido de pagamento
5. telemetria deve nascer antes de ML

Regras:
1. nao reescrever o fluxo atual inteiro
2. preferir evolucao incremental sobre rewrite
3. nao deixar ML ou heuristica escrever verdade primaria
4. auditar troca de e-mail e transicoes sensiveis
5. tratar CPF e saude como dados de risco maior

Entregas esperadas:
1. modelagem e migrations
2. ajustes em use cases e repositories
3. telas do wizard
4. telemetria minima
5. testes por circuito

Qualidade:
1. experiencia simples para o aluno
2. pouco trabalho manual para a operacao
3. base pronta para intelligence layer futura
4. risco controlado de debito tecnico
```

## 12. Fecho

Este plano so merece nota 10 se respeitar esta sequencia:

1. primeiro organizar a verdade
2. depois organizar a jornada
3. depois medir comportamento
4. so depois personalizar e prever

Em linguagem simples:

1. primeiro construimos a estrada
2. depois colocamos sensores
3. so depois ligamos a inteligencia de navegacao
