# Audit: Cache Call Sites em Apps TENANT

**Sprint 0 — gerado em 2026-05-08**
**Escopo:** todos os `cache.get/set/delete` em apps que serão classificadas como TENANT_APPS após a migração schema-per-tenant. Identificar quais cache keys já incluem identificador de tenant e quais são ambíguos (risco de vazamento cross-tenant).

---

## Problema central

Com django-tenants, cada request ativa um schema (`SET search_path TO box_xxx, public`). O cache Redis, porém, é **compartilhado entre todos os tenants** (Redis não tem schema isolation). Uma cache key que não inclui `box_id` ou `tenant_slug` vaza dados entre tenants.

**Risco concreto:** tenant A faz `cache.set('student:42:home', payload)`. Tenant B tem um student com `id=42` no SEU schema. Se B fizer `cache.get('student:42:home')` recebe o payload de A.

---

## Apps classificadas como TENANT_APPS (revisão preliminar)

| App | Status TENANT |
|---|---|
| `students` | TENANT ✅ |
| `finance` | TENANT ✅ |
| `operations` | TENANT ✅ |
| `dashboard` | TENANT ✅ |
| `access` | TENANT ✅ |
| `student_app` | TENANT ✅ |
| `onboarding` | TENANT ✅ |
| `communications` | TENANT ✅ |
| `quick_sales` | TENANT ✅ |
| `guide` | TENANT ✅ |
| `auditing` | misto — AuditEvent per-tenant, PlatformAuditEvent public |

Apps SHARED_APPS (public — cache seguro por design):
- `student_identity`, `shared_support`, `signup`, `integrations`, `knowledge`, `monitoring`

---

## 1. Mapa de call sites por arquivo

### `dashboard/dashboard_snapshot_queries.py:384`
```python
cache.get_or_set(cache_key, _calculate, timeout=jittered_ttl)
```
- **Precisa investigar:** qual é o formato de `cache_key`? Ver definição na função.
- **Risco:** ALTO se cache_key não inclui tenant. Dashboard snapshot contém dados financeiros e de alunos.

### `access/signals.py:30,37`
```python
cache.delete(cache_key)
```
- Invalidação. Problema se `cache_key` foi gerado sem tenant → não invalida o item certo para o tenant.

### `access/shell_actions.py:77,130`
```python
cache.get(cache_key)
cache.set(cache_key, counts, timeout=...)
```
- Counts de alunos/status. **Risco:** MÉDIO se key não diferencia tenant.

### `access/roles/__init__.py:66,77`
```python
cache.get(cache_key)  # cache_key usa role.slug
cache.set(cache_key, role.slug, timeout=86400)
```
- Role lookup. Roles são globais (auth.Group em public) → provavelmente OK. Mas se roles são per-tenant via Membership.role → VERIFICAR.

### `operations/services/wod_day_apply_undo.py:27,33,52`
```python
cache.get(key)
cache.delete(key)
```
- Undo de WOD day (estado temporário). **Risco:** MÉDIO se key usa apenas `wod_day_id` sem tenant.

### `operations/services/wod_day_apply_executor.py:120`
```python
cache.set(...)
```
- Execução de aplicação de WOD. **Risco:** MÉDIO.

### `shared_support/editing_locks.py:101,135,137,152,156,170,190`
```python
cache.get(key), cache.set(key, ...), cache.delete(key)
```
- Locks de edição. **Risco:** ALTO. Se lock key = `lock:student:42` sem tenant, tenant A pode bloquear recurso de tenant B.

### `shared_support/background_jobs.py:62,106`
```python
cache.get(f"{JOB_PREFIX}{job_id}")
cache.set(f"{JOB_PREFIX}{job_id}", ...)
```
- Jobs em background. `job_id` é provavelmente UUID único — **Risco BAIXO** (UUID improvável de colidir).

### `shared_support/redis_snapshots.py:27,96,111,129,136`
```python
cache.get(key)
cache.set(key, ...)
cache.get_many(keys)
cache.set_many(payloads, ...)
cache.delete(key)
```
- Snapshots Redis. **Risco:** ALTO. Ver formato de `key` na função `build_key`.

### `shared_support/defenses/anti_exfiltration_throttles.py:42,52`
```python
self.history = cache.get(self.key, [])
cache.set(self.key, self.history, self.duration)
```
- Throttle de exfiltração. Key provavelmente inclui user_id + IP. **Risco:** BAIXO (user é global).

### `shared_support/security/__init__.py:145,147,315,323,325`
```python
cache.incr(cache_key)
cache.set(cache_key, 1, timeout=window_seconds)
cache.get(cache_key, 0)
```
- Rate limiting. Keys geralmente incluem IP/user. **Risco:** BAIXO mas verificar se inclui tenant quando throttle é per-box.

### `student_app/application/wod_snapshots.py:134,150`
```python
cache.get(cache_key)
cache.set(cache_key, snapshot, timeout=...)
```
- Snapshots do WOD do aluno. **Risco:** ALTO. Ver cache_keys.py.

