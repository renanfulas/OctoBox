# ADR-003 — Middleware de autenticação do aluno separado do Django LoginRequired

**Status:** Aceito  
**Data:** 2026-04-21  
**Contexto:** Student OAuth onboarding polish

## Decisão

Rotas do aluno (`/aluno/*`) são protegidas por `StudentAuthMiddleware` (cookie `octobox_student_session`) e não pelo `LoginRequiredMixin` do Django (que verifica `request.user` do staff).

`STUDENT_LOGIN_URL` é uma setting separada de `LOGIN_URL` do staff.

## Por quê

O sistema tem dois contextos de autenticação distintos:
1. **Staff** — Django `auth.User` + session framework + `LOGIN_URL = /login/`
2. **Aluno** — cookie HMAC assinado `octobox_student_session` + `STUDENT_LOGIN_URL = /aluno/auth/login/`

Misturar os dois contextos causaria: staff logado acessando app do aluno, ou aluno sendo redirecionado para login do staff ao expirar sessão.

## Consequências

- Middleware intercepta `/aluno/*` exceto rotas públicas (auth, offline, manifest, sw)
- Respeita `student_pending_onboarding` no Django session para o fluxo de onboarding
- Emite `student_app.anonymous_access_redirected` para rastreio de acessos não autenticados
