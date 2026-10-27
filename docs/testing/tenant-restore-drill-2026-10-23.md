# Relatório F2 — restore seletivo A/B em PostgreSQL descartável

## Resultado e escopo

**Resultado:** roundtrip seletivo aprovado para o cenário sintético, incluindo smoke semântico OctoBOX e preservação do fingerprint de B.

**Não é aceite operacional nem promoção.** O ensaio usou somente PostgreSQL Docker descartável, dois Boxes sintéticos e dados inventados. Não usou backup, PII, serviço, credencial ou tenant de homologação/produção. Não houve writers concorrentes, freeze A, tráfego real em B, jobs, cron, webhook, retry ou reconciliação de efeitos externos.

| Campo | Evidência |
|---|---|
| Data | 2026-10-23 UTC |
| Checkout | branch `codex/fix-wod-calendar-behavior`, HEAD `a2ab398f5774b609b979a31c00527bc88b64b1fb` mais alterações locais preservadas |
| Banco | PostgreSQL `15.19`, container descartável `octobox_f2_semantic_lab_20261023` |
| Ferramentas | `pg_dump 15.19`, `pg_restore 15.19`; migrations executadas pelo Django do checkout |
| Origem | database `f2_lab`, criado vazio para este ensaio |
| Destino | database novo `octobox_restore_f2_semantic_20261023`, criado pelo script de restore |
| Canários | Boxes `alpha`/`bravo`; Student PK `1` nos dois schemas; identidades shared distintas; 1 StudentBoxMembership por Box |

## Execução

1. Aplicadas todas as migrations shared; ambas as migrations tenant foram executadas pelo `provision_box` oficial, com Owner, Groups e MembershipPlan.
2. Criado um aluno sintético em cada Box, ligado a `StudentIdentity` e `StudentBoxMembership` shared. Ambos receberam `student_id=1`, validando colisão de PK entre schemas.
3. `smoke_test_tenant --slug alpha --schema-only --restore-semantic --verbose` e o mesmo para `bravo`: **6/6 checks passaram em cada Box** antes dos dumps.
4. Gerados dump full e dump tenant de A pelos scripts reais, com manifestos. Hash full: `ae032534596b7deda5e5789bac64e711d05a484412251dddc410d82380324a16`; hash tenant A: `a5dfb7b50781636ed8efc3edd28862bcf82ddcef71637e5df37ef85d027618fb`.
5. O script `restore_tenant_schema.sh` verificou hashes, origem e versões, criou destino novo, restaurou o full, substituiu somente `box_alpha` no clone e terminou com **57 tabelas tenant e 0 FKs não validadas**. Tempo reportado pelo script: **6 s** (`19:09:21–19:09:27 UTC`); exclui provisionamento/migrations e não é RTO comercial.
6. `migrate_schemas --schema=box_alpha --check --noinput` passou. O smoke semântico passou **6/6 para A e 6/6 para B** no destino.
7. Fingerprint determinístico de B, incluindo PKs, vínculo tenant→identity, Box e membership shared: `7e6222f0befb4808a48f83fedf4ea730` antes e depois; igual.
8. Testes negativos, feitos somente no banco de destino descartável: `box_root_slug` divergente foi reprovado; ligar Student de A à identidade de B foi reprovado com as duas inconsistências correspondentes. Canário corrigido ao fim; A/B voltaram a passar **6/6**.
9. O teste de regressão `tests/test_tenant_restore_semantic_smoke.py` passou **1/1** em PostgreSQL descartável com migrations; cobre membership com slug divergente, Student de A ligado à identidade de B e `StudentBoxMembership.student_id` em conflito com `StudentIdentity.student_id`. O teste roda no job `tenant-restore-semantic-smoke` do workflow `backup-integrity-check.yml`; execução GitHub ainda pendente.

## Revalidação complementar — 2026-10-24

Esta rodada amplia a evidência anterior com tráfego HTTP autenticado e uma segunda cópia seletiva; continua sendo um ensaio sintético.

| Campo | Evidência |
|---|---|
| PostgreSQL | `15.19`, container descartável `octobox_f2_lab_20261024`, publicado somente em `127.0.0.1:55434` |
| Origem / destino | `octobox_f2_source` → banco novo `octobox_restore_f2_20261024_a`; o script recebeu `--forbid-database octobox_f2_source` |
| Boxes | `f2-lab-a` e `f2-lab-b`, com Owners/Membership sintéticos; Coach sintético em A; Students, pagamentos, aulas e WODs sintéticos com IDs coincidentes nos dois schemas |
| Restore | dump full + dump de A e manifestos compatíveis; **58 tabelas tenant, 0 FKs não validadas** |
| Migrations e semântica | `migrate_schemas --schema=box_f2-lab-a --check --noinput` passou; smoke semântico A **6/6** e B **6/6** |
| Preservação de B | dump de dados do schema B antes/depois coincidiu após remover somente as linhas aleatórias de wrapper `restrict`/`unrestrict` emitidas por `pg_dump`; SHA-256 normalizado igual: `85e63539934c48677878ad3a4af0e9d9b6021918c85e498854a74f1c0256e55a` |
| HTTP | Coach de A abriu `/operacao/wod/paste/` com **200**; Owner de A abriu `/financeiro/` com **200**. Os logs registraram `box_f2-lab-a` e os papéis Coach/Owner |
| Resolução | `Domain` não tinha registros para A/B; a sessão com Membership primário resolveu o tenant das duas requisições. `StudentBoxMembership` não tinha linhas neste corpus; os vínculos de identidade seguem cobertos pelo ensaio semântico de 23/10 |

Os dumps e manifestos permaneceram dentro do container. A comparação bruta dos arquivos SQL variava apenas pelo token aleatório de proteção do `pg_dump`; a normalização acima removeu essas duas linhas de wrapper, sem retirar DDL ou dados. Uma invocação intermediada por PowerShell também produziu `python3\r` como argumento; chamar o script normalizado diretamente com `docker exec ... bash ...` executou o fluxo. Isso sugere documentar uma receita única de execução Linux/container e dependências do script.

## Limites e pendências

- O roundtrip prova os scripts reais e o contrato semântico básico contra um snapshot shared sintético coerente; não prova restore de dados reais ou de volumes de produção.
- O ensaio de 23/10 não exercitou `Domain`, login/roteamento HTTP, financeiro/WOD nem fingerprints amplos; a revalidação de 24/10 cobriu HTTP por sessão/Membership e dump de dados de B, mas não criou `Domain` nem `StudentBoxMembership` neste corpus.
- O fingerprint prova que B do clone pós-restore coincide com o snapshot full usado na recuperação; a origem descartável não sofreu alteração. Isso não simula B recebendo escrita durante o restore.
- F2 segue aberto até ensaio em homologação com freeze/drenagem de A, B exercitado durante a janela, contenção e reconciliação dos writers/efeitos externos, smoke funcional, horários e aceite responsável. Eventos sem Box, fila legada, SSE aberto, workers futuros e operação real do host permanecem fora desta prova.

## Limpeza

Em ambas as rodadas, o banco de origem, o destino restaurado, os dumps e os manifestos ficaram dentro de containers PostgreSQL descartáveis e foram removidos junto com eles após a coleta das evidências. Nenhum arquivo de dump foi copiado para o workspace. A revalidação de 24/10 confirmou que o container não toca a base local do preview nem um tenant real.
