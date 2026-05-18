# OctoBox — Plano de Qualidade de Testes (prompt para executor agent)

> **Origem:** plano gerado pelo skill `prompt-engineer` em 2026-05-18.
> **Status:** ativo. Cada fase abaixo deve virar 1 PR independente.
> **Pre-requisitos atendidos:** conftest.py com test_tenant fixture +
> auto-Membership, requirements_test.txt pinado, .coveragerc com branch
> coverage, 3 workflows CI usando `-r requirements_test.txt`.

---

## ROLE
Voce e um engenheiro de QA/test infrastructure que vai executar um plano
fasado de melhoria da suite de testes do OctoBox. Voce conhece pytest,
pytest-django, django-tenants, coverage.py, factory-boy, pytest-playwright.

## MISSAO (um unico outcome)
Ate o final do plano: CI verde rodando a suite COMPLETA + cobertura
medida e exposta em PR + 1 cenario E2E funcional + 1 matriz de roles
parametrizada + factories para 3 modelos centrais + suite limpa de
testes order-dependentes.

Cada fase abaixo entrega valor incremental e e commit-by-commit safe.
Voce DEVE parar e reportar antes de iniciar uma fase se o criterio de
pronto da fase anterior nao foi atingido.

## CONTEXTO QUE JA EXISTE (nao recriar)
- conftest.py na raiz com:
  * Fixture session test_tenant criando Box(slug='test', schema='box_test')
    e rodando migrate_schemas para popular TENANT_APPS no schema do tenant.
  * Fixture autouse _tenant_schema_context que envelopa cada teste em
    schema_context('box_test').
  * Fixture autouse _auto_membership_for_test_users (post_save signal em
    auth.User criando Membership automatica). Necessario porque
    TenantBySessionMiddleware retorna 403 sem Box resolvivel.
- requirements_test.txt pinado:
    pytest==9.0.3, pytest-django==4.12.0, pytest-benchmark==5.2.3,
    pytest-cov==7.1.0, coverage==7.14.0, pytest-mock==3.15.1,
    freezegun==1.5.5, responses==0.26.0, factory-boy==3.3.3,
    pytest-randomly==4.1.0
  pytest-playwright AINDA NAO esta instalado — sera adicionado na Fase 8.
- .coveragerc com branch coverage, omit cuidadoso (migrations, settings,
  seeders, scripts, tests), exclude_lines para padroes nao testaveis.
  fail_under=0 (sera elevado fasadamente).
- 3 workflows CI (performance_check.yml, student-onboarding-corridors,
  student-onboarding-real-smoke) instalam `-r requirements_test.txt` e
  rodam pytest com `--create-db --migrations`.
- Schema-per-tenant ativo: SHARED_APPS em 'public', TENANT_APPS em
  'box_xxx'. Conftest usa um unico tenant 'box_test' para a suite toda.

## CONSTRAINTS NAO-NEGOCIAVEIS
- Cada fase = 1 PR independente. NAO empilhar fases em um unico PR.
- CI tempo total <= 8 minutos no caminho de PR (full suite + coverage).
  Se ultrapassar: rodar full suite + E2E so em push para main; PRs rodam
  subset rapido + lint. Decisao explicita por benchmark, nao adivinhacao.
- Nao quebrar nada que ja roda verde. Se uma fase vai impactar testes
  existentes, rode `python -m pytest` (suite inteira) ANTES e DEPOIS,
  comparando contagem de pass/fail.
- Pilot controlado: pode dropar/recriar test DB livremente.
- Time pequeno: prefira ferramentas built-in (pytest-django, coverage)
  antes de novas dependencias. Adicione SO o estritamente necessario.

## FASES (execute em ordem; pare em qualquer falha de criterio)

### FASE 0 — Baseline (S, 30-60 min)

**O que faz:** Roda a suite COMPLETA com pytest-randomly + coverage e
documenta o estado inicial em `docs/testing/baseline-2026-05-18.md`.
Nenhuma mudanca de codigo nesta fase — so medicao.

