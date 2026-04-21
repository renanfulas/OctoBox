# ADR-001 — Invite token fora da query string observável

**Status:** Aceito  
**Data:** 2026-04-21  
**Contexto:** Student OAuth onboarding polish

## Decisão

Migrar `invite_token` de query param (`?invite=<token>`) para cookie HttpOnly `student_invite_pending` com TTL de 15 minutos (900s), SameSite=Lax, Secure em produção.

## Por quê

Query string vaza em:
- Access log do Nginx (linha de request)
- Header `Referer` para terceiros ao clicar em link externo
- Extensões de browser e barras de histórico
- Analytics/APM que capturam URLs completas

Um token que funciona como permissão de entrada não pode estar em canal observável.

## Consequências

- URL de login fica limpa: `/aluno/auth/login/` sem parâmetros
- Fluxo: landing seta cookie → OAuth start lê cookie → embute no HMAC state → callback extrai do state
- Pequena complexidade adicional de cookie, aceita em troca de higiene de secrets
- Fallback: cookie ausente → `request.GET.get('invite')` (compatibilidade com links antigos até expiração de cache)
