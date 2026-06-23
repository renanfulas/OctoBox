<!--
ARQUIVO: plano C.O.R.D.A. do gate de entrada com PAR-Q + termo de responsabilidade no onboarding do aluno.

TIPO DE DOCUMENTO:
- plano de execucao de produto + arquitetura + UX + operacao
- C.O.R.D.A. por ondas

AUTORIDADE:
- alta para a frente de triagem de saude e consentimento do aluno

DOCUMENTOS PAIS:
- [intelligent-student-onboarding-plan.md](intelligent-student-onboarding-plan.md)
- [student-onboarding-funnel-metrics-plan.md](student-onboarding-funnel-metrics-plan.md)
- [../architecture/center-layer.md](../architecture/center-layer.md)

QUANDO USAR:
- quando a tarefa envolver triagem de saude (PAR-Q), termo de responsabilidade (waiver) ou bloqueio de acesso por liberacao pendente
- quando precisarmos decidir onde o gate de entrada do aluno deve viver sem inflar o dominio nem o wizard
- quando quisermos executar a frente em ondas curtas, com baixo risco de regressao e rollback instantaneo

POR QUE ELE EXISTE:
- o onboarding do aluno hoje leva de "convidado" a "dentro do app", mas nao tem triagem de saude nem termo
- triagem e termo sao especificos de um box (barra, caixote, risco fisico) e nao podem ser tratados so como UI
- este plano transforma a estrategia em um gate de entrada unico, reusando o que ja existe, sem criar status novo de membership

O QUE ESTE ARQUIVO FAZ:
1. formaliza o gate de entrada (bloquear ENTRADA, nao treino) no dispatch existente
2. define o modelo de consentimento versionado com minimo de dado de saude
3. organiza a implementacao em ondas curtas e executaveis, com feature flag
4. protege a arquitetura contra fan-out de status, dado de saude no schema publico e consentimento juridico falso

PONTOS CRITICOS:
- bloqueio = bloquear ENTRADA no app, nunca travar a conclusao do cadastro nem o check-in multi-superficie
- liberacao = MANUAL, por staff, contra atestado medico fisico; o software nao decide saude
- waiver entra MUDO (placeholder nao-vinculante) ate existir texto juridico real (Onda E)
- dado de saude detalhado nunca vai para o schema publico; o publico carrega so o outcome clear/flagged
- o gate fica atras de feature flag ate validacao em staging
-->

# Plano C.O.R.D.A. - Gate de Entrada com PAR-Q + Termo de Responsabilidade

## 1. Resumo executivo

O onboarding do aluno ja sabe levar uma pessoa de `convidado` a `dentro do app`.

O que falta nao e mais motor de cadastro.

O que falta e uma `porta de seguranca` antes da entrada:

1. uma triagem de saude curta (`PAR-Q`)
2. um termo de responsabilidade (`waiver`)
3. um bloqueio seguro quando houver risco, liberado so com `atestado medico` entregue no box

A regra central desta frente:

1. quem esta ok passa com um toque
2. quem tem risco conclui o cadastro, mas nao entra no app ate liberar
3. ninguem fica preso no corredor: a parede de bloqueio e um proximo-passo acolhedor, nao um erro

## 2. C.O.R.D.A.

### C - Contexto

Fundamentos que ja existem no runtime:

1. tres corredores oficiais de onboarding (`mass_box_invite`, `imported_lead_invite`, `registered_student_invite`)
2. funil instrumentado via `AuditEvent` (`record_student_onboarding_event`)
3. gate de entrada unico ja provado em `StudentIdentityRequiredMixin.dispatch()` (`student_app/views/base.py`), que hoje ja redireciona para `pending_onboarding`, `suspended_financial` e `no_active_box`
4. telas-parede provadas (`membership_pending.html`, `suspended_financial.html`, `no_active_box.html`)
5. governanca de pedido-sem-escrita-direta (ver `StudentRequestFreezeView` e o profile-edit como pending request)

