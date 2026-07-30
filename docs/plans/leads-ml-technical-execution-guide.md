<!--
ARQUIVO: guia tecnico de execucao das ondas da frente de ML de leads e inteligencia de rede.

TIPO DE DOCUMENTO:
- decomposicao tecnica executavel (irmao operacional do plano)

AUTORIDADE:
- alta para COMO implementar cada onda
- baixa para O QUE priorizar (isso vive no plano pai)

DOCUMENTO PAI:
- [leads-ml-foundation-and-network-intelligence-plan.md](leads-ml-foundation-and-network-intelligence-plan.md)

QUANDO USAR:
- ao sentar para implementar qualquer onda
- quando a duvida for assinatura, migration, teste ou ordem de commit

POR QUE ELE EXISTE:
- o plano pai define ondas e criterios; este arquivo desce ao nivel de arquivo,
  assinatura, migration e teste para que a execucao nao precise redescobrir o desenho.
- evita que a implementacao invente estrutura nova quando ja existe padrao no repo.

O QUE ESTE ARQUIVO FAZ:
1. da o esqueleto de codigo de cada onda com assinaturas reais.
2. lista migrations, testes e comando de verificacao por onda.
3. registra ordem de commit e rollback.

PONTOS CRITICOS:
- os esqueletos sao direcao, nao codigo final colavel; adapte ao que o runtime mostrar.
- toda migration em models com app_label 'boxcore' entra em boxcore/migrations/.
- rodar testes exige PostgreSQL (ver docs/testing/README.md); nao existe caminho SQLite.
- ATIVO.
-->

# Guia tecnico de execucao — ML de leads e inteligencia de rede

## Convencoes que valem para todas as ondas

