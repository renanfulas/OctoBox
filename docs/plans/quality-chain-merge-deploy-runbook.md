# Runbook: Merge da Quality Chain + Deploy em Produção

**Data de criação:** 2026-05-22  
**Scope:** PRs #74–#82 (9 PRs, quality chain + fix de admin stub)  
**Estado no momento da escrita:** todos os PRs MERGEABLE / CLEAN, zero drift em relação a `main` (`c15b063`)

---

## Contexto

Esta chain acumula 9 PRs que vivem em branches encadeadas há semanas. Nenhum
deles pode ser mergeado de forma autônoma sem retargetar a base — todos foram
abertos apontando para a branch predecessor, não para `main`.

O risco central **não** é técnico (as mudanças são seguras), é operacional: cada
push para `main` aciona `deploy-vps.yml` via `workflow_run`. Sem desabilitar o
autodeploy antes, o primeiro merge já tentaria fazer deploy de um estado
incompleto.

---

## Estado pré-merge confirmado

| Item | Status |
|---|---|
| Todos os 9 PRs | MERGEABLE / CLEAN |
| Drift em relação a `main` | Zero — merge-base = `c15b063` |
| CI das branches individuais | Verde (última run: phase-9-docs ✓) |
| Migrações (4 novos arquivos) | Não-destrutivas — CREATE TABLE e ADD COLUMN NULL |
| Produção atual | Saudável (VPS Deploy: skipped = sem trigger recente, esperado) |

### PRs e dependências

```
PR #74  claude/admiring-fermi-531840        base: main       ← raiz da chain
PR #75  test-quality/phase-1-full-ci        base: #74
PR #76  test-quality/phase-3-order-dependent base: #75
PR #77  test-quality/phase-4-factories      base: #76
PR #78  test-quality/phase-5-parametrize    base: #77
PR #79  test-quality/phase-6-db-constraints base: #78
PR #80  test-quality/phase-7-error-scenarios base: #79
PR #81  test-quality/phase-8-e2e-playwright  base: #80
PR #82  test-quality/phase-9-docs            base: #81
```

---

## PASSO 0 — Desabilitar autodeploy

> **Obrigatório antes de qualquer merge.** Sem isso o primeiro push para `main`
> dispara um deploy de estado parcial.

```bash
gh workflow disable "OctoBox CI Checks (Performance & Integrity)"
```

**Confirmar:**
```bash
gh workflow list | grep "Performance"
# Esperado: "disabled" na coluna de estado
```

**Por que esse workflow e não `deploy-vps.yml` diretamente?**  
`deploy-vps.yml` usa `workflow_run` aguardando `OctoBox CI Checks (Performance &
Integrity)`. Se esse workflow não dispara, o trigger do deploy nunca chega.
Desabilitar a fonte é mais seguro que desabilitar o consumidor.

---

## PASSO 1 — Merge PR #74

PR #74 é a única branch da chain com base direta em `main`. Nenhum retarget
necessário.

```bash
gh pr merge 74 --merge --subject "fix: placeholder admin stub"
```

**Por que `--merge` e não `--squash`?**  
As 8 branches subsequentes têm histórico baseado nos commits de #74. Squash
recria SHAs — os rebase points das branches filhas ficam desconectados e o
GitHub reportaria conflito em todos os PRs seguintes.

CI de `main` vai rodar após esse merge. Como o autodeploy está desabilitado,
para aí sem consequências.

---

## PASSO 2 — Retargetar e mergear PR #75

PR #75 foi aberto com base na branch de #74. Agora que #74 está em `main`,
retargetamos para `main` antes do merge.

```bash
gh pr edit 75 --base main
gh pr merge 75 --merge --subject "ci: fase 1 — full test suite (917 testes, pytest-xdist)"
```

### ⚠ Ponto de verificação obrigatório

PR #75 é o que adiciona o job `full-test-suite` em `main`. Este é o merge mais
crítico da chain. Antes de avançar para #76, aguardar o CI de `main` completar:

```bash
gh run list --branch main --limit 5
gh run watch <run-id-do-full-test-suite>
```

Se o job `Full Test Suite` falhar aqui em `main`, **parar** e diagnosticar
antes de prosseguir. Os 8 PRs restantes herdam esse estado.

---

## PASSO 3 — PRs #76 a #82: loop de retarget + merge

Após #75 passar o CI, executar em sequência. Não há necessidade de aguardar CI
entre cada um — o objetivo é acumular todos os commits em `main` antes do deploy.
A verificação definitiva acontece no Passo 5.

```bash
gh pr edit 76 --base main && gh pr merge 76 --merge
gh pr edit 77 --base main && gh pr merge 77 --merge
gh pr edit 78 --base main && gh pr merge 78 --merge
gh pr edit 79 --base main && gh pr merge 79 --merge
gh pr edit 80 --base main && gh pr merge 80 --merge
gh pr edit 81 --base main && gh pr merge 81 --merge
gh pr edit 82 --base main && gh pr merge 82 --merge
```

