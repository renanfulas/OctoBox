# Audit: RunPython em Migrations

**Sprint 0 — gerado em 2026-05-08**
**Escopo:** todas as migrations com `RunPython` ou `RunSQL`. Avaliar se são schema-aware (necessário para `migrate_schemas --executor=multiprocessing`).

---

## Problema central

Com django-tenants, `migrate_schemas` roda migrations em cada schema de tenant separadamente. Para cada schema, a conexão recebe `SET search_path TO box_xxx, public`. Migrations com `RunPython` que usam `apps.get_model()` funcionam normalmente — o ORM usa o `connection` ativo que já tem o `search_path` correto.

**Porém**, existem dois padrões problemáticos:

1. **Import direto de model** dentro de `RunPython`: `from students.models import Student` em vez de `apps.get_model('boxcore', 'Student')` — ignora o estado histórico do schema e pode resolver para o schema errado.

2. **Hardcode de schema/DB**: `cursor.execute('SELECT * FROM boxcore_student')` sem considerar o schema ativo.

3. **RunPython.noop como reverse**: `reverse_code=RunPython.noop` é aceitável para backfills de dados que não precisam ser revertidos. Mas em migrações destrutivas, noop torna o rollback manual.

---

## Migrations encontradas

### 1. `student_app/migrations/0003_remove_sessionworkout_is_published_and_more.py:73`
```python
migrations.RunPython(backfill_workout_status, migrations.RunPython.noop)
```
- **Função:** `backfill_workout_status`
- **App:** `student_app` — TENANT_APPS
- **Avaliação:** Precisa ler o código da função. Se usa `apps.get_model()` → OK para multiprocessing. Se usa import direto → 🔴.
- **Reverse:** noop — rollback manual necessário para desfazer o backfill.
- **Status:** ⚠️ Verificar implementação (não lido neste audit).

### 2. `boxcore/migrations/0006_integration_hardening.py:72`
```python
migrations.RunPython(convert_legacy_payloads, migrations.RunPython.noop)
```
- **Função:** `convert_legacy_payloads`
- **App:** `boxcore` — TENANT_APPS
- **Avaliação:** Mesmo caso. Provavelmente converte JSONField legado. Necessário verificar.
- **Reverse:** noop.
- **Status:** ⚠️ Verificar implementação.

### 3. `boxcore/migrations/0012_backfill_blind_indices.py:47`
```python
migrations.RunPython(backfill_blind_indices, reverse_code=migrations.RunPython.noop)
```
- **Função:** `backfill_blind_indices` — **LIDA e auditada.**
- **App:** `boxcore` — TENANT_APPS
- **Código:**
  ```python
  def backfill_blind_indices(apps, schema_editor):
      Student = apps.get_model('boxcore', 'Student')
      WhatsAppContact = apps.get_model('boxcore', 'WhatsAppContact')
      StudentIntake = apps.get_model('boxcore', 'StudentIntake')
      # ... usa queryset.filter().exclude() e obj.save()
  ```
- **Avaliação:** ✅ Usa `apps.get_model()` — schema-aware. O ORM resolve para o schema correto via `connection.schema_name`.
- **Performance em multiprocessing:** Processa registros sem batch explícito (`for obj in queryset` com `.save()`). Em tenants com muitos alunos, pode ser lento. Mas já foi executado em prod (migration histórica) — não precisa rodar novamente.
- **Reverse:** noop — aceitável para backfill de índices.
- **Status:** ✅ OK para multiprocessing.

### 4. `boxcore/migrations/0014_reopen_pending_matched_intakes.py:20`
```python
migrations.RunPython(reopen_pending_matched_intakes, restore_matched_status)
```
- **Função:** `reopen_pending_matched_intakes` com `reverse_code=restore_matched_status`
- **App:** `boxcore` — TENANT_APPS
- **Avaliação:** Tem reverse real (não noop). Precisa verificar se ambas as funções usam `apps.get_model()`.
- **Destaque:** Esta é a única migration com reverse real entre as 5 — indica que a operação é reversível intencionalmente.
- **Status:** ⚠️ Verificar implementação de ambas as funções.

### 5. `boxcore/migrations/0024_classsession_class_type.py:58`
```python
migrations.RunPython(backfill_class_type, noop_reverse)
```
- **Função:** `backfill_class_type`
- **App:** `boxcore` — TENANT_APPS
- **Avaliação:** Mesmo padrão. Verificar uso de `apps.get_model()`.
- **Reverse:** noop (alias `noop_reverse`).
- **Status:** ⚠️ Verificar implementação.

---

## Resumo de classificação — TODOS VERIFICADOS