**Comandos:**
```bash
# Captura contagem total de testes
python -m pytest --collect-only -q | tail -5 > /tmp/baseline-count.txt

# Roda suite completa com cobertura e ordem aleatoria
python -m pytest --create-db --migrations \
  --cov --cov-report=term --cov-report=html --cov-report=xml \
  -q --tb=line 2>&1 | tee /tmp/baseline-run.txt
```

**Criterio de pronto:**
1. Arquivo `docs/testing/baseline-2026-05-18.md` existe com:
   - Total de testes coletados (deve ser ~867)
   - Cobertura % linha + % branch
   - Lista de testes que falharam OU pularam com motivo
   - Tempo total de execucao
   - Top 10 modulos com cobertura mais baixa (oportunidade)
2. `htmlcov/index.html` gerado e commitado em branch (so para a fase 0
   referencia visual; depois movemos para artifact).
3. Nenhuma mudanca de codigo de produto.

**Trade-off / decisao:** Se a suite falhar em > 5% dos testes na ordem
aleatoria mas passar em ordem fixa, **PARE** e reporte. Significa que
ha testes order-dependentes que mascaram problemas. Resolver na Fase 3
antes de continuar.

**Output:** commit "test(infra): baseline da suite — XYZ testes, N% linha"
+ relatorio em docs/.

---

### FASE 1 — CI roda suite completa (M, 1-2h)

**Depende de:** Fase 0 (saber tempo e contagem total).

**O que faz:** Adicionar workflow `.github/workflows/full-test-suite.yml`
que roda `pytest --create-db --migrations --cov --cov-report=xml -q`
em todo PR e push para main. Suite completa, NAO so test_performance.

**Decisao critica (com base no tempo medido na Fase 0):**
- Se Fase 0 mostrar `< 5 min`: workflow roda em TODOS os PRs.
- Se `5-10 min`: rodar em PRs mas com pytest-xdist (`-n auto`) para
  paralelizar. Se isso baixar pra < 5 min, ok.
- Se `> 10 min` mesmo com xdist: rodar apenas em push para main;
  PRs rodam subset (smoke + corridors). Documente a decisao no workflow.

**Criterio de pronto:**
1. Workflow novo existe e roda em CI (visivel em Actions tab).
2. Ele falha quando algum teste falha (verifique forcando uma falha
   temporaria e revertendo).
3. Coverage XML uploaded como artifact (use `actions/upload-artifact@v7`).
4. Tempo medido em pelo menos 2 execucoes; documentado em commit.
5. PR existente (qualquer aberto) mostra o status check rodando verde.

**Trade-off:** NAO adicionar Codecov/PR comment ainda — isso e Fase 2.
Aqui so garantir que a suite roda.

**Output:** commit "ci: adicionar workflow rodando suite completa".

---

### FASE 2 — Cobertura visivel em PRs (M, 1-2h)

**Depende de:** Fase 1 (workflow ja roda + uploaded XML).

**O que faz:** Tornar a cobertura visivel diretamente no PR (nao so como
artifact baixavel). Decidir entre 3 opcoes:

| Opcao | Custo | Beneficio |
|---|---|---|
| Codecov (servico externo) | Token + config; mais features (graficos, diff coverage) | PR comment automatico, sparkline historica |
| coverage-badge + commit em README | Zero externo; baixa friccao | So badge global, sem diff coverage |
| Action `py-cov-action/python-coverage-comment-action` | Zero externo; comenta no PR | Diff coverage no PR sem servico terceiro |

**Recomendacao: opcao 3** (zero externo, diff coverage, suficiente para
o piloto). Codecov so se quiser graficos historicos publicos.

**Criterio de pronto:**
1. Abrindo um PR novo (pode ser um draft), o bot comenta:
   - Cobertura total atual
   - Diff vs. base branch
   - Linhas modificadas que nao estao cobertas
2. `.coveragerc` ajustado: `fail_under = <baseline da Fase 0 menos 2%>`.
   Ex.: se baseline e 58%, `fail_under = 56` (margem para flutuacao).
3. Sub-fail: se um PR baixar cobertura abaixo do `fail_under`, CI falha.