O problema atual:

1. nao ha triagem de saude em lugar nenhum
2. nao ha termo de responsabilidade
3. nao ha estado de "aguardando liberacao"

### O - Objetivo

Adicionar PAR-Q + termo como `gate de entrada` do aluno, com:

1. UX destravada no caminho feliz (uma tela focada, um toque)
2. bloqueio de ENTRADA (nao de treino) no caso de risco
3. liberacao manual por staff contra atestado fisico
4. consentimento versionado com minimo de dado de saude
5. rollback instantaneo via feature flag

Sucesso significa:

1. 95% dos alunos passam sem friccao perceptivel
2. o caso de risco e barrado na entrada com instrucao clara
3. o box ve quem esta aguardando liberacao e age em um clique
4. zero regressao no dominio de membership
5. nenhum consentimento juridico falso gravado

### R - Riscos

#### 1. Risco de fan-out de status

Criar um status novo de membership tocaria os ~59 leitores de status (middleware, queries, snapshots, finance). Mitigacao: usar campo ORTOGONAL, nao status novo.

#### 2. Risco de bloqueio multi-superficie

Bloquear `treino` exigiria gate em check-in do aluno, recepcao e API ao mesmo tempo. Mitigacao: bloquear ENTRADA no `dispatch()`, que e chokepoint unico.

#### 3. Risco de dado de saude no schema publico

`flagged` colado a nome/e-mail no schema publico e dado sensivel (LGPD). Mitigacao: publico guarda so o outcome `clear|flagged`; respostas detalhadas no schema do box, ou nao persistir.

#### 4. Risco de consentimento juridico falso

Gravar `aceite informado` sobre texto placeholder e passivo, nao ativo. Mitigacao: waiver entra MUDO; `waiver_accepted` so liga na Onda E com texto real.

#### 5. Risco de matar conversao

Bloquear entrada tranca o aluno flagged. Se o PAR-Q for sensivel demais, tranca segmento legitimo. Mitigacao: conjunto de red-flags enxuto, revisado por humano; parede acolhedora com proximo-passo.

#### 6. Risco de migration fragil

App shared (`student_identity`) tem historico do gotcha "grava sem DDL" do `TenantSyncRouter` (mordeu o app `knowledge`). Mitigacao: validar `migrate_schemas --shared` E o schema tenant separadamente na Onda A.

### D - Direcao

#### Tese central

1. consentimento e uma TELA DEDICADA E FOCADA pos-auth, nao um inchaco no wizard de dados
2. o bloqueio mora em um gate unico de entrada, com campo ortogonal, nao em status novo
3. a decisao clinica sai do software e vai para um humano com o atestado na mao

#### Frases de arquitetura

1. `Bloquear entrada, nunca travar o cadastro nem o check-in.`
2. `O publico carrega o veredito (clear/flagged); a saude detalhada fica no box.`
3. `O waiver entra mudo ate o juridico falar.`
4. `O software guarda a porta; o atestado e o humano destrancam.`
5. `Feature flag primeiro; gate no caminho critico nunca entra sem rollback.`

#### O que nao fazer

1. nao criar status novo de membership
2. nao bloquear treino/check-in nesta frente
3. nao inflar `onboarding_wizard.html`
4. nao gravar aceite vinculante de waiver placeholder
5. nao mandar resposta detalhada de PAR-Q para o schema publico
6. nao inventar a lista clinica de red-flags

### A - Acoes

Ver ondas na secao 4.

## 3. Decisoes travadas

