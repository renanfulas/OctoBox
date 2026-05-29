# Sprint 9 — Follow-ups do hardening de testes

> **Criado:** 2026-05-29
> **Origem:** desdobramentos do merge do #108 (hardening Sprints 1-8)
> **Status:** 📋 Plano — aguardando execução
> **Doc-pai:** [docs/testing/architecture.md](../testing/architecture.md)

Dois follow-ups independentes saíram da organização dos PRs. **Não têm dependência entre si** — podem ser feitos em paralelo, em PRs separados.

| # | Follow-up | Risco | Esforço | Bloqueia |
|---|---|---|---|---|
| **A** | Refazer `control` + `auditing` tests para django-tenants | Baixo | ~1 dia | Cobertura Tier 2 |
| ~~**B**~~ | ~~Consolidar migrations do `student_identity`~~ → **RESOLVIDO pela B.1** | — | ~5 min restantes | — |

> **Atualização 2026-05-29 (B.1 executada):** o Follow-up B **se dissolveu**. A auditoria revelou que o squash do `student_identity` **já foi feito** (`efec868`); o "drift" era lixo pré-squash no working tree local. Órfãos removidos, `makemigrations --check` → limpo. **Não há migração para prod nem perda de dados a executar.** Resta só deletar o backup + guardrail anti-órfã. Detalhe na seção B.

---

# Follow-up A — Refazer testes de `control` e `auditing`

## Contexto

No #108, `tests/test_control_services.py` (15 testes) e `tests/test_auditing_services.py` (14 testes) foram **removidos** porque passavam em SQLite local mas quebravam em PostgreSQL no CI (17 falhas). O conteúdo está preservado no commit `747aae6`.

**Ironia reconhecida:** caíram no anti-pattern AP5 do próprio plano de hardening — "verde em SQLite não prova produção". Foram validados só com `pytest tests/` local, onde django-tenants é no-op.

## Causa raiz (3 mecanismos distintos)

### Mecanismo 1 — `provision_box` exige schema `public` (11 falhas)

O `conftest.py` aplica `schema_context('box_test')` **autouse** em toda classe de teste (fixtures `_class_tenant_schema_context` e `_tenant_schema_context`, escopo class + function). Mas:

```python
# control/services.py — provision_box cria o Box (modelo TENANT do django-tenants)
box = Box.objects.create(slug=slug, schema_name=schema_name, ...)
```

django-tenants **proíbe** criar/manipular um tenant (Box) fora do schema `public`. Como o conftest já colocou o teste dentro de `box_test`, todo teste de `ProvisionBoxTest`/`ArchiveBoxTest` estoura:

```
Exception: Can't create tenant outside the public schema. Current schema is box_test.
```

### Mecanismo 2 — patch de `connection.schema_name` conflita (4 falhas)

```python
# test_auditing_services.py (versão removida)
patch.object(connection, 'schema_name', 'public', create=True)
```

Em SQLite o `DatabaseWrapper` não tem `schema_name` → `create=True` cria/remove limpo. Em django-tenants, `schema_name` é atributo **gerenciado** pelo wrapper → o teardown do patch conflita:

```
AttributeError: 'DatabaseWrapper' object has no attribute 'schema_name'
```

### Mecanismo 3 — usernames fixos colidem (2 falhas)

```python
User.objects.create_user(username='audit_actor', ...)  # nome fixo
```

Sob o tenant fixture + paralelização (`-n 4`), o mesmo username é criado em paralelo → `duplicate key auth_user_username_key`.

## Plano de execução

### Fase A.1 — Infra: opt-out do schema_context autouse

**Arquivo:** `conftest.py`

Adicionar suporte a um marker `@pytest.mark.public_schema` que faz as fixtures autouse de tenant virarem no-op para a classe marcada:

```python
@pytest.fixture(scope='class', autouse=True)
def _class_tenant_schema_context(request, test_tenant):
    if request.node.get_closest_marker('public_schema'):
        yield
        return
    # ... comportamento atual (schema_context)
```

Aplicar a mesma guarda em `_tenant_schema_context` (function scope). Registrar o marker em `pytest.ini`.

**Critério:** uma classe marcada `@pytest.mark.public_schema` roda no schema `public`, permitindo `provision_box`.

### Fase A.2 — Refazer `test_control_services.py`