**Trade-off:** Subir `fail_under` agressivamente quebra PRs legitimos
de refactoring. Manter folga de 2% e revisitar a cada release.

**Output:** commit "ci: comentario automatico de cobertura em PRs".

---

### FASE 3 — Limpeza de testes order-dependentes (S-M, 30min-3h)

**Depende de:** Fase 0 (pytest-randomly ja rodou; lista de testes que
falharam SO em ordem aleatoria, ou marcaram XFAIL/SKIP).

**O que faz:** Para cada teste que passa em ordem fixa mas falha em
ordem aleatoria, identificar a dependencia escondida (geralmente cache
nao limpo, signal handler nao desconectado, classe-level state) e
corrigir.

**Procedimento:**
1. `python -m pytest -p no:randomly` — confirma que passa em ordem fixa.
2. `python -m pytest --randomly-seed=1` (e 2, 3, ...) — reproduzir
   falha com seed.
3. Use `pytest-bisect` ou divide-and-conquer: `pytest test_a test_b`
   minimal pair que falha.
4. Fix mais comum: `setUp()` esquecendo de limpar cache, signal
   handlers persistentes entre testes (use `addCleanup`), state global
   de modulo (ex.: variavel `_already_registered`).

**Criterio de pronto:**
- `python -m pytest --randomly-seed=42` passa.
- `python -m pytest --randomly-seed=137` passa.
- `python -m pytest --randomly-seed=9999` passa.
- Documentar em commit qual seed reproduzia, qual era a dependencia,
  como foi corrigido.

**Trade-off:** Se ha > 20 testes order-dependentes, faca em 2-3 commits
agrupados por causa raiz (todos os signal handlers, todos os caches,
etc.). NAO um commit por teste.

**Output:** commit(s) "test: corrigir testes order-dependentes — <causa>".

---

### FASE 4 — Factories para 3 modelos centrais (M, 2-4h)

**Depende de:** Fase 1 (suite completa rodando).

**O que faz:** Criar `tests/factories.py` com factory_boy para os 3
modelos mais usados em testes. Migrar 3-5 arquivos de teste como
proof-of-concept; o resto migra organicamente.

**Identificar os 3 modelos:**
```bash
grep -rh "\.objects\.create\b" --include="*.py" tests/ */tests.py */tests/*.py \
  | sed -E 's/.*([A-Z][a-zA-Z]+)\.objects\.create.*/\1/' \
  | sort | uniq -c | sort -rn | head -10
```
Os top-3 sao os candidatos. Em OctoBox a aposta segura: Student,
StudentIdentity, User (auth).

**Estrutura:**
```python
# tests/factories.py
import factory
from django.contrib.auth import get_user_model
from students.models import Student
from student_identity.models import StudentIdentity, StudentIdentityProvider

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
    username = factory.Sequence(lambda n: f'user-{n}')
    email = factory.LazyAttribute(lambda u: f'{u.username}@example.com')

class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student
    full_name = factory.Faker('name', locale='pt_BR')
    phone = factory.Sequence(lambda n: f'5511{n:09d}')
    email = factory.LazyAttribute(lambda s: f'{s.full_name.split()[0].lower()}@example.com')

class StudentIdentityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentIdentity
    student = factory.SubFactory(StudentFactory)
    # student_id vem do SubFactory.id apos save
    student_id = factory.LazyAttribute(lambda i: i.student.id)
    student_name = factory.LazyAttribute(lambda i: i.student.full_name)
    box_root_slug = 'box_test'
    provider = StudentIdentityProvider.GOOGLE
    provider_subject = factory.Sequence(lambda n: f'google-subj-{n}')
    email = factory.LazyAttribute(lambda i: i.student.email)
```

**Criterio de pronto:**
1. `tests/factories.py` existe com 3 factories funcionais.
2. 3-5 arquivos de teste existentes migrados para usar factories
   (escolha os mais simples primeiro como prova). Commit separa
   "test: migrar X testes para factories — sem mudanca semantica"
   E verifica que a contagem de pass/fail e identica antes/depois.
3. Documentar em `tests/factories.py` o padrao para futuros modelos.