1. **Bloqueio = bloquear ENTRADA**, via gate unico em `StudentIdentityRequiredMixin.dispatch()`.
2. **Sem status novo**: campo ortogonal em `StudentBoxMembership` (`clearance_required`, `cleared_at`, `cleared_by`). Status segue `ACTIVE`/`PENDING_APPROVAL`.
3. **Liberacao = manual**, por staff, contra atestado fisico (acao "Liberar acesso" seta `cleared_at`).
4. **Abrangencia = 3 corredores**, via gate de consentimento UNIFICADO pos-auth.
5. **B1 (legal)**: waiver entra como PLACEHOLDER nao-vinculante; `waiver_accepted` so liga na Onda E.
6. **B2 (clinico)**: semear o PAR-Q canonico de 7 perguntas, marcado `PENDENTE_REVISAO_CLINICA`; lista revisada por humano antes da Onda B abrir red-flags em producao.
7. **B3 (dado)**: persistir no publico SO o outcome (`clear|flagged`); respostas detalhadas no tenant ou nao persistir.

## 4. Ondas de execucao

Cada onda e um PR pequeno, verde no gate Postgres (`--create-db --migrations`).

### Onda A - Modelo + flag + seed + migrations

1. `ConsentDocument` (publico): `kind` (`waiver`|`parq`), `version`, `effective_at`, `body`, `is_active`.
   - seed `parq` v1 com as 7 perguntas canonicas (`PENDENTE_REVISAO_CLINICA`)
   - seed `waiver` v1 marcado `PLACEHOLDER_NAO_VINCULANTE`
2. `StudentConsent` (publico, junto de `StudentIdentity`): `identity` FK, `box` FK, `document_kind`, `version`, `accepted_at`, `ip`, `user_agent`, `parq_outcome` (`clear`|`flagged`). NAO guardar quais respostas.
3. `StudentBoxMembership`: + `clearance_required` (bool), `cleared_at` (datetime null), `cleared_by` (FK staff null).
4. respostas detalhadas do PAR-Q: no schema do box, ligadas ao `Student`; ou nao persistir (decidir aqui, default = nao persistir).
5. migrations: validar `migrate_schemas --shared` E o schema tenant separadamente.

Sem UI nesta onda.

### Onda B - Tela de consentimento + gate (a)

1. tela unica de consentimento pos-auth (reuso de `student-card`, `student-form-stack`, `student-form-note`, `student-button`)
2. PAR-Q em toggles Sim/Nao curtos; termo em caixa rolavel com altura limitada
3. botao SEMPRE habilitado (sem "role ate o fim"); validacao no submit
4. gate (a) em `dispatch()`: se falta consentimento da versao vigente -> `redirect('student-app-consent')`
5. feature flag `STUDENT_CONSENT_GATE_ENABLED` (default OFF)
6. PAR-Q funcional; waiver exibido mas SEM gravar aceite vinculante
7. decisao `clear|flagged` em workflow/use-case, nunca em template/view

### Onda C - Parede de clearance + gate (b)

1. parede `student-app-clearance` no molde de `membership_pending.html`
   - copy acolhedora: "Recebemos suas respostas. Por seguranca, entregue um atestado medico no seu box para liberar o acesso." + nome/contato do box
2. no flagged: `complete_*_onboarding` (ou o submit do gate) seta `membership.clearance_required = True`
3. gate (b) em `dispatch()`: se `clearance_required and not cleared_at` -> `redirect('student-app-clearance')`
4. aluno flagged nao acessa nenhuma rota do app

### Onda D - Liberacao por staff + fila operacional

1. acao de staff "Liberar acesso" seta `cleared_at`/`cleared_by` (set-once, idempotente)
2. fila operacional filtrando `clearance_required=True, cleared_at IS NULL` (reuso da superficie de operacoes)
3. evento `clearance_granted`

### Onda E - Waiver vinculante (BLOQUEADA por juridico)

1. substituir o placeholder pelo texto juridico real
2. ligar `waiver_accepted` como aceite vinculante
3. so abre quando houver texto aprovado

## 5. Eventos de funil

Estender `record_student_onboarding_event`, padrao `student_onboarding.<journey>.<event>`:

1. `consent_step_viewed`
2. `waiver_accepted` (so quando texto real, Onda E)
3. `parq_completed`
4. `parq_flagged`
5. `clearance_pending`
6. `clearance_granted`