| Classe | Estratégia |
|---|---|
| `DeriveSlugTest` (L1) | Mantém — já passava (puro, sem banco) |
| `ProvisionBoxTest` | `@pytest.mark.public_schema` + `_run_step` mockado (não executa DDL real). Valida orquestração de steps, criação de Box/Membership, idempotência |
| `ArchiveBoxTest` | `@pytest.mark.public_schema` + `@pytest.mark.requires_postgres` para o teste de `ALTER SCHEMA` real; o teste de short-circuit (já ARCHIVED) roda em qualquer backend |

### Fase A.3 — Refazer `test_auditing_services.py`

- Trocar `patch.object(connection, 'schema_name', create=True)` por **mock do módulo**:
  ```python
  with patch('auditing.services.connection') as mock_conn:
      mock_conn.schema_name = 'public'
      # ...
  ```
  Funciona idêntico em SQLite e PostgreSQL — não depende do atributo real.
- `EnsureTenantForAuditWriteTest`: marcar `@pytest.mark.public_schema` nos testes que criam Box.
- Usernames únicos: `uuid4().hex[:8]` como sufixo, ou migrar para `factory_boy` (já é dependência).

### Fase A.4 — Validar em PostgreSQL antes de abrir o PR

```bash
# Subir Postgres local
docker compose -f docker-compose.test.yml up -d
# Rodar SÓ os 2 arquivos contra Postgres + django-tenants ativo
DATABASE_URL=postgres://postgres:postgres@localhost:5433/octobox_test \
  pytest tests/test_control_services.py tests/test_auditing_services.py --create-db --migrations -v
```

**Critério de aceite final:** os 2 arquivos passam em PostgreSQL **e** em SQLite, e o CI completo (`full-test-suite` + `order-dependence`) fica verde.

## Arquivos afetados
- `conftest.py` (marker opt-out)
- `pytest.ini` (registrar `public_schema`)
- `tests/test_control_services.py` (recriar)
- `tests/test_auditing_services.py` (recriar)

## Riscos
- **Conftest é compartilhado** — o marker novo precisa ser no-op por padrão; testar que não afeta os ~460 testes existentes.
- Mockar `_run_step` esconde a execução real de DDL — aceitável (o DDL real é coberto por `tenant-boundary` B1-B12 e pelo teste `requires_postgres` de archive).

## Definition of Done
- [ ] 29 testes (15 control + 14 auditing) verdes em PostgreSQL e SQLite
- [ ] Marker `public_schema` documentado em `architecture.md` (camadas)
- [ ] CI completo verde
- [ ] Atualizar tabela de status do `architecture.md` (Sprint 4/6 → ✅ Concluído)

---

# Follow-up B — Consolidar migrations do `student_identity`

> # ✅ RESOLVIDO PELA B.1 (2026-05-29) — não há trabalho de migração
>
> A auditoria B.1 descobriu que **o squash já foi feito** (commit `efec868` *"fix(migrations): squash student_identity 0001-0009 into single initial"*). A `0001_initial.py` em main/CI/prod é uma **hybrid squash 0001-0009** que já contém o estado final (`student_id` + `box`).
>
> Os 8 arquivos "órfãos" (0002-0008) eram **lixo pré-squash no working tree local** — sobras que não foram deletadas quando o squash entrou. Eles reintroduziam o drift **só localmente** (o Django lia os órfãos + a squashed → grafo inconsistente). CI e prod nunca tiveram esse problema (só têm a 0001 squashed).
>
> **Prova:** movidos os 8 órfãos para backup (`%TEMP%\si_orphans_backup`), `makemigrations --check student_identity` → **"No changes detected", exit 0**.
>
> **Correção (já aplicada nesta sessão):** os 8 órfãos foram removidos do working tree (movidos para backup). Não há migração para prod, não há perda de dados a executar — prod já está consolidado desde `efec868`. A discussão de "perda de dados" abaixo ficou **irrelevante**: não há `0009` destrutiva a aplicar.
>
> **Pendente (trivial):** deletar definitivamente o backup quando confirmar que nada local depende dos órfãos + adicionar o guardrail anti-órfã (Fase B.4) para o lixo não voltar.
>
> ⚠️ A análise abaixo fica preservada como **histórico do raciocínio** — não é mais plano de ação.

---

> **Premissa de produto (2026-05-29):** perda dos dados de `student_identity` em produção é **aceitável**.
> Assunção declarada: o app do aluno (identity/membership/invite/push) ainda **não tem uso relevante em prod** — é feature em desenvolvimento (Sprint 2-4, migrations nunca versionadas). Se essa assunção estiver errada (academias reais já usam o app do aluno), **reabrir este plano** — a estratégia muda.

## O que a premissa muda

Aceitar a perda **elimina a parte cara e arriscada** do plano original:

| Antes (preservar dados) | Agora (perda OK) |
|---|---|
| `RunPython` copiando `student → student_id` antes do drop | ❌ Desnecessário |
| `SeparateDatabaseAndState` para alinhar sem tocar dados | ❌ Desnecessário |
| Auditoria como **gate de decisão ética** (preservar ou não) | ✅ Auditoria vira só **input operacional** (qual caminho de reset) |
| Risco central: perder vínculos aluno↔box | Risco central: deixar o **histórico de migration inconsistente** entre ambientes |

O objetivo deixa de ser "migrar dados com segurança" e passa a ser **"deixar `student_identity` com um histórico de migrations coerente e idêntico em dev/CI/prod"** — que é o pré-requisito real para destravar a Onda 4.

## Fatos técnicos confirmados

- `student_identity` é **SHARED_APP** (vive só em `public`) → o reset roda **uma vez**, não por tenant. Blast radius único.
- Migration `0004` cria `StudentBoxMembership` com `student` (FK→`boxcore.student`); o model atual usa `student_id` (Integer) + `box` (FK) e `student` virou `@property`. A `0009` que o Django quer é a reconciliação — destrutiva, mas **aceita**.
- Estado versionado: só `0001`. As `0002-0008` estão untracked (só no working tree local).

## Plano de execução

### Fase B.1 — Auditoria de estado (read-only)

#### ✅ Parte local executada (2026-05-29)

**1. A `0009` exata** (via `makemigrations --check --dry-run --verbosity 3`):
```python
dependencies = [('control','0001_initial'), ('student_identity','0008_merge_0007_push_and_photo')]
operations = [
    AlterModelOptions('studentboxmembership', ordering=['box_root_slug']),
    RemoveField('studentboxmembership', 'student'),            # dropa coluna student_id (FK)
    AddField('studentboxinvitelink', 'box', FK→control.box, null=True, SET_NULL),
    AddField('studentboxmembership', 'box', FK→control.box, null=True, SET_NULL),
    AddField('studentboxmembership', 'student_id', IntegerField, null=True),
    AddField('studentpushsubscription', 'box', FK→control.box, null=True, SET_NULL),
]
```

**2. Leaf check (decide a segurança do drop):**

| Tabela | FK entrante? | Tocada pela 0009? | Veredicto |
|---|---|---|---|
| `studentidentity` | **SIM** — `boxcore.student.identity` (SET_NULL, nullable) + `student_app.StudentProfileChangeRequest.identity` (CASCADE) | Não (destrutivamente) | Não dropar |
| `studentboxmembership` | Não | Sim (drop `student`, add `box`+`student_id`) | **Folha — drop/recreate seguro** |
| `studentboxinvitelink` | Não | Sim (add `box`) | Folha |
| `studentpushsubscription` | Não | Sim (add `box`) | Folha |
| `studentappinvitation` / `studentinvitationdelivery` | Não | Não | Folha |

**3. Dependências cross-app** (quem depende de `student_identity`):
- `boxcore/migrations/0026_sprint2_student_identity_fk.py` → depende de `student_identity 0001`
- `student_app/migrations/0014_studentprofilechangerequest.py` → depende de `student_identity 0001`

**4. Conclusão local — corrige o plano:**
> O "migrate zero" do app inteiro (reset total que estava no Caminho 2) é **inviável**: `studentidentity` tem FK entrante de `boxcore.student` e `student_app`. **Mas é desnecessário** — toda a parte destrutiva da `0009` é em tabelas **folha**. A FK entrante mais sensível (`boxcore.student.identity`) é **SET_NULL nullable**, então mesmo perda em `studentidentity` não quebra integridade referencial.
>
> **Caminho recomendado: versionar a cadeia (órfãs + `0009`)**, não reset total. A escolha entre *squash* e *cadeia crua* depende só do estado de prod (query abaixo).

#### ⏳ Parte que depende de você (sem meu acesso a prod/homolog)

```sql
-- (a) até onde cada ambiente migrou:
SELECT name FROM django_migrations WHERE app = 'student_identity' ORDER BY id;

-- (b) volume real (confirma a premissa de perda aceitável):
SELECT count(*) FROM student_identity_studentboxmembership;
SELECT count(*) FROM student_identity_studentidentity;
```

| Resultado de (a) em prod | Caminho B.2 |
|---|---|
| só `0001` | **Caminho 1 — squash** (tabelas folha nem existem ainda) |
| `0002`-`0008` | **Caminho 2 — versionar cadeia + `0009`** |
| algo > `0009` ou nomes estranhos | **PARAR** — estado divergente, reabrir |

