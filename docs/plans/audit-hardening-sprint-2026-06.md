<!--
ARQUIVO: quadro de sprint para correcao dos achados da auditoria de saude do projeto de 2026-06-11.

TIPO DE DOCUMENTO:
- plano curto de execucao (sprint de correcao)

AUTORIDADE:
- alta enquanto o sprint estiver aberto
- historica apos o fechamento (marcar status final e tratar como referencia)

DOCUMENTO PAI:
- [../../README.md](../../README.md)

QUANDO USAR:
- quando a duvida for qual correcao da auditoria executar agora, em que ordem e com qual criterio de pronto

POR QUE ELE EXISTE:
- transforma os achados da auditoria em frente ativa com gates objetivos, em vez de diagnostico solto em conversa.
- separa correcao (este sprint) de evolucao (trilhos proprios ja documentados), para o sprint ser pequeno e fechavel.

O QUE ESTE ARQUIVO FAZ:
1. registra os 6 achados da auditoria com evidencia e prioridade.
2. define acoes, criterio de pronto e validacao por item.
3. define a ordem de execucao e o criterio de fechamento do sprint.
4. lista explicitamente o que NAO entra neste sprint.

PONTOS CRITICOS:
- S1 bloqueia o deploy de producao: o gate do deploy exige Security Scanners verde no mesmo SHA, e o scanner falha desde 2026-06-08.
- este quadro precisa continuar honesto: item so vira "pronto" com validacao executada e link de PR.
- ao fechar o sprint, atualizar o registro de progresso e marcar o documento como fechado.
-->

# Sprint de hardening pós-auditoria (2026-06)

## Contexto

Auditoria de saúde do projeto executada em 2026-06-11, com base em:

1. docs canônicos (README, mapa de autoridade, modelo arquitetural, plano de crescimento)
2. RAG offline (`.claude/skills/navigate-octobox/driver.py`, porque o Postgres local estava fora do ar — ver S5)
3. evidência de runtime: runs reais do GitHub Actions, logs de falha, git log, requirements e tamanho dos apps

Veredito da auditoria: **fundação sólida; os problemas encontrados são de manutenção, não estruturais.** Este sprint corrige exatamente esses problemas.

Regra do sprint:

1. itens pequenos, fecháveis e com validação objetiva
2. nada de misturar com evolução (read model, Fase 2, fatias do boxcore) — isso tem trilho próprio
3. um PR por item, sempre que possível

## Legenda de status

1. aberto
2. em execução
3. pronto (com data e link do PR)

---

## S1 — P0 — Subir Django 6.0.5 para 6.0.6 (PYSEC-2026-199)

Status:

1. em execução — PR [#123](https://github.com/renanfulas/OctoBox/pull/123) aberto em 2026-06-11; `pip-audit` local no requirements novo: **No known vulnerabilities found**; CI do PR com full-test-suite, security-audit e 3 seeds de ordem **verdes** em Django 6.0.6; na suíte local, 5 falhas em `tests/test_tenant_boundary.py` foram isoladas por A/B como problema do ambiente local (mesma assinatura em 6.0.5 e 6.0.6; verdes no CI) — registradas como evidência no S5

Problema e evidência:

1. o workflow `Security Scanners 🛡️` falha desde 2026-06-08: `pip-audit` encontrou 5 vulnerabilidades conhecidas no Django 6.0.5 (ID `PYSEC-2026-199`; versões com fix: 5.2.15 e 6.0.6)
2. produção roda esse Django (VPS, deploy via [deploy-vps.yml](../../.github/workflows/deploy-vps.yml))
3. o job `verify-gates` do deploy exige Security Scanners verde no mesmo SHA — **o próximo push na main bloqueia o deploy até este item fechar**

Ações:

1. em [requirements.txt](../../requirements.txt), mudar `Django==6.0.5` para `Django==6.0.6`
2. atualizar a referência "compativeis com Django==6.0.5" no cabeçalho de [requirements_test.txt](../../requirements_test.txt)
3. rodar a suite completa com Postgres (`python -m pytest --create-db --migrations -n 4 -q`)
4. confirmar com `pip-audit -r requirements.txt` que a vulnerabilidade sumiu
5. abrir PR explicando que isso desbloqueia o gate de deploy

Critério de pronto:

1. Security Scanners verde na main
2. deploy de produção desbloqueado

---

## S2 — P0 — E2E nightly verde de novo + alarme de falha do nightly

Status:

1. em execução — PR [#122](https://github.com/renanfulas/OctoBox/pull/122) aberto em 2026-06-11; validado local (antes `1 passed + 5 errors`, depois `5 passed`) e com **dispatch manual do workflow verde no branch**

Problema e evidência:

1. o workflow `E2E Tests (Nightly)` **nunca teve um run verde**: 55 falhas em 55 runs desde a criação em 2026-05-21, e ninguém percebeu (run agendado não notifica por padrão)
2. causa raiz dupla, confirmada no PR: (a) o sync API do Playwright mantém um event loop asyncio no thread principal do pytest e o guard async do Django derruba o flush do pytest-django em setup/teardown (`SynchronousOnlyOperation`); (b) `sync_playwright()` aninhado no teste de contrato visual — segundo bug, mascarado pelo primeiro
3. a hipótese inicial da auditoria (regressão por `playwright` transitivo não pinado) **não se confirmou** — todos os runs instalaram 1.60.0; o pin entra mesmo assim como higiene de reprodutibilidade

Ações:

1. definir `DJANGO_ALLOW_ASYNC_UNSAFE=true` na importação de [tests/e2e/conftest.py](../../tests/e2e/conftest.py) — correção documentada pelo Django para browser automation + live_server, com escopo restrito ao E2E
2. reescrever o teste de contrato visual para usar a fixture `browser` do pytest-playwright (elimina o sync API aninhado e a sensibilidade à ordem)
3. pinar `playwright==1.60.0` em [requirements_test.txt](../../requirements_test.txt)
4. adicionar alarme: step final no workflow que abre/atualiza issue com marcador `[e2e-nightly]` quando um run **agendado** falhar (o gap real foi ninguém ver o vermelho)

Critério de pronto:

1. `gh workflow run e2e-nightly.yml` termina verde (já demonstrado no branch do PR)
2. falha agendada futura gera notificação visível (issue criada automaticamente)

---

## S3 — P1 — Re-medir cobertura e subir o fail_under

Status:

1. aberto

Problema e evidência:

1. o baseline de cobertura é de 2026-05-21 (74,7%, gate em 72) e o playbook em [docs/testing/README.md](../testing/README.md) manda re-medir a cada sprint
2. desde o baseline entraram +123 testes (Sprints 1–9) e várias frentes de 100% de cobertura (presenters de `student_identity`) — a folga provavelmente já passou de 5 pp, o gatilho oficial do ratchet

Ações:

1. medir: `python -m pytest --create-db --migrations -n 4 --cov --cov-report=term -q`
2. aplicar a regra oficial: novo `fail_under` = cobertura_atual − 2 pp (nunca mais que isso)
3. atualizar [.coveragerc](../../.coveragerc) e o comentário de baseline
4. PR com a medição no corpo

Critério de pronto:

1. `fail_under` atualizado conforme a regra do playbook
2. CI verde na main com o novo gate

---

## S4 — P1 — Sincronizar docs de alta autoridade defasados

Status:

1. em execução — PR [#124](https://github.com/renanfulas/OctoBox/pull/124) aberto em 2026-06-11; os dois docs foram corrigidos, o RAG foi reindexado (1514 docs, 1028 chunks) e o smoke test confirmou a seção corrigida como primeiro resultado; este quadro entra no mesmo PR

Problema e evidência:

1. [architecture-growth-plan.md](../architecture/architecture-growth-plan.md) (autoridade alta) ainda afirmava "tudo vive dentro do boxcore", "não existe API versionada / integrações / jobs" — falso desde a criação dos apps `api/`, `integrations/`, `jobs/` e da virada multi-tenant
2. [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md) (data-base 2026-04-13) tratava multitenancy como filosofia de Fase 3 distante — mas o schema-per-tenant entrou em produção em 2026-05-23
3. pelo critério do próprio [mapa de autoridade](../reference/documentation-authority-map.md), docs com sinais de envelhecimento perdem autoridade até revisão; como agentes navegam via RAG, doc de alta autoridade defasado envenena respostas

Ações:

1. atualizar a seção "Estado atual resumido" do growth-plan para o runtime real (apps existentes, tenants vivos), preservando a tese e as fases como historico do que foi executado
2. re-ancorar o plano de escala na topologia schema-per-tenant viva: o que a virada antecipou, o que ainda vale (gates de densidade, custo por box, célula), citando [schema-per-tenant-migration-plan.md](schema-per-tenant-migration-plan.md) e ADR-005..010
3. reindexar o RAG: `python manage.py ingest_project_knowledge` (depende de Postgres local — ver S5)

Critério de pronto:

1. os dois docs descrevem o estado atual sem afirmação falsa sobre o runtime
2. RAG reindexado com os textos novos

---

## S5 — P2 — Ambiente de dev local confiável

Status:

1. aberto — nota de 2026-06-11: o cluster da 5433 estava parado e foi religado manualmente (`pg_ctl start`) para o reindex do S4; a causa de ele não sobreviver/subir sozinho segue sem tratamento

Problema e evidência:

1. o Postgres local (porta 5433) estava fora do ar durante a auditoria — o RAG online (`search_project_knowledge`) falhou com `connection timeout` e foi preciso usar o fallback offline
2. a memória do projeto registra bloqueios recorrentes: migrations inconsistentes locais e OneDrive desidratando arquivos
3. o working tree vive dentro do OneDrive — risco real de sync corromper `.venv`, dados do Postgres e `node_modules`
4. descoberto em 2026-06-11 durante a validação do S1: os 5 testes de `tests/test_tenant_boundary.py` (B1, B2, B5, B6, B7) **falham no cluster local** com `relação "boxcore_student" não existe` em schema de tenant recém-criado — mesma assinatura em Django 6.0.5 e 6.0.6, banco de teste recriado do zero, e os mesmos testes verdes no CI (PG 15). Suspeitos: PG 16 local vs PG 15 do CI, role `octobox_app` não-superuser, ou o gotcha do `TenantSyncRouter` (migrations registradas sem DDL). Investigar dentro deste item

Ações:

1. subir e validar o cluster local e confirmar `search_project_knowledge` respondendo
2. decidir e executar uma das duas mitigações:
   a. mover o working tree para fora do OneDrive (ex.: `C:\dev\OctoBox`), mantendo o GitHub como fonte de verdade, ou
   b. marcar `.venv`, dados locais e `node_modules` como "sempre manter neste dispositivo" e excluí-los do sync
3. considerar auto-start do cluster (serviço Windows ou tarefa agendada) para o RAG não voltar a ficar mudo
4. se a decisão gerar lição não-óbvia, destilar em `docs/decisions/` via pr-lesson

Critério de pronto:

1. RAG online responde localmente sem intervenção manual
2. a causa de quebra do ambiente está eliminada ou mitigada com decisão registrada

---

## S6 — P2 — Higiene de branches remotas

Status:

1. aberto

Problema e evidência:

1. ~24 branches no remoto; várias já mergeadas ou mortas (`ops/fetch-vps-logs`, fixes antigos, branches de workout já integradas)

Ações:

1. listar mergeadas: `git branch -r --merged origin/main`
2. apagar as mortas no remoto, preservando qualquer branch com trabalho vivo
3. conferir se alguma branch viva carrega trabalho que deveria virar PR ou ser descartado conscientemente

Critério de pronto:

1. só restam branches com trabalho vivo ou em revisão

---

## Ordem de execução recomendada

1. **S1 primeiro** — desbloqueia o trem de deploy; é uma linha + suite
2. **S2 em paralelo com S1** — são independentes (worktrees separados)
3. **S3** — rápido, aproveita a suite já validada por S1
4. **S4** — exige leitura cuidadosa; reindex do RAG depende de S5.1 (cluster de pé)
5. **S5 e S6** — quando couber, sem bloquear os anteriores

## O que NÃO entra neste sprint

Estes itens apareceram na auditoria como evolução, não correção. Têm trilho próprio e não devem inchar o sprint:

1. gate da Fase 1 (backup/restore **testado**, custo medido por box) — trilho em [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md) e docs de rollout
2. read model operacional leve (tirar leitura quente de `AuditEvent`) — pré-requisito de Fase 2, não deste sprint
3. crescimento da suite E2E (cadastro de aluno, pagamento no balcão, check-in) — só depois de S2 fechado
4. próximas fatias de drenagem do `boxcore` — trilho em [boxcore-state-residue-inventory.md](../architecture/boxcore-state-residue-inventory.md)

## Critério de fechamento do sprint

1. todos os itens com status "pronto", cada um com link de PR e data
2. Security Scanners e E2E nightly verdes na main por 3 dias corridos
3. lição não-óbvia (se houver) destilada via pr-lesson em `docs/decisions/`; se for tudo mecânico, SKIP consciente
4. este documento atualizado com o registro final e marcado como fechado

## Registro de progresso

| Item | Prioridade | Status | PR | Data |
|---|---|---|---|---|
| S1 — Django 6.0.6 | P0 | em execução | [#123](https://github.com/renanfulas/OctoBox/pull/123) | 2026-06-11 |
| S2 — E2E nightly + alarme | P0 | em execução | [#122](https://github.com/renanfulas/OctoBox/pull/122) | 2026-06-11 |
| S3 — ratchet de cobertura | P1 | aberto | — | — |
| S4 — sync de docs de autoridade | P1 | em execução | [#124](https://github.com/renanfulas/OctoBox/pull/124) | 2026-06-11 |
| S5 — ambiente dev local | P2 | aberto | — | — |
| S6 — higiene de branches | P2 | aberto | — | — |