Após o último merge, `main` terá os 9 PRs integrados.

---

## PASSO 4 — Verificação local antes de reabilitar

```bash
git fetch origin && git checkout main && git pull

# Instala todas as dependências incluindo as de teste
pip install -r requirements.txt -r requirements_test.txt

# Roda a suite completa (mesmo ambiente que o CI usa)
pytest -n auto --tb=short -q

# Verifica o plano de migrações sem aplicar
python manage.py migrate --plan
python manage.py migrate --shared --plan
```

O `--plan` deve listar exatamente 4 migrações pendentes:

```
control.0001_initial
student_identity.0001_initial
boxcore.0026_sprint2_student_identity_fk
student_app.0014_...
```

### Ordem de dependência das migrações

O Django resolve isso automaticamente via grafo de dependências, mas é útil
entender a ordem para diagnóstico de falhas:

```
1. control/0001_initial          → CREATE TABLE (schema público, SHARED_APPS)
2. student_identity/0001_initial → CREATE TABLE (schema público, SHARED_APPS)
3. boxcore/0026                  → ADD COLUMN identity_id NULL (cada tenant schema)
4. student_app/0014              → FK para student_identity (schema público)
```

`control/0001` deve aplicar antes de `student_identity/0001` (FK dependency).
`student_identity/0001` deve aplicar antes de `boxcore/0026` e `student_app/0014`.

Com `django-tenants`, `migrate --noinput` aplica `SHARED_APPS` no schema público
e `TENANT_APPS` em cada schema de tenant. Nenhuma intervenção manual é necessária.

---

## PASSO 5 — Verificar variáveis de ambiente no VPS

> **Fazer antes de reabilitar o deploy.**

Os novos módulos (`control`, `student_identity`, `integrations`) podem ler env
vars no `AppConfig.ready()`. Se alguma estiver ausente, o gunicorn falha no
restart com `ImproperlyConfigured`.

No VPS:
```bash
# Verificar quais env vars os novos módulos leem
grep -r "os.environ\[" student_identity/ control/ integrations/
grep -r "os.getenv(" student_identity/ control/ integrations/

# Comparar com o arquivo de env atual
cat /etc/octobox.env   # ou onde estiver o arquivo de env do servidor
```

Variáveis já conhecidas como obrigatórias (sem default em `base.py`):
```
DATABASE_URL
REDIS_URL
STUDENT_RESEND_API_KEY
STUDENT_RESEND_WEBHOOK_SECRET
STUDENT_GOOGLE_OAUTH_CLIENT_ID
STUDENT_GOOGLE_OAUTH_CLIENT_SECRET
STUDENT_APPLE_OAUTH_*
STUDENT_OAUTH_PUBLIC_BASE_URL
STUDENT_WEB_PUSH_VAPID_*
```

---

## PASSO 6 — Reabilitar autodeploy e disparar

```bash
gh workflow enable "OctoBox CI Checks (Performance & Integrity)"
```

O workflow está reabilitado mas não dispara automaticamente sem um push.
Disparar com um commit vazio:

```bash
git commit --allow-empty -m "chore: trigger deploy after quality chain merge [skip-heavy]"
git push origin main
```

### O que acontece a partir daqui (cadeia automática)

```
push origin main
  └─ OctoBox CI Checks (Performance & Integrity) [performance_check.yml]
       └─ deploy-vps.yml (workflow_run trigger)
            └─ verify-gates: valida 4 workflows obrigatórios
                 └─ deploy: executa script no VPS
                      ├─ git reset --hard origin/main
                      ├─ pip install
                      ├─ collectstatic
                      ├─ migrate --noinput          ← aplica as 4 migrações
                      ├─ bootstrap_roles
                      └─ systemctl restart octobox-gunicorn
                           └─ health check: curl /api/v1/health/
```

**Monitorar:**
```bash
gh run list --workflow="OctoBox CI Checks (Performance & Integrity)" --limit 3
gh run list --workflow="VPS Deploy (Hostgator São Paulo)" --limit 3
```

---

## PASSO 7 — Verificações pós-deploy

```bash
# Confirma que o deploy completou com sucesso
gh run list --workflow="VPS Deploy (Hostgator São Paulo)" --limit 1

# Health check
curl -s https://app.octoboxfit.com.br/api/v1/health/ | python -m json.tool
```

### Smoke manual dos novos módulos

O health check padrão cobre apenas o core da app. Verificar manualmente:

```bash
# No VPS: confirmar que as novas tabelas existem nos schemas corretos

# Schema público (control e student_identity são SHARED_APPS)
python manage.py dbshell
\dt control_*
\dt student_identity_*

# Schema de um tenant real (boxcore é TENANT_APP)
python manage.py tenant_command dbshell --schema=<slug-de-um-tenant>
\dt boxcore_*
# Confirmar que a coluna identity_id existe em boxcore_student
\d boxcore_student
```

---

## Plano de rollback por ponto de falha

| Onde falha | Sintoma | Ação |
|---|---|---|
| CI de `main` após #75 | `Full Test Suite` vermelho | `git revert HEAD` em `main` — remove só #75 sem afetar #74. Diagnosticar antes de retentar |
| Migrations falham no deploy | Deploy script loga erro antes do restart | Banco inalterado. Corrigir migration no código, push, novo trigger |
| Restart do gunicorn falha | `systemctl status octobox-gunicorn` mostra erro | `systemctl status` no VPS para diagnosticar. Rollback via `git reset --hard c15b063` no VPS + restart manual |
| Health check falha após restart | `curl /api/v1/health/` retorna não-200 | Reverter para SHA anterior em `main`: `git revert` dos commits de merge + push + trigger redeploy |
| Env var ausente | `ImproperlyConfigured` nos logs do gunicorn | Adicionar var ao arquivo de env no VPS + `systemctl restart octobox-gunicorn` (sem necessidade de redeploy) |

---

## Gap Analysis — O que estava faltando e não tínhamos visto

Estes pontos **não bloqueiam** o merge. São riscos residuais e um item de
follow-up que deve virar PR separado.

### GAP 1 — `full-test-suite` não está no gate de deploy ⚠️ Alta prioridade

`deploy-vps.yml` valida exatamente estes 4 workflows no job `verify-gates`:

- `OctoBox CI Checks (Performance & Integrity)`
- `Onboarding Corridors`
- `Onboarding Real Smoke`
- `Security Scanners`

O job `Full Test Suite` (917 testes, adicionado pelo PR #75) **não está nessa
lista**. Isso significa que, mesmo após todos os merges, se os 917 testes
quebrarem em `main`, o deploy ocorre normalmente.

**Ação:** Abrir PR separado adicionando `Full Test Suite` à lista de required
workflows em `deploy-vps.yml`. Não misturar com esta chain para não criar
dependência nova agora.

### GAP 2 — Variáveis de ambiente novas podem não estar no VPS ⚠️ Alta prioridade

Coberto no Passo 5. Verificação obrigatória antes do deploy.

### GAP 3 — Health check pós-deploy não cobre os novos endpoints

`/api/v1/health/` existe no core da app. Não testa se `student_identity`,
`control` ou `integrations` inicializaram corretamente. Um app que falha
silenciosamente (tabela não encontrada) retorna 200 assim mesmo.

**Ação (manual):** Smoke manual dos novos módulos conforme Passo 7.

### GAP 4 — Sem verificação de tenant após migrate

`migrate --noinput` aplica as migrations de tenant em todos os schemas
existentes. Se um tenant estiver em estado corrompido, a migration pode falhar
para aquele tenant específico sem abortar o deploy global.

**Ação (manual):** Após deploy, verificar coluna `identity_id` em pelo menos
um tenant real conforme Passo 7.

### GAP 5 — Janela sem CI completo entre #74 e #75

Após #74 mergear e antes de #75 mergear, `main` não tem o job `full-test-suite`.
Qualquer push acidental nessa janela seria protegido apenas pelos 4 workflows
antigos.

**Cobertura existente:** Passo 0 (autodeploy desabilitado) cobre completamente
este risco. A janela existe mas não tem consequências práticas.

---

## Resumo executivo

```
1. gh workflow disable "OctoBox CI Checks (Performance & Integrity)"
2. gh pr merge 74 --merge
3. gh pr edit 75 --base main && gh pr merge 75 --merge
   → AGUARDAR CI (Full Test Suite em main)
4. gh pr edit 76 --base main && gh pr merge 76 --merge
   gh pr edit 77 --base main && gh pr merge 77 --merge
   gh pr edit 78 --base main && gh pr merge 78 --merge
   gh pr edit 79 --base main && gh pr merge 79 --merge
   gh pr edit 80 --base main && gh pr merge 80 --merge
   gh pr edit 81 --base main && gh pr merge 81 --merge
   gh pr edit 82 --base main && gh pr merge 82 --merge
5. pytest -n auto --tb=short -q  (verificação local)
6. Verificar env vars no VPS
7. gh workflow enable "OctoBox CI Checks (Performance & Integrity)"
8. git commit --allow-empty -m "chore: trigger deploy" && git push origin main
9. Monitorar deploy + smoke manual pós-deploy
10. Abrir PR: adicionar full-test-suite ao verify-gates em deploy-vps.yml
```

**Tempo estimado:** 30–45 min (dominado pela espera do CI após #75 e pelo
deploy em si).
