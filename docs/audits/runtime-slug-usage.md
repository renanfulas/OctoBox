# Audit: BOX_RUNTIME_SLUG Usage

**Sprint 0 — gerado em 2026-05-08**
**Escopo:** todos os usos de `BOX_RUNTIME_SLUG`, `get_box_runtime_slug()`, `normalize_box_runtime_slug()`, `box_root_slug` como campo de modelo. Confirmar ou ajustar §1.2 do plano de migração.

---

## Fonte central

**`shared_support/box_runtime.py`** — módulo único que encapsula o runtime slug:

```python
DEFAULT_BOX_RUNTIME_SLUG = 'control'

def normalize_box_runtime_slug(value: str | None) -> str:
    return normalized or DEFAULT_BOX_RUNTIME_SLUG

def get_box_runtime_slug() -> str:
    return normalize_box_runtime_slug(
        os.getenv('BOX_RUNTIME_SLUG')
        or DEFAULT_BOX_RUNTIME_SLUG
    )

def get_box_runtime_namespace(base_prefix: str = 'octobox') -> str:
    return f'{normalized_base}:{get_box_runtime_slug()}'
```

Este módulo lê `BOX_RUNTIME_SLUG` do ambiente. Com schema-per-tenant, o "runtime slug" será fornecido pelo `connection.schema_name` (django-tenants), não mais pela variável de ambiente.

---

## Mapa de uso por arquivo

### Grupo A: SHARED_APPS — `student_identity` (7 arquivos, ~40 call sites)

Estes arquivos usam `get_box_runtime_slug()` para preencher `box_root_slug` em modelos que **serão migrados para public**. Após a migração, `box_root_slug: CharField` vira `box_id: FK(control.Box)`.

| Arquivo | Tipo de uso | Ação |
|---|---|---|
| `student_identity/models.py:23` | `default=_default_box_root_slug` em 4 modelos | Sprint 2: substituir default por `box_id` FK |
| `student_identity/oauth_journeys.py:58` | `if box_invite_link.box_root_slug != get_box_runtime_slug()` | Sprint 2: comparar `box_id` vs `request.tenant.id` |
| `student_identity/staff_delivery_actions.py:31,65` | `.filter(box_root_slug=get_box_runtime_slug())` | Sprint 2: `.filter(box_id=request.tenant.id)` |
| `student_identity/staff_membership_actions.py:44,78` | `box_root_slug=get_box_runtime_slug()` em create | Sprint 2: `box_id=request.tenant.id` |
| `student_identity/staff_invite_actions.py:41,59,100,110,127,130,142` | múltiplos usos em create + dict | Sprint 2: refatorar para `box_id` |
| `student_identity/staff_invite_actions.py:59` | f-string em descrição de auditoria | Sprint 2: usar `box.name` ou slug |
| `student_identity/queries/invitation_operations_queries.py:39` | `self.box_root_slug = get_box_runtime_slug()` | Sprint 2: `self.box = request.tenant` |
| `student_identity/views.py:74,113,296,376` | `box_root_slug=get_box_runtime_slug()` em contexto | Sprint 2: `box_id=request.tenant.id` |

**Total estimado: ~25 substituições em student_identity.**

---

### Grupo B: SHARED_APPS — `student_app/application/cache_invalidation.py`

```python
# linha 39
return normalize_student_cache_box_slug(fallback or get_box_runtime_slug())

# linhas 45, 81, 82, 84, 85, 131, 133 (cache_invalidation patterns)
cache.delete_pattern(f'*student_app:agenda:v1:{box_slug}:*')
```

- **Problema:** `get_box_runtime_slug()` retorna o slug global de ambiente. Em multitenancy, deve retornar o slug do tenant ativo.
- **Ação Sprint 3:** Refatorar `_resolve_box_slug()` para usar `connection.schema_name` ou `connection.tenant.slug` em vez de `get_box_runtime_slug()`.

---

### Grupo C: TENANT_APPS — `student_app/views/onboarding_loader.py:42`

```python
'box_root_slug': pending_onboarding.get('box_root_slug') or get_box_runtime_slug()
```

- Fallback para slug de runtime se não encontrar no pending_onboarding. Em multitenancy, o tenant já está ativo no request — usar `connection.schema_name` como fallback.
- **Ação Sprint 3:** Usar `connection.tenant.slug` como fallback.

---

### Grupo D: TENANT_APPS — `onboarding/intake_invite_actions.py:72,106`

```python
box_root_slug=get_box_runtime_slug()
# e
'box_root_slug': get_box_runtime_slug()
```

- `onboarding` é TENANT_APPS (lida com StudentIntake, StudentAppInvitation).
- Estes campos referenciam `box_root_slug` em `StudentAppInvitation` que migra para public.
- **Ação Sprint 2:** Refatorar para passar `box_id` em vez de `box_root_slug`.

---

### Grupo E: SHARED_APPS — `api/v1/views.py:75,76`

```python
'runtime_slug': get_box_runtime_slug(),
'runtime_namespace': get_box_runtime_namespace(),
```

