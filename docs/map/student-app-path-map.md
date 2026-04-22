<!--
ARQUIVO: mapa operacional do app do aluno e da rota `/aluno/`.

POR QUE ELE EXISTE:
- junta em um unico trilho a entrada HTTP, a autenticacao, as views, os templates, o CSS, o JS e os models do app do aluno.
- reduz busca cega quando a pergunta for "onde mexo de verdade nesta pagina?".

O QUE ESTE ARQUIVO FAZ:
1. define a ordem curta de leitura do circuito `/aluno/`.
2. aponta ownership tecnico de front-end e back-end do app do aluno.
3. registra o comportamento atual do runtime na entrada anonima.
4. mostra onde investigar quando a pagina, o login, o WOD, o PWA ou o shell quebrarem.

PONTOS CRITICOS:
- este mapa depende do runtime atual; se URLs, templates, mixins ou models mudarem, ele precisa ser revisado.
- o app autenticado em `/aluno/` nao deve ser confundido com a superficie publica em `/renan/`.
- este documento nao substitui o codigo nem os testes; ele organiza a leitura operacional do circuito.
-->

# Mapa do app do aluno

Este documento explica o corredor real do app do aluno no OctoBox.

Pense assim:

1. `config/urls.py` e a portaria do predio
2. `student_identity` e a catraca de identidade
3. `student_app/views/base.py` e o porteiro que valida sessao, membership e box ativo
4. `student_app/views/shell_views.py` e o corredor das telas principais
5. `templates/student_app/*` e `static/css/student_app/app.css` sao a fachada visual
6. `student_app/application/use_cases.py` e `student_app/models.py` guardam a regra e o estado proprio do app

## Ordem curta de leitura

Se a pergunta for "como `/aluno/` funciona hoje?", leia nesta ordem:

1. [../../README.md](../../README.md)
2. [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)
3. [../../config/urls.py](../../config/urls.py)
4. [../../student_app/urls.py](../../student_app/urls.py)
5. [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py)
6. [../../student_identity/urls.py](../../student_identity/urls.py)
7. [../../student_identity/views.py](../../student_identity/views.py)
8. [../../student_app/views/base.py](../../student_app/views/base.py)
9. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)
10. [../../student_app/views/membership_views.py](../../student_app/views/membership_views.py)
11. [../../student_app/views/onboarding_views.py](../../student_app/views/onboarding_views.py)
12. [../../student_app/views/pwa_views.py](../../student_app/views/pwa_views.py)
13. [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)
14. [../../student_app/models.py](../../student_app/models.py)
15. [../../templates/student_app/layout.html](../../templates/student_app/layout.html)
16. [../../templates/student_app/home.html](../../templates/student_app/home.html)
17. [../../templates/student_identity/login.html](../../templates/student_identity/login.html)
18. [../../static/css/student_app/app.css](../../static/css/student_app/app.css)
19. [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js)
20. [../../student_app/tests.py](../../student_app/tests.py)

## Verdade atual do runtime

Observacao confirmada localmente em `22/04/2026`:

1. `GET /aluno/` sem sessao responde `302 Found`
2. o destino atual do redirecionamento e `/aluno/auth/login/`
3. a mensagem aplicada para acesso anonimo e `Faca login para acessar o app.`

Traducao pratica:

1. a home do aluno existe
2. mas a porta publica real do fluxo e a tela de login
3. qualquer ajuste visual em `/aluno/` precisa considerar o estado anonimo e o estado autenticado

## Mapa mental rapido

Hoje o circuito do app funciona assim:

1. a raiz HTTP publica `aluno/` em [../../config/urls.py](../../config/urls.py)
2. o roteador do app quebra a superficie em auth, shell, membership, onboarding e PWA em [../../student_app/urls.py](../../student_app/urls.py)
3. o middleware bloqueia acessos anonimos a rotas protegidas em [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py)
4. a identidade do aluno entra por `student_identity` em [../../student_identity/views.py](../../student_identity/views.py)
5. o mixin base resolve cookie, membership, box ativo e device fingerprint em [../../student_app/views/base.py](../../student_app/views/base.py)
6. as telas principais vivem em [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)
7. o shell visual compartilhado nasce em [../../templates/student_app/layout.html](../../templates/student_app/layout.html)
8. o estilo principal do app fica em [../../static/css/student_app/app.css](../../static/css/student_app/app.css)
9. o PWA e o registro do service worker vivem em [../../student_app/views/pwa_views.py](../../student_app/views/pwa_views.py) e [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js)
10. a leitura de dashboard e WOD fica em [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)
11. os dados proprios do app ficam em [../../student_app/models.py](../../student_app/models.py)

## Mapa de rotas

### 1. Portaria canonica

Arquivo principal:

1. [../../config/urls.py](../../config/urls.py)

Aqui mora:

1. `path('aluno/', include('student_app.urls'))`
2. `path('renan/', include('student_app.public_urls'))`

Regra importante:

1. `/aluno/` e o app autenticado do aluno
2. `/renan/` e outra superficie, publica, voltada a treino publicado
3. misturar as duas leituras cria diagnostico errado