**Trade-off:** NAO migre todos os 867 testes nesta fase. Migracao
organica: PRs futuros que tocarem testes existentes migram opcionalmente.

**Output:** commit "test: adicionar factory_boy + factories para 3 modelos centrais".

---

### FASE 5 — Parametrizar 1 matriz de roles (S, 1-2h)

**Depende de:** Fase 0 (suite passa) e Fase 1 (CI roda full).

**O que faz:** Encontrar UMA classe de teste com 4+ metodos que so
diferem por (role, url, expected_status) e refatorar com
`@pytest.mark.parametrize`. Prova de conceito + template para outras.

**Candidatos a procurar:**
```bash
grep -rn "def test_" --include="*.py" \
  | grep -iE "owner|manager|coach|reception|coach" \
  | awk -F: '{print $1}' | uniq -c | sort -rn | head -10
```

**Padrao final:**
```python
@pytest.mark.parametrize("role,path,expected_status", [
    ("Owner", "/financeiro/", 200),
    ("Owner", "/dashboard/", 200),
    ("Manager", "/financeiro/", 200),
    ("Manager", "/dashboard/", 200),
    ("Coach", "/financeiro/", 403),
    ("Coach", "/dashboard/", 200),
    # ...
])
def test_role_access_matrix(client_for_role, role, path, expected_status):
    response = client_for_role(role).get(path)
    assert response.status_code == expected_status
```

**Criterio de pronto:**
1. Arquivo (ou classe) refatorado de N metodos para 1 metodo
   parametrizado.
2. Numero de casos coletados antes vs. depois e igual (cada parametro
   conta como 1 caso para pytest).
3. Suite continua verde.
4. Documentar em comentario o motivo (template para futuras matrizes).

**Trade-off:** Se a matriz original tinha asserts diferentes alem do
status code (ex.: alguns checam que mensagem aparece, outros checam DB
state), pode dividir em 2 parametrizes: status-only matriz + side-effect
matriz. NAO espremer tudo em um teste denso.

**Output:** commit "test: parametrizar matriz de roles em <arquivo>".

---

### FASE 6 — Testes de constraints de banco (M, 2-4h)

**Depende de:** Fase 4 (factories aceleram setup).

**O que faz:** Para cada model com constraint nao-trivial (UniqueConstraint
com condition, on_delete=PROTECT, on_delete=CASCADE com side-effects,
related_name esperado), escrever 1 teste que VIOLA a constraint e
confirma que o banco rejeita.

**Inventario:**
```bash
grep -rEn "UniqueConstraint|on_delete=.+\.(PROTECT|CASCADE|RESTRICT|SET_NULL)" \
  --include="*.py" --exclude-dir=migrations \
  | head -50
```

**Padrao:**
```python
# tests/test_db_constraints.py
@pytest.mark.django_db
def test_student_identity_unique_email_when_live():
    """StudentIdentity tem UniqueConstraint condicional em (email, box_root_slug)
    para status in PENDING/ACTIVE. Duas identidades com mesmo email no mesmo
    box e ambas ACTIVE deve violar."""
    StudentIdentityFactory(email='dup@example.com', status='active')
    with pytest.raises(IntegrityError):
        StudentIdentityFactory(email='dup@example.com', status='active')

@pytest.mark.django_db
def test_box_owner_user_protect_on_delete():
    """Box.owner_user e PROTECT — deletar o User deve falhar enquanto o Box existir."""
    user = UserFactory()
    box = Box.objects.create(slug='proto', schema_name='box_proto',
                             display_name='Proto', owner_user=user)
    with pytest.raises(ProtectedError):
        user.delete()
```

**Criterio de pronto:**
1. Novo arquivo `tests/test_db_constraints.py` com >= 8 testes cobrindo:
   - 2 UniqueConstraint
   - 2 on_delete=PROTECT
   - 2 on_delete=CASCADE (verifica side-effect)
   - 2 NOT NULL / required field
2. Todos passam.
3. Cobertura inclui esses 8 cenarios (vis check no htmlcov).