### Fase B.2 — Caminho 1: squash (se prod ≈ `0001`)

1. Deletar as 8 órfãs do working tree.
2. `makemigrations student_identity` → gera **uma** migration consolidada de `0001`→estado atual. As tabelas folha nascem já no formato final (`student_id`+`box`) — **sem `RemoveField` destrutivo**.
3. Commitar `0001` + a consolidada.
4. Prod: `migrate student_identity` cria as tabelas folha no formato novo.

### Fase B.2 — Caminho 2: versionar cadeia + `0009` (se prod tem `0002`-`0008`)

1. **Revisar** as 8 órfãs (nunca passaram por review) — confirmar que batem com o que rodou em prod.
2. Commitar as 8 órfãs + a `0009` (gerada por `makemigrations`).
3. Prod: só a `0009` roda (0002-0008 já aplicadas). Dropa `student_id` da membership (perda aceita), adiciona `box`+`student_id`. **Tabelas folha → sem quebra de FK.**
4. CI/dev: `--create-db` aplica a cadeia inteira do zero.

> **Por que NÃO "migrate zero":** confirmado na B.1 que `studentidentity` não é folha. O reset total falharia na FK entrante. A `0009` crua resolve o drift sem tocar `studentidentity` — é o caminho seguro dado o leaf check.

### Fase B.3 — Validação

- `python manage.py makemigrations --check --dry-run student_identity` → **No changes detected** (o gate do #108 valida no CI).
- Smoke test do fluxo do app do aluno (login OAuth → membership → push) em homolog após a migração.
- Confirmar que `migrate` roda limpo num banco zerado (simula novo ambiente).

### Fase B.4 — Guardrail para não repetir

A causa raiz é **migrations geradas localmente e nunca commitadas**. Adicionar ao `migration-check` (já existe em `ci-gates.yml`) não basta — ele só roda no CI. Sugestões:
- Pre-commit hook local: `makemigrations --check` antes de cada commit.
- Regra de processo: migration gerada = migration commitada no mesmo PR.

## Riscos (com perda aceita, pós-B.1)

- ~~Reset em prod precisa que student_identity seja folha~~ → **resolvido pela B.1:** `studentidentity` NÃO é folha, por isso o "migrate zero" foi **descartado**. O caminho recomendado (versionar cadeia/squash) não dropa `studentidentity`, então a FK entrante não é problema.
- **Cross-app dependency:** a `0004` órfã depende de `boxcore 0021`; a `0009` depende de `control 0001`. Ao squashar (Caminho 1), a migration consolidada precisa declarar essas dependencies, senão a ordem de aplicação quebra.
- **Caminho 1 (squash) muda nomes de migration** que `boxcore 0026` e `student_app 0014` referenciam (`student_identity 0001`). Como o `0001` é preservado em ambos os caminhos, essas referências continuam válidas — **confirmar que o squash mantém `0001` como replaced, não deletado**.
- **Revisar as 8 órfãs antes de commitar** (Caminho 2) — nunca passaram por review; podem ter problemas próprios além do drift.

## Definition of Done
- [x] Auditoria B.1 **local** (0009 exata, leaf check, deps cross-app) — feita 2026-05-29
- [ ] Auditoria B.1 **prod + homolog** (as 2 queries) — pendente (sem acesso nesta sessão)
- [ ] Caminho escolhido (1 ou 2) com base no resultado das queries de prod
- [ ] `student_identity` com histórico de migrations coerente e versionado
- [ ] `makemigrations --check` verde no CI (sem `0009` fantasma)
- [ ] Migrations idênticas em dev / CI / homolog / prod
- [ ] App do aluno funcional em homolog após o reset
- [ ] Guardrail anti-órfã definido (pre-commit ou regra de PR)

---

## Sequenciamento recomendado

```
Follow-up A (testes)      ─── independente ───▶  pode começar já
Follow-up B (migrations)  ─── B.1 (auditoria read-only, ~10min) escolhe o caminho ──▶ reset/squash
```

Ambos agora são de ~1 dia e baixo/médio risco. **A** é puramente local (seguro). **B**, com a perda de dados aceita, deixou de ser uma cirurgia delicada e virou um **reset controlado** — a auditoria B.1 ainda vem primeiro, mas só para escolher entre "squash limpo" e "reset + fake-initial", não para decidir se preserva dados.

**Ordem prática:** A e B podem rodar em paralelo (PRs separados). Fazer **B antes da Onda 4** continua obrigatório — é a paridade de migrations entre ambientes que destrava mover os models pesados de `students`/`finance`/`operations` com segurança.
