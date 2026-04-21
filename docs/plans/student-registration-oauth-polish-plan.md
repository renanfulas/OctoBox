<!--
ARQUIVO: plano de polimento do fluxo de cadastro + OAuth do aluno.

TIPO DE DOCUMENTO:
- plano de execucao por ondas

AUTORIDADE:
- alta para qualquer tarefa que mexa no corredor de entrada do aluno

DOCUMENTOS PAIS:
- [student-access-invite-switch-corda.md](student-access-invite-switch-corda.md)
- [intelligent-student-onboarding-plan.md](intelligent-student-onboarding-plan.md)
- [../map/leads-intake-cadastro-alunos-map.md](../map/leads-intake-cadastro-alunos-map.md)

QUANDO USAR:
- antes de qualquer tarefa que altere invite landing, login social, callback OAuth, onboarding wizard ou student app home
- quando houver duvida sobre qual parte do corredor de entrada esta implementada e qual ainda esta aberta
- quando precisar saber o que pode ser mexido com seguranca e o que exige cuidado

POR QUE ELE EXISTE:
- o corredor de entrada do aluno ja tem base solida, mas ainda tem gaps de UX, redirects nao tratados e edge cases sem cobertura
- este plano transforma a base pronta em um fluxo fechado, testado e facil de evoluir sem bug

O QUE ESTE ARQUIVO FAZ:
1. fotografa o corredor atual de ponta a ponta
2. identifica cada ponto de risco real
3. organiza a implementacao em ondas curtas e seguras
4. define criterio de pronto por onda

PONTOS CRITICOS:
- nao mexer no modelo de identidade sem ler student-access-invite-switch-corda.md
- nao reescrever o callback OAuth; apenas fechar os gaps de redirect e mensagem
- nao criar wizard novo; usar o que ja existe em student_app/workflows/
- qualquer mudanca aqui precisa rodar o corredor de regressao inteiro antes de ir para main
-->

# Plano — Polimento do Fluxo de Cadastro + OAuth do Aluno

## Fotografia do corredor atual (2026-04-20)

### O que ja existe e funciona

```
[Staff cria invite]
        ↓
[Link enviado por WhatsApp ou email]
        ↓
/aluno/invite/<token>/          → StudentInviteLandingView    ✓
/aluno/box-invite/<token>/      → StudentBoxInviteLandingView ✓
        ↓
/aluno/auth/login/?invite=<token>  → StudentSignInView        ✓
        ↓
[Botoes Google / Apple]
        ↓
/aluno/auth/oauth/<provider>/start/?invite=<token>
        → StudentOAuthStartView                               ✓
        → build_oauth_state(provider, invite_token)          ✓
        ↓
[Redirect externo: Google / Apple]
        ↓
/aluno/auth/oauth/<provider>/callback/
        → StudentOAuthCallbackView                           ✓
        → valida state, troca code, resolve identidade       ✓
        → resolve jornada (mass / lead / registered)        ✓
        ↓
[Jornada 1 — MASS_BOX_INVITE]
        → store_pending_student_onboarding()                 ✓
        → redirect student-app-onboarding                   ✓
        → OnboardingWorkflow.complete_mass_onboarding()      ✓

[Jornada 2 — IMPORTED_LEAD_INVITE]
        → attach_student_session_cookie()                    ✓
        → redirect student-app-onboarding                   ✓
        → OnboardingWorkflow.complete_imported_lead_onboarding() ✓

[Jornada 3 — REGISTERED_STUDENT_INVITE]
        → attach_student_session_cookie()                    ✓
        → redirect student-app-home                         ✓
```

### O que esta aberto ou fragil

| # | Ponto | Tipo de risco |
|---|-------|--------------|
| 1 | `StudentInviteLandingView` nao valida se o invite ainda e valido antes de mostrar a tela | UX — aluno ve landing de invite expirado sem mensagem clara |
| 2 | `StudentBoxInviteLandingView` nao valida se o link em massa ainda pode aceitar antes de mostrar a tela | UX — aluno tenta entrar num link pausado sem feedback |
| 3 | A tela de login (`/aluno/auth/login/`) nao exibe mensagem de contexto quando invite_token esta presente | UX — aluno nao sabe que esta entrando por um convite especifico |
| 4 | `StudentOAuthStartView` nao valida se o provider esta configurado *antes* de construir a URL de authorize | BUG — se settings mudarem no deploy, gera redirect para URL invalida em vez de mensagem clara |
| 5 | Callback com `invite_token` invalido apos OAuth completado redireciona para login sem mensagem suficiente | UX — aluno completa OAuth no Google e cai num login limpo sem saber o que aconteceu |
| 6 | A jornada `MASS_BOX_INVITE` leva para `student-app-onboarding` mas nao valida se o payload de sessao chegou corretamente antes de renderizar o wizard | BUG — se sessao expirar entre callback e wizard, o onboarding renderiza vazio |
| 7 | Nao existe redirect de fallback para `/aluno/auth/login/` quando o aluno acessa `/aluno/` sem sessao ativa | BUG — 403 ou 500 em vez de redirect para login |
| 8 | A tela de login nao trata o caso de provedor nao configurado visualmente (botao aparece mas falha ao clicar) | UX — botao morto confunde o aluno |
| 9 | Sem throttle dedicado para `StudentBoxInviteLandingView` (o throttle individual existe, o do box-invite nao) | Seguranca — enumeracao de links em massa sem custo |
| 10 | O `record_student_onboarding_event` em `StudentBoxInviteLandingView` nao e chamado quando `box_invite_link` e None (link invalido) | Observabilidade — landing invalida nao gera evento auditavel |

