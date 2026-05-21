# ADR-007 — Higiene de PUBLIC_SCHEMA_PATHS no TenantBySessionMiddleware

**Status:** Aceito
**Data:** 2026-05-19
**Contexto:** Sprint 4 schema-per-tenant, Bucket B+C (middleware + API discovery)

## Decisão

`TenantBySessionMiddleware` aplica 2 regras de higiene em paths públicos:

1. **Save/restore do tenant ao redor da request:** ao entrar em path público,
   salva `connection.tenant` anterior; após `get_response` retornar, restaura.
   O DURANTE do request continua em `public` (proteção C1 contra estado
   herdado), mas o estado pós-request não vaza entre requests.

2. **`PUBLIC_SCHEMA_EXACT_PATHS` ao lado de `PUBLIC_SCHEMA_PATHS`:** matches
   `path == prefix` (igual literal) em vez de `path.startswith(prefix)`. Usado
   para discovery endpoints onde o pai é público mas filhos são privados.
   Exemplo: `/api/` (root) e `/api/v1/` (manifest) são públicos; `/api/v1/finance/`
   é privado e exige tenant.

## Por quê

**Sobre save/restore (regra 1):**

`Client.get('/aluno/auth/login/').assertRedirects(response, url)` faz uma
**segunda** Client.get pro URL destino. Se o middleware deixou `connection`
em `public` após o primeiro request, a segunda assertion do teste
(`AuditEvent.objects.filter().exists()`) roda em `public` — onde o tabela
TENANT_APP não existe — e falha com `ProgrammingError`.

Em prod com CONN_MAX_AGE/pool, o efeito é mitigado por garbage-collection
de conexão. Em testes, a conexão é reusada dentro do test method e o vazamento
é determinístico. Save/restore protege ambos.

**Sobre exact paths (regra 2):**

Implementação anterior usava `startswith` exclusivamente. Adicionar `/api/` ao
PUBLIC_SCHEMA_PATHS capturava também `/api/v1/finance/freeze-student/` — quebrava
auth + tenant. Inverso (sem `/api/`) → discovery anônimo recebia 302→/login/.

Exact match resolve o conflito sem afrouxar a proteção dos subpaths privados.

## Consequências

- Recuperou 1 teste do anonymous redirect (Bucket B cluster 4) — save/restore.
- Recuperou 4 testes de API (api root, manifest, health, finance) — exact paths.
- Recuperou 1 teste de marketing landing — exact path em `/`.
- Recuperou 2 testes do public_landing (efeito colateral).

## Anti-pattern proibido

- Adicionar path ao `PUBLIC_SCHEMA_PATHS` sem verificar se sub-rotas privadas
  começam com o mesmo prefix. Se sim, usar `PUBLIC_SCHEMA_EXACT_PATHS`.
- Confiar em `connection.set_schema_to_public()` em uma view de path público
  para "limpar" estado — o middleware já faz isso na entrada, e o save/restore
  cuida do pós.

## Referências

- `control/middleware.py::TenantBySessionMiddleware`
- `control/middleware.py::PUBLIC_SCHEMA_EXACT_PATHS`