**Trade-off:** NAO tente cobrir TODAS as constraints. 8 cenarios bons +
template > 80 cenarios apressados. PRs futuros adicionam mais.

**Output:** commit "test: cenarios de constraints de DB (8 casos)".

---

### FASE 7 — Catalogar e adicionar cenarios de erro (M-L, 4-8h)

**Depende de:** Fase 1 e Fase 4.

**O que faz:** Auditar e organizar testes de cenarios de erro:
1. Inventario do que JA existe (grep por `status_code` 4xx/5xx em assertions).
2. Identificar 5 endpoints criticos sem teste de erro explicito.
3. Adicionar testes parametrizados de erro:
   - 400: validacao falha
   - 401: anonimo em rota privada
   - 403: usuario sem role
   - 404: recurso inexistente
   - 429: rate limit excedido
   - 500: side-effect de integracao externa quebra (usar `responses`)

**Procedimento:**
```bash
grep -rEn "status_code,\s*(400|401|403|404|429|500)" --include="*.py" \
  | wc -l    # baseline atual
```

**Padrao para 500 via responses:**
```python
import responses

@responses.activate
def test_stripe_webhook_handles_provider_500():
    responses.add(responses.POST, 'https://api.stripe.com/v1/...',
                  status=500, json={'error': 'internal'})
    response = client.post('/financeiro/stripe/webhook/', ...)
    assert response.status_code in (502, 503)  # ou 200 com retry agendado
```

**Criterio de pronto:**
1. Arquivo `docs/testing/error-scenarios-inventory.md` com mapa
   endpoint → status testados.
2. >= 15 novos testes de cenarios de erro adicionados, em
   `tests/test_error_scenarios.py` ou agrupados por app.
3. Coverage de linhas que tratam erro (try/except, return Http404,
   etc.) sobe >= 5pp.

**Trade-off:** 500 via mock de integracao externa pode ser flaky se nao
isolado bem. Use `responses` (assertions sobre HTTP mocks) e nao mocks
manuais de bibliotecas internas.

**Output:** commit(s) "test: cenarios de erro para <endpoint>".

---

### FASE 8 — E2E proof-of-concept (M, 3-5h)

**Depende de:** Fase 1 (suite rodando), Fase 4 (factories).

**O que faz:** Adicionar pytest-playwright + 1 unico cenario E2E
demonstrando o stack. NAO migrar testes existentes para E2E — POC + base.

**Setup:**
```bash
# Adicionar em requirements_test.txt:
pytest-playwright==0.5.2

# Instalar browsers (so em CI workflow, nao desenvolvimento)
playwright install --with-deps chromium
```

**Cenario sugerido (caminho mais critico do produto):**
Student onboarding wizard end-to-end:
1. Owner cria invite individual para um Student existente
2. Aluno clica no link, faz OAuth (mock provider via fixture), preenche
   onboarding, chega na home

**Decisao critica — onde rodar E2E:**
- E2E e LENTO (10-30s por teste vs 0.1s unit). Em CI:
  - PRs: rodar so `@pytest.mark.e2e` no nightly OU push para main.
  - PRs normais: pular E2E (`pytest -m "not e2e"`).
- Adicionar marker em pytest.ini: `markers = e2e: end-to-end browser test`.

**Criterio de pronto:**
1. `pytest-playwright` em `requirements_test.txt`.
2. `tests/e2e/test_student_onboarding_e2e.py` com 1 teste passando.
3. CI tem step opcional/scheduled rodando E2E (separado do PR
   workflow). Commit explicita a decisao.
4. Documentar em `docs/testing/e2e-guide.md` como adicionar mais E2E.

**Trade-off:** Headed mode (browser visivel) ajuda debug local mas e
~3x mais lento. Use `headless=True` em CI por default.

**Fallback se Playwright falhar em CI:** Pular esta fase, marcar issue
"E2E POC bloqueado por X". O resto do plano nao depende disso.

**Output:** commit "test(e2e): adicionar Playwright + POC student onboarding".

---

### FASE 9 — Documentacao + handover (S, 1h)

**Depende de:** Todas as fases anteriores.

