<!--
ARQUIVO: mapa completo do app autenticado dos alunos.

TIPO DE DOCUMENTO:
- mapa operacional completo
- referencia de navegacao por camada

AUTORIDADE:
- alta para localizar ownership tecnico do app do aluno
- subordinado ao runtime real, testes e codigo atual

DOCUMENTOS PAIS:
- [../../README.md](../../README.md)
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
- [../architecture/octobox-architecture-model.md](../architecture/octobox-architecture-model.md)
- [student-app-path-map.md](student-app-path-map.md)

QUANDO USAR:
- quando a pergunta for "onde mexo no app do aluno?"
- quando uma rota em `/aluno/` quebrar
- quando houver duvida entre identidade, membership, shell, PWA, WOD, RM, grade ou settings
- quando um agente precisar entender o circuito inteiro antes de editar

POR QUE ELE EXISTE:
- o app do aluno ja virou uma superficie real de produto, nao apenas uma pagina Django.
- ele mistura identidade propria, memberships por box, PWA, agenda, WOD, RM, cache e estados excepcionais.
- este mapa reduz busca cega e impede mexer na camada errada.

O QUE ESTE ARQUIVO FAZ:
1. mapeia a portaria HTTP do app do aluno.
2. separa identidade, runtime, shell, telas, dados, cache, PWA e testes.
3. explica a ordem segura de leitura por tipo de problema.
4. registra os principais contratos que nao devem ser quebrados.

PONTOS CRITICOS:
- `/aluno/` e o app autenticado do aluno.
- `/renan/` e outra superficie publica de treino publicado.
- docs ajudam a navegar, mas o runtime real vence quando houver divergencia.
- nao coloque regra de negocio sensivel em template; use use cases, workflows ou snapshots.
-->

# Mapa completo do app do aluno

## Tese curta

O app do aluno e a cabine mobile/PWA do OctoBox.

Pense como uma escola:

1. `student_identity` pergunta "quem e voce?"
2. `student_app/views/base.py` pergunta "qual box voce pode acessar agora?"
3. `student_app/views/shell_views.py` escolhe a sala certa: Inicio, Grade, WOD, RM ou Perfil
4. `student_app/application/*` monta a mochila pronta com dados de agenda, treino, RM e cache
5. `templates/student_app/*` mostra isso para o aluno sem conhecer o banco inteiro

Em termos tecnicos:

1. identidade e sessao ficam fora da conta interna de funcionarios
2. views HTTP devem continuar finas
3. leitura de tela deve passar por snapshots/use cases
4. mutacoes ficam em workflows ou actions especificas
5. cache acelera leitura, mas nao vira fonte de verdade

## Ordem curta de leitura

Se voce chegou sem contexto, leia nesta ordem:

1. [../../README.md](../../README.md)
2. [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
3. [student-app-path-map.md](student-app-path-map.md)
4. [../../config/urls.py](../../config/urls.py)
5. [../../student_app/urls.py](../../student_app/urls.py)
6. [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py)
7. [../../student_identity/models.py](../../student_identity/models.py)
8. [../../student_identity/views.py](../../student_identity/views.py)
9. [../../student_app/views/base.py](../../student_app/views/base.py)
10. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)
11. [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)
12. [../../student_app/application/results.py](../../student_app/application/results.py)
13. [../../student_app/models.py](../../student_app/models.py)
14. [../../templates/student_app/layout.html](../../templates/student_app/layout.html)
15. [../../static/css/student_app/app.css](../../static/css/student_app/app.css)
16. [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js)
17. [../../student_app/tests.py](../../student_app/tests.py)

## Portaria HTTP

### Raiz de URLs

Arquivo:

1. [../../config/urls.py](../../config/urls.py)

Contratos:

1. `path('aluno/', include('student_app.urls'))` entrega o app autenticado
2. `path('renan/', include('student_app.public_urls'))` entrega a superficie publica

Regra:

1. nunca diagnostique `/aluno/` usando a logica de `/renan/`
2. nunca exponha comportamento autenticado do aluno na superficie publica sem gate explicito

### Rotas autenticadas

Arquivo:

1. [../../student_app/urls.py](../../student_app/urls.py)

Rotas principais:

1. `/aluno/` -> `StudentHomeView`
2. `/aluno/grade/` -> `StudentGradeView`
3. `/aluno/wod/` -> `StudentWodView`
4. `/aluno/treino/` -> alias de `StudentWodView`
5. `/aluno/rm/` -> `StudentRmView`
6. `/aluno/rm/adicionar/` -> `StudentAddRmView`
7. `/aluno/rm/<pk>/atualizar/` -> `StudentUpdateRmView`
8. `/aluno/aula/<session_id>/turma/` -> `StudentSessionAttendeesView`
9. `/aluno/configuracoes/` -> `StudentSettingsView`
10. `/aluno/presenca/confirmar/` -> `StudentConfirmAttendanceView`
11. `/aluno/presenca/cancelar/` -> `StudentCancelAttendanceView`
12. `/aluno/onboarding/` -> `StudentOnboardingWizardView`
13. `/aluno/aguardando-aprovacao/` -> estado de membership pendente
14. `/aluno/suspenso-financeiro/` -> estado de suspensao financeira
15. `/aluno/sem-box/` -> estado sem box ativo
16. `/aluno/entrar-com-convite/` -> entrada por convite
17. `/aluno/box/switch/` -> troca de box ativo
18. `/aluno/auth/*` -> `student_identity.urls`
19. `/aluno/manifest.webmanifest` -> manifest PWA
20. `/aluno/sw.js` -> service worker
21. `/aluno/offline/` -> fallback offline
22. `/aluno/push/subscribe/` e `/aluno/push/unsubscribe/` -> push web

## Gate de identidade e sessao

### Middleware de protecao

Arquivo:

1. [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py)

Responsabilidade:

1. intercepta rotas com prefixo `/aluno/`
2. libera prefixos publicos do proprio app: auth, offline, manifest e service worker
3. le cookie de sessao do aluno
4. aceita pending onboarding como excecao
5. redireciona anonimo para `/aluno/auth/login/`
6. registra auditoria de acesso anonimo redirecionado

Heuristica:

1. se anonimo entra onde nao deveria, comece aqui
2. se rota publica do PWA passou a pedir login, revise `_PUBLIC_PREFIXES`
3. se login parece funcionar mas a pagina volta para auth, continue em `views/base.py`

### Identidade do aluno

Arquivos:

1. [../../student_identity/models.py](../../student_identity/models.py)
2. [../../student_identity/views.py](../../student_identity/views.py)
3. [../../student_identity/infrastructure/session.py](../../student_identity/infrastructure/session.py)
4. [../../student_identity/security.py](../../student_identity/security.py)

Modelos centrais:

1. `StudentIdentity` separa conta do aluno da conta interna de funcionario
2. `StudentBoxMembership` define vinculo e status por box
3. `StudentAppInvitation` ancora convite individual
4. `StudentBoxInviteLink` ancora convite aberto do box
5. `StudentPushSubscription` guarda inscricao push por identidade/dispositivo

Fluxo:

1. login aparece em `StudentSignInView`
2. OAuth inicia em `StudentOAuthStartView`
3. callback resolve provider, state, invite e identidade em `StudentOAuthCallbackView`
4. logout limpa cookie em `StudentSignOutView`

Regra:

1. `student_identity` responde "quem e esta pessoa?"
2. `student_app` responde "o que esta pessoa pode ver agora?"

### Runtime autenticado

Arquivo:

1. [../../student_app/views/base.py](../../student_app/views/base.py)

Responsabilidade:

1. resolve cookie `octobox_student_session`
2. busca `StudentIdentity`
3. carrega memberships
4. escolhe box ativo
5. protege troca forte de dispositivo via fingerprint
6. redireciona para onboarding, sem-box ou suspenso-financeiro
7. injeta contexto comum do shell
8. renova cookie com box ativo e fingerprint atual

Classes importantes:

1. `StudentIdentityRequiredMixin` exige membership ativo
2. `StudentSessionIdentityMixin` aceita ativo e pendente
3. `StudentAnyMembershipMixin` aceita qualquer membership e pode operar sem box ativo

## Shell autenticado

### Views principais

Arquivo:

1. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)

Ownership:

1. `StudentHomeView` monta Inicio
2. `StudentGradeView` monta Grade
3. `StudentWodView` monta WOD e calculadora
4. `StudentRmView` monta RM e historico
5. `StudentSessionAttendeesView` monta turma da aula
6. `StudentSettingsView` monta Perfil/configuracoes
7. `StudentConfirmAttendanceView` confirma reserva/presenca
8. `StudentCancelAttendanceView` cancela reserva

Regra de arquitetura:

1. view decide fluxo HTTP
2. use case monta leitura
3. template renderiza
4. workflow executa regra mutavel de escrita

### Use cases e snapshots

Arquivos:

1. [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)
2. [../../student_app/application/results.py](../../student_app/application/results.py)
3. [../../student_app/application/agenda_snapshots.py](../../student_app/application/agenda_snapshots.py)
4. [../../student_app/application/home_snapshots.py](../../student_app/application/home_snapshots.py)
5. [../../student_app/application/wod_snapshots.py](../../student_app/application/wod_snapshots.py)
6. [../../student_app/application/rm_snapshots.py](../../student_app/application/rm_snapshots.py)

Use cases principais:

1. `GetStudentDashboard` monta Inicio, Grade curta, acao primaria, WOD ativo e RM do dia
2. `GetStudentMonthSchedule` monta calendario mensal
3. `GetStudentWorkoutDay` monta treino publicado personalizado por RM
4. `GetStudentWorkoutPrescription` calcula carga baseada em RM e percentual

Dataclasses de saida:

1. `StudentDashboardResult`
2. `StudentSessionCard`
3. `StudentPrimaryAction`
4. `StudentRmOfTheDay`
5. `StudentWorkoutDayResult`
6. `StudentWorkoutBlockCard`
7. `StudentWorkoutMovementCard`
8. `WorkoutPrescriptionResult`

Traducao simples:

1. dataclass e uma marmita fechada
2. o template so abre a marmita
3. ele nao deveria cozinhar a refeicao

## Telas e ownership visual

### Layout global

Arquivo:

1. [../../templates/student_app/layout.html](../../templates/student_app/layout.html)

Responsabilidade:

1. shell visual compartilhado
2. head assets
3. sidebar desktop
4. topbar
5. mobile nav
6. box switcher
7. flash stack
8. PWA activation
9. inclusao de CSS e JS comuns

Se a app inteira parece quebrada:

1. olhe `layout.html`
2. depois olhe [../../static/css/student_app/app.css](../../static/css/student_app/app.css)
3. depois olhe o CSS da tela especifica em `static/css/student_app/screens/`

### Telas

Templates:

1. [../../templates/student_app/home.html](../../templates/student_app/home.html)
2. [../../templates/student_app/grade.html](../../templates/student_app/grade.html)
3. [../../templates/student_app/wod.html](../../templates/student_app/wod.html)
4. [../../templates/student_app/rm.html](../../templates/student_app/rm.html)
5. [../../templates/student_app/settings.html](../../templates/student_app/settings.html)
6. [../../templates/student_app/session_attendees.html](../../templates/student_app/session_attendees.html)
7. [../../templates/student_app/onboarding_wizard.html](../../templates/student_app/onboarding_wizard.html)
8. [../../templates/student_app/offline.html](../../templates/student_app/offline.html)

CSS por camada:

1. [../../static/css/student_app/app.css](../../static/css/student_app/app.css) agrega o app
2. `static/css/student_app/primitives/` guarda blocos reutilizaveis
3. `static/css/student_app/shell/` guarda shell, sidebar, topbar e responsivo
4. `static/css/student_app/screens/` guarda telas especificas

JS por superficie:

1. [../../static/js/student_app/theme.js](../../static/js/student_app/theme.js) controla tema runtime
2. [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js) controla instalacao/push
3. [../../static/js/student_app/session-card.js](../../static/js/student_app/session-card.js) apoia cards de aula
4. [../../static/js/student_app/grade-month.js](../../static/js/student_app/grade-month.js) apoia calendario
5. [../../static/js/student_app/day-filter.js](../../static/js/student_app/day-filter.js) apoia filtros por dia
6. [../../static/js/student_app/wod.js](../../static/js/student_app/wod.js) apoia WOD
7. [../../static/js/student_app/rm.js](../../static/js/student_app/rm.js) apoia RM

Regra visual:

1. home e WOD podem ter mais tensao visual
2. perfil, forms e settings devem ficar mais silenciosos
3. nao crie sistema paralelo de tema; o runtime real em `body[data-theme]` vence

## Modelos proprios do app

Arquivo:

1. [../../student_app/models.py](../../student_app/models.py)

Familias:

1. RM do aluno: `StudentExerciseMax`, `StudentExerciseMaxHistory`
2. atividade: `StudentAppActivity`, `StudentAppActivityKind`
3. alteracao de perfil: `StudentProfileChangeRequest`
4. WOD por aula: `SessionWorkout`, `SessionWorkoutBlock`, `SessionWorkoutMovement`
5. revisao e publicacao: `SessionWorkoutRevision`
6. visualizacao do aluno: `StudentWorkoutView`
7. follow-up operacional: `SessionWorkoutFollowUpAction`
8. memoria operacional: `SessionWorkoutOperationalMemory`
9. checkpoint semanal: `WorkoutWeeklyManagementCheckpoint`
10. gap de RM por WOD: `SessionWorkoutRmGapAction`
11. Smart Paste semanal: `WeeklyWodPlan`, `DayPlan`, `PlanBlock`, `PlanMovement`, `ReplicationBatch`

Observacao importante:

1. varios modelos de WOD vivem em `student_app.models`
2. mas boa parte da operacao de criacao/aprovacao vive em `operations/*`
3. isso e uma fronteira historica/atual: modelo compartilhado, corredores de uso separados

## Cache, performance e invalidacao

Arquivos:

1. [../../student_app/application/cache_keys.py](../../student_app/application/cache_keys.py)
2. [../../student_app/application/cache_invalidation.py](../../student_app/application/cache_invalidation.py)
3. [../../student_app/signals.py](../../student_app/signals.py)
4. [../../student_app/application/cache_telemetry.py](../../student_app/application/cache_telemetry.py)

Snapshots:

1. agenda por box, data e janela
2. home por box, aluno, data e janela
3. home-rm por box, aluno e sessao
4. rm por box e aluno
5. WOD publicado por box, sessao e versao do workout

Invalidacoes:

1. `ClassSession` muda -> agenda/home
2. `Attendance` muda -> agenda/home do aluno
3. `SessionWorkout` muda -> agenda/home
4. `SessionWorkoutBlock` muda -> agenda/home
5. `SessionWorkoutMovement` muda -> agenda/home
6. `StudentExerciseMax` ou history muda -> home/RM
7. `StudentAppActivity` muda -> home
8. `Enrollment` muda -> home

Regra:

1. cache e uma foto rapida
2. banco e a pessoa real
3. se a foto envelhece, invalidacao troca a foto

## PWA

Arquivos:

1. [../../student_app/views/pwa_views.py](../../student_app/views/pwa_views.py)
2. [../../templates/student_app/sw.js](../../templates/student_app/sw.js)
3. [../../templates/student_app/offline.html](../../templates/student_app/offline.html)
4. [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js)
5. [../../templates/student_app/_partials/_pwa_activation.html](../../templates/student_app/_partials/_pwa_activation.html)

Contratos:

1. scope do PWA e `/aluno/`
2. start URL e `/aluno/`
3. service worker e manifesto precisam continuar publicos dentro do prefixo
4. push subscription pertence a `StudentIdentity` e box
5. permissao de notificacao sozinha nao deve significar ativacao completa

## Fluxos de escrita

### Presenca

Arquivos:

1. [../../student_app/workflows/attendance_workflows.py](../../student_app/workflows/attendance_workflows.py)
2. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)

Views:

1. `StudentConfirmAttendanceView`
2. `StudentCancelAttendanceView`

Regra:

1. view recebe POST
2. workflow valida e executa
3. activity registra evento util

### RM

Arquivos:

1. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)
2. [../../student_app/application/rm_snapshots.py](../../student_app/application/rm_snapshots.py)
3. [../../student_app/domain/workout_prescription.py](../../student_app/domain/workout_prescription.py)

Views:

1. `StudentAddRmView`
2. `StudentUpdateRmView`

Regra:

1. salvar RM atualiza `StudentExerciseMax`
2. historico vai para `StudentExerciseMaxHistory`
3. snapshots de RM/home devem ser invalidados
4. WOD usa RM para recomendar carga quando movimento usa `% do RM`

