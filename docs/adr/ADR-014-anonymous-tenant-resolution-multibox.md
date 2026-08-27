# ADR-014 — Resolução de tenant em rotas anônimas do aluno, com N boxes ATIVOS

**Status:** Aceito
**Data:** 2026-08-26
**Contexto:** Onda 6 do plano de correção de tenancy/billing/autorização (docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md) — "matar o teto de 1 box". Onda 4 (namespace de cache por box) e Onda 1c (papel por box) já concluídas; essas duas dependências estavam bloqueando esta onda.

## Decisão

**Rejeitada** a abordagem originalmente esboçada no plano (middleware genérico de prefixo de path `/b/<slug>/` cobrindo as ~5 rotas anônimas que hoje dependem do fallback `SINGLE_ACTIVE_BOX`). **Adotada** uma correção cirúrgica: apenas o único ponto que genuinamente precisava de resolução por sinal explícito (o token assinado de `StudentSourceCaptureView`) ganha código novo — os outros quatro já degradam corretamente hoje, e continuam assim, sem mudança.

## Contexto

`SINGLE_ACTIVE_BOX` é uma strategy de fallback (documentada em [ADR-006](ADR-006-center-layer-tenant-resolution.md)) usada por dois facades do Center Layer — `student_identity/facade/tenant_resolver.py` e `auditing/services.py::_ensure_tenant_for_audit_write` — além de um call site que reimplementava a mesma lógica **fora** da facade (`catalog/views/student_views.py::StudentSourceCaptureView`, violando o anti-padrão que a própria ADR-006 proíbe). Ela só resolve quando existe **exatamente 1** `Box` com `status=ACTIVE`; com N≥2, retorna `None`.

O plano original (escrito um dia antes desta decisão) listou ~5 pontos de produção afetados e propôs um middleware novo, resolvendo tenant por um prefixo de URL (`/b/<slug>/`), inspirado — mas não idêntico a — `django_tenants.middleware.TenantSubfolderMiddleware`.

## Auditoria site-a-site dos ~5 pontos

| Local | O que faz | Tem sinal alternativo além de `SINGLE_ACTIVE_BOX`? |
|---|---|---|
| `catalog/views/student_views.py::StudentSourceCaptureView.dispatch` | Ativa tenant para ler um `Student` (TENANT_APP) a partir de um link público de qualificação de origem | **Sim** — o token assinado já nasce dentro do schema do box (é gerado a partir de um `Student` existente). Só não carregava essa informação. |
| `student_app/middleware/student_auth.py` (~linha 190) | Escreve `AuditEvent` sobre acesso anônimo a rota protegida do app do aluno, antes de redirecionar para login | Não — é o primeiro contato, sem cookie, sem token, sem identidade prévia. Escrita já é `try/except` best-effort. |
| `student_identity/views.py::StudentOAuthCallbackView._handle_callback` (~linha 186) | Ativa tenant só para permitir que o rate-limit do callback escreva `AuditEvent` | Não diretamente — mas o rate-limit em si (`check_student_flow_rate_limit`, `shared_support/security/fintech_throttles.py`) usa cache por IP, **não depende de tenant resolvido**. Só a auditoria do bloqueio é afetada, e o próprio código-fonte (`student_identity/oauth_loader.py:35-38`) já documenta isso como best-effort esperado. |
| `student_identity/views.py` (~linha 396, invite landing) | Escreve `AuditEvent` quando um `invite_token` é **inválido** | Não, por definição — se o token não resolve a nada, não há box para ativar. |
| `auditing/services.py::_ensure_tenant_for_audit_write` (Strategy 3) | Fallback genérico de qualquer `log_audit_event` sem tenant ativo | Parcialmente — Strategy 2 (Membership `is_primary_box` do `actor`) já cobre o caso mais comum (login de staff). Strategy 3 só entra quando não há actor ou o actor não tem primary_box — sem sinal, por definição. |

**Achado central:** dos 5 pontos, só o primeiro tem um sinal real e barato de capturar. Os outros quatro **não têm nenhuma informação disponível** sobre qual box ativar — são momentos genuinamente pré-identidade (primeiro contato anônimo, token inválido, ou call site sem acesso a request). Forçar uma resolução ali seria inventar sinal que não existe, não corrigir um bug.

## Por que o middleware de prefixo de path foi descartado

