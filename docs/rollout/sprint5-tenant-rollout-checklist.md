# Sprint 5 — Checklist de rollout multi-tenant em produção

> **STATUS: PARCIALMENTE CONCLUIDO em 2026-05-23**
> - Fases 1-5: executadas via workflows GitHub Actions (`sprint5-stage0` → `sprint5-stage3`)
> - Box `octoboxfit-production` ativo em `control_box` com 51 tabelas no schema dedicado
> - 359 linhas migradas de `public` para `box_octoboxfit-production` (sem `--truncate-source`)
> - Primeiro aluno real autenticado via OAuth (`renanjuniorfulas@gmail.com`)
> - Fases 6-8 pendentes: E2E Early Adopter, 24h de observacao, proximos 5 boxes
> - Marco registrado em [../history/mudaram-o-nivel-do-projeto.md](../history/mudaram-o-nivel-do-projeto.md) (itens 107-114 + "Nota sobre o primeiro aluno em producao")

> **Critério de pronto original**: 5 boxes ativos em prod; 0 vazamento; `/api/v1/health/` verde por 24h contínuas.

## Pré-requisitos (antes de começar)

- [ ] `manage.py check` retorna 0 issues em DEV
- [ ] Todos os 23 boundary tests passam em CI (`python manage.py test tests.test_tenant_boundary`)
- [ ] Branch `claude/admiring-fermi-531840` revisada e mergeada em `main`

---

## Fase 1 — Backup e freeze

```bash
# 1a. Backup completo antes de qualquer mudança
pg_dump $DATABASE_URL \
  --format=custom \
  --compress=9 \
  --file=/backups/pre-tenant/$(date +%Y%m%d_%H%M%S)_full.dump

# 1b. Verificar que o dump tem tamanho razoável (não é 0 bytes)
ls -lh /backups/pre-tenant/

# 1c. Testar restore do dump em banco de staging (opcional mas recomendado)
```

- [ ] Backup salvo e tamanho verificado

---

## Fase 2 — Deploy do código

```bash
# 2a. Deploy da branch
git pull origin main

# 2b. Instalar dependências (django-tenants já no requirements.txt)
pip install -r requirements.txt

# 2c. System check
python manage.py check

# 2d. Aplicar migrations SHARED (control_box, control_membership, etc.)
python manage.py migrate_schemas --shared
```

- [ ] `migrate_schemas --shared` retorna exit 0
- [ ] Tabelas em public: `control_box`, `control_membership`, `control_boxprovisioningevent`, `control_platformauditevent`

---

## Fase 3 — Provisionar box_pilot

```bash
# 3a. Criar o owner do box_pilot (se ainda não existe)
python manage.py createsuperuser --username=owner_pilot --email=owner@octoboxfit.com.br

# 3b. Provisionar o schema
python manage.py provision_box \
  --slug=pilot \
  --owner-email=owner@octoboxfit.com.br \
  --display-name="Box Piloto" \
  --plan=monthly

# 3c. Verificar schema criado
# Em psql:
# \dt box_pilot.*
# Deve listar 30+ tabelas
```

- [ ] `provision_box` retorna exit 0
- [ ] `\dt box_pilot.*` lista ≥ 30 tabelas
- [ ] `control_boxprovisioningevent` tem 4 linhas com `status='ok'` para o box_pilot

---

## Fase 4 — Migrar dados existentes

```bash
# 4a. Preview (sem escrever nada)
python manage.py migrate_existing_data_to_pilot --slug=pilot --dry-run

# 4b. Verificar contagens no preview — espera-se N linhas em cada tabela boxcore_*

# 4c. Execução real
python manage.py migrate_existing_data_to_pilot --slug=pilot

# 4d. Validar contagens (incluído automaticamente, mas pode rodar isolado)
# Procure por "Todas as contagens conferem." na saída

# 4e. Smoke test do tenant
python manage.py smoke_test_tenant --slug=pilot --verbose
```

- [ ] `migrate_existing_data_to_pilot` retorna exit 0
- [ ] "Todas as contagens conferem." aparece na saída
- [ ] `smoke_test_tenant --slug=pilot` retorna exit 0 (8/8 checks)

---

## Fase 5 — Smoke tests por papel

Para cada papel, logar com um usuário real e verificar:

| Papel | URL | Expectativa |
|---|---|---|
| Owner | `/dashboard/` | Dashboard carrega sem erro 500 |
| Manager | `/dashboard/` | Dashboard carrega sem erro 500 |
| Coach | `/dashboard/` | Dashboard carrega sem erro 500 |
| Recepção | `/dashboard/` | Dashboard carrega sem erro 500 |

