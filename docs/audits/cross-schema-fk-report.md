# Audit: FK Cross-Schema

**Sprint 0 — gerado em 2026-05-08**
**Escopo:** todas as ForeignKey/OneToOneField que cruzarão a fronteira public↔tenant após a migração schema-per-tenant.

---

## Regra de referência

| Direção | Suporte Postgres PG14+ | Integridade referencial no ORM |
|---|---|---|
| tenant → public | ✅ FK real possível (`box_001.student.identity_id → public.studentidentity.id`) | ✅ |
| public → tenant | ❌ Não é possível FK cross-schema sem schema fixo | ⚠️ Nenhuma, deve ser `db_constraint=False` ou `IntegerField` |
| tenant → tenant (mesmo schema) | ✅ FK normal | ✅ |

---

## 1. FKs CRÍTICAS — cruzam a fronteira public → tenant

Estes campos existem em modelos que **irão para SHARED_APPS (public)** mas referenciam `boxcore.Student` que **fica em TENANT_APPS**.

### 1.1 `student_identity.StudentIdentity.student` (OneToOneField)
- **Arquivo:** `student_identity/models.py:80`
- **Tipo atual:** `OneToOneField(Student, on_delete=CASCADE, related_name='app_identity')`
- **Direção pós-migração:** public → tenant ❌
- **Problema:** PostgreSQL não pode criar FK constraint de public para schema variável.
- **Ação obrigatória (§3.5 do plano):** QUEBRAR este O2O. Adicionar `Student.identity_id = FK(public.StudentIdentity, on_delete=PROTECT)` no lado tenant. Rota: tenant→public ✅.
- **Risco se não corrigido:** IntegrityError silenciosa. O ORM não valida FKs cross-schema, mas `CASCADE` de public.StudentIdentity deletaria Student somente se o ORM iterar todos os schemas — o que nunca acontece. Resultado: Student órfão.

### 1.2 `student_identity.StudentBoxMembership.student` (ForeignKey)
- **Arquivo:** `student_identity/models.py:120`
- **Tipo atual:** `ForeignKey(Student, on_delete=CASCADE, related_name='box_memberships')`
- **Direção pós-migração:** public → tenant ❌
- **Ação obrigatória:** Mudar para `student_id = IntegerField(db_index=True)` (sem constraint DB) + adicionar `box_id = FK(control.Box)` para identificar o tenant correto. `on_delete=CASCADE` deve ser simulado via sinal ou job de cleanup, não via banco.
- **Nota:** A identidade real vem do campo `identity = FK(StudentIdentity)` — que permanecerá na mesma tabela (ambas public). Esta FK continua OK.

### 1.3 `student_identity.StudentAppInvitation.student` (ForeignKey)
- **Arquivo:** `student_identity/models.py:182`
- **Tipo atual:** `ForeignKey(Student, on_delete=CASCADE, related_name='app_invitations')`
- **Direção pós-migração:** public → tenant ❌
- **Ação obrigatória:** Mesma estratégia que 1.2. Trocar `student_id` para `IntegerField` + adicionar `box_id = FK(control.Box)`.

### 1.4 `student_identity.StudentTransfer.student` (ForeignKey)
- **Arquivo:** `student_identity/models.py:257`
- **Tipo atual:** `ForeignKey(Student, on_delete=CASCADE, related_name='app_transfers')`
- **Direção pós-migração:** public → tenant ❌
- **Ação obrigatória:** Mesma estratégia. `StudentTransfer` também referencia `StudentIdentity` via FK — OK (ambas public após migração).

### 1.5 `student_identity.StudentPushSubscription.identity` (ForeignKey)
- **Arquivo:** `student_identity/models.py:328`
- **Tipo atual:** `ForeignKey(StudentIdentity, on_delete=CASCADE, related_name='push_subscriptions')`
- **Direção pós-migração:** public → public ✅ (ambas em SHARED_APPS)
- **Status:** OK. Nenhuma ação necessária.

---

## 2. FKs que ficam no tenant (tenant → tenant)

Estes modelos **ficam em TENANT_APPS** e referenciam outros modelos do mesmo tenant. Sem problema.