### `student_app/application/rm_snapshots.py:107,125`
```python
cache.get(cache_key)
cache.set(cache_key, snapshot, timeout=...)
```
- Snapshots de RM. **Risco:** ALTO. Mesmo formato.

### `student_app/application/home_snapshots.py:201,282,304,325`
```python
cache.get(cache_key), cache.set(cache_key, ...)
```
- Home snapshot do aluno. Dados pessoais. **Risco:** ALTO.

### `student_app/application/agenda_snapshots.py:92,186`
```python
cache.get(cache_key), cache.set(cache_key, ...)
```
- Agenda. **Risco:** ALTO.

### `student_app/application/cache_invalidation.py:39,45,74,81,82,84,85,124,131,133,140`
```python
cache.delete_pattern(f'*student_app:agenda:v1:{box_slug}:*')
cache.delete_pattern(f'*student_app:home:v1:{box_slug}:student:*')
```
- **POSITIVO:** Invalida por `box_slug`. Indica que o padrão de key JÁ inclui box_slug.
- **Risco residual:** Se `box_slug` vira `box_id` (inteiro) pós-migração, as keys antigas ficam stale. Exige flush ou versão de prefixo.

### `student_identity/security.py:96,98`
```python
cache.incr(cache_key), cache.set(cache_key, 1, ...)
```
- Rate limiting de identity (OAuth, convites). `student_identity` é SHARED_APPS → cache é compartilhado entre tenants por design. **Risco:** BAIXO se key inclui IP/email.

### `finance/views/stripe_checkout.py:42,48`
```python
cache.get(key, 0)
cache.set(key, attempts + 1, timeout=3600)
```
- Retry throttle de checkout. `finance` é TENANT. Key deve incluir tenant ou user_id único. **Risco:** MÉDIO.

### `monitoring/signal_mesh_runtime.py:17,30`
```python
cache.get(SIGNAL_MESH_RUNTIME_CACHE_KEY)
cache.set(SIGNAL_MESH_RUNTIME_CACHE_KEY, state, ...)
```
- Estado de monitoramento global. `SIGNAL_MESH_RUNTIME_CACHE_KEY` é constante. **Risco:** MÉDIO-ALTO. Com 20 tenants, qual tenant atualiza o key? Qual tenant lê? Deve ser por tenant ou movido para SHARED.

---

## 2. `student_app/application/cache_keys.py` — análise do padrão atual

```python
from shared_support.box_runtime import normalize_box_runtime_slug

def normalize_student_cache_box_slug(box_root_slug):
    return normalize_box_runtime_slug(box_root_slug)
```

O padrão atual usa `box_root_slug` como discriminador. Após a migração:
- `box_root_slug` será substituído por `box_id` (FK para `control.Box`)
- O slug do box ainda existirá em `Box.slug` mas não será mais lido de `BOX_RUNTIME_SLUG`
- **Ação necessária:** Atualizar `cache_keys.py` para aceitar `box_slug` vindo do tenant ativo (`connection.tenant.slug` ou `connection.schema_name`) em vez de `get_box_runtime_slug()`

---

## 3. Classificação de risco consolidada

| Nível | Arquivos | Ação no Sprint |
|---|---|---|
| 🔴 ALTO | `student_app/application/*_snapshots.py`, `shared_support/editing_locks.py`, `shared_support/redis_snapshots.py`, `dashboard/dashboard_snapshot_queries.py` | Sprint 3: Validar que key inclui tenant schema name |
| 🟡 MÉDIO | `operations/services/wod_day_apply_*.py`, `access/shell_actions.py`, `monitoring/signal_mesh_runtime.py`, `finance/views/stripe_checkout.py` | Sprint 3: Revisar e adicionar prefixo de tenant |
| 🟢 BAIXO | `shared_support/background_jobs.py`, `shared_support/defenses/anti_exfiltration_throttles.py`, `shared_support/security/__init__.py`, `student_identity/security.py` | Sprint 3: Confirmar via teste |

---

## 4. Padrão recomendado pós-migração

```python
# Em vez de:
cache_key = f"student_app:home:v1:{get_box_runtime_slug()}:student:{student_id}"

# Usar (via django-tenants connection):
from django.db import connection
tenant_slug = connection.schema_name  # retorna 'box_001', 'box_002', etc.
cache_key = f"student_app:home:v1:{tenant_slug}:student:{student_id}"
```

O `schema_name` é o discriminador mais seguro porque:
1. É único por tenant (garantido pelo django-tenants)
2. É o mesmo valor que o Postgres usa para search_path
3. Não depende de `BOX_RUNTIME_SLUG` que será removido

---

## 5. Checklist de pronto (Sprint 3)

- [ ] Todos os arquivos 🔴 ALTO auditados individualmente (verificar `cache_key` real)
- [ ] `cache_invalidation.py` atualizado para usar `connection.schema_name` em vez de `box_slug` string
- [ ] `cache_keys.py` atualizado — remover dependência de `get_box_runtime_slug()`
- [ ] `monitoring/signal_mesh_runtime.py` movido para SHARED ou key inclui `schema_name`
- [ ] Teste boundary: cache de box_001 não vaza para box_002 (ver boundary tests Sprint 4)