```bash
# Healthcheck tenant (via curl após login)
curl -b session=<cookie> https://app.octoboxfit.com.br/api/v1/health/tenant/
# Esperado: {"status":"ok","tenant":"box_pilot","healthy":true}

# Healthcheck público
curl https://app.octoboxfit.com.br/api/v1/health/
# Esperado: {"status":"ok","runtime":"control","tenants_active":1,"healthy":true}
```

- [ ] 4 logins OK (Owner, Coach, Manager, Recepção)
- [ ] `/api/v1/health/tenant/` retorna `healthy:true` com `tenant:"box_pilot"`
- [ ] `/api/v1/health/` retorna `tenants_active:1`

---

## Fase 6 — E2E Early Adopter (primeiro tenant pago)

```bash
# 6a. Criar PendingSignup via formulário de signup ou admin
# 6b. Completar fluxo Stripe checkout (modo test com cartão 4242...)
# 6c. Webhook chega → mark_pending_signup_paid → magic link enviado
# 6d. Clicar no link → OnboardingWizardView → activate_and_provision()
# 6e. Verificar:
python manage.py smoke_test_tenant --slug=<novo-slug> --verbose
```

- [ ] E2E Early Adopter completo em < 5 minutos
- [ ] `activate_and_provision` criou User + Box + Membership
- [ ] `smoke_test_tenant` passa para o novo box

---

## Fase 7 — 24h de observação

```bash
# Monitorar logs em tempo real
tail -f /logs/octobox.log | grep -E "ERROR|CRITICAL|schema_name"

# Verificar ausência de erros cross-schema
grep "cross-schema\|SchemaDoesNotExist\|relation.*does not exist" /logs/octobox.log

# Healthcheck a cada hora (configurar no Sentry/UptimeRobot)
curl https://app.octoboxfit.com.br/api/v1/health/
```

- [ ] 0 erros `ERROR` ou `CRITICAL` relacionados a tenant/schema
- [ ] `/api/v1/health/` verde por 24h contínuas
- [ ] Nenhum aluno reporta "tela branca" ou erro 500

---

## Fase 8 — Provisionar próximos 5 boxes

Repetir Fase 3+4 para cada box. Para boxes novos (sem dados legados em public), apenas:

```bash
python manage.py provision_box \
  --slug=<slug-do-cliente> \
  --owner-email=<email-do-owner> \
  --display-name="<Nome do Box>"

python manage.py smoke_test_tenant --slug=<slug-do-cliente>
```

- [ ] Box 2 provisionado e smoke test OK
- [ ] Box 3 provisionado e smoke test OK
- [ ] Box 4 provisionado e smoke test OK
- [ ] Box 5 provisionado e smoke test OK
- [ ] Box 6 provisionado e smoke test OK

---

## Rollback de emergência

Se algo der errado após a Fase 2 (antes de migrate_existing_data_to_pilot):

```bash
# Reverter deploy
git revert HEAD --no-edit
git push origin main

# Rollback do schema (se provision_box já rodou)
python manage.py archive_box --slug=pilot  # renomeia schema para archived_box_pilot_<ts>

# Restaurar backup se dados foram corrompidos
pg_restore --clean --if-exists -d $DATABASE_URL /backups/pre-tenant/<ts>_full.dump
```

Se `migrate_existing_data_to_pilot` **sem** `--truncate-source` já rodou mas deu erro:
- Os dados originais em `public` **não foram removidos** (sem `--truncate-source`)
- O schema `box_pilot` pode estar parcialmente migrado
- Archive o `box_pilot` e provisione novamente: `archive_box --slug=pilot` + `provision_box --slug=pilot`
- Re-execute `migrate_existing_data_to_pilot` (idempotente via ON CONFLICT DO NOTHING)

---

## Critério final de pronto Sprint 5

- [ ] ≥ 5 boxes ACTIVE em `SELECT COUNT(*) FROM control_box WHERE status='active'`
- [ ] `SELECT COUNT(*) FROM control_platformauditevent WHERE kind='box.provisioned'` ≥ 5
- [ ] 0 linhas em `control_platformauditevent WHERE kind LIKE 'box.suspended%'`
- [ ] `/api/v1/health/` com `tenants_active ≥ 5` e `healthy: true`
- [ ] 24h sem ERROR nos logs