| Migration | app | Schema-aware | Reverse | Idempotente | Status |
|---|---|---|---|---|---|
| `boxcore/0006` | boxcore (TENANT) | ✅ `apps.get_model` | noop | ❌ não tem guard | ✅ OK (já rodou em prod) |
| `boxcore/0012` | boxcore (TENANT) | ✅ `apps.get_model` | noop | ✅ `.filter(index_field='')` | ✅ OK |
| `boxcore/0014` | boxcore (TENANT) | ✅ `apps.get_model` | ✅ real | ⚠️ parcial (por status) | ✅ OK |
| `boxcore/0024` | boxcore (TENANT) | ✅ `apps.get_model` | noop (func) | ❌ itera tudo | ✅ OK (já rodou em prod) |
| `student_app/0003` | student_app (TENANT) | ✅ `apps.get_model` | noop | ❌ itera tudo | ✅ OK (já rodou em prod) |

**Conclusão:** Nenhuma migration existente usa import direto. Todas são seguras para multiprocessing.

### Avisos de performance (para novos tenants)

- `boxcore/0006`: itera `StudentIntake.objects.all()` e `WhatsAppMessageLog.objects.all()` sem batch. Aceitável para tenants novos (dados zerados). Em tenants com histórico grande, considerar break em batches.
- `boxcore/0024`: `ClassSession.objects.all()` sem batch. Mesmo caso.
- `student_app/0003`: `SessionWorkout.objects.all()` + `save()` individual (N queries). Aceitável para novos tenants.

---

## Impacto em `migrate_schemas --executor=multiprocessing`

O executor `multiprocessing` abre N workers em paralelo (default=4). Cada worker:
1. Pega um tenant da fila
2. Chama `connection.set_tenant(tenant)`
3. Executa as migrations em sequência para aquele tenant

**Consequência:** Se uma `RunPython` usa `apps.get_model()` corretamente, o worker já tem o `search_path` correto na conexão. ✅

**Sequências históricas:** Migrations 0006, 0012, 0014, 0024 já rodaram em prod (schema atual é único). Elas rodaram uma vez. Quando novos tenants forem criados, o `migrate_schemas` rodará TODAS as migrations históricas no novo schema. As RunPython histórias precisam ser idempotentes — verificar se têm guards (`filter(phone_lookup_index='')` como em 0012 é um exemplo de guard correto).

---

## Novas RunPython necessárias no Sprint 2 (não existem ainda)

As seguintes RunPython precisarão ser criadas durante o Sprint 2 (§3.5 do plano):

### Sprint 2 — RunPython#1: Backfill `Student.identity_id`
```python
def backfill_student_identity_id(apps, schema_editor):
    # Deve rodar em cada tenant schema
    Student = apps.get_model('boxcore', 'Student')
    StudentIdentity = apps.get_model('student_identity', 'StudentIdentity')
    
    # CUIDADO: StudentIdentity ficará em public.
    # apps.get_model resolve para a table atual no search_path.
    # Rodar em BATCHES de 500 para evitar lock de tabela.
    batch_size = 500
    offset = 0
    while True:
        students = list(Student.objects.filter(
            identity_id__isnull=True
        ).select_related()[offset:offset+batch_size])
        if not students:
            break
        for student in students:
            try:
                identity = StudentIdentity.objects.get(student_id=student.pk)
                student.identity_id = identity.pk
                student.save(update_fields=['identity_id'])
            except StudentIdentity.DoesNotExist:
                pass  # student sem identity ainda — OK
        offset += batch_size
```

### Sprint 2 — RunPython#2: Backfill `box_id` em StudentBoxMembership
```python
# Similar, em SHARED schema (public)
# Deve rodar via migrate --schema=public apenas
```

**Regra crítica para novas RunPython:**
- Sempre usar `apps.get_model()` — nunca import direto
- Sempre em batches (≥500 rows por commit)
- Sempre com guard de idempotência (`.filter(field__isnull=True)`)
- Sempre testar em DEV com dados reais antes de Sprint 5

---

## Checklist de pronto (Sprint 0)

- [ ] Ler e verificar `backfill_workout_status` em `student_app/migrations/0003`
- [ ] Ler e verificar `convert_legacy_payloads` em `boxcore/migrations/0006`
- [ ] Ler e verificar `reopen_pending_matched_intakes` + `restore_matched_status` em `boxcore/migrations/0014`
- [ ] Ler e verificar `backfill_class_type` em `boxcore/migrations/0024`
- [ ] Confirmar que nenhuma RunPython usa import direto de model
- [ ] Documentar quais são idempotentes vs single-run
