<!--
ARQUIVO: regras de comportamento para agentes de IA neste repositório.
NÃO é um doc de navegação (isso é o README + docs/). São regras curtas que o agente segue.
Mantenha enxuto: cada linha aqui custa contexto em TODA sessão.
-->

# CLAUDE.md — regras para agentes no OctoBox

## Navegação do repositório (RAG-first para "onde/como funciona")

Para perguntas de **"onde fica X"** ou **"como funciona X"**, consulte o RAG **antes** de varrer arquivos:

```
# Windows (PowerShell) — use SEMPRE o Python do .venv; o `python` global não tem Django
.\.venv\Scripts\python.exe manage.py search_project_knowledge "<pergunta>"

# Linux / macOS
./.venv/bin/python manage.py search_project_knowledge "<pergunta>"
```

- Índice SHARED no schema `public`. Pré-requisito: Postgres no ar (dev local: porta **5433**).
- Erro `ModuleNotFoundError: No module named 'django'` = você chamou o `python` global. Troque pelo do `.venv` (comando acima) — não instale Django global.
- Se o RAG não responder (Postgres fora, índice vazio), **pare e ative antes de continuar**: suba o Postgres e reindexe com `.\.venv\Scripts\python.exe manage.py ingest_project_knowledge`.
- Sem Postgres / offline: `.claude/skills/navigate-octobox/driver.py find "<pergunta>"`.
- **Não** use o RAG para um símbolo que você **já conhece** — aí `Grep` é mais barato e direto.
- Medido: para o caso frio (não sei a palavra-chave), o RAG custa ~50x menos tokens que o grep cego. Para símbolo conhecido, ~6x ou menos — então não force "RAG antes de tudo".
- Skill de navegação completa: `/navigate-octobox`.

## Qual doc vence (precedência)

Em conflito/ambiguidade/idade entre docs, a fonte de verdade é
[docs/reference/documentation-authority-map.md](docs/reference/documentation-authority-map.md).
Runtime real e testes vencem qualquer doc.

## Skills do projeto — roteamento por contexto

> **Regra (importante):** invoque **no máximo UMA** skill, e **só quando a tarefa casar** com o gatilho.
> Não carregue skills em lote nem especulativamente — cada uma custa contexto. Se nada casar, trabalhe direto.
> O handle de invocação é o que está em `backtick`.

| Quando o trabalho é… | Use |
|---|---|
| achar **onde** algo está / **como** funciona / qual doc vence / consultar o RAG | `navigate-octobox` |
| **bug**, erro, stack trace, "não reproduz" | `master_debugger` — *Passo 0: monta o cluster (impl + testes + callers) via RAG antes de editar; não edite antes disso* |
| fechar um **PR** com aprendizado não-óbvio | `pr-lesson` — *destila lição em `docs/decisions/`; se foi óbvio/mecânico, `SKIP`* |
| **arquitetura** de sistema, escala, fronteiras de domínio, decidir refactor grande | `software-architecture-chief` |
| **banco**, PostgreSQL, schema, índices, performance de query, multitenancy/isolamento | `octobox-sql-architect` |
| **performance** de runtime, latência, throughput, eficiência de pacote | `performance_architect` (OctoBox High Performance Architect) |
| **segurança defensiva**, hardening, anti-abuso/anti-cheat, throttles | `security_performance_engineer` (OctoBox Security & Anti-Cheat Engineer) |
| **ofensivo**/red-team, cripto, forense, zero-trust, higiene de dados | `white_hat_hacker` (OctoBox White Hat Hacker) |
| **criar** UI nova distintiva / landing / redesign com direção artística forte | `frontend-aesthetic-director` |
| aplicar o **tema oficial** OctoBox (Luxo Futurista 2050) — tokens, hero, shell, atmosfera | `octobox-design` *(vence em tema visual)* |
| **arquitetura/expansão de CSS** Django (organizar, não embelezar) | `css_front_end_architect` |
| **auditar/limpar** débito de CSS/HTML, overrides, código morto, refactor seguro de front | `octobox-ui-cleanup-auditor` |
| UX de **checkout/pagamento/cobrança** | `ui_ux_payments` (OctoBox UI/UX Payments Expert) |
| escrever/depurar **prompts**, instruções de agente, eval | `prompt-engineer` (rápido: `prompt-daily`) |

