# Handover: Test Quality Fase 2 — Cobertura visível em PRs

> Copie/cole tudo abaixo da linha `---` em uma nova conversa. O contexto é
> auto-suficiente; o agente novo deve conseguir executar sem precisar da
> conversa anterior.

---

## CONTEXTO

Repositório: **OctoBox** (Django 5 + django-tenants + Postgres 14+, schema-per-tenant).

Worktree atual: `C:\Users\renan\OneDrive\Documents\New project\OctoBox\.claude\worktrees\admiring-fermi-531840`

Branch ativa: **`test-quality/phase-1-full-ci`** (PR #75, stacked sobre PR #74).

CI atual (último push): **4/4 workflows verde**. Full Test Suite: 889 passed, 7 skipped, 0 failed em 3:17min.

`tests/broken-tests.txt` está **vazio** (zero quarentena). Fases 0, 0.5 e 1 do quality plan **concluídas**.

## SUA MISSÃO (única)

Executar **Fase 2** do plano em `docs/testing/quality-plan-prompt.md`:

**Cobertura visível em PRs via Codecov + PR comment com diff de cobertura.**

Esforço esperado: **1-2h, baixo risco, paralelo ao merge do PR #75**.

## SCOPE

Apenas estes 3 outcomes:

1. **Codecov upload** no workflow `.github/workflows/full-test-suite.yml` (já existe e roda `pytest --cov`).
2. **PR comment** com delta de cobertura (Codecov faz isso nativo com bot + token).
3. **`.coveragerc::fail_under`** ajustado para `baseline - 2%` para não bloquear PRs imediatamente.

## CONSTRAINTS NÃO-NEGOCIÁVEIS

- **NÃO** mexer em `tests/broken-tests.txt` — mantém vazio.
- **NÃO** mexer em `conftest.py` — class-scope fixtures são pré-requisito de Fase 0.5 (ver ADR-005).
- **NÃO** rodar `git rebase` em `main` — branch está stacked em PR #74 ainda não mergeado.
- **NÃO** instalar `pytest-playwright` ou ferramentas de Fase 3+.
- **NÃO** criar ADRs novos — Fase 9 fará handover.
- **NÃO** mudar `requirements_test.txt` (Codecov upload é GitHub Action, não pip).
- **NÃO** mexer em código de produção (Django views, models, etc.) — Fase 2 é só CI + relatório.

## CONTEXTO DE ARQUIVOS-CHAVE

### `.coveragerc` (já existe)

```ini
[run]
branch = True
source = access,auditing,boxcore,catalog,communications,control,dashboard,finance,guide,...
omit = */migrations/*, */settings/*, */seeders/*, */tests/*, scripts/*
fail_under = 0

[report]
exclude_lines = pragma: no cover, raise NotImplementedError, if __name__ == .__main__.:
```

### `.github/workflows/full-test-suite.yml` (já existe)

Roda em PR + push pra main. Comando atual:

```yaml
- name: Run full suite
  run: |
    pytest --create-db --migrations -n 4 -p no:randomly \
      --cov --cov-report=xml --cov-report=term \
      --junitxml=junit-report.xml
```

`coverage.xml` já é gerado. Falta upload + PR comment.

### `docs/testing/quality-plan-prompt.md::FASE 2` (especificação canonical)

Leia esta seção INTEIRA antes de começar. Tem critérios de pronto, decisões, trade-offs.

## PASSOS RECOMENDADOS

1. **Ler `docs/testing/quality-plan-prompt.md::FASE 2`** — especificação canonical.
2. **Decidir Codecov vs Coverage Comments Action**:
   - Codecov: setup em 5min, dashboard rico, requer token no secret `CODECOV_TOKEN` (usuário precisa criar conta + adicionar repo).
   - `py-cov-action/python-coverage-comment-action`: zero serviço externo, comment direto no PR via `GITHUB_TOKEN`. **Preferir esta opção** se usuário não quiser conta Codecov.
3. **Adicionar step no workflow** após o `pytest`.
4. **Medir baseline** do último run verde:
   ```bash
   gh run view <id-do-Full-Test-Suite> --log | grep -E "TOTAL|coverage"
   ```
   O baseline é o valor atual de `% covered`. Setar `fail_under = max(0, baseline - 2)` em `.coveragerc`.
5. **Validar localmente** que `coverage.xml` é gerado:
   ```bash
   python -m pytest --cov --cov-report=xml --cov-report=term -x -k test_audit_user_logged_in 2>&1 | tail -10
   ls -la coverage.xml
   ```
6. **Commit + push**. Confirmar CI verde.
7. **Verificar PR comment apareceu** no PR #75 (vai aparecer no rerun automático).

## CRITÉRIOS DE PRONTO

- [ ] Workflow `.github/workflows/full-test-suite.yml` faz upload/processamento de `coverage.xml`.
- [ ] PR #75 recebe **1 comment automático** com diff de cobertura na próxima execução.
- [ ] `.coveragerc::fail_under` setado com valor mensurado (não 0, não 80%).
- [ ] CI Full Test Suite continua verde (889+ passed, 0 failed).
- [ ] `broken-tests.txt` permanece vazio (sanity check).
- [ ] 1 commit pequeno (~20 linhas em workflow + `.coveragerc`). Push para `test-quality/phase-1-full-ci`.

## ANTI-PATTERNS A EVITAR

- Setar `fail_under = 80%` "porque é o padrão" — quebra CI imediatamente se baseline é menor.
- Adicionar Codecov SEM medir baseline real — vira chute.
- Tentar fazer Fase 3 (order-dependent cleanup) junto — escopo creep.
- Criar arquivos novos de doc além do necessário — Fase 9 cuida disso.

## COMANDOS ÚTEIS

```bash
# Estado atual da branch
git log --oneline -5
git status --short

# Último run de CI da branch
gh run list --branch test-quality/phase-1-full-ci --limit 5 --json status,conclusion,name

# Medir coverage atual
python -m pytest --cov --cov-report=term student_identity/tests.py 2>&1 | tail -5

# Validar workflow YAML
cat .github/workflows/full-test-suite.yml

# Após mudar workflow: push + acompanhar CI
git push origin test-quality/phase-1-full-ci
gh run watch
```

## QUANDO TERMINAR

- Reporte: workflow link, número do commit, baseline medido, `fail_under` setado.
- Não invente próximas fases — pare aqui.
- Pergunte ao usuário se quer continuar Fase 3 (order-dependent cleanup) ou pivotar.

## SE ALGO QUEBRAR

- CI vermelha após push: rollback do commit Fase 2, **não** mexer em código de produção. Investigar isolado.
- Coverage muito baixo (< 50%): **não** abaixe `fail_under` cegamente. Reporte o número e pergunte ao usuário.
- Token Codecov não disponível: pivote pra `python-coverage-comment-action` sem perguntar (zero setup externo).

---

**Fim do handover.** Boa execução.