### Perfil

Arquivos:

1. [../../student_app/forms.py](../../student_app/forms.py)
2. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)
3. [../../templates/student_app/settings.html](../../templates/student_app/settings.html)

Regra:

1. aluno nao altera dados sensiveis direto
2. cria `StudentProfileChangeRequest`
3. aprovacao futura fica separada do shell do aluno

## Heuristicas de debug

### Redirecionamento ou login

Comece por:

1. [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py)
2. [../../student_app/views/base.py](../../student_app/views/base.py)
3. [../../student_identity/infrastructure/session.py](../../student_identity/infrastructure/session.py)
4. [../../student_identity/views.py](../../student_identity/views.py)

Perguntas:

1. rota esta em `_PUBLIC_PREFIXES`?
2. cookie existe?
3. cookie decodifica?
4. identity existe?
5. membership ativo existe?
6. fingerprint mudou?

### Grade, reserva ou aula invisivel

Comece por:

1. [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)
2. [../../student_app/application/agenda_snapshots.py](../../student_app/application/agenda_snapshots.py)
3. [../../student_app/application/home_snapshots.py](../../student_app/application/home_snapshots.py)
4. [../../student_app/workflows/attendance_workflows.py](../../student_app/workflows/attendance_workflows.py)

Perguntas:

1. data esta no fuso do box?
2. janela de leitura inclui hoje?
3. aluno tem reserva ativa?
4. plano esta ativo?
5. cache foi invalidado?

### WOD invisivel

Comece por:

1. [student-app-wod-page-structure-map.md](student-app-wod-page-structure-map.md)
2. [student-app-wod-communication-map.md](student-app-wod-communication-map.md)
3. [../../student_app/views/wod_context.py](../../student_app/views/wod_context.py)
4. [../../student_app/application/wod_snapshots.py](../../student_app/application/wod_snapshots.py)
5. [../../student_app/models.py](../../student_app/models.py)

Perguntas:

1. existe `SessionWorkout` para a aula?
2. status e `published`?
3. `session_id` alvo e o certo?
4. dashboard tem `active_wod_session` ou `focal_session`?
5. cache antigo esta escondendo mudanca?

### Tela quebrada visualmente

Comece por:

1. [../../templates/student_app/layout.html](../../templates/student_app/layout.html)
2. [../../templates/student_app/_partials/_head_assets.html](../../templates/student_app/_partials/_head_assets.html)
3. [../../static/css/student_app/app.css](../../static/css/student_app/app.css)
4. `static/css/student_app/screens/<tela>.css`
5. `static/js/student_app/<tela>.js`

Gates uteis:

1. `.\.venv\Scripts\python.exe manage.py check_static_drift --strict`
2. se houver drift, `.\.venv\Scripts\python.exe manage.py sync_runtime_assets --collectstatic`

## Testes e validacao

Gate principal:

1. `.\.venv\Scripts\python.exe manage.py test student_app.tests --noinput`

Smokes HTTP uteis:

1. `/aluno/`
2. `/aluno/grade/`
3. `/aluno/wod/`
4. `/aluno/rm/`
5. `/aluno/configuracoes/`
6. `/aluno/aula/<session_id>/turma/`
7. `/aluno/manifest.webmanifest`
8. `/aluno/sw.js`
9. `/aluno/offline/`

No PowerShell, quando precisar de status HTTP simples:

```powershell
curl.exe -o NUL -w "%{http_code}" http://127.0.0.1:8000/aluno/
```

## Riscos de debito tecnico

Evite:

1. colocar regra de reserva, WOD ou RM dentro de template
2. consultar ORM pesado direto em partial visual
3. criar outro sistema de tema alem de `body[data-theme]`
4. tratar cache como fonte de verdade
5. misturar `/aluno/` com `/renan/`
6. publicar WOD sem passar pelos estados `draft`, `pending_approval` ou `published`
7. editar WOD publicado sem entender que isso reseta status para `draft` em alguns corredores
8. fazer view de shell virar "Deus view"

Regra mental:

1. se uma mudanca parece pequena mas toca identidade, membership, WOD publicado ou cache, trate como mexer no quadro de energia da casa
2. da para trocar a lampada rapido, mas primeiro confirme qual disjuntor alimenta o comodo