**Desambiguação rápida:**
- Front-end: **criar bonito** → `frontend-aesthetic-director` · **tema oficial** → `octobox-design` · **organizar CSS** → `css_front_end_architect` · **limpar débito** → `octobox-ui-cleanup-auditor`.
- Segurança: **defesa/hardening** → `security_performance_engineer` · **ataque/forense** → `white_hat_hacker`.
- Arquitetura: **sistema/escala** → `software-architecture-chief` · **banco** → `octobox-sql-architect`.

## Skills `octobox-*` (pacotes novos) vs. skills legadas

Três pacotes importados vivem em `.claude/skills/` com prefixo `octobox-` e `disable-model-invocation: true` (a descrição **não** entra no contexto; só rodam quando o usuário chama `/nome`):

- **Octobox Marketing** → `octobox-<nome>` (51 skills: `octobox-copywriting`, `octobox-cro`, `octobox-emails`, `octobox-ads`…)
- **Octobox Social Media Mentor** → `octobox-social-mentor-<nome>` (17 skills)
- **Octobox Taste Design UI/UX Personality** → `octobox-taste-design-ui-ux-personality` (principal) e `octobox-taste-<variante>` (13 skills)

**Roteadores de pacote:** chamar `/octobox-marketing`, `/octobox-social-mentor` ou `/octobox-taste-design-ui-ux-personality` ativa o pacote inteiro; escolha 1 a 5 skills do pacote conforme o contexto, leia o `SKILL.md` de cada e siga.

**Regra de precedência:**
- Se o usuário **chamou** uma `octobox-*` pelo nome, **só ela** vale para a tarefa.
- Se **não chamou**, nunca dispare uma `octobox-*` por conta própria: use a skill legada equivalente (ex.: texto/copy → `copywriter-sintese`; UI/tema → `octobox-design` ou `frontend-aesthetic-director`; CSS → `css_front_end_architect`; prompts → `prompt-engineer`).

**Pré-requisitos externos (lembrar o usuário ao usar):**
- `octobox-social-mentor-reels-scripting` exige as variáveis `APIFY_API_TOKEN` e `GOOGLE_AI_API_KEY`.
- `octobox-social-mentor-niche-research` exige a extensão Claude for Chrome.

## Gotchas de runtime que você precisa saber

- **Só roda em PostgreSQL.** `django-tenants` não tem caminho SQLite — `migrate`/`runserver` em SQLite quebra com `'DatabaseWrapper' object has no attribute 'set_schema'`. Cluster dev local: porta 5433 (ver memória `octobox-local-postgres-cluster`).
- **O RAG (`knowledge`) é SHARED** (índice único no `public`, indexado uma vez — não por box). O índice é **descartável** (regenera com `ingest_project_knowledge`); o que é durável é o markdown versionado (incl. `docs/decisions/`).
- Rodar testes: ver [docs/testing/README.md](docs/testing/README.md) (pytest + Postgres + `--create-db --migrations`).
- **`config/urls_public.py` é código morto.** `ROOT_URLCONF` é sempre `config.urls` — nenhum middleware troca `request.urlconf` (django-tenants entra só como app/DB router, não como middleware de request). Toda rota de `urls_public.py` já existe em `config/urls.py`. A isolação real de "roda sem tenant" é `control.middleware.TenantBySessionMiddleware.PUBLIC_SCHEMA_PATHS` (whitelist de path, não domínio/porta). Não editar `urls_public.py` esperando efeito em produção. Plano de mitigação: [docs/plans/urls-public-dead-code-mitigation-corda.md](docs/plans/urls-public-dead-code-mitigation-corda.md).

## Manter o índice fresco (opcional, recomendado)

Hook git que reindexa o RAG local após cada merge/pull:

```
git config core.hooksPath scripts/hooks
```

(O hook no-op se o Postgres estiver fora do ar — nunca bloqueia um merge.)