- Endpoint `/api/v1/health/tenant/` (ou similar) que expõe o runtime slug.
- Plano §9 menciona que healthcheck deve reportar tenant atual.
- **Ação Sprint 1:** Quando tenant estiver ativo, expor `connection.tenant.slug` (ou `connection.schema_name`) em vez de `get_box_runtime_slug()`.

---

### Grupo F: TESTES — `boxcore/tests/test_guide.py` e `student_identity/tests.py`

Dezenas de ocorrências de `get_box_runtime_slug()` em fixtures de teste. Após a migração:
- Testes de TENANT_APPS precisarão de `TestCase` com `set_schema_to('box_001')` ou equivalente django-tenants.
- Fixture de `box_root_slug=get_box_runtime_slug()` deve ser substituída por `box_id=Box.objects.get(slug='box-test').id`.
- **Ação Sprint 4 (boundary tests):** Migrar fixtures de teste para o novo padrão.

---

### Grupo G: Script legado — `scripts/hostgator_bootstrap_octobox.py:48,59`

```python
runtime_slug = os.environ.get("OCTOBOX_RUNTIME_SLUG", "octoboxfit-production")
```

- Script de bootstrap para Hostgator (deploy legado — pré-multitenancy).
- Usa `OCTOBOX_RUNTIME_SLUG` em vez de `BOX_RUNTIME_SLUG` — já é uma variante diferente.
- **Ação:** Marcar como deprecated no Sprint 5. Não bloqueia migration.

---

## Campos de modelo `box_root_slug: CharField` a serem substituídos

| Model | Arquivo | Campo | Tipo atual | Ação |
|---|---|---|---|---|
| `StudentIdentity` | `student_identity/models.py:81` | `box_root_slug` | `CharField(max_length=64)` | Sprint 2: remover |
| `StudentIdentity` | `student_identity/models.py:82` | `primary_box_root_slug` | `CharField(max_length=64)` | Sprint 2: remover |
| `StudentBoxMembership` | `student_identity/models.py:121` | `box_root_slug` | `CharField(max_length=64)` | Sprint 2: → `box_id FK` |
| `StudentAppInvitation` | `student_identity/models.py:183` | `box_root_slug` | `CharField(max_length=64)` | Sprint 2: → `box_id FK` |
| `StudentBoxInviteLink` | `student_identity/models.py:214` | `box_root_slug` | `CharField(max_length=64)` | Sprint 2: → `box_id FK` |
| `StudentTransfer` | `student_identity/models.py:258,259` | `from_box_root_slug` / `to_box_root_slug` | `CharField(max_length=64)` | Sprint 2: → `from_box_id FK` / `to_box_id FK` |
| `StudentPushSubscription` | `student_identity/models.py:329` | `box_root_slug` | `CharField(max_length=64)` | Sprint 2: → `box_id FK` |

**Total: 8 campos CharField a migrar para FK ou IntegerField.**

---

## Dependência de BOX_RUNTIME_SLUG no ambiente

Com schema-per-tenant, a variável `BOX_RUNTIME_SLUG` perde sua razão de existir para o runtime de tenant. Ela será mantida apenas para:

1. **`api/v1/views.py`** (health endpoint) — até ser atualizado no Sprint 1
2. **Testes de integração** que ainda não usam django-tenants — até Sprint 4
3. **Compatibilidade de fallback** durante transição do Sprint 3

**Risco durante transição:** Se código antigo chamar `get_box_runtime_slug()` durante uma request multitenancy, retornará o valor de `BOX_RUNTIME_SLUG` do ambiente (`control`) em vez do slug do tenant ativo. Isso causa:
- Cache key incorreto (dados do tenant `control` lidos por outro tenant)
- `box_root_slug` persistido incorreto em modelos públicos

**Mitigação:** Adicionar warning de deprecação em `get_box_runtime_slug()` no Sprint 1:
```python
import warnings
def get_box_runtime_slug() -> str:
    from django.db import connection
    if hasattr(connection, 'tenant') and connection.tenant is not None:
        warnings.warn(
            "get_box_runtime_slug() chamado durante request multitenancy. "
            "Use connection.tenant.slug ou connection.schema_name.",
            DeprecationWarning, stacklevel=2
        )
    return normalize_box_runtime_slug(os.getenv('BOX_RUNTIME_SLUG') or DEFAULT_BOX_RUNTIME_SLUG)
```

---

## Checklist de pronto (Sprint 0)

- [x] Mapear todos os call sites de `get_box_runtime_slug()`
- [x] Identificar todos os campos `box_root_slug: CharField` nos modelos
- [x] Confirmar que `box_runtime.py` é o único módulo que lê `BOX_RUNTIME_SLUG`
- [ ] Adicionar warning de deprecação em `get_box_runtime_slug()` no Sprint 1
- [ ] Sprint 2: todos os 8 campos CharField migrados para FK
- [ ] Sprint 3: todos os call sites em cache_invalidation.py atualizados
- [ ] Sprint 4: fixtures de teste migradas