| Model | FK | Schema pós-migração |
|---|---|---|
| `student_app.StudentExerciseMax` | `student → boxcore.Student` | tenant → tenant ✅ |
| `student_app.StudentAppActivity` | `student → boxcore.Student` | tenant → tenant ✅ |
| `student_app.StudentProfileChangeRequest` | `student → boxcore.Student` | tenant → tenant ✅ |
| `operations.ClassAttendance` | `student → boxcore.Student` | tenant → tenant ✅ |
| `finance.Enrollment` | `student → boxcore.Student` | tenant → tenant ✅ |
| `finance.Payment` | `student → boxcore.Student` | tenant → tenant ✅ |

---

## 3. FKs tenant → public (OK após migração)

Estes são os campos que **devem ser criados** ou mantidos para a direção segura.

| Model | FK pretendida | Status |
|---|---|---|
| `boxcore.Student.identity_id` | `→ public.StudentIdentity` | ⚠️ NÃO EXISTE AINDA — deve ser criado no Sprint 2 |
| `student_app.StudentProfileChangeRequest.identity` | `→ student_identity.StudentIdentity` (futuro: public) | ✅ Direção correta pós-migração |

### Detalhe: `student_app.StudentProfileChangeRequest.identity`
- **Arquivo:** `student_app/models.py:90`
- **Tipo atual:** `ForeignKey('student_identity.StudentIdentity', on_delete=CASCADE)`
- **Direção pós-migração:** tenant → public ✅
- **Observação:** Postgres PG14+ suporta FK cross-schema nesta direção. O Django gerará a constraint corretamente desde que o `search_path` do tenant inclua `public`. Confirmar com SQL-1 (ver `docs/audits/` — validação search_path).

---

## 4. FKs em SHARED_APPS que referenciam auth.User (public → public)

Todos os modelos em `student_identity` que têm `ForeignKey(settings.AUTH_USER_MODEL)` são public→public após a migração. Sem problema.

Exemplos:
- `StudentBoxMembership.approved_by → auth.User` — ✅
- `StudentAppInvitation.created_by → auth.User` — ✅
- `StudentBoxInviteLink.created_by → auth.User` — ✅

**Atenção:** `auth.User` fica em `public` (SHARED_APPS). Qualquer modelo de tenant que referencie `auth.User` é OK (tenant→public).

---

## 5. Resumo de ações por sprint

| Sprint | Ação | Arquivo alvo |
|---|---|---|
| Sprint 2 | Quebrar `StudentIdentity.student` O2O | `student_identity/models.py:80` |
| Sprint 2 | Adicionar `Student.identity_id = FK(public.StudentIdentity)` | `students/model_definitions.py` / nova migration boxcore |
| Sprint 2 | Mudar `StudentBoxMembership.student` para `IntegerField` + `box_id FK` | `student_identity/models.py:120` |
| Sprint 2 | Mudar `StudentAppInvitation.student` para `IntegerField` + `box_id FK` | `student_identity/models.py:182` |
| Sprint 2 | Mudar `StudentTransfer.student` para `IntegerField` + `box_id FK` | `student_identity/models.py:257` |
| Sprint 2 | Backfill `Student.identity_id` para todos os tenants | migration RunPython em batches |

---

## 6. Validação SQL proposta (SQL-1)

Após migração do Sprint 2, executar em DEV:

```sql
-- Verificar se FK cross-schema tenant→public funciona
SET search_path TO box_001, public;
SELECT conname, confrelid::regclass
FROM pg_constraint
WHERE conrelid = 'box_001.boxcore_student'::regclass
  AND contype = 'f';
-- Esperado: fk para public.student_identity_studentidentity
```

```sql
-- Verificar que NÃO há FK de public para tenant
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f'
  AND conrelid::regclass::text LIKE 'student_identity%'
  AND confrelid::regclass::text LIKE 'boxcore%';
-- Esperado: 0 linhas
```

---

## 7. Checklist de pronto (Sprint 0)

- [x] Identificar todas as FKs cross-schema
- [ ] Confirmar que Postgres DEV está rodando (pré-requisito SQL-1)
- [ ] Executar SQL-1 em DEV após Sprint 1 (schema criado)
- [ ] Todas as FKs public→tenant resolvidas antes do Sprint 3
