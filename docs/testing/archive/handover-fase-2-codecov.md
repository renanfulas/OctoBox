# Handover: Test Quality — Estado atual e próxima fase

> Documento atualizado em 2026-05-25. Reflete o estado real da main após
> merge dos PRs #74 e #75 (2026-05-22) e confirmação visual do workflow.

---

## ESTADO ATUAL (main, 2026-05-25)

| Fase | Status | Evidência |
|---|---|---|
| Fase 0 — Baseline | ✅ Concluída | `docs/testing/baseline-2026-05-18.md` |
| Fase 0.5 — Stabilization | ✅ Concluída | `tests/broken-tests.txt` vazio; 193→0 broken |
| Fase 1 — CI suite completa | ✅ Concluída | `.github/workflows/full-test-suite.yml` rodando, PR #75 merged |
| Fase 2 — Cobertura visível em PRs | ✅ Concluída | `py-cov-action/python-coverage-comment-action@v3` no workflow; `fail_under = 72` |
| Fase 3 — Order-dependence | ✅ Concluída | `order-dependence-check` job rodando 3 seeds (42, 137, 9999); validado 2026-05-21 |
| Fase 4 — Factories | ⬜ Pendente | `tests/factories.py` não existe |
| Fase 5 — Matriz de roles parametrizada | ⬜ Pendente | — |
| Fase 6 — Constraints de banco | ⬜ Pendente | — |
| Fase 7 — Cenários de erro | ⬜ Pendente | — |

**CI atual:** 4/4 workflows verdes. Full Test Suite: 889+ passed, 0 failed, ~3:17min.
`broken-tests.txt` vazio (zero quarentena). Cobertura baseline: **74.7%** (`fail_under = 72`).

---

## CONTEXTO DO QUE FOI FEITO

### Workflow `.github/workflows/full-test-suite.yml`

Dois jobs ativos:

1. **`full-test-suite`** — roda suite completa com `-n 4`, gera `coverage.xml`,
   comenta diff de cobertura em PRs via `py-cov-action/python-coverage-comment-action@v3`.
2. **`order-dependence-check`** — roda a suite com 3 seeds fixos (42, 137, 9999)
   via matrix strategy para detectar order-dependência.

### `.coveragerc`

- `branch = True` e `relative_files = True` (necessário para o comment action).
- `fail_under = 72` — baseline 74.7% medido em 2026-05-21, margem de 2pp.
- `source` inclui todos os apps de produto; `omit` exclui migrations, settings, seeders.

### `tests/broken-tests.txt`

Vazio. Os 193 testes quebrados originais foram recuperados em 3 buckets (A, B, C)
durante a Fase 0.5. Padrões consolidados nos ADRs 005–012.

---

## PRÓXIMA MISSÃO: FASE 4 — Factories para 3 modelos centrais

**Spec canonical:** `docs/testing/quality-plan-prompt.md` seção `FASE 4`.

**O que fazer:**

1. Criar `tests/factories.py` com factory_boy para os 3 modelos mais usados:
   - `UserFactory` (auth.User)
   - `StudentFactory` (students.Student)
   - `StudentIdentityFactory` (student_identity.StudentIdentity)

2. Migrar 3–5 arquivos de teste existentes para usar as factories como
   prova de conceito. Não migrar tudo — migração orgânica nos PRs futuros.

3. Verificar que contagem de pass/fail é idêntica antes e depois.

**Identificar os modelos mais usados:**
```bash
grep -rh "\.objects\.create\b" --include="*.py" tests/ */tests.py */tests/*.py \
  | sed -E 's/.*([A-Z][a-zA-Z]+)\.objects\.create.*/\1/' \
  | sort | uniq -c | sort -rn | head -10
```

**Critério de pronto:**
- [ ] `tests/factories.py` existe com 3 factories funcionais e documentadas.
- [ ] 3–5 arquivos de teste migrados (sem mudança semântica).
- [ ] `python -m pytest` — contagem de pass/fail idêntica antes e depois.
- [ ] CI Full Test Suite continua verde.
- [ ] `broken-tests.txt` permanece vazio.
- [ ] 1 commit: `"test: adicionar factory_boy + factories para 3 modelos centrais"`.

**Constraints:**
- **NÃO** migrar todos os testes — só 3–5 como proof of concept.
- **NÃO** mexer em `conftest.py` nem em `broken-tests.txt`.
- **NÃO** mexer em código de produção.
- **NÃO** adicionar dependências além de `factory-boy` (já está em `requirements_test.txt`).

---

## COMANDOS ÚTEIS

```bash
# Estado atual
git log --oneline -5
git status --short

# Último run de CI na main
gh run list --branch main --limit 5 --json status,conclusion,name

# Verificar se factory-boy está disponível
python -c "import factory; print(factory.__version__)"

# Rodar suite completa local antes e depois
python -m pytest --create-db --migrations -n 4 -q 2>&1 | tail -5

# Validar sem order-dependência (seed fixo)
python -m pytest --create-db --migrations --randomly-seed=42 -n 4 -q 2>&1 | tail -5
```

---

## QUANDO TERMINAR A FASE 4

Atualizar a tabela de estado no topo deste documento.
Não iniciar Fase 5 sem confirmar critério de pronto da Fase 4.
Perguntar ao usuário se quer continuar para Fase 5 (matriz de roles parametrizada)
ou pivotar para outro trabalho.