### 2. Rotas internas do app autenticado

Arquivo principal:

1. [../../student_app/urls.py](../../student_app/urls.py)

Aqui mora:

1. `/aluno/` -> `StudentHomeView`
2. `/aluno/grade/` -> `StudentGradeView`
3. `/aluno/wod/` e `/aluno/treino/` -> `StudentWodView`
4. `/aluno/rm/` -> `StudentRmView`
5. `/aluno/configuracoes/` -> `StudentSettingsView`
6. `/aluno/presenca/confirmar/` -> `StudentConfirmAttendanceView`
7. `/aluno/onboarding/` -> `StudentOnboardingWizardView`
8. `/aluno/aguardando-aprovacao/`, `/aluno/suspenso-financeiro/` e `/aluno/sem-box/` -> estados excepcionais
9. `/aluno/auth/*` -> `student_identity.urls`
10. `/aluno/manifest.webmanifest`, `/aluno/sw.js` e `/aluno/offline/` -> superficie PWA

## Back-end por corredor

### 1. Gate anonimo e sessao

Arquivos principais:

1. [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py)
2. [../../student_app/views/base.py](../../student_app/views/base.py)

Aqui mora:

1. protecao das rotas de `/aluno/`
2. leitura do cookie `octobox_student_session`
3. redirecionamento para login
4. resolucao de memberships ativas e box ativo
5. validacao de device fingerprint
6. redirecionamento para onboarding, suspensao financeira ou ausencia de box

Heuristica:

1. se `/aluno/` pula para login quando nao deveria, comece aqui
2. se a identidade abre mas cai em `sem-box` ou `suspenso-financeiro`, continue aqui
3. se o box ativo troca sozinho ou some, aqui e a primeira parada

### 2. Entrada de identidade

Arquivos principais:

1. [../../student_identity/urls.py](../../student_identity/urls.py)
2. [../../student_identity/views.py](../../student_identity/views.py)
3. [../../templates/student_identity/login.html](../../templates/student_identity/login.html)

Aqui mora:

1. login do aluno em `/aluno/auth/login/`
2. logout em `/aluno/auth/logout/`
3. invite individual e box invite
4. inicio e callback de OAuth
5. copy e CTA da tela de entrada

Traducao simples:

1. `student_identity` decide "quem e voce?"
2. `student_app` decide "o que voce pode ver agora?"

### 3. Shell autenticado do aluno

Arquivos principais:

1. [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py)
2. [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)

Aqui mora:

1. `StudentHomeView`
2. `StudentGradeView`
3. `StudentWodView`
4. `StudentRmView`
5. `StudentSettingsView`
6. `StudentConfirmAttendanceView`
7. leitura do dashboard e resolucao de `home_mode`
8. recomendacao de carga por `% RM`

Regra importante:

1. a home do aluno nao e estatica
2. `GetStudentDashboard` alterna entre `schedule_default` e `wod_active`
3. a home e como um semaforo inteligente: antes da aula mostra agenda, na janela do treino sobe o WOD

### 4. Estados excepcionais e troca de box

Arquivos principais:

1. [../../student_app/views/membership_views.py](../../student_app/views/membership_views.py)

Aqui mora:

1. pendencia de aprovacao
2. suspensao financeira
3. ausencia de box ativo
4. colagem de token de convite
5. troca de contexto entre boxes

### 5. Onboarding

Arquivos principais:

1. [../../student_app/views/onboarding_views.py](../../student_app/views/onboarding_views.py)
2. [../../student_app/views/onboarding_loader.py](../../student_app/views/onboarding_loader.py)
3. [../../student_app/workflows/onboarding_workflows.py](../../student_app/workflows/onboarding_workflows.py)

Aqui mora:

1. wizard de onboarding do aluno
2. reentrada da sessao pendente
3. conclusao de onboarding por convite ou link em massa

### 6. PWA

Arquivos principais:

1. [../../student_app/views/pwa_views.py](../../student_app/views/pwa_views.py)
2. [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js)
3. [../../templates/student_app/sw.js](../../templates/student_app/sw.js)

Aqui mora:

1. manifest
2. service worker
3. tela offline
4. registro do app como PWA com `scope /aluno/`

## Front-end por camada

### 1. Layout compartilhado

Arquivo principal:

1. [../../templates/student_app/layout.html](../../templates/student_app/layout.html)

Aqui mora:

1. sidebar desktop
2. topbar do aluno
3. seletor de box
4. navegacao mobile
5. inclusao do CSS principal
6. inclusao do JS do PWA

Se a pagina "parece quebrada" inteira:

1. olhe primeiro este arquivo
2. depois olhe `app.css`

### 2. Home

Arquivo principal:

1. [../../templates/student_app/home.html](../../templates/student_app/home.html)

Aqui mora:

1. os dois modos de home
2. hero de agenda
3. hero de WOD ativo
4. CTAs de confirmar presenca, abrir grade e abrir WOD

Observacao importante:

1. a home depende de `student_home_mode`
2. se a home estiver com layout certo e conteudo errado, normalmente o bug esta no `GetStudentDashboard`

### 3. Outras telas do shell

Arquivos principais:

1. [../../templates/student_app/grade.html](../../templates/student_app/grade.html)
2. [../../templates/student_app/wod.html](../../templates/student_app/wod.html)
3. [../../templates/student_app/rm.html](../../templates/student_app/rm.html)
4. [../../templates/student_app/settings.html](../../templates/student_app/settings.html)

Aqui mora:

1. leitura da agenda do aluno
2. leitura do WOD publicado
3. leitura dos records maximos
4. perfil e configuracoes

### 4. CSS

Arquivo principal:

1. [../../static/css/student_app/app.css](../../static/css/student_app/app.css)

Aqui mora:

1. tokens do app do aluno
2. shell grid
3. topbar
4. sidebar
5. cards
6. navegacao mobile
7. superfices de home, grade, WOD, RM e estados

Regra pratica:

1. este arquivo e a tinta da fachada
2. mudar classe aqui afeta varias telas de uma vez

### 5. Login do aluno

Arquivos principais:

1. [../../templates/student_identity/login.html](../../templates/student_identity/login.html)
2. [../../static/css/student_identity/login.css](../../static/css/student_identity/login.css)

Aqui mora:

1. tela de entrada
2. CTA de Google e Apple
3. copy de convite
4. fallback quando provider nao esta disponivel

## Estado e dominio proprio do app

Arquivos principais:

1. [../../student_app/models.py](../../student_app/models.py)
2. [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)

Aqui mora:

1. `StudentExerciseMax`
2. `SessionWorkout`
3. `SessionWorkoutBlock`
4. `SessionWorkoutMovement`
5. `StudentWorkoutView`
6. follow-up operacional do WOD
7. checkpoint semanal e gap de RM

Traducao simples:

1. o coach publica a regra do treino
2. o aluno carrega seu RM
3. o app junta os dois para sugerir carga

## Fluxo ponta a ponta

Leia o circuito oficial assim:

1. o usuario tenta abrir `/aluno/`
2. `StudentAuthMiddleware` verifica se a rota e protegida
3. sem cookie valido, o fluxo vai para `/aluno/auth/login/`
4. com identidade e membership validas, `StudentIdentityRequiredMixin` monta o runtime do aluno
5. `StudentHomeView` chama `GetStudentDashboard`
6. a view injeta contexto no template `templates/student_app/home.html`
7. `layout.html` aplica shell, navecacao e assets compartilhados
8. `app.css` veste a tela
9. `pwa.js` tenta registrar o service worker para o escopo `/aluno/`

## Onde procurar bugs por assunto

Use esta trilha:

1. `/aluno/` redireciona errado: [../../student_app/middleware/student_auth.py](../../student_app/middleware/student_auth.py) e [../../student_app/views/base.py](../../student_app/views/base.py)
2. login nao abre provider ou callback falha: [../../student_identity/views.py](../../student_identity/views.py)
3. box ativo errado ou troca de box falhando: [../../student_app/views/membership_views.py](../../student_app/views/membership_views.py)
4. home mostra modo errado entre Grade e WOD: [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py)
5. presenca nao confirma: [../../student_app/views/shell_views.py](../../student_app/views/shell_views.py) e [../../student_app/workflows/attendance_workflows.py](../../student_app/workflows/attendance_workflows.py)
6. WOD nao aparece ou carga recomendada vem errada: [../../student_app/application/use_cases.py](../../student_app/application/use_cases.py) e [../../student_app/models.py](../../student_app/models.py)
7. layout inteiro desalinhado: [../../templates/student_app/layout.html](../../templates/student_app/layout.html) e [../../static/css/student_app/app.css](../../static/css/student_app/app.css)
8. app nao instala como PWA ou offline falha: [../../student_app/views/pwa_views.py](../../student_app/views/pwa_views.py), [../../templates/student_app/sw.js](../../templates/student_app/sw.js) e [../../static/js/student_app/pwa.js](../../static/js/student_app/pwa.js)

## Riscos e guardrails

Existem quatro cuidados que valem ouro aqui:

1. nao trate a home `/aluno/` como tela unica; ela depende de autenticacao e de `home_mode`
2. nao misture o shell autenticado com a superficie publica de treino em `/renan/`
3. nao mude `layout.html` ou `app.css` sem lembrar que varias telas compartilham os mesmos blocos
4. nao mexa em sessao, membership ou fingerprint sem revisar `student_app/tests.py`, porque essa area e sensivel e quebra de forma silenciosa

## Melhor proximo passo para mexer na pagina

Se o objetivo agora for editar a experiencia de `/aluno/`, a ordem mais segura e:

1. decidir se a mudanca e de auth, shell, conteudo da home ou estilo
2. confirmar qual estado queremos testar: anonimo, autenticado com Grade ou autenticado com WOD
3. editar primeiro o template ou a view dona da experiencia
4. tocar no CSS compartilhado so depois, com cuidado para nao gerar regressao em `grade`, `wod`, `rm` e `settings`
