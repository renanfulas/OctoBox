# ADR-011 — Signal handlers defensivos a valores cru

**Status:** Aceito
**Data:** 2026-05-20
**Contexto:** Sprint 4, Bucket C (reset_demo_workspace + session_cancellation)

## Decisão

Signal handlers (`post_save`, `post_delete`) **devem normalizar tipos** antes
de fazer aritmética/comparação com campos do modelo. Especificamente:

- DateTime fields: aceitar `str` ISO via `parse_datetime` fallback + `None` → default.
- Operações aritméticas: envolver em `try/except TypeError` se o tipo final ainda
  pode falhar.

Caso concreto em `operations/signals/session_cancellation.py:62-78`:

```python
session_time = getattr(instance, 'scheduled_at', now)
if isinstance(session_time, str):
    parsed = parse_datetime(session_time)
    session_time = parsed if parsed is not None else now
if session_time is None:
    session_time = now
try:
    lead_minutes = max(0, int((session_time - now).total_seconds() / 60))
except TypeError:
    lead_minutes = 0
```

## Por quê

Django converte `str` → `datetime` no save da DB, mas signal `post_save`
dispara com o **state em memória** do `instance`. Em alguns fluxos:

- Bulk operations (`reset_demo_workspace` command) podem re-emitir signals
  com o state pre-conversão.
- Callers que passam string como atalho (ex.: testes com `scheduled_at='2026-03-10T07:00:00Z'`)
  fazem a string sobreviver até o signal.
- Re-leitura via `refresh_from_db()` vs uso direto do parâmetro `instance` no
  signal cria divergência de tipo.

Resultado: `TypeError: unsupported operand type(s) for -: 'str' and 'datetime.datetime'`.

Signal handler é **corredor natural** para receber valores cru — o contrato do
sender pode mudar (refactor, novo caller, bulk operation) e o handler precisa
ser robusto.

## Consequências

- Recuperou 2 testes do reset_demo_workspace (Bucket C).
- Removeu risco latente em produção: qualquer fluxo bulk que re-emite signal
  agora não quebra mesmo com state inconsistente.
- Tests também devem usar `datetime` real em `objects.create(scheduled_at=...)` —
  defensividade dupla. Test foi atualizado em paralelo.

## Anti-pattern proibido

- Acessar `instance.<datetime_field>` em signal handler sem normalização.
- Aritmética em campo do `instance` sem `try/except` defensivo se há histórico
  de divergência de tipo.
- Confiar que `kwargs['raw']` chega no signal — Django passa o instance state-as-is.

## Referências

- `operations/signals/session_cancellation.py:60-78` — implementação canonical.
- Django docs: <https://docs.djangoproject.com/en/5.0/ref/signals/#post-save>
  ("`instance` is the actual instance being saved").
