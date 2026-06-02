<!--
ARQUIVO: regras de comportamento para agentes de IA neste repositório.
NÃO é um doc de navegação (isso é o README + docs/). São regras curtas que o agente segue.
Mantenha enxuto: cada linha aqui custa contexto em TODA sessão.
-->

# CLAUDE.md — regras para agentes no OctoBox

## Navegação do repositório (RAG-first para "onde/como funciona")

Para perguntas de **"onde fica X"** ou **"como funciona X"**, consulte o RAG **antes** de varrer arquivos:

```
python manage.py search_project_knowledge "<pergunta>"      # índice SHARED no schema public
```

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

## Gotchas de runtime que você precisa saber

- **Só roda em PostgreSQL.** `django-tenants` não tem caminho SQLite — `migrate`/`runserver` em SQLite quebra com `'DatabaseWrapper' object has no attribute 'set_schema'`. Cluster dev local: porta 5433 (ver memória `octobox-local-postgres-cluster`).
- **O RAG (`knowledge`) é SHARED** (índice único no `public`, indexado uma vez — não por box). O índice é **descartável** (regenera com `ingest_project_knowledge`); o que é durável é o markdown versionado (incl. `docs/decisions/`).
- Rodar testes: ver [docs/testing/README.md](docs/testing/README.md) (pytest + Postgres + `--create-db --migrations`).

## Manter o índice fresco (opcional, recomendado)

Hook git que reindexa o RAG local após cada merge/pull:

```
git config core.hooksPath scripts/hooks
```

(O hook no-op se o Postgres estiver fora do ar — nunca bloqueia um merge.)