---

## Tres frases de arquitetura que guiam tudo

```
1. Invite decide contexto. OAuth decide identidade.
2. Redirect sem mensagem e redirect perdido.
3. Sessao expirada entre callback e wizard e o bug mais silencioso do fluxo.
```

---

## Ondas de implementacao

### Onda 1 — Fechar os redirects mudos (baixo risco, alto impacto de UX)

**Objetivo:** nenhum redirect sem mensagem. O aluno sempre sabe o que aconteceu.

**Escopo exato:**

```
student_identity/views.py
  StudentInviteLandingView.get_context_data()
    → adicionar: valida invite.is_expired e invite.accepted_at
    → se expirado: renderiza landing com flag expired=True
    → template mostra mensagem "Este convite expirou. Fale com a recepção."

  StudentBoxInviteLandingView.get_context_data()
    → adicionar: valida box_invite_link.can_accept
    → se link pausado/esgotado: renderiza landing com flag unavailable=True
    → template mostra mensagem "Este link nao esta mais disponivel."

  StudentSignInView.get_context_data()
    → se invite_token presente: adicionar invite_context_label ao context
    → template mostra banner discreto "Voce esta entrando por convite do [box_name]"

  StudentOAuthCallbackView._handle_callback()
    → se invite_token invalido pos-OAuth: messages.error com texto especifico
    → "O convite informado nao foi encontrado ou expirou. Tente entrar sem convite."
```

**Criterio de pronto:**
- Landing de invite expirado mostra mensagem, nao tela em branco
- Landing de box-invite pausado mostra mensagem
- Tela de login mostra contexto de convite quando presente
- Callback com invite invalido redireciona com mensagem legivel

**Risco de regressao:** baixo — apenas adiciona contexto ao render, nao altera fluxo de auth

---

### Onda 2 — Guardar a sessao de onboarding contra expiração (risco médio)

**Objetivo:** o aluno nunca chega no wizard com sessao vazia.

Este e o bug mais silencioso do fluxo. O aluno completa o OAuth no Google, o callback salva o payload na sessao, mas se o aluno demorar mais de X minutos (timeout de sessao), o wizard abre vazio e quebra.

**Escopo exato:**

```
student_app/views/onboarding_loader.py
  load_pending_student_onboarding()
    → ja existe, mas o chamador nao trata None de forma clara

student_app/views/ [view que renderiza o wizard]
  dispatch() ou get()
    → se load_pending_student_onboarding() retornar None:
      → redirect para student-identity-login com messages.warning
      → "Sua sessao expirou durante o cadastro. Tente novamente."
    → essa validacao precisa acontecer ANTES de qualquer render

student_identity/oauth_journeys.py
  handle_student_special_oauth_journey()
    → garantir que store_pending_student_onboarding() sempre salva
      box_root_slug e journey, mesmo que outros campos estejam vazios
    → adicionar validacao de payload minimo antes de redirect para wizard
```

**Criterio de pronto:**
- Acesso direto a `/aluno/app/onboarding/` sem sessao redireciona para login com mensagem
- Sessao com payload incompleto nao renderiza wizard quebrado
- Teste: simular sessao expirada entre callback e wizard

**Risco de regressao:** medio — altera o dispatch do wizard. Rodar suite completa de onboarding antes de mergear.

---

### Onda 3 — Botoes de provider morto e fallback de configuracao (baixo risco)

**Objetivo:** botao que nao funciona nao aparece.

```
student_identity/views.py
  StudentSignInView.get_context_data()
    → google_available e apple_available ja existem no context ✓
    → garantir que template usa esses flags para esconder (nao desabilitar) o botao
    → se nenhum provider disponivel: mostrar mensagem "Entre em contato com a recepção para acessar o app."

student_identity/oauth_providers.py
  build_provider()
    → ja levanta OAuthProviderError ✓
    → garantir que a mensagem mapeada em _map_provider_error e suficientemente clara
```

**Criterio de pronto:**
- Sem GOOGLE_CLIENT_ID configurado: botao Google some da tela (nao aparece cinza)
- Sem nenhum provider configurado: tela mostra mensagem de contato

**Risco de regressao:** muito baixo — apenas template logic

---