Idempotencia onde ha marcador de sessao.

## 6. Gate unificado (como os 3 corredores convergem)

Em `dispatch()`, apos resolver `active_membership`, nesta ordem (ambos atras da feature flag):

1. se falta consentimento da versao vigente -> `redirect('student-app-consent')`
2. se `active_membership.clearance_required and not cleared_at` -> `redirect('student-app-clearance')`

Convergencia:

1. `mass_box_invite` / `imported_lead_invite`: terminam o wizard -> gate (1) -> se flagged, gate (2)
2. `registered_student_invite` (sem wizard): autentica -> gate (1) direto -> idem

`clearance_required` e por membership (por box), nao por identidade.

## 7. Aceite / testes (gate Postgres)

1. consentimento sem flag -> `parq_outcome='clear'`, entra normalmente
2. consentimento com flag -> `parq_outcome='flagged'`, `clearance_required=True`, evento `parq_flagged`, e na proxima entrada cai na parede
3. aluno flagged NAO acessa rota nenhuma (home, grade, wod -> todas caem na parede)
4. `registered_student_invite` sem consentimento vigente -> ve o gate; consente sem flag -> entra; com flag -> parede
5. ja consentido na versao vigente -> NAO reve o gate
6. staff "Liberar acesso" -> `cleared_at` setado, evento `clearance_granted`, aluno passa a entrar
7. feature flag OFF -> nenhum gate aparece (rollback instantaneo)
8. idempotencia: revisitar nao duplica consent nem evento
9. estender `scripts/run_student_onboarding_corridors_regression.py` com os cenarios acima

## 8. Verificacao local (obrigatoria)

1. cluster PG 5433 + seed (recipes de preview local do aluno)
2. exercitar os 3 corredores no preview: caminho feliz (1 toque) e caminho flagged (parede + WOD inacessivel)
3. testar no viewport mobile
4. anexar screenshots no PR

## 9. Edge cases

1. versao do termo muda no meio -> grava a versao LIDA na tela, nao a vigente no submit
2. aluno multi-box -> gate olha o `active_membership` certo; `clearance_required` e por box
3. flag OFF com gente ja flagged -> ninguem fica preso; ao religar, volta a barrar
4. liberacao dupla / corrida -> `cleared_at` set-once; segunda e no-op
5. `registered_student_invite` cai direto no gate sem passar pelo wizard -> testar isolado (ponto que mais quebra)
6. dado de saude -> so `clear|flagged` no publico; nunca quais respostas

## 10. Guardrails

1. decisao `clear/flagged/versao` em workflow/use-case, nunca em template/view
2. red-flags do PAR-Q enxutos e revisados por humano antes de producao
3. `AuditEvent` so como trilha; nao vira read-model
4. dado de saude detalhado nunca no schema publico
5. gate sempre atras de feature flag ate validacao em staging
6. se qualquer ancora de codigo divergir, PARAR e reportar o delta antes de prosseguir

## 11. Ancoras de codigo (confirmar antes de editar)

1. gate de entrada: `student_app/views/base.py` (`StudentIdentityRequiredMixin.dispatch`)
2. telas-parede: `student_app/views/membership_views.py` + `templates/student_app/membership_pending.html`
3. wizard: `templates/student_app/onboarding_wizard.html` + `student_app/forms.py`
4. conclusao dos corredores: `student_app/workflows/onboarding_workflows.py`
5. funil: `student_identity/funnel_events.py`
6. status de membership: `student_identity/models.py` (`StudentBoxMembershipStatus`)
7. regressao (gate CI): `scripts/run_student_onboarding_corridors_regression.py`

## 12. Formula curta

O melhor onboarding nao baixa a guarda na seguranca.

Ele poe UMA porta na entrada: quem esta ok passa com um toque, quem tem risco espera do lado de fora com instrucao clara, e o atestado na mao de um humano e que destranca.