1. **Viola a ADR-006.** A regra explícita ("se precisar de nova estratégia, ela entra na facade, nunca um `connection.set_tenant()` ad-hoc em outro módulo") existe precisamente para não reintroduzir o padrão que o Center Layer eliminou.
2. **O próprio plano já excluiu `/aluno/` e `/renan/` do escopo** — por causa do cookie de sessão do aluno (`path=/aluno/` fixo), do Service Worker (`Service-Worker-Allowed: /aluno/`) e do `redirect_uri` do OAuth (fixo, cadastrado no console do Google). Mas 4 dos 5 pontos listados vivem **dentro** de `/aluno/*` — não sobra rota coerente para o middleware prefixar sem violar a própria exclusão que o plano definiu.
3. **Sem necessidade.** Nenhum dos 4 pontos remanescentes bloqueia funcionalidade real — todos são escrita de auditoria best-effort, já documentada como tal no código-fonte antes desta ADR existir.

## Opção escolhida

**Embutir `box_root_slug` no token assinado de source-capture.** `students/infrastructure/source_capture_links.py::build_student_source_capture_token` ganha parâmetro opcional `box_root_slug`; a emissão (`catalog/views/student_views.py::_build_student_source_capture_url`) passa o schema ativo no momento da emissão (contexto staff, já resolvido). A leitura (`StudentSourceCaptureView._activate_tenant_for_token`) decodifica o payload primeiro, resolve o `Box` por `schema_name`, e só cai no fallback `SINGLE_ACTIVE_BOX` para tokens emitidos **antes** desta mudança (até 30 dias em voo — mesmo `max_age` já existente).

Isso corrige, de quebra, o anti-padrão da ADR-006 nesse call site: a resolução deixa de ser reimplementada inline e passa a decodificar um sinal explícito, no espírito das outras strategies `_resolve_from_*` do Center Layer.

## Alternativas consideradas

- **Middleware de prefixo de path (`/b/<slug>/`), escopo reduzido às ~5 rotas** — descartada; ver seção anterior.
- **Parâmetro `state` do OAuth carregando `box_root_slug`** (`student_identity/oauth_state.py`, que já existe e já carrega `invite_token`) — investigada e descartada: o ponto de partida do fluxo (`StudentOAuthStartView`) só tem contexto de box quando **já** há `invite_token` — caso em que a Strategy 1 (`_resolve_from_invite_token`) já resolve, sem precisar de `state`. Para o login "frio" sem convite, o `StudentOAuthStartView` também não sabe qual box — não há sinal para embutir. Retornos de usuários existentes já são resolvidos corretamente por `EXISTING_IDENTITY_BY_SUBJECT`/`_BY_EMAIL` (busca por identidade, não por box), independente de quantos boxes estão ATIVOS.
- **Aceitar a degradação best-effort dos 4 pontos remanescentes sem qualquer mudança** — adotada, porque é o que já acontece hoje (código já documenta isso), e forçar uma correção ali exigiria inventar infraestrutura nova (ex.: subdomínio por box, `redirect_uri` por box) fora do escopo e do orçamento de risco desta onda.

## Consequências

- `SINGLE_ACTIVE_BOX` permanece no código como fallback pilot — não é removido, nem precisa ser, porque os call sites que ainda o usam são genuinamente best-effort ou pré-identidade.
- Tokens de source-capture emitidos antes desta mudança continuam funcionando enquanto o sistema operar com 1 box ATIVO (o cenário de hoje); passam a exigir esse mesmo cenário — sem regressão — assim que expiram (30 dias).
- **Auditoria de rate-limit do callback OAuth, de acesso anônimo redirecionado, e de invite inválido continuam silenciosamente ausentes em cenário N≥2 boxes sem sinal** — risco residual aceito e explícito, não um gap descoberto por acidente depois.
- Gate de saída da Onda 6 ("dois boxes ACTIVE simultâneos, rotas anônimas funcionando") é satisfeito apenas para o ponto que tinha sinal disponível — os outros quatro nunca prometeram funcionar sem sinal, então não há gate a cumprir ali.

## Referências

- [ADR-006](ADR-006-center-layer-tenant-resolution.md) — Center Layer, `SINGLE_ACTIVE_BOX`, anti-padrão de resolução ad-hoc.
- [ADR-008](ADR-008-audit-event-best-effort-public-paths.md) — filosofia de auditoria best-effort em paths públicos, que os 4 pontos remanescentes já seguem.
- `students/infrastructure/source_capture_links.py`, `catalog/views/student_views.py::StudentSourceCaptureView` — implementação.
- `tests/test_source_capture_multibox.py` — gate de saída, prova com 2 boxes `ACTIVE` simultâneos.
- `docs/plans/ondas-correcao-tenancy-billing-2026-08-25.md`, Onda 6 — plano original e o que mudou nele.