### Onda 4 — Throttle do box-invite landing e auditoria de landing invalida (segurança)

**Objetivo:** fechar o gap de enumeracao de links em massa.

```
student_identity/views.py
  StudentBoxInviteLandingView.dispatch()
    → adicionar throttle similar ao StudentInviteLandingView
    → rate limit: mesmos parametros de STUDENT_INVITE_LANDING_RATE_LIMIT_*
    → registrar AuditEvent quando rate limited

  StudentBoxInviteLandingView.get_context_data()
    → se box_invite_link e None: registrar AuditEvent com token tentado
    → "student_box_invite_landing.invalid_token_accessed"
    → isso fecha o gap de observabilidade do ponto 10
```

**Criterio de pronto:**
- Acesso repetido a box-invite landing gera 429 igual ao invite individual
- Landing com token invalido gera AuditEvent auditavel
- Teste unitario cobrindo o throttle do box-invite

**Risco de regressao:** baixo — segue o mesmo padrao ja existente no StudentInviteLandingView

---

### Onda 5 — Redirect de fallback para aluno sem sessao (bug silencioso)

**Objetivo:** nunca deixar o aluno ver 403 ou 500 quando chega em rota protegida sem sessao.

```
student_app/views/ [middleware ou mixin de autenticacao do aluno]
  → verificar como a autenticacao do aluno e feita hoje
  → se usa cookie proprio (student_session_cookie): garantir que a view
    de fallback redireciona para student-identity-login
  → se usa LoginRequiredMixin do Django: confirmar que LOGIN_URL esta
    apontando para a rota certa do aluno (nao do staff)

config/settings/base.py
  → verificar se LOGIN_URL esta configurado corretamente para o contexto do aluno
  → se necessario, adicionar STUDENT_LOGIN_URL separado
```

**Criterio de pronto:**
- GET /aluno/app/ sem sessao → redirect para /aluno/auth/login/ (nao 403)
- GET /aluno/app/onboarding/ sem sessao → redirect com mensagem
- Teste smoke cobrindo acesso anonimo nas rotas principais do aluno

**Risco de regressao:** medio — mexe na autenticacao. Rodar todos os testes de student_identity e student_app antes de mergear.

---

## Ordem recomendada de execucao

```
Onda 3  (mais facil, zero risco)          → faz hoje
Onda 1  (alto impacto UX, baixo risco)   → faz amanha
Onda 4  (seguranca, padrao ja existe)    → faz junto com onda 1
Onda 2  (risco medio, precisa de teste)  → faz depois com suite completa
Onda 5  (risco medio, precisa de teste)  → faz depois da onda 2
```

---

## Suite de regressao obrigatoria antes de cada merge

Estes sao os testes que precisam passar sem nenhuma falha antes de qualquer onda ir para main:

```bash
python manage.py test student_identity.tests -v 2
python manage.py test student_app.tests -v 2
```

Testes especificos a olhar:
- `test_smoke_open_box_invite_waits_for_approval_then_student_enters_home`
- `test_smoke_staff_creates_individual_invite_and_student_reaches_home_in_grade_mode`
- `test_smoke_student_oauth_reaches_home_in_wod_mode_when_attendance_window_is_active`
- `test_mass_box_invite_redirects_to_onboarding_wizard`
- `test_imported_lead_invite_redirects_to_reduced_onboarding`
- `test_registered_student_invite_redirects_directly_to_app_with_funnel_events`

---

## Criterio de pronto global (o fluxo esta redondinho quando)

```
[ ] 1. Aluno abre link de invite expirado → ve mensagem clara, nao tela em branco
[ ] 2. Aluno abre box-invite pausado → ve mensagem clara, nao tela em branco
[ ] 3. Aluno ve tela de login → sabe que esta entrando por convite (se vier de invite)
[ ] 4. Aluno completa OAuth com invite invalido → ve mensagem clara, nao tela de login limpa
[ ] 5. Aluno demora no OAuth e sessao expira → ve mensagem de reingresso, nao wizard quebrado
[ ] 6. Nenhum provider configurado → aluno ve mensagem de contato, nao botao morto
[ ] 7. Acesso anonimo a rota protegida do aluno → redirect para login, nao 403 ou 500
[ ] 8. Rate limit de box-invite landing funcionando igual ao invite individual
[ ] 9. Landing invalida (token nao existe) gera AuditEvent
[ ] 10. Suite completa de student_identity + student_app passando sem falha
```

---

## O que NAO fazer neste plano

```
✗ Nao reescrever o callback OAuth — a logica esta correta, apenas os redirects precisam fechar
✗ Nao criar wizard novo — o OnboardingWorkflow ja existe e funciona
✗ Nao alterar StudentIdentity, StudentAppInvitation ou StudentBoxInviteLink — modelos corretos
✗ Nao mudar as URLs publicas — rotas estabilizadas no contrato de shell
✗ Nao adicionar login social para staff neste plano — corredor separado, risco separado
```