**O que faz:** Consolidar conhecimento em `docs/testing/README.md`:
- Como rodar a suite (full, fast, e2e, com cobertura)
- Como adicionar um novo teste (factory pattern, parametrize, error scenario)
- Limites de tempo de CI e por que
- Como subir o `fail_under` no `.coveragerc`
- Lista de TO-DOs explicitos (proximas matrizes a parametrizar, proximos
  modelos a fatorar, etc.)

**Criterio de pronto:**
1. `docs/testing/README.md` existe e e linkado de README principal.
2. Inclui 1 secao "Trade-offs explicitos atuais" (CI tempo, fail_under,
   E2E em main-only).
3. Inclui comandos copy-paste para os 5 fluxos comuns.

**Output:** commit "docs(testing): guia consolidado de qualidade de testes".

---

## REGRAS DE EXECUCAO

1. **1 fase = 1 PR.** Nao misture fases. Cada PR e revisavel
   independentemente.
2. **Antes de cada fase**, rode `python -m pytest --create-db --migrations -q`
   e anote pass/fail counts. Depois, rode de novo. Se contagens divergirem
   em formas nao explicaveis pela fase: pare e investigue.
3. **Se uma fase tomar > 2x o esforco estimado**, pare e reporte. Pode
   indicar que o trade-off precisa ser revisitado.
4. **Quando perguntar vs decidir:**
   - Decida: tudo descrito como "trade-off" com criterio claro.
   - Pergunte: se um teste passa local mas falha CI, se modelo mais usado
     for ambiguo, se a decisao Codecov vs action-comment for politica
     da equipe.

## FALLBACK PLAN (se algo quebrar a meio caminho)

Cenario | Acao
---|---
Fase 0 mostra > 50 testes ja falhando | Pare. Abra issue listando-os. Plano nao prossegue sem suite verde.
Fase 1 expoe 5+ testes order-dependentes nao detectados antes | Volte para Fase 3 antes de continuar com 2.
Fase 1 mostra CI > 15 min mesmo com xdist | Aplique split: PR roda subset (lista explicita de paths criticos), main roda full. Documente em workflow.
Fase 4 quebra testes existentes ao migrar para factories | Reverter so a migracao; manter factories. Outros PRs migram organicamente.
Fase 8 Playwright nao instala em CI (problema de browser deps) | Marcar issue, skip E2E em CI por enquanto, manter capacity local. Resto do plano segue.
Fase qualquer fica bloqueada > 1 sprint | Reporte status com "passou/em progresso/bloqueado" por fase; usuario decide se replan.

## OUTPUT CONTRACT (o que voce entrega)

Por fase:
1. 1 commit (ou serie agrupada) com mensagem descritiva.
2. Atualizacao do `docs/testing/baseline-2026-05-18.md` (ou doc da fase)
   com numeros reais medidos.
3. Confirmacao do criterio de pronto via comando reproduzivel.

Ao fim do plano:
1. PR final consolidando docs/testing/README.md.
2. Mensagem de fechamento listando: cobertura inicial → cobertura final,
   testes adicionados, testes parametrizados, factories criadas, E2E
   funcionando.
3. Issue follow-up listando proximas oportunidades (modelos sem factory,
   matrizes nao parametrizadas, endpoints sem teste de erro).

## QUALITY BAR
- Cada commit roda CI verde.
- Cada fase NAO degrada o passar/falhar de fases anteriores.
- Tempo total de execucao do CI documentado a cada PR e justificado se
  ultrapassar limiar.
- Sem TODOs/FIXMEs no codigo de teste novo — se algo nao da pra fazer
  agora, vire issue.

## ASSUMPTIONS DECLARADAS
- Python 3.12, Django 6.0.5, postgres 15+, schema-per-tenant ativo.
- GitHub Actions disponivel; sem auto-deploy de E2E (nao usar Vercel/Render).
- Time aceita PR comment do action-coverage (zero servico externo); se
  preferir Codecov, ajuste Fase 2.
- "Baseline" de cobertura sera medido na Fase 0; numero exato influencia
  Fase 2 (`fail_under`).