1. **Banco**: PostgreSQL obrigatorio. `docker compose -f docker-compose.postgres.yml up -d` antes de qualquer teste.
2. **Suite rapida**: `python -m pytest boxcore/ tests/ -q`. Antes de PR: `python -m pytest --create-db --migrations -n 4 -q`.
3. **Migrations**: models de dominio tem `app_label = 'boxcore'` (ancora historica). Migration nova vai em `boxcore/migrations/`, proxima na sequencia depois de `0027_payment_currency_payment_stripe_charge_id_and_more.py`.
4. **Um commit por onda**, no minimo. Onda com migration = commit separado da migration.
5. **Nada de reescrita**: toda onda edita arquivo existente ou cria arquivo pequeno novo.
6. **Windows local — armadilha do `python-magic`**: `requirements.txt` fixa
   `python-magic==0.4.27`, que espera `libmagic` nativo (padrao no Linux/Mac).
   No Windows, o import desse modulo pode travar o processo inteiro ou crashar
   com access violation ANTES de qualquer `except ImportError` conseguir
   capturar (e' uma falha nativa, nao uma excecao Python) — isso derrubava
   `pytest-xdist` inteiro sempre que um worker executava
   `test_operational_settings_can_import_contacts_csv` (usa
   `shared_support/validators.py:validate_file_security`). Fix local, sem
   tocar `requirements.txt`: `pip install python-magic-bin` no venv (traz a
   DLL do libmagic para Windows). Descoberto e resolvido em 2026-07-29.
7. **`-n auto` e arriscado neste projeto no Windows**: com muitos workers, um
   crash de worker as vezes deixa o processo principal preso indefinidamente
   em vez de recuperar. Preferir `-n 4` (como a doc de testes ja recomenda) e,
   se quiser rede de seguranca extra, `pip install pytest-timeout` +
   `--timeout=120` para abortar teste individual em vez de travar a suite inteira.

---

## Onda 1 — Trilho de job por tenant

> **STATUS: IMPLEMENTADA em 2026-07-28** (pendente de execucao da suite — o
> ambiente da sessao nao tinha Postgres). Ver secao "Resultado real" no fim desta onda.

### Problema

`manage.py` nao passa por middleware de tenant, entao comando agendado roda em `connection.schema_name == 'public'`. Models de dominio sao TENANT (`boxcore` em `TENANT_APPS`). Tabela nao existe no `public` -> `ProgrammingError`.

O padrao correto ja existe em `finance/reconciliation.py`: itera `Box.objects.filter(status=Box.Status.ACTIVE)` com `schema_context(box.schema_name)`.

### Arquivo novo: `shared_support/tenant_sweep.py`

```python
"""
ARQUIVO: varredura institucional de tenants para comandos agendados.

POR QUE ELE EXISTE:
- comando agendado roda a partir do schema public (cron/systemd nao passa por
  middleware de tenant). Model de dominio e TENANT. Sem schema_context, a query
  bate numa tabela que nao existe no public.

PONTOS CRITICOS:
- todo comando agendado que toque model TENANT deve passar por aqui.
- falha de um box nao pode abortar a varredura dos outros.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django_tenants.utils import schema_context


@dataclass
class TenantSweepResult:
    schemas_touched: int = 0
    schemas_failed: int = 0
    results: list = field(default_factory=list)
    failures: list = field(default_factory=list)


def sweep_active_tenants(handler, *, only_schema: str = '', raise_on_error: bool = False) -> TenantSweepResult:
    """Executa `handler(box)` dentro do schema de cada box ativo.

    handler recebe o Box e roda ja dentro de schema_context.
    Retorno do handler e acumulado em result.results como (schema_name, valor).
    """
    from control.models import Box

    sweep = TenantSweepResult()
    queryset = Box.objects.filter(status=Box.Status.ACTIVE).order_by('schema_name')
    if only_schema:
        queryset = queryset.filter(schema_name=only_schema)

    for box in queryset:
        try:
            with schema_context(box.schema_name):
                sweep.results.append((box.schema_name, handler(box)))
            sweep.schemas_touched += 1
        except Exception as exc:  # noqa: BLE001 — varredura nao pode morrer por 1 box
            sweep.schemas_failed += 1
            sweep.failures.append((box.schema_name, repr(exc)))
            if raise_on_error:
                raise
    return sweep


__all__ = ['TenantSweepResult', 'sweep_active_tenants']
```

### Comandos a migrar

| Comando | Chamada atual | Vira |
|---|---|---|
| `finance/management/commands/evaluate_finance_followups.py` | `evaluate_pending_finance_follow_ups(...)` direto | `sweep_active_tenants(lambda box: evaluate_pending_finance_follow_ups(...))` |
| `operations/management/commands/run_due_nightly_lead_import_jobs.py` | `count_due_nightly_lead_import_jobs(...)` direto | idem, dentro do handler |
| `jobs/management/commands/run_due_async_job_retries.py` | `reprocess_due_async_jobs(...)` direto | idem |

Adicionar em todos: `--schema` (rodar so um box, para debug) e sumario com `schemas_touched` / `schemas_failed`.

### Teste: `tests/test_tenant_boundary.py`

```python
def test_sweep_active_tenants_runs_inside_each_schema(self):
    # cria 2 boxes ativos, roda um handler que grava connection.schema_name
    # assere que os 2 schemas foram visitados e que nenhum foi 'public'

def test_sweep_active_tenants_isolates_failure_per_box(self):
    # handler que levanta no primeiro box; assere schemas_touched >= 1 e failures == 1

def test_scheduled_commands_do_not_query_tenant_models_from_public(self):
    # chama call_command a partir do public; assere ausencia de ProgrammingError
```

### Verificacao manual

```bash
python manage.py evaluate_finance_followups --window 7d
```

Pronto quando: roda do `public` sem `ProgrammingError` e o sumario reporta N schemas.

### Rollback

Reverter os comandos ao corpo anterior; `tenant_sweep.py` fica orfao e inofensivo.

### Resultado real (2026-07-28)

O plano previa 3 comandos agendados. A varredura do repositorio encontrou **6**,
e a auditoria de tenancy de cada um mudou o escopo:

| Comando | Model tocado | Tenancy | Acao |
|---|---|---|---|
| `finance/.../evaluate_finance_followups.py` | `FinanceFollowUp` | TENANT | migrado |
| `jobs/.../run_due_async_job_retries.py` | `AsyncJob` | TENANT | migrado |
| `operations/.../run_due_nightly_lead_import_jobs.py` | `LeadImportJob` | TENANT | migrado |
| `shared_support/.../run_signal_mesh_retry_sweep.py` | `AsyncJob` + 2 SHARED | **misto** | migrado (so a perna TENANT) |
| `integrations/.../run_due_webhook_retries.py` | `WebhookEvent` | SHARED | **nao precisa** |
| `communications/.../cron_whatsapp_log_sweep.py` | `WhatsAppMessageLog` | TENANT | **NAO migrado — decisao pendente** |

Tres descobertas que o plano nao previa:

1. **`run_signal_mesh_retry_sweep` tem tenancy MISTA.** As tres pernas rodavam
   juntas no `public`: so a de `AsyncJob` quebrava, e a mensagem de sucesso
   escondia a falha parcial. Agora a perna TENANT passa pela varredura e as duas
   SHARED continuam rodando uma vez no `public`.
2. **Celery nao esta instalado** (sem `config/celery.py`, ausente do
   `requirements.txt`). O shim de `shared_task` em `operations/tasks.py` faz
   `wrapper.delay = func`, ou seja, `.delay()` roda **sincrono, em processo** —
   por isso o disparo herda o schema da varredura e a correcao funciona hoje.
   **Armadilha futura:** no dia em que Celery entrar, o worker roda em outro
   processo, de novo no `public`, e o schema PRECISA viajar no payload da task.
   Registrado no docstring de `run_due_nightly_lead_import_jobs.py`.
3. **`cron_whatsapp_log_sweep` faz DELETE em massa** (logs de WhatsApp com mais
   de 7 dias) e hoje falha no `public` — ou seja, esta falhando de forma segura.
   Corrigi-lo o torna ativo e passa a apagar dados em todos os boxes. **Nao foi
   migrado de proposito:** ligar exclusao em massa e decisao do dono, nao efeito
   colateral de uma onda de infraestrutura.

### Arquivos alterados

1. novo: `shared_support/tenant_sweep.py`
2. `finance/management/commands/evaluate_finance_followups.py`
3. `jobs/management/commands/run_due_async_job_retries.py`
4. `operations/management/commands/run_due_nightly_lead_import_jobs.py`
5. `shared_support/management/commands/run_signal_mesh_retry_sweep.py`
6. testes: `tests/test_tenant_boundary.py` (classe nova B13, 6 testes),
   `boxcore/tests/test_operations_night_dispatch_command.py` (3 testes novos),
   `tests/test_jobs_management_command.py` e
   `tests/test_signal_mesh_management_commands.py` (adaptados: sao
   `SimpleTestCase` e a varredura consulta `Box`, entao usam `_fake_sweep`)

---

## Onda 2 — Higiene de fronteira e parar de mentir na tela

> **STATUS: IMPLEMENTADA em 2026-07-29.** Ver "Resultado real" no fim desta onda.

### 2a. Vazamento de cache cross-tenant

`access/shell_actions.py` usa `f'octobox:shell-counts:{today}'` — sem schema. `access` e TENANT; o payload inclui `pending_intakes`. Helper pronto e nao usado em `control/cache.py`.

```python
# antes
cache_key = f'octobox:shell-counts:{today}'
cached_counts = cache.get(cache_key)
cache.set(cache_key, counts, timeout)

# depois
from control.cache import tenant_cache_key, tcache_get, tcache_set
cache_key = tenant_cache_key(f'shell-counts:{today}')   # so para telemetria
cached_counts = tcache_get(f'shell-counts:{today}')
tcache_set(f'shell-counts:{today}', counts, timeout)
```

Atencao: a chave exibida na telemetria deve continuar batendo com a chave real — usar `tenant_cache_key` para o campo de telemetria.

Varrer tambem os demais call sites listados em `docs/audits/cache-call-sites.md` (o doc ja marca `access/shell_actions.py` como pendencia de Sprint 3 nunca executada).

Teste: em `tests/test_tenant_boundary.py`, gravar contagem no box A, ler no box B, assertir isolamento.

### 2b. Copy que mente

| Arquivo | Hoje | Vira |
|---|---|---|
| `onboarding/queries.py` (KPI) | `'label': 'Captação'` | `'Fila por canal'` |
| `onboarding/queries.py` (copy periodo `all`) | "histórico inteiro" | "fila aberta acumulada" |
| `student_identity/recommendations/invitation_operations_recommendations.py` | "Conversão final da janela" + alerta | rotulo `eventos finais / eventos iniciais (30d)`, N ao lado, alerta desativado ate coorte existir |

Regra permanente: nenhuma tela apresenta razao de eventos como taxa de conversao sem coorte e sem N visivel.

Pronto quando: box B nao le contador de A, e nenhum percentual sem coorte aparece rotulado como conversao.

### Resultado real (2026-07-29)

Implementado como planejado, com um ajuste:

1. **2a**: `access/shell_actions.py` migrado para `tcache_get`/`tcache_set`/`tenant_cache_key`.
   A chave de telemetria (`telemetry['cache_key']`) tambem passou a usar
   `tenant_cache_key(...)` para continuar batendo com a chave real usada no
   Redis (senao a telemetria mentiria sobre o que foi de fato lido/escrito).
2. **2b**: `onboarding/queries.py` — KPI renomeado nos dois lugares
   (`interactive_kpis` e `hero_stats`); copy do periodo `all` corrigido.
   `invitation_operations_recommendations.py` — alerta de "conversao baixa"
   removido (com comentario explicando a razao matematica: razao entre eventos
   independentes na mesma janela, sem coorte, pode passar de 100%); rotulo
   renomeado; `headline_value` passou a incluir o N bruto ao lado do percentual
   (`'83.3% (5/6)'`) sem precisar tocar no template (ele so interpola o valor).
3. **Descoberta:** `invitation_operations_recommendations.py` tem **zero
   cobertura de teste** no repositorio inteiro (nenhum teste unitario da classe,
   nenhum teste de view que renderize a pagina que a usa). A mudanca foi
   validada por leitura + `py_compile`, nao por teste automatizado. Isso e uma
   lacuna pre-existente, nao introduzida por esta onda — registrada aqui para
   nao ser esquecida caso essa tela vire alvo de trabalho futuro.
4. **Escopo NAO expandido:** `docs/audits/cache-call-sites.md` lista uma
   auditoria de Sprint 3 muito maior (`dashboard/`, `student_app/*_snapshots.py`,
   `shared_support/editing_locks.py`, `redis_snapshots.py`, etc.) com o mesmo
   risco. Deliberadamente fora do escopo desta onda — e outro esforco, maior,
   que nao pertence ao plano de ML de leads.

Testes rodados: `tests/test_performance.py`, `tests/test_shell_and_context.py`,
`boxcore/tests/test_onboarding.py` — 14 passed, 0 failed.

---

## Onda 3 — Desfazer a colinearidade e fechar a taxonomia

### 3a. Parar de derivar `source` do canal

`onboarding/intake_actions.py` hoje faz:

```python
created_entry.source = derive_operational_source(acquisition_channel=..., entry_kind=...)
...build_intake_attribution_payload(source=created_entry.source, ...)
```

Vira: `source` recebe a **origem real da captura**, nao o canal declarado.

```python
CAPTURE_SURFACE_TO_SOURCE = {
    'intake-center': IntakeSource.MANUAL,   # digitacao no balcao
    'lead-import': IntakeSource.IMPORT,     # ingestao em lote
    'whatsapp-inbound': IntakeSource.WHATSAPP,
}
created_entry.source = CAPTURE_SURFACE_TO_SOURCE.get(captured_via, IntakeSource.MANUAL)
```

`derive_operational_source` fica **isolada no caminho legado** (ou e removida). Se sobreviver: cobrir os 11 canais explicitamente e levantar `ValueError` em canal nao mapeado, em vez do fallback silencioso `WHATSAPP`/`MANUAL`.

Efeito colateral a tratar na mesma onda: `onboarding/facade.py` liga o botao de convite com `intake.source == IntakeSource.IMPORT`. Apos a correcao, lead de balcao que declarou Instagram deixa de ser `IMPORT`. Trocar o criterio por condicao explicita (ver decisao 4 do plano):

```python
'can_send_whatsapp_invite': bool(intake.phone) and intake.linked_student_id is None
```

### 3b. `captured_at`

`onboarding/intake_actions.py` passa a chamar `build_intake_attribution_payload(..., captured_at=timezone.now())`. Bumpar `ATTRIBUTION_SCHEMA_VERSION` para 2 e asserir `captured_at` no teste de `tests/test_onboarding_attribution.py`.

### 3c. Procedencia do canal

`extract_acquisition_channel` passa a devolver procedencia:

```python
@dataclass(frozen=True, slots=True)
class AcquisitionChannelReading:
    channel: str
    provenance: str   # 'confirmed' | 'declared' | 'legacy_inferred' | 'missing'

def extract_acquisition_channel_reading(*, raw_payload, fallback_source='') -> AcquisitionChannelReading:
    ...
```

Manter `extract_acquisition_channel()` como wrapper fino (`.channel`) para nao quebrar os 2 call sites atuais. `summarize_acquisition_channels` passa a contar `legacy_inferred` em balde proprio — inferencia deixa de ser contada como declaracao.

### 3d. Sentinelas na reconciliacao

`shared_support/acquisition.py` ganha:

```python
SENTINEL_ACQUISITION_CHANNELS = frozenset({'unidentified', 'legacy'})
```

`students/domain/acquisition_resolution.py` trata sentinela como **ausencia de evidencia dos dois lados**, antes dos branches de conflito. Hoje so o lado operacional tem esse tratamento — a assimetria gera conflito falso e descarta declaracao boa.

### 3e. Importador em lote grava o contrato

`operations/services/contact_importer.py` passa a chamar `build_intake_attribution_payload(..., captured_via='lead-import')` no `bulk_create`. E a trilha de maior volume de leads e hoje ela nao grava atribuicao nenhuma.

### 3f. Codigo morto e doc

- Remover o bloco `ml_features` do payload (derivavel a custo zero na leitura) — ou fechar o circuito da qualificacao (decisao 4 do plano). Nao deixar contrato documentado sem produtor.
- `docs/reference/lead-attribution-ml-foundation.md`: trocar `onboarding/views.py` por `onboarding/intake_actions.py` na lista "Onde isso mora hoje"; acrescentar `intake_dispatcher.py` e `shared_support/acquisition.py`.

### Testes

```python
def test_balcao_com_canal_evento_grava_origem_manual(self)          # A1 fechado
def test_captured_at_preenchido_no_quick_create(self)               # M3
def test_extract_channel_marca_legacy_inferred(self)                # M6/L1
def test_sentinela_nao_gera_conflito_falso(self)                    # M15
def test_importador_grava_bloco_attribution(self)                   # M11
def test_canal_nao_mapeado_levanta_em_vez_de_cair_no_fallback(self)
```

### Rollback

Onda sem migration — reverter por commit. `schema_version=2` convive com `1`; leitor aceita ambos.

---

## Onda 4 — Marcadores de desfecho

### Migration: `boxcore/migrations/0028_studentintake_outcome_markers.py`

Campos novos em `StudentIntake` (`onboarding/model_definitions.py`):

```python
first_contacted_at = models.DateTimeField(null=True, blank=True, db_index=True)
converted_at       = models.DateTimeField(null=True, blank=True, db_index=True)
rejected_at        = models.DateTimeField(null=True, blank=True, db_index=True)
conversion_kind    = models.CharField(max_length=24, blank=True)   # 'enrollment' | 'invite' | 'manual'
```

Todos nullable — migration sem default e sem lock longo. **Nao** criar tabela `IntakeStageTransition`: para o volume de uma box, quatro colunas denormalizadas entregam o valor com fracao do custo (decisao registrada no plano pai).

### Helper unico de transicao: `onboarding/stage_transitions.py`

```python
"""
ARQUIVO: ponto unico de transicao de estagio do intake.

POR QUE ELE EXISTE:
- as transicoes estavam espalhadas por 4 arquivos, todas gravando so `status`,
  sem datar desfecho e sem deixar trilha. Sem desfecho datado nao existe janela
  de maturacao, e sem ela toda taxa de conversao subestima o resultado.
"""

TERMINAL_TIMESTAMP_FIELD = {
    IntakeStatus.APPROVED: 'converted_at',
    IntakeStatus.REJECTED: 'rejected_at',
}


def transition_intake_status(
    *,
    intake,
    to_status,
    actor_id=None,
    surface='',
    conversion_kind='',
    now=None,
    extra_update_fields=(),
):
    """Muda o status do intake, data o desfecho e emite audit event.

    Unico caminho legitimo de mutacao de StudentIntake.status.
    """
    now = now or timezone.now()
    from_status = intake.status
    update_fields = ['status', 'updated_at', *extra_update_fields]

    intake.status = to_status
    stamp_field = TERMINAL_TIMESTAMP_FIELD.get(to_status)
    if stamp_field and getattr(intake, stamp_field) is None:
        setattr(intake, stamp_field, now)
        update_fields.append(stamp_field)
    if to_status == IntakeStatus.APPROVED and conversion_kind and not intake.conversion_kind:
        intake.conversion_kind = conversion_kind
        update_fields.append('conversion_kind')

    intake.save(update_fields=list(dict.fromkeys(update_fields)))

    log_audit_event(
        actor=..., action='intake_stage_changed', target=intake,
        description=f'{from_status} -> {to_status}',
        metadata={'from_status': from_status, 'to_status': to_status, 'surface': surface},
    )
    return intake
```

Call sites a migrar:

| Arquivo | Transicao |
|---|---|
| `onboarding/facade.py` | `NEW -> REVIEWING` e `-> REJECTED` |
| `onboarding/intake_invite_actions.py` | `-> MATCHED` (**nao** e conversao — ver decisao 1) |
| `students/infrastructure/django_intakes.py` | `-> APPROVED` com `conversion_kind='enrollment'` |

`first_contacted_at`: gravado no envio de convite (`intake_invite_actions.py`) e no primeiro toque de WhatsApp.

### Migration de backfill: `0029_backfill_intake_outcome_markers.py`

```python
# converted_at <- AuditEvent(action='student_intake_converted').created_at, por target_id
# first_contacted_at <- StudentInvitationDelivery.sent_at, quando houver
# rejected_at: NAO tem fonte — fica null para o historico. Registrar isso.
```

Backfill idempotente e `elidable=False`. Rodar via `RunPython` com `reverse_code=migrations.RunPython.noop`.

### Guarda de regressao

Teste que falha se alguem gravar `status` fora do helper:

```python
def test_nenhuma_mutacao_de_status_fora_do_helper(self):
    # grep no source: save(update_fields=[...'status'...]) so pode aparecer
    # em onboarding/stage_transitions.py
```

### Testes

```python
def test_rejeicao_grava_rejected_at(self)
def test_conversao_grava_converted_at_e_conversion_kind(self)
def test_convite_nao_grava_converted_at(self)            # A3 — o ponto central
def test_transicao_emite_audit_event(self)
def test_backfill_recupera_converted_at_do_audit_event(self)
```

### Rollback

Migration reversivel (campos nullable, drop limpo). Backfill tem `noop` reverso — dado backfillado permanece, o que e seguro.

---

## Onda 5 — Separar leitura operacional de leitura analitica

### O defeito

`onboarding/queries.py`: `base_queryset` filtra `status__in=[NEW, REVIEWING, MATCHED]` **e** `linked_student__isnull=True`; `metrics_queryset` reusa esse mesmo queryset. Todo lead convertido some do agregado.

### A correcao

```python
# fila operacional: mantem o recorte (e o que o time trabalha hoje)
queue_queryset = StudentIntake.objects.filter(
    status__in=[IntakeStatus.NEW, IntakeStatus.REVIEWING, IntakeStatus.MATCHED],
    linked_student__isnull=True,
)

# leitura analitica: universo de leads ENTRADOS na janela, sem recorte de desfecho
analytics_queryset = StudentIntake.objects.filter(created_at__date__gte=window_start)
```

O radar continua sendo fila aberta (renomeado na Onda 2). Ao lado nasce a leitura por canal com `captured_total` / `converted_total` / `rejected_total` / `open_total`.

### Invariantes a codificar

1. cards derivados de `ACQUISITION_CHANNEL_MODEL_CHOICES`, nao de lista literal
2. `sum(cards) + missing == total` (hoje quebra: 3 canais sem bucket)
3. filtro `resolved` **troca a base** em vez de intersectar (hoje retorna vazio sempre)

### Testes

```python
def test_soma_dos_cards_fecha_com_total(self)                       # M9
def test_filtro_resolvido_retorna_linhas(self)                      # M2
def test_leitura_analitica_inclui_lead_convertido(self)             # A6
def test_fila_operacional_continua_excluindo_convertido(self)
```

### Nao fazer

Nada de ML aqui. Nada de persistencia dentro do GET — o anti-padrao de `catalog/finance_snapshot/snapshot.py` (persiste `queue_preview[:8]` durante o render) e exatamente o que nao replicar.

---

## Onda 6 — Feature layer minimo por tenant

### Estrutura

Novo app TENANT `intelligence` (registrar em `TENANT_APPS` no `config/settings/base.py`), com `intelligence/leads/`:

```
intelligence/
  __init__.py
  apps.py
  model_definitions.py      # LeadChannelDailyFact
  models.py
  leads/
    __init__.py
    features.py             # calculo puro
    jobs.py                 # orquestracao idempotente
  management/commands/
    compute_lead_features.py
```

### Model: `LeadChannelDailyFact`

```python
class LeadChannelDailyFact(TimeStampedModel):
    window_start   = models.DateField(db_index=True)
    window_end     = models.DateField()
    channel        = models.CharField(max_length=32, db_index=True)
    provenance     = models.CharField(max_length=24)   # declared | legacy_inferred | missing
    confidence_bucket = models.CharField(max_length=16)  # high | medium | low | unknown

    captured_total  = models.PositiveIntegerField(default=0)
    converted_total = models.PositiveIntegerField(default=0)
    rejected_total  = models.PositiveIntegerField(default=0)
    open_total      = models.PositiveIntegerField(default=0)
    median_days_to_conversion = models.DecimalField(max_digits=6, decimal_places=1, null=True)

    rule_version = models.CharField(max_length=32)
    computed_at  = models.DateTimeField(db_index=True)
    input_window = models.CharField(max_length=24)

    class Meta:
        app_label = 'intelligence'
        constraints = [
            models.UniqueConstraint(
                fields=['window_start', 'channel', 'confidence_bucket', 'rule_version'],
                name='unique_lead_channel_fact_cell',
            )
        ]
        indexes = [models.Index(fields=['window_start', 'channel'])]
```

Regras de contrato (documento pai): toda saida carrega `rule_version`, `computed_at`, `input_window`, `is_recommendation=False`. Nada de score aqui.

### Honestidade estatistica obrigatoria

1. **Coorte com maturacao**: so entram no denominador leads criados ate `hoje - maturation_days` (sugerido 30). Lead de ontem nao e lead perdido — e censura a direita.
2. **Estratificar, nao ponderar**: taxa por canal reportada separadamente por bucket de confianca, com N de cada bucket. `source_confidence` nao e calibrado (M16) e nao pode virar peso.
3. **Piso de publicacao**: celula com menos de 20 conversoes nao publica percentual (suprime, nao zera). N sempre visivel.
4. **Deduplicacao** por `phone_lookup_index` — a unica chave de join valida (o telefone e `EncryptedCharField`, L3).

### Indices de suporte (so agora, quando existe query que os use)

```python
# StudentIntake.Meta.indexes
models.Index(fields=['created_at', 'status']),
models.Index(fields=['converted_at']),
```

Se a agregacao por canal ficar lenta: promover o canal resolvido para coluna materializada `StudentIntake.acquisition_channel` em vez de indexar JSON (M14).

### Comando

```bash
python manage.py compute_lead_features --window 90d        # todos os tenants, via Onda 1
python manage.py compute_lead_features --schema box_001    # debug de um box
```

### Testes

```python
def test_job_e_idempotente(self)                         # 2 execucoes = mesmo resultado
def test_lead_recente_nao_entra_no_denominador(self)     # maturacao
def test_taxa_suprimida_abaixo_do_piso(self)
def test_saida_carrega_contrato_de_ml(self)              # rule_version/computed_at/input_window
def test_job_nao_escreve_em_studentintake(self)          # ML nao escreve verdade primaria
```

---

## Onda 7 — Segmento do aluno (per-tenant)

`Student.status` e ciclo de vida (lead/active/paused/inactive), nao segmento. Esta onda cria o segmento como **regra transparente versionada**, dentro de `intelligence/students/`.

### Dimensoes (materia-prima ja existente)

| Dimensao | Fonte |
|---|---|
| plano / ciclo | `Enrollment.plan` -> `MembershipPlan.billing_cycle`, `sessions_per_week` |
| comportamento de pagamento | `finance/overdue_metrics.py` (pontual / atrasado recorrente) |
| faixa etaria | `Student.birth_date` |
| canal resolvido | `Student.resolved_acquisition_source` |

### Saida

```python
segment_key = 'trimestral|pontual|30-40'    # baixa cardinalidade, legivel, versionada
```

`rule_version='student_segment_v1'`. **Nao** gravar no model `Student` — e leitura derivada, vive no data product. **Nao** usar clustering opaco nesta fase.

### Fechamento do loop

Com Ondas 4 + 7, o join per-tenant fica computavel:

```
StudentIntake.converted_at -> Student -> segment (Onda 7) -> churn/retencao (trilha financeira)
```

A pergunta vira **"qual canal traz aluno que fica"**, nao "qual canal traz mais lead". Canal de aquisicao vira feature de risco de churn; risco por segmento vira qualidade de canal. As duas trilhas de ML viram um circuito so.

---

## Onda 8 — Hub de rede (SHARED app no public)

### Estrutura

Novo app `intelligence_network` em **`SHARED_APPS`** (precedente: `student_identity` e SHARED).

### Regra inegociavel

Dado cru de aluno ou lead **nunca** sai do schema do tenant. Sobe para o `public` apenas celula agregada, e so quando `N >= k` (sugerido k=10).

### Model (sem FK cross-schema — licao do Sprint 2)

```python
class NetworkChannelAggregate(TimeStampedModel):
    box_slug     = models.CharField(max_length=64, db_index=True)   # denormalizado, sem FK
    box_cohort   = models.CharField(max_length=32, db_index=True)   # porte/ticket/regiao
    segment_key  = models.CharField(max_length=64, db_index=True)
    channel      = models.CharField(max_length=32, db_index=True)
    window       = models.CharField(max_length=24)

    captured_total  = models.PositiveIntegerField()
    converted_total = models.PositiveIntegerField()
    retained_90d_total = models.PositiveIntegerField(default=0)

    k_floor_applied = models.PositiveSmallIntegerField()
    contributed_at  = models.DateTimeField(db_index=True)

    class Meta:
        app_label = 'intelligence_network'
```

### Job de contribuicao

Usa o sweep da Onda 1: varre tenants, le os data products das Ondas 6-7, aplica piso `k`, faz upsert no hub.

### Cohort de box

Obrigatorio desde o inicio. Mediar box premium de capital com box de bairro produz prior enganoso. Benchmark compara com o **cohort**, nunca com a rede inteira.

### Primeira superficie

Benchmark anonimo no radar: "seu Instagram converte 12% · mediana do seu porte: 18% (N=7 boxes)". Celula abaixo do piso e **suprimida**, nao zerada.

### Testes

```python
def test_celula_abaixo_do_piso_k_nao_sobe(self)
def test_nenhum_dado_individual_no_hub(self)          # varre campos por PII
def test_benchmark_nao_permite_inferir_box_individual(self)
def test_cohort_separa_boxes_heterogeneas(self)
```

### Nao fazer

Nenhum prior aplicado nesta onda — so leitura comparativa.

---

## Onda 9 — Priors e correcao local (shrinkage)

### Formula

```
leitura_ajustada = (n_local * taxa_local + m * prior_da_rede) / (n_local + m)
```

`m` = peso do prior (sugerido 10), documentado e versionado. Com `n_local=0` a leitura **e** o prior. Com `n_local` grande o prior vira ruido de fundo. Transicao continua, auditavel, sem caixa-preta.

### Implementacao

```python
def apply_shrinkage(*, local_rate, local_n, prior_rate, prior_weight=10):
    if local_n <= 0:
        return prior_rate
    return round(
        (local_n * local_rate + prior_weight * prior_rate) / (local_n + prior_weight), 1
    )
```

### Superficie

Leitura ajustada exibida **ao lado** da crua, com `is_network_prior=True` quando o prior domina. A box sempre sabe quando esta lendo a rede e quando esta lendo a si mesma.

### Cold start

Box nova nasce com prior do cohort mais proximo. Radar e fila uteis no dia 1, rotulados como herdados, convergindo para o dado local conforme `n_local` cresce. **Este e o "automaticamente ir corrigindo para novos boxes".**

### Aplicacao retroativa no churn

`build_recommendation_historical_score_map` (`catalog/finance_snapshot/ai/scoring.py`) hoje devolve `0.0` para acao sem historico local. Passa a partir do prior de rede. Isso **conserta o defeito ja conhecido**: o piso `min_realized_count=5` em `catalog/finance_snapshot/ai/learning.py` e gambiarra de amostra pequena — com prior, celula pequena e encolhida na direcao do padrao coletivo em vez de descartada ou superconfiante.

### Testes

```python
def test_prior_domina_com_n_local_zero(self)
def test_local_domina_com_n_local_grande(self)
def test_convergencia_e_monotonica(self)
def test_leitura_marca_is_network_prior(self)
def test_prior_expirado_nao_e_usado(self)      # input_window rolante
```

---

## Ordem de execucao e dependencias

```
Onda 1 (job por tenant) ─┬─> Onda 6 (feature layer) ─> Onda 7 (segmento) ─> Onda 8 (hub) ─> Onda 9 (priors)
Onda 2 (higiene)  ───────┘                    ▲
Onda 3 (colinearidade) ──> Onda 4 (desfecho) ─┴─> Onda 5 (leitura analitica)
```

1. Ondas 1 e 2 sao paralelas e independentes
2. Onda 4 depende da 3 (canal correto antes de datar desfecho)
3. Onda 6 depende de 1, 4 e 5
4. Trilho B (7-9) so abre com Trilho A fechado e gate de numero de boxes atendido

## Pendencias que dependem de decisao do dono

Bloqueiam a onda indicada ate serem respondidas (recomendacoes no plano pai):

| Decisao | Bloqueia |
|---|---|
| Definicao oficial de "lead convertido" | Onda 4 (semantica de `converted_at`) |
| Convite restrito a `IMPORT`? | Onda 3 (efeito colateral) |
| Lead some da fila ao ser convidado? | Onda 5 |
| "Nao identificado" e resposta valida? | Onda 3 (sentinelas) |
| Duplicata: bloquear ou fundir? | Onda 6 (denominador) |
| Opt-in ou opt-out da rede | Onda 8 |
| Benchmark aberto ou por plano | Onda 8 |
