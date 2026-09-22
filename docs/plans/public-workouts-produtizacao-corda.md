# C.O.R.D.A. — Produtização do corredor de treinos (`/renan/`)

**Plano de produto (o "porquê"):** [public-workouts-produtizacao-plan.md](public-workouts-produtizacao-plan.md)
**Este documento:** execução técnica, dividida em duas frentes paralelas.
**Vender isso (branding, oferta, preço, landing page):** [public-workouts-go-to-market-plan.md](public-workouts-go-to-market-plan.md)
**Continuação técnica (Entrega 5 concretizada + Entrega 6 nutrição):** [public-workouts-escala-e-nutricao-corda.md](public-workouts-escala-e-nutricao-corda.md)

---

# C — Contexto

## C.1 O que existe hoje

`/renan/<slug>` serve 10 páginas HTML escritas à mão (400–1.400 linhas cada,
~16k no total) onde o treino **é** o markup: séries, reps e links do MuscleWiki
vivem em `<table>` hardcoded. Roda no **schema `public`, sem tenant**
(`PUBLIC_SCHEMA_PATHS` em `control/middleware.py`), sem login e sem cobrança.

A carga que o aluno registra vive em `localStorage[store_key]` — única cópia no
mundo, nunca esteve no servidor.

## C.2 Os quatro defeitos ativos

### A1 — `avaliacoes.json` é público e o slug é o nome do aluno
`student_app/views/public_workout_assessment_views.py:24` não tem autenticação.
`/renan/franciele/avaliacoes.json` devolve peso, %gordura, circunferências e notas.
Slugs são primeiros nomes. **Dado sensível de saúde (LGPD art. 5º, II) em URL
adivinhável.**

### A4 — O aparelho de cada aluno guarda o dado de todos
`templates/public_workouts/sw.js:6-13` monta o `ALLOWLIST` com **todos** os slugs
(`plan_slugs = tuple(PUBLIC_WORKOUT_LIBRARY)`) e `:38` faz `cache.add()` de cada um.
Os HTMLs carregam `Idade / Body fat / Peso` no cabeçalho. **O celular da Giovanna tem
o %gordura do Bruno, offline, sem ela saber.**

### A2 — Cache-first serve treino velho
`sw.js:100-105` busca da rede, atualiza o cache e **retorna o cacheado**. A chave
(`VERSION`) é o mtime dos CSS/JS — não muda quando o treino muda.

### A3 — A trava financeira não alcança `/renan/`
`student_auth.py` protege `/aluno/`; `/renan/` está em `PUBLIC_SCHEMA_PATHS` e nunca
passa pelo gate. E o PWA tem a página em cache.

## C.3 O que o OctoBox já resolveu (não reconstruir)

| Frente | Onde |
|---|---|
| Login social, token de uso único, entrega auditada | `oauth_providers.py:163`, `StudentAppInvitation` |
| Cookie de sessão stateless (30 d = 1 variável) | `student_identity/infrastructure/session.py` |
| Aluno paga própria fatura + rate limit + ownership | `StudentPayInvoiceView`, `fintech_throttles`, `resolve_payable_student_invoice` |
| Notificação e-mail + push + WhatsApp isolada por canal | `finance/payment_notifications.py:29` |
| Push VAPID cliente e servidor | `static/js/student_app/pwa.js`, `push_notifications.py` |
| Job agendado | management command + **systemd timer** (`run_due_async_job_retries`) |
| Templates de programa + política de aprovação | `WorkoutTemplate`, `WorkoutApprovalPolicySetting` (`operations:246,274`) |
| Prescrição por %RM | `load_type='percentage_of_rm'` |
| Calculadora de carga por % | `_rm_calculator.html` |
| Gráfico SVG (silhueta, conectores, gauges) | `static/js/public_workouts/assessments.js` |
| Fórmulas US Navy / JP3 / **JP7** / IMC / RCQ | `public_workouts/formulas.py` |
| Design system + primitives de aluno (3.803 linhas) | `static/css/design-system/`, `static/css/student_app/` |
| PDF | `reportlab==4.4.1` + `reporting/infrastructure/http_exports.py` |
| Auditoria + scrubber de PII | `auditing/services.py`, `auditing/scrubber.py` |

---

# O — Objetivo

1. **Fechar os dois vazamentos de dado pessoal ativos** (A1, A4) — antes de tudo.
2. Transformar treino de markup em **dado versionado**, publicado como snapshot
   imutável no schema `public`.
3. Dar ao aluno **identidade própria** e ao profissional **cobrança automática**.
4. Preservar a memória de força do aluno **atravessando 5–12 programas por ano**.
5. Fazer isso **reusando** o que o OctoBox já tem, não reconstruindo.
6. **Dois desenvolvedores em paralelo, sem colisão de arquivo nem de migration.**

---

# R — Riscos

### R1. Corrigir o código do A4 não apaga as cópias já gravadas
Os 10 aparelhos com PWA instalado seguem com o cache cruzado. **Só o bump de
`VERSION` expurga.** Tratar a correção de código como suficiente deixa o vazamento
exatamente onde está.

### R2. Erro de fronteira tenant↔public passa no teste e quebra em produção
O `conftest` força `schema_context('box_test')`. Uma view de `/renan/` que toque
modelo de TENANT_APPS **passa em CI** e só falha em produção — o
`public_workout_views.py` já documenta isso.

### R3. Reusar template do `/aluno/` arrasta `{% load %}` de tenant
`_progress_strip.html` faz `{% load student_shell %}`. Se a templatetag consultar
modelo tenant, cai em R2.

### R4. Regravar o golden durante a migração apaga a rede de segurança
`UPDATE_PUBLIC_WORKOUT_GOLDEN=1` regrava a baseline. Regravar antes de conferir o
diff faz o erro de transcrição entrar como se fosse o esperado.

### R5. Duas frentes criando migration no mesmo app
Conflito de `dependencies` e de numeração. Mitigado por **propriedade exclusiva de
diretório** (ver D.4).

### R6. Uma frente esperando a outra
Se a Frente B precisar do model da Frente A para começar, o paralelismo morre.
Mitigado por **contratos acordados antes de codar** (ver D.5).

### R7. `access_until` dentro do snapshot imutável
Renovar assinatura obrigaria republicar o programa. Vive no pacote do aluno.

### R8. Histórico de carga não é recuperável retroativamente
`reps` e `rir` faltando na Entrega 3 = buraco permanente no período que o review
semanal vai querer analisar.

### R9. Fase B (login obrigatório) sem pré-aviso vira parede
10 clientes pagantes batendo em tela de login no mesmo dia.

### R10. `weeks` interpretado como expiração
Aluno perde acesso ao treino porque o profissional atrasou o programa novo.

---

## R.T — Mapa de impacto em testes

Levantado antes de começar. **Nove testes existentes quebram**, e dois deles são o
caso mais perigoso: **codificam o defeito como especificação**.

### 🔴 Categoria 1 — testes que hoje garantem o vazamento

Estes não são "quebra a consertar". São **testes que precisam ser invertidos**, porque
afirmam como correto o comportamento que estamos removendo. Se alguém os "consertar"
sem ler, restaura o vazamento.

| Teste | Onde | Por que quebra |
|---|---|---|
| `PublicWorkoutAssessmentsEndpointTests` | `student_app/tests.py:2208` | A docstring da classe é literalmente **"GET /renan/<slug>/avaliacoes.json — publico, sem auth, so leitura."** |
| ↳ `test_returns_empty_shape_for_plan_without_assessments` | `:2211` | GET sem cookie espera **200**; passa a ser **404** |
| ↳ `test_returns_indicators_once_an_assessment_exists` | `:2221` | idem — GET sem cookie espera 200 com payload de saúde |
| `test_public_workout_service_worker_and_offline_route_are_available` | `:2082` | assere `assertIn('/renan/<slug>', sw_content)` **para os 8 slugs** + `?source=pwa` para 7. **É o teste que garante o A4.** |

**Mitigação (obrigatória na B0, no mesmo PR da correção):**

1. `avaliacoes.json` — reescrever como **trio**: sem cookie → 404; cookie do dono →
   200; **cookie de outro aluno → 404**. A docstring da classe muda junto, senão fica
   mentindo no repo.
2. Service worker — **inverter a asserção**: o SW **não** contém slug de outro aluno;
   contém o slug resolvido em runtime. Um teste que prova ausência, não presença.

> O terceiro teste da classe (`:2218`, slug inexistente → 404) **continua passando** —
> e é por isso que 404 é a resposta certa para slug de outro aluno: o formato de
> resposta fica indistinguível de "não existe".

### 🟡 Categoria 2 — quebram porque a fonte de verdade muda

| Teste | Onde | Por que quebra | Mitigação |
|---|---|---|---|
| `test_public_workout_pages_are_open_without_login` | `:2026` | 8 GETs esperando 200 **sem login**; a fase B exige login em plano pago | **dividir em dois**: `..._open_without_login` (legado/cortesia) e `..._require_login_for_paid_plan` (novo) |
| `test_public_workout_content_signature_is_stable` | `:2265` | compara assinatura do HTML com o golden — o template único muda o HTML; e assere `len(slugs) == 10` em `PUBLIC_WORKOUT_LIBRARY`, que deixa de existir | trocar a fonte dos slugs de dict para query em `PublicWorkoutProgram`; **diff aprovado à mão antes de regravar** (R4) |
| `test_public_workout_manifest_is_dynamic_per_slug` | `:2069` | `theme_color` / `background_color` / `short_name` saem do dataclass `PublicWorkoutPlan` e passam a vir do banco | fixture de `PublicWorkoutProgram` no `setUp` |
| `test_public_workout_page_renders_install_cta` | `:2118` | o install prompt sai do `_base.html` e da injeção legada para o template único | asserção pelo `id="public-workout-install"`, que é contrato, não pela classe CSS |
| `public_workouts/tests.py` — validação de slug | `:125` | `_validate_plan_slug` importa `PUBLIC_WORKOUT_LIBRARY` **de dentro da função** (para evitar import circular); a fonte passa a ser `PublicWorkoutProgram` | testes de serviço criam fixture no banco em vez de depender do dict |

### 🟢 Categoria 3 — devem quebrar, e isso é o objetivo

| Teste | Onde | Papel |
|---|---|---|
| `test_juliana_week_order_reflects_quad_frequency_program` | `:2126` | **detector de erro de transcrição da A2** |
| `test_henrique_week_order_reflects_split_and_required_back_exercises` | `:2157` | idem |
| `test_johnespanha_week_order_reflects_glute_priority_and_low_back_volume` | `:2179` | idem — e `johnespanha` é um dos 3 legados por substituição de string |

Estes asseram ordem de dias e presença de exercícios obrigatórios no HTML. Quando o
HTML passar a vir do payload, **eles são a rede que pega parser errando**.

> 🔴 **Não relaxar, não regravar, não marcar `xfail`.** Se um deles quebrar durante a
> A2, o parser errou — não o teste. Essa é a única leitura permitida.

### ⚪ Categoria 4 — risco indireto, rodar a suíte antes de seguir

| Frente | Suíte | Por que |
|---|---|---|
| B1 | `tests/test_integrations_stripe_*.py`, `tests/test_payment_*.py` (8 arquivos) | `stripe.api_key` sai do escopo de módulo (`auth.py:16`, `services.py:18`). Testes que fazem `patch(...stripe)` seguem valendo; quem depende do **side effect do import** pode quebrar silenciosamente |
| A0 | `seed_movement_library` | é idempotente por slug (`update_or_create`). Campos novos (`modality`, `movement_pattern`, `status`) **sem default** quebram o seed existente → nascer com default (`modality='crossfit'` nos atuais, `status='active'`) |
| A1 | `tests/test_tenant_boundary.py` (39 testes) | não deve quebrar — é o **guarda**. A A1 deve **adicionar** um irmão específico para `/renan/` |

### 🔵 Categoria 5 — testes de isolamento entre produtos *(novos, obrigatórios)*

Provam que a regra D.00 continua valendo. São **regressão de arquitetura**: quebram
quando alguém religa o acoplamento, não quando algo "para de funcionar".

```
tests/test_public_workouts_isolation.py
  ✓ nenhum modelo de public_workouts tem FK para finance.Payment      (V3)
  ✓ nenhum modelo de public_workouts tem FK para StudentBoxMembership (D.0)
  ✓ publicar programa nao cria linha em MovementLibrary               (V1)
  ✓ publicar programa nao cria linha em WorkoutTemplate               (V2)
  ✓ cobrar consultoria nao cria linha em finance.Payment              (V3)
  ✓ cobrar consultoria nao aparece em overdue_metrics do box          (V3)
  ✓ login de treino nao cria StudentAppInvitation                     (V5)
  ✓ corredor nao importa integrations.stripe.router nem .services      (N2)
  ✓ trocar e-mail em um produto nao altera o outro                     (N5)
  ✓ movimento pending do corredor nao aparece no picker do coach      (V1)
```

> O penúltimo é o mais concreto de explicar para quem revisar: **se o coach do box
> abrir o seletor de movimentos e enxergar "abdução de quadril na máquina (pendente)"
> do aluno de consultoria, os dois produtos se atravessaram.** O teste falha antes de
> alguém descobrir isso na tela.

### Testes que NÃO existem e precisam nascer

Buracos de cobertura que o plano cria ou expõe:

| Teste novo | Onda | Por que é obrigatório |
|---|---|---|
| ✅ Nenhuma view de `/renan/` toca TENANT_APPS | A1 | **R2** — o `conftest` força `schema_context`, então hoje o erro passa em CI e só quebra em produção. Sem esse teste, DA-1 não tem rede. **Fechado nesta sessão** (auditoria pós-merge de #236): `tests/test_tenant_boundary.py::B14PublicWorkoutViewsNeverTouchTenantAppsTest`, `@pytest.mark.public_schema` de verdade (não só ausência de `schema_context` — reset explícito pro schema `public`, sem nenhum tenant provisionado), 3 views cobertas (detail, `avaliacoes.json`, `treino.pdf`). Passou de primeira — a proteção do B0 (`control/middleware.py::PUBLIC_SCHEMA_PATHS`) já existia, só faltava o teste que provasse. Categoria 5 (`tests/test_public_workouts_isolation.py`) também ganhou o item V2 que faltava (publicar programa não cria `operations.WorkoutTemplate`) — V1 já tinha teste próprio desde a Onda A0, não duplicado. |
| Aluno A logado abrindo slug de B → **404** | B3 | ownership (DA-2) — hoje não existe conceito de dono de slug |
| `record_load` reenviado com a mesma `idempotency_key` não duplica | A1 | outbox offline reenvia por construção |
| Duas versões ativas para o mesmo slug são recusadas **pelo banco** | A1 | a constraint parcial é a garantia, não o código |
| Rollback: publicar v2, voltar v1, aluno vê v1 | A1 | `is_active` |
| `movement_slug` sobrevive a republicação | A1 | **D1** — se não sobreviver, substituição e histórico se perdem a cada programa |
| `estimate_one_rep_max` devolve `None` acima de 15 reps efetivas | A3 | honestidade estatística |
| Prompt do parser acima de **4.096 tokens** | A2 | abaixo disso o cache do Haiku **para de funcionar sem erro** |
| Nenhum `.json` sob `/renan/` entra no `PAGE_CACHE` | B0 | A1+A4 vistos do lado do dispositivo |
| `drain_payment_notices` rodado duas vezes no mesmo dia não duplica envio | B2 | a unique constraint é a garantia |

### 📌 Baseline medido — 2026-09-13, antes de qualquer código deste plano

```
.venv/Scripts/python.exe -m pytest --create-db --migrations -n 4 -q
```

| Métrica | Valor |
|---|---|
| Passaram | **1.584** |
| Pulados | 5 |
| **Falhas** | **0** |
| Subtests | 103 |
| Tempo total | **241 s** (4 min 01 s) |

**É contra este número que se compara.** Qualquer falha depois disso foi introduzida
por este trabalho — não havia nada quebrado antes.

Os 241 s também são a referência do **N6**: quando a Onda A1 adicionar os ~8 modelos
SHARED, medir de novo. Se dobrar, revisar quais precisam mesmo ser SHARED.

> ⚠️ **Os 5 skips estão todos em `tests/test_tenant_boundary.py`**, com a mensagem
> *"Schema de teste não existe: relation `boxcore_student` does not exist"* — eles se
> auto-pulam quando o schema tenant não está montado naquele worker do `-n 4`.
>
> **Isso importa diretamente para a Onda A1:** o teste de fronteira do `/renan/` (R2)
> nasce nesse mesmo arquivo. Se ele herdar o skip, **passa sem testar nada** — e a rede
> da DA-1 deixa de existir sem ninguém perceber. Ao escrever esse teste, conferir que
> ele roda de fato (comparar `-n 4` com `-n 0`), não só que "passou".

> Pré-requisito: Docker Desktop com engine Linux ativo. Na medição, `docker compose -f
> docker-compose.postgres.yml up -d` **falhou na primeira tentativa** (pipe do engine
> ainda não disponível) e funcionou na segunda. Se acontecer, é só repetir.

### Ordem de execução recomendada

1. **Antes de tocar código:** comparar com o baseline acima. Sem ele, não há como
   distinguir "eu quebrei" de "já estava quebrado".
   Ver [docs/testing/README.md](../testing/README.md) — Postgres obrigatório,
   `--create-db --migrations`.
2. **B0:** inverter os 3 testes de Categoria 1 **no mesmo PR** da correção. Nunca
   commitar a correção com o teste antigo verde.
3. **A0:** aplicar e reverter migration em banco limpo antes de seguir.
4. **B1:** suíte de Stripe completa depois do seam.
5. **A2:** os 3 testes de Categoria 3 são o critério de aceite da migração.
6. **B3:** golden só regravado em **commit separado**, com diff aprovado por humano.

### Contagem

| | Quantidade |
|---|---|
| Testes que quebram e precisam ser **invertidos** (Cat. 1) | 3 |
| Testes que quebram por troca de fonte (Cat. 2) | 5 |
| Testes que **devem** quebrar se algo der errado (Cat. 3) | 3 |
| Suítes a rodar por precaução (Cat. 4) | 3 |
| Testes novos obrigatórios | 10 |

---

## R.N — Engenharia reversa com o isolamento em vigor

Simulação do sistema completo **depois** de D.000, D.00 e D.0. Cinco cenários novos
— três quebram, e um deles é consequência direta do próprio isolamento.

### N1 — 🔴 `PaymentWebhookEvent`: escrever nele viola a regra que acabei de escrever?

O corredor tem endpoint próprio (S3), mas o envelope do evento precisa ser persistido e
deduplicado. `PaymentWebhookEvent` vive em `integrations/` (**SHARED**), e o docstring
do modelo diz: *"SHARED (public): app_label='integrations'. **Nunca expor fora de
integrations/**."*

**Decisão, com o trade-off à mostra:** o corredor **grava** em `PaymentWebhookEvent`, e
isso é consistente com D.00 — `integrations/` é a fronteira com o mundo externo,
compartilhada por todos os produtos, como os gateways de entrega e o `auditing`.
Persistir envelope bruto é **transporte**, não decisão de negócio.

Três condições para isso não virar brecha:

1. O corredor **não adiciona campo** ao modelo. `event_id` já é único e o envelope bruto
   já carrega `metadata.product` — nada a acrescentar. É *append de linha*, não mudança
   de schema.
2. O corredor **não importa** nada de `integrations/stripe/router.py`. Só
   `verify_stripe_webhook` (`auth.py`), que é função pura.
3. **A dedup fica global — e isso é uma vantagem, não concessão.** Se a Stripe reenviar
   o mesmo `evt_` para o endpoint errado, uma tabela única pega; duas tabelas deixariam
   passar.

### N2 — 🔴 O seam `resolve_stripe_account` não deveria estar nesta entrega

A Onda B1 previa refatorar `integrations/stripe/auth.py:16` e `services.py:18` para
tirar `stripe.api_key` do escopo de módulo. **Isso é modificar o app principal motivado
pelo corredor** — exatamente o que D.000 proíbe.

E é desnecessário: se o corredor tem **checkout próprio**
(`public_workouts/stripe_checkout.py`), ele resolve a própria conta e nunca chama
`create_checkout_session` do box.

**Correção:** o seam **sai da Onda B1** e vira nota de dívida do OctoBox — legítima
(chave global no import é dívida do próprio box), mas em PR separado, do box, no tempo
dele. O corredor já nasce com a conta resolvida por ele, que aliás é o desenho correto
para multi-personal.

Uma modificação a menos no principal.

### N3 — 🟡 O isolamento tirou o financeiro do corredor dos relatórios

**Consequência direta de V3 que eu não contabilizei.** Ao separar `PublicWorkoutPayment`
de `finance.Payment`, a receita de consultoria **deixou de aparecer** em
`overdue_metrics`, no dashboard financeiro e em qualquer relatório do box.

Isso é o comportamento correto — mas **o profissional vai querer ver o dinheiro dele**.

**Não é bug, é escopo faltando:** uma tela própria de financeiro do corredor (quem
pagou, quem está atrasado, quanto entrou no mês). Entra como **5.6**, na Entrega 5,
junto com o painel do personal (5.4) — mesma tela, provavelmente.

O custo é real e estava escondido atrás de uma decisão de arquitetura.

### N4 — 🟡 Campo 7 da anamnese é texto livre indo para a API da Anthropic

*"Maior dificuldade no treino ou em manter a rotina"* é campo aberto. A pessoa pode
escrever *"tenho ansiedade e travo antes de treinar"* ou *"estou em tratamento e canso
fácil"* — **dado sensível de saúde que ninguém previu**, saindo do país (D2).

O consentimento (0.5) cobre "dado de saúde", mas quem preenche não relaciona uma coisa
com a outra na hora de escrever.

**Correção barata e honesta:** aviso **no próprio campo**, não só no termo —
*"Isso é usado para montar e ajustar seu treino."* Quem escrever algo sensível escreve
sabendo. Custa uma linha de UI e resolve o problema no momento certo.

### N5 — 🟡 Pessoa que é aluna de box **e** de consultoria

Ela terá `StudentIdentity` (Google, no `/aluno/`) e `PublicWorkoutAccount` (e-mail, no
`/treinos/`), vinculados por referência fraca. Dois cookies, paths diferentes — isso
funciona.

O que quebra: **ela troca de e-mail.** Atualiza de um lado e o outro fica velho.

**Decisão:** a vinculação é **informativa, nunca autoritativa**. Cada produto mantém seu
contato. O corredor não lê e-mail de `StudentIdentity` para mandar cobrança — usa o
dele. Sincronizar os dois seria acoplamento disfarçado de conveniência.

Teste: mudar o e-mail em um lado **não altera** o outro, e nenhum dos dois quebra.

### N6 — ⚪ Custo de migration no schema public

`public_workouts` ganha ~8 modelos, todos SHARED. Toda criação de schema `public` em
teste paga isso — inclusive suítes que não têm nada a ver com o corredor.

Não é bloqueio, mas vale **medir o tempo de `--create-db` antes e depois da Onda A1**.
Se dobrar, vale revisar quais modelos precisam mesmo ser SHARED.

---

## R.C — Connect Express: o que não pode atravessar entre os dois produtos

O corredor vai usar **Connect Express com repasse** (personal recebe, plataforma retém
~10%). O box SaaS usa **conta única**. Dois modelos de dinheiro no mesmo processo Python
— e é aí que mora o risco.

### 🔴 C1 — `stripe.api_key` é global do processo. Isso é race condition.

```python
integrations/stripe/auth.py:16      stripe.api_key = settings.STRIPE_SECRET_KEY   # import
integrations/stripe/services.py:18  stripe.api_key = settings.STRIPE_SECRET_KEY   # import
signup/services.py:119              stripe.api_key = secret_key   # ← DENTRO de função
signup/services.py:211              stripe.api_key = secret_key   # ← DENTRO de função
```

`stripe.api_key` é atributo de **módulo** — compartilhado por todo o processo. Mutá-lo
em runtime, num servidor com threads, cria a seguinte janela:

```
thread A (box)      : stripe.api_key = chave_plataforma
thread B (corredor) : stripe.api_key = chave_do_personal      ← sobrescreve
thread A            : stripe.checkout.Session.create(...)     ← usa a chave do PERSONAL
```

**Com conta única isso é invisível** — todas as chaves são a mesma. **Com Connect, o
pagamento sai pela conta errada**, sem erro e sem log. É o pior tipo de bug silencioso:
o checkout funciona, o cliente paga, e o dinheiro entra no lugar errado.

**Regra para o corredor — nunca mutar o módulo:**

```python
# public_workouts/stripe_checkout.py
client = stripe.StripeClient(api_key=<chave>)          # cliente por instância
client.checkout.sessions.create(..., stripe_account=<acct_do_personal>)
```

Cliente por instância (ou `api_key=` explícito em cada chamada) mantém a chave **no
escopo da requisição**. `stripe==15.5.1` suporta — confirmar a forma exata na doc da
versão antes de escrever.

> **Dívida do box, não nossa:** `signup/services.py` já faz mutação em runtime hoje.
> Enquanto houver uma conta só, é inofensivo. No dia que o box também usar Connect, vira
> o mesmo bug. Fica registrado como ponteiro, não como trabalho desta entrega (D.000).

### 🔴 C2 — Idempotency key com Connect é escopada por conta

A chave de idempotência da Stripe é única **por conta**. Uma chave como
`assinatura-aluno-42` colide entre contas conectadas diferentes se o mesmo padrão for
reusado.

**Regra:** a chave do corredor inclui o `acct_` do personal e o `PublicWorkoutPayment.id`
— nunca só o id do aluno.

O molde correto já existe no repo: `signup/services.py:160` monta a chave com o
`price_id` justamente para evitar colisão silenciosa. Mesmo raciocínio, outro eixo.

### 🟡 C3 — O valor cobrado ≠ o valor que o personal recebe

Com `application_fee`, o aluno paga R$ 89,90, a plataforma retém ~10% e o personal
recebe o resto **menos a taxa da Stripe**. Um único campo `amount` não representa isso —
e a conferência ("quanto eu recebi mesmo?") fica impossível.

`PublicWorkoutPayment` precisa de **três valores**, não um:

| Campo | O que é |
|---|---|
| `gross_amount` | o que o aluno pagou |
| `application_fee_amount` | o que a plataforma reteve |
| `net_amount` | o que caiu na conta do personal (vem do `balance_transaction`) |

Sem `net_amount` vindo do Stripe, a tela financeira (5.6) mostra número que não bate com
o extrato — e aí ninguém confia nela.

### 🟡 C4 — Evento de conta conectada tem um campo a mais

Eventos de Connect chegam com `account` no envelope (a conta conectada que originou).
`PaymentWebhookEvent` não tem esse campo — mas **o envelope bruto tem**, e a decisão N1
foi não adicionar campo ao modelo.

**Consequência:** o handler do corredor lê `account` **do payload**, não de coluna. Vale
anotar no código, porque é exatamente o tipo de coisa que alguém tenta "melhorar"
adicionando a coluna — e aí sobrecarrega o principal.

### 🟡 C5 — Onboarding do personal é fluxo novo, não é login

Connect Express exige KYC: o personal cria conta, envia documento, informa dados
bancários. Isso é `AccountLink` da Stripe, com estados (`pending`, `restricted`,
`enabled`) que precisam ser refletidos no produto — **um personal sem KYC completo não
pode receber**, e o aluno não deveria conseguir assinar antes disso.

Não está em nenhuma onda. Entra na **Entrega 5**, junto com o multi-personal — não antes,
porque enquanto for um personal só (você), o repasse não existe.

### 🟡 C6 — Estorno precisa decidir o que fazer com a comissão

Estornar R$ 89,90 reverte os 10% retidos? A Stripe permite reverter ou não
(`refund_application_fee` / `reverse_transfer`). São políticas comerciais diferentes:

- **Reverter:** o personal devolve o serviço, a plataforma devolve a comissão. Mais justo.
- **Não reverter:** a plataforma fica com a taxa. Mais agressivo.

**Decisão do produto, não do código** — mas precisa estar tomada antes do primeiro
estorno, senão vira caso a caso.

### Testes adicionais de Connect

```
tests/test_public_workout_connect_isolation.py
  ✓ checkout do corredor nao altera stripe.api_key global        (C1)
  ✓ duas chamadas concorrentes usam contas diferentes            (C1)
  ✓ idempotency key inclui o acct_ do personal                   (C2)
  ✓ gross/fee/net sao persistidos e gross = fee + net + taxa      (C3)
  ✓ handler le 'account' do payload, nao de coluna               (C4)
  ✓ assinar com personal sem KYC completo e recusado             (C5)
```

> **C1 é o único com potencial de mandar dinheiro para a conta errada.** O teste de
> concorrência (duas threads, duas contas, asserção de que cada uma usou a sua) é
> obrigatório antes do primeiro real com Connect.

---

## R.P — Pagamentos: bugs silenciosos e como travá-los

Bug silencioso é o que **não levanta erro, não aparece em log e não tem quem
reclame** — porque quem sofre não sabe que deveria estar diferente. Em cobrança, os
três piores são: aluno travado tendo pago, aluno livre sem ter pago, e mensagem
disparada duas vezes.

### O que o projeto já faz — seguir estes padrões, não inventar outros

| Padrão existente | Onde | O que garante |
|---|---|---|
| `PaymentWebhookEvent.event_id` **unique** | `integrations/stripe/models.py:38` | o mesmo evento Stripe nunca processa duas vezes |
| `StripePaymentRef.payment_intent_id` **unique** | `:118` | uma intenção de pagamento = uma referência |
| Claim/release com bloqueio | `tests/test_payment_create_idempotency.py:41` | duplo POST cria **uma** cobrança |
| Rate limit por usuário | `tests/test_payment_p0_guardrails.py:45` | `allows_until_max_then_blocks`, contador **por usuário** |
| Reconciliação independente do webhook | `tests/test_stripe_reconciliation.py` | estado converge mesmo se o webhook falhar |
| PIX assíncrono | `tests/test_stripe_pix_async_confirmation.py` | `checkout.session.completed` ≠ pagamento confirmado |

**13 arquivos de teste de pagamento já existem.** A Entrega 2 não estreia um domínio —
entra num domínio com disciplina estabelecida.

### Matriz de bug silencioso — o que pode dar errado nesta entrega

| # | Bug silencioso | Como acontece | Custo | Teste que trava |
|---|---|---|---|---|
| **P1** | **Aviso disparado duas vezes** | job roda 2× (timer + retry manual); `sent_at` marcado **depois** do envio e o processo morre no meio | aluno recebe 2 WhatsApps; confiança | `drain` rodado 2× no mesmo dia → **1** envio por `(payment, offset_days)` |
| **P2** | **Aviso nunca enviado** | `sent_at` marcado **antes** do envio e o canal falha → fica marcado como enviado para sempre | aluno não é avisado e trava sem entender | envio que falha **não** deixa `sent_at` preenchido; estado `failed` permite retry |
| **P3** | **Aluno travado tendo pago** | job `D+2` olha só `due_date`; webhook de confirmação ainda em trânsito | cliente pagante sem acesso — **o pior dos três** | pagamento confirmado há 1 min → job **não** suspende; janela de graça explícita |
| **P4** | **Aluno pago que não destrava** | `invoice.payment_succeeded` falha ou não chega; só o webhook destrava | cliente paga e continua travado, e **ninguém fica sabendo** | reconciliação (não o webhook) destrava; teste com webhook **suprimido** |
| **P5** | **Webhook de aluno suspende o BOX** | roteador novo (`StudentBoxMembership`) coexiste com o de `Box` (`router.py:306-419`); discriminador erra | **catastrófico** — suspende todos os alunos do box | evento de assinatura de aluno **nunca** altera `Box.status`, e vice-versa |
| **P6** | **Assinatura duplicada** | duplo clique em "assinar" → duas subscriptions no Stripe | cobrado 2× | duplo POST → **uma** subscription (molde: `test_payment_create_idempotency`) |
| **P7** | **Notificação para o aluno errado** | resolução de aluno sem tenant correto no job | dado de cobrança de A vai para B | job em 2 boxes: cada aviso cita o `payment.id` do próprio box |
| **P8** | **Valor absurdo no presencial** | `Payment.amount` é livre por orçamento; form sem validação | cobra R$ 0 ou R$ 8.990 | `amount` fora de faixa configurada é recusado **no serviço**, não só no form |
| **P9** | **Canal cai e ninguém percebe** | `notify_*` engole exceção por canal (é o desenho correto) e ninguém lê o retorno | régua "funcionando" sem entregar nada | retorno por canal é **persistido**, e `failed` em todos os canais gera log de erro |
| **P10** | **Feriado ignorado** | `scheduled_for` calculado sem `brazilian_holidays` | aviso de vencimento em dia que não vence | vencimento em feriado/domingo → data ajustada |

### Regras de teste para esta entrega

1. **Todo efeito colateral externo tem teste de idempotência.** Stripe, WhatsApp,
   push e e-mail. A pergunta é sempre *"e se rodar duas vezes?"*.
2. **Todo job agendado tem teste de dupla execução.** `drain_payment_notices` rodado
   2× no mesmo dia produz 1 efeito. Sem isso, um retry manual vira spam.
3. **Todo estado que trava tem teste bidirecional.** Não basta testar que trava —
   **tem que testar que destrava**, com o webhook suprimido (P4).
4. **Nada de `except: pass`.** Falha de canal é capturada, mas **registrada em estado
   persistido**, não só em log. O desenho de `notify_payment_confirmed` (retorno por
   canal) já é isso — a régua persiste esse retorno.
5. **Marcação de envio é transacional.** `select_for_update` na linha do
   `PublicWorkoutPaymentNotice`, `sent_at` gravado no mesmo commit do resultado do envio. Nem antes
   (P2) nem solto depois (P1).
6. **Dinheiro nunca é asserido por efeito colateral.** Teste de cobrança assere o
   registro no banco, não "o mock foi chamado".
7. **Toda suspensão automática é auditada.** `log_audit_event` com motivo — sem isso,
   "por que esse aluno travou?" não tem resposta.

### Testes obrigatórios da Onda B2

```
tests/test_payment_notice_schedule.py
  ✓ as 5 linhas nascem com o Payment, datas corretas (D-7,-3,-1,0,+2)
  ✓ vencimento em domingo/feriado ajusta scheduled_for
  ✓ mudar due_date recalcula as nao enviadas e preserva as enviadas
  ✓ unique (payment, offset_days) recusa duplicata no banco

tests/test_payment_notice_drain.py
  ✓ drain 2x no mesmo dia = 1 envio            (P1)
  ✓ nenhum registro entra em finance.Payment   (V3)
  ✓ canal falhando nao marca sent_at           (P2)
  ✓ falha em todos os canais gera log de erro  (P9)
  ✓ resultado por canal fica persistido        (P9)

tests/test_student_subscription_lifecycle.py
  ✓ duplo POST cria UMA subscription           (P6)
  ✓ D+2 sem pagamento suspende
  ✓ pagamento confirmado ha 1 min NAO suspende (P3)
  ✓ invoice.payment_succeeded reativa
  ✓ reconciliacao reativa com webhook suprimido (P4)
  ✓ cartao recusado gera copy diferente de inadimplencia

tests/test_student_vs_box_webhook_routing.py
  ✓ evento do corredor nao chega ao router do box         (P5, por endpoint)
  ✓ evento do box nao chega ao handler do corredor        (P5)
  ✓ assinatura HMAC do endpoint do corredor e verificada
  ✓ o mesmo evt_ reenviado ao endpoint errado e deduplicado (N1)

tests/test_payment_amount_guardrails.py
  ✓ amount fora de faixa e recusado no servico (P8)
  ✓ amount zero e recusado
```

> **P5 é o único com potencial catastrófico** — errar o roteamento suspende o box
> inteiro. Ele ganha teste nos dois sentidos e uma asserção negativa explícita
> (`Box.status` **inalterado**), porque o modo de falha é justamente *não acontecer
> nada visível do lado certo e acontecer tudo do lado errado*.

### Regra de ouro da Onda B2

**Nenhum PR de pagamento entra sem o teste de dupla execução do seu efeito.** Se o
código manda mensagem, cobra, trava ou destrava, existe um teste que roda aquilo duas
vezes e assere que o mundo mudou uma vez só.

---

# D — Direção

## D.00 O core: reutilizar a base, não SER a mesma base

> **Princípio que governa todo o resto deste documento.** O corredor de treinos
> **consome serviços** do OctoBox. Ele **não estende modelos** dele.

### As três formas de reuso

| Forma | Acoplamento | Veredito | Exemplos |
|---|---|---|---|
| **Copiar padrão** | zero | ✅ livre | primitives de CSS, molde de `wod_session_llm_parser`, estrutura de `notify_payment_confirmed` |
| **Chamar serviço** | de interface | ✅ ok | `send_html_email`, push VAPID, gateway do WhatsApp, `log_audit_event` |
| **Estender modelo do principal** | de schema | ❌ **proibido** | adicionar campo em `MovementLibrary`, gravar linha em `finance.Payment` |

**Quando o corredor precisa de algo que já existe no principal e precisaria
modificá-lo: ramifica.** Cria o seu, no app `public_workouts`, copiando a estrutura
que funciona. Duplicar 40 linhas de modelo é barato; acoplar dois produtos não é.

### Varredura — onde o plano ainda violava isso

| # | Violação | Por que machuca | Correção |
|---|---|---|---|
| **V1** | `MovementLibrary` ganharia `modality`, `movement_pattern`, `status` | o corredor gravaria movimentos de musculação e `pending` na tabela do box — **movimento pendente do seu aluno apareceria no picker do coach** | **`PublicWorkoutMovement`** próprio. Pode ser *semeado a partir* de `MovementLibrary`, nunca escrever nela |
| **V2** | `WorkoutTemplateMovement` ganharia `reps_spec`/`rir_spec` | modifica `operations/` para servir outro produto | **`PublicWorkoutTemplate`** + `...Block` + `...Movement` próprios, já nascendo com faixa e RIR |
| **V3** | `finance.Payment` cobraria consultoria | alimenta `overdue_metrics`, relatório e dashboard **do box** — receita de consultoria entraria no financeiro da academia | **`PublicWorkoutPayment`** próprio |
| **V4** | `notify_payment_due` dentro de `finance/payment_notifications.py` | função do corredor morando no app do box | **`public_workouts/notifications.py`** — copia a forma, chama os mesmos senders |
| **V5** | `StudentAppInvitation` como token de login | tem `box`, `student_id`, `onboarding_journey`; convite de box e login de treino dividiriam tabela com o mesmo campo significando coisas diferentes | **`PublicWorkoutLoginToken`** próprio, reusando `delivery_gateways.py` |
| **V6** | Views do corredor em `student_app/views/` | **atravessamento que já existe hoje**, antes deste plano | mover para **`public_workouts/views/`** |
| **V7** | Roteamento de negócio em `integrations/stripe/router.py` | o receiver e a verificação HMAC são infra; *o que fazer com o evento* é regra de negócio | router do principal **despacha por `metadata.product`**; o handler vive em `public_workouts/stripe_handlers.py` |

> **V5 revoga uma decisão anterior deste documento.** A DA-2 defendia reusar
> `StudentAppInvitation` com o argumento de "não criar dois sistemas de token". O
> argumento estava errado: **reusar o mecanismo não exige reusar a tabela.** O que se
> reusa é a entrega auditada (`StudentInvitationDelivery` → gateways) e o padrão de
> token de uso único — não o registro que carrega semântica de box.

### O que o corredor passa a ter de seu

```
public_workouts/
├── models.py
│   ├── PublicWorkoutProgram          ← snapshot publicado (era PublishedWorkout)
│   ├── PublicWorkoutLoadLog          ← carga por pessoa+movimento
│   ├── PublicWorkoutSubscription     ← assinatura e trava   (NÃO StudentBoxMembership)
│   ├── PublicWorkoutPayment          ← cobrança             (NÃO finance.Payment)
│   ├── PublicWorkoutPaymentNotice    ← régua de avisos
│   ├── PublicWorkoutMovement         ← catálogo             (NÃO MovementLibrary)
│   ├── PublicWorkoutTemplate/Block/Movement  ← biblioteca de programas
│   ├── PublicWorkoutLoginToken       ← token de e-mail      (NÃO StudentAppInvitation)
│   ├── PublicWorkoutSubstitution
│   └── PublicWorkoutAssessment       ← já existe
├── views/                            ← movidas de student_app/views/
├── services.py · notifications.py · stripe_handlers.py
├── parser.py · schema.py · formulas.py
└── management/commands/
```

### O que continua compartilhado — e por quê

| Compartilhado | Natureza | Justificativa |
|---|---|---|
| `StudentIdentity` | **credencial** | é o cofre; decisão de produto já tomada. O corredor a usa só para saber *quem é a pessoa* — o vínculo com o produto é `PublicWorkoutSubscription` |
| `delivery_gateways.py`, `send_html_email`, push VAPID, Evolution | **transporte** | enviar mensagem não é regra de negócio |
| `auditing`, `PIIScrubber` | **transversal** | auditoria é infraestrutura de conformidade |
| `brazilian_holidays.py` | **utilitário puro** | função sem estado |
| Design system e primitives | **apresentação** | somente leitura |
| `integrations/stripe` — receiver, HMAC, `PaymentWebhookEvent` | **transporte** | verificar assinatura e deduplicar evento não é negócio |

**A linha:** compartilha-se o que **transporta** e o que **identifica**. Nunca o que
**decide**.

---

## D.000 Sobrecarga zero — o corredor não pesa no app principal

> **Regra:** o corredor de treinos **não adiciona peso** ao OctoBox. Nem modelo, nem
> campo, nem valor de enum, nem branch de `if`, nem setting compartilhada.
> **O máximo que ele deixa no app principal é um comentário dizendo onde ele mora.**

### As três sobrecargas que ainda restavam

| # | Sobrecarga | Custo real | Solução |
|---|---|---|---|
| **S1** | `StudentIdentityProvider` ganharia `EMAIL` | muda o enum que governa o login do app de box; toda query que assume `google\|apple` passa a ter um terceiro caso | **`PublicWorkoutAccount`** próprio, com token de e-mail. Vincula a `StudentIdentity` por referência fraca **quando a pessoa também for aluno de box** — e a reconhece sem alterar nada dela |
| **S2** | `STUDENT_APP_SESSION_COOKIE_AGE` de 7 → 30 dias | 🔴 **essa variável governa o app do aluno de box.** Mudá-la altera o comportamento do outro produto | **`PUBLIC_WORKOUT_SESSION_COOKIE_AGE`** próprio. O cookie do corredor tem nome, path e validade próprios |
| **S3** | Despacho por `metadata.product` em `integrations/stripe/router.py` | um `if` que existe **só** por causa do corredor, dentro do roteador do box | **endpoint de webhook próprio.** A Stripe permite N endpoints configurados; cada produto tem o seu. `router.py` **não muda uma linha** |

**S3 é a mais bonita das três:** eu tinha desenhado um discriminador compartilhado e
depois uma bateria de testes (P5) para garantir que ele não erraria. Com endpoints
separados no painel da Stripe, **o evento do corredor nunca chega ao roteador do box**.
Não há o que discriminar, nem o que testar.

### O custo total no app principal: uma linha

`/renan/` **já está** em `PUBLIC_SCHEMA_PATHS` (`control/middleware.py:93`). As rotas
novas que não cabem sob esse prefixo — login e webhook, que não pertencem ao namespace
de um personal específico — ficam sob **`/treinos/`**:

```
/treinos/login            ← tela própria do produto
/treinos/stripe/webhook/  ← endpoint próprio (S3)
```

Uma única entrada `'/treinos/'` em `PUBLIC_SCHEMA_PATHS` cobre as duas. **É a única
modificação que o corredor faz no OctoBox** — e é config de roteamento, não lógica.

### Ponteiros de fronteira — o adendo, não o acoplamento

Onde um desenvolvedor do OctoBox **procuraria** algo do corredor e não acharia, fica um
comentário. Sem import, sem código, sem `if`. Só o endereço:

| Arquivo do OctoBox | Ponteiro a deixar |
|---|---|
| `student_app/views/__init__.py` | `# Views de /renan/ vivem em public_workouts/views/ (produto separado).` |
| `student_app/models.py`, acima de `MovementLibrary` | `# Catálogo do corredor de treinos: PublicWorkoutMovement, em public_workouts/models.py. Este aqui é do box — não receber movimento de lá.` |
| `operations/model_definitions.py`, acima de `WorkoutTemplate` | `# Templates do corredor de treinos: PublicWorkoutTemplate, em public_workouts/models.py.` |
| `finance/payment_notifications.py` | `# Cobrança do corredor de treinos: public_workouts/notifications.py. Esta aqui é do box.` |
| `finance/model_definitions.py`, acima de `Payment` | `# Cobrança do corredor: PublicWorkoutPayment. Não entra em overdue_metrics do box.` |
| `integrations/stripe/router.py` | `# Webhooks do corredor de treinos têm endpoint próprio (/treinos/stripe/webhook/) e handler em public_workouts/stripe_handlers.py. Nada dele passa por aqui.` |
| `signup/services.py`, acima da mutação de `api_key` | `# stripe.api_key é global do processo: mutar em runtime é race condition quando há mais de uma conta Stripe. Inofensivo hoje (conta única); ver R.C/C1 do CORDA do corredor antes de adotar Connect aqui.` |
| `student_identity/models.py`, acima de `StudentIdentityProvider` | `# O corredor de treinos autentica por PublicWorkoutAccount (token de e-mail próprio). Não adicionar provider por causa dele.` |
| `config/settings/base.py`, acima de `STUDENT_APP_SESSION_COOKIE_AGE` | `# Sessão do corredor de treinos: PUBLIC_WORKOUT_SESSION_COOKIE_AGE. Esta governa só o app do aluno de box.` |
| `control/middleware.py`, na entrada `/renan/` | atualizar o comentário existente para citar o app dono |

**Por que isso vale mais que documentação avulsa:** o ponteiro fica exatamente no ponto
onde a fronteira seria violada. Quem for adicionar `modality` em `MovementLibrary` lê o
comentário **antes** de escrever a migration — não depois, no code review.

E o custo é literalmente zero em runtime.

---

## D.0 Fronteira entre os dois produtos — nome e estado

> **Correção de rota (revisão desta seção).** Versões anteriores deste CORDA
> reusavam `StudentBoxMembership` para a trava do corredor de treinos e chamavam o
> registro de carga de `StudentLoadLog`. **As duas coisas estavam erradas** e pela
> mesma razão: misturavam estado de negócio de dois produtos diferentes.

O corredor de treinos e o SaaS de box **dividem infraestrutura, nunca regra de
negócio**:

| Camada | Compartilha? | Exemplos |
|---|---|---|
| Identidade / autenticação | ✅ | `StudentIdentity`, `StudentAppInvitation`, cookie assinado |
| Infra de transporte | ✅ | push VAPID, Resend, Evolution, systemd timer |
| Design system | ✅ | tokens, primitives (somente leitura) |
| **Estado de negócio** | ❌ **nunca** | assinatura, programa, carga, avaliação, trava |

### Por que `StudentBoxMembership` não serve

É o vínculo **aluno↔box do SaaS de academia**. O aluno de consultoria online não
frequenta aula, não tem `Attendance`, não aparece em `ClassSession`. Colocá-lo ali
significa que ele passa a existir em toda query de "alunos do box", em relatório de
frequência e em dashboard de aula — **atravessamento por construção**, não por bug.

**Substituído por `PublicWorkoutSubscription`**, no app `public_workouts`, com estado
próprio (`active`, `past_due`, `suspended`, `canceled`). O gate do `/renan/` consulta
ele. `StudentBoxMembership` e `SUSPENDED_FINANCIAL` continuam existindo e **não são
tocados** — governam o outro produto.

### Regra de nomenclatura

**Todo modelo do corredor de treinos vive em `public_workouts/` e tem prefixo
`PublicWorkout`.** O app já estabelece o padrão (`PublicWorkoutAssessment`).

| Antes (ambíguo) | Agora | Colidia com |
|---|---|---|
| `PublishedWorkout` | **`PublicWorkoutProgram`** | `SessionWorkout`, `WorkoutTemplate` |
| `StudentLoadLog` | **`PublicWorkoutLoadLog`** | `StudentExerciseMax`, `StudentExerciseMaxHistory` |
| `StudentBoxMembership` (reuso) | **`PublicWorkoutSubscription`** | o vínculo de box do SaaS |
| `PaymentNotice` | **`PublicWorkoutPaymentNotice`** | `payment_notifications.py` do box |
| `StudentExerciseSubstitution` | **`PublicWorkoutSubstitution`** | — |

**Nenhum modelo novo do corredor começa com `Student`.** Esse prefixo pertence ao
SaaS de box; usá-lo nos dois lados é convidar o desenvolvedor a abrir o arquivo
errado — e com duas frentes em paralelo, isso vira bug de produção.

### O que isso faz com o P5

**P5 deixa de ser um bug a testar e passa a ser impossível por construção.**

O roteador de webhook não precisa "acertar o discriminador": são **dois roteadores que
leem coisas diferentes**. A assinatura carrega `metadata.product` (`coaching` ou
`box_saas`) gravado no checkout, e:

- `product='coaching'` → resolve `PublicWorkoutSubscription`. **Não conhece `Box`.**
- `product='box_saas'` → resolve `Box`. **Não conhece `PublicWorkoutSubscription`.**
- sem `metadata.product` → **recusa e loga**, nunca adivinha.

Um evento de aluno não tem como suspender um box porque o caminho de código que
suspende box **não é alcançável** a partir dele.

Os testes de P5 continuam no plano — mas agora como **teste de regressão de
arquitetura** ("ninguém religou o acoplamento"), não como rede sob um risco vivo.

## D.1 Tese central

O `/renan/` não precisa de um sistema novo — precisa **parar de ser um sistema
paralelo**. Quase tudo que ele faz à mão (prescrição, push, pagamento, gráfico,
design, agendamento) já existe no OctoBox, testado em produção. O trabalho real é
**atravessar uma única fronteira** — tenant → public — e o resto é composição.

A fronteira se atravessa com **snapshot publicado**: a prescrição continua morando
no tenant (`WeeklyWodPlan`, `WorkoutTemplate`, `MovementLibrary`), e o `public`
guarda uma **fotografia imutável** que a página lê sem tenant, sem query
cross-schema, sem segunda verdade.

## D.2 Frases de arquitetura

1. `O eixo do dado do aluno é pessoa + movimento — nunca o treino. Programa é contexto, não chave.`
2. `Nada mutável entra no snapshot. Se muda por evento de negócio, o lugar é o pacote do aluno.`
3. `O snapshot é a prescrição; tudo que o aluno produz vive fora dele, referenciando (slug, version, movement_slug).`
4. `PostgreSQL é a verdade. O aparelho guarda o casco, o pacote do dono e o rascunho — nunca dado de terceiro.`
5. `Autenticado não é autorizado: slug de outro aluno devolve 404, nunca 403.`
6. `A assinatura controla a porta, nunca o conteúdo. Suspender não toca em programa publicado.`
7. `weeks é informativo. O único mecanismo que tira acesso é o financeiro.`
8. `Tudo que alimenta a IA começa a coletar antes da IA existir.`
9. `Nada gerado por IA publica sem passar por WorkoutApprovalPolicySetting.`
10. `Movimento desconhecido não bloqueia publicação — entra como pending e vai para fila.`
11. `A Frente A entrega serviços sem HTTP. A Frente B entrega rotas, templates e views.`
12. `Cada diretório tem um dono. Migration só nasce no diretório do dono.`
13. `Todo efeito colateral externo tem teste de dupla execução: rodar duas vezes muda o mundo uma vez só.`
14. `Falha de canal é capturada em estado persistido, nunca em except: pass.`
15. `Trava e destrava se testam juntos — e o destrava se testa com o webhook suprimido.`
16. `Teste de dinheiro assere o registro no banco, nunca que o mock foi chamado.`
17. `O corredor consome serviços do OctoBox. Nunca estende modelos dele.`
18. `Precisou modificar modelo do app principal? Ramifica: cria o seu, copiando a estrutura.`
19. `Compartilha-se o que transporta e o que identifica. Nunca o que decide.`
20. `Nenhuma migration do corredor nasce fora de public_workouts/ — vale para as duas frentes.`
21. `D.000 e principio, D.4 e mecanismo. Quando colidem, o mecanismo cede.`

## D.3 Onde mexe / onde NÃO mexe (visão geral)

### Mexe

**Domínio de treino (Frente A)**
- `public_workouts/models.py` — `PublicWorkoutProgram`, `PublicWorkoutLoadLog`, `PublicWorkoutSubscription`, `student_identity_id` em `PublicWorkoutAssessment`
- `public_workouts/services.py` — `get_active_program`, `publish_program`, `build_student_package`
- `public_workouts/formulas.py` — `estimate_one_rep_max` + `OneRepMaxEstimate`
- `public_workouts/migrations/` — **dono exclusivo**
- `public_workouts/schema.py` *(novo)* — JSON Schema do payload
- `public_workouts/parser.py` *(novo)* — HTML/texto → payload via Haiku
- `public_workouts/models.py` — `PublicWorkoutMovement` (**não** `MovementLibrary`; V1)
- `public_workouts/management/commands/seed_public_workout_movements.py` *(novo)*
- `public_workouts/management/commands/extract_movements_from_html.py` *(novo)*
- `public_workouts/models.py` — `PublicWorkoutTemplate/Block/Movement` já com faixa e RIR (V2)

**Acesso, dinheiro e entrega (Frente B)**
- `public_workouts/views/assessments.py` — fechar (A1), movida de `student_app/views/` (V6)
- `public_workouts/views/pages.py` — ownership, render do snapshot, matar legado (V6)
- `templates/public_workouts/sw.js` — allowlist, estratégias, ETag
- `templates/public_workouts/workout.html` *(novo)* — template único sobre o DS
- `student_app/public_urls.py` — rotas novas
- `public_workouts/models.py` — `PublicWorkoutLoginToken` (V5); `public_workouts/views/auth.py` — tela `/treinos/login`
- `public_workouts/notifications.py` *(novo)* — `notify_payment_due` (V4)
- `public_workouts/` — `PublicWorkoutSubscription`, `PublicWorkoutPaymentNotice`
- `public_workouts/stripe_checkout.py` *(novo)* — checkout próprio, conta própria (N2)
- `public_workouts/stripe_handlers.py` *(novo)* — handler próprio, endpoint próprio (S3)
- `integrations/stripe/auth.py` — **somente leitura**: importa `verify_stripe_webhook` (função pura)
- `config/settings/base.py`, `.env.example` — Google OAuth, `PUBLIC_WORKOUT_SESSION_COOKIE_AGE`, `PUBLIC_WORKOUT_STRIPE_*` e **uma** entrada `'/treinos/'` em `PUBLIC_SCHEMA_PATHS`
- `static/js/public_workouts/` — outbox, sync do pacote, draft

### NÃO mexe

- **Rota `/renan/<slug>` e os slugs** — estão em links distribuídos, no `start_url`
  dos PWAs instalados e no escopo do service worker. Congelados.
- **`store_key`** — namespace de `localStorage`; não construir nada novo sobre ele.
- `WeeklyWodPlan`, `DayPlan`, `PlanBlock`, `PlanMovement` — a prescrição tenant
  continua como está.
- `SessionWorkout` e toda a árvore de WOD de box.
- `WorkoutApprovalPolicySetting` — **usar**, não alterar.
- `StudentExerciseMax` / `StudentExerciseMaxHistory` — servem de molde; não são
  alterados nem migrados.
- `templates/student_app/**` e `static/css/student_app/**` — **reuso somente leitura**.
  Copiar padrão, nunca editar o original.
- `static/css/design-system/**` — autoridade de tokens; não recebe override local.
- `integrations/whatsapp/` — Evolution permanece (DI-1).
- `signup/services.py` — a assinatura box→plataforma não muda.
- Nenhum framework novo: sem Celery (systemd timer), sem CDN, sem Hermes.
- `assessment_sex` em `PublicWorkoutPlan` — continua servindo às fórmulas;
  unificação com `Student.gender` fica para depois.

## D.3b Estratégia de branch e divisão de responsabilidade

### Quem faz o quê

| | **Frente A — domínio de treino** | **Frente B — acesso, dinheiro e entrega** |
|---|---|---|
| **Responsável** | Renan (+ Claude) | segundo desenvolvedor |
| **Natureza** | decisão de domínio: movimentos, variações, 1RM, periodização | volume de infraestrutura: login, cobrança, PWA, front |
| **Volume** | **~13–18 dias** | **~25–35 dias** |
| **Ondas** | A0, A1, A2, A3 | B1, B2, B3, B4, B5 |

**A divisão não é só por tamanho — é por quem consegue decidir.** A Frente A carrega
escolhas que exigem saber treinar: se hip thrust com barra e na máquina somam carga,
quantas reps efetivas ainda permitem estimar 1RM, o que conta como programa novo, qual
`movement_pattern` agrupa o quê. Essas decisões não se delegam a quem não prescreve.

A Frente B é maior em dias e menor em ambiguidade: o que ela precisa saber está no
código do OctoBox, não na cabeça de um treinador.

### 🔴 Exceção: a Onda B0 sai antes de tudo, e não é do dono da Frente B

B0 fecha dois vazamentos de dado pessoal **ativos em produção**. Ela **não pode esperar
o projeto inteiro** numa branch de integração de 40 dias.

| | B0 |
|---|---|
| Quem | **Renan (+ Claude)**, imediatamente |
| Branch | `fix/renan-vazamento-dados`, direto de `main` |
| Merge | em `main`, assim que a suíte passar |
| Duração | 1–2 dias |
| Depende de | **nada** |

Ela toca diretório da Frente B (`sw.js`, views) — mas acontece **antes de a divisão de
frentes começar**, como PR solo. Depois disso a propriedade de diretório (D.4) passa a
valer sem exceção.

Efeito prático: o segundo desenvolvedor começa a Frente B com a `main` **já corrigida**,
e o dado sensível para de ficar exposto em dias, não em semanas.

### Estratégia de branch

```
main
 ├── fix/renan-vazamento-dados          ← B0, PR solo, merge IMEDIATO em main
 │
 └── feat/produtizacao-corredor          ← integração; só vai para main no fim
      ├── feat/pc-a0-fundacao-dados      → PR → merge na integração   (A)
      ├── feat/pc-b1-identidade          → PR → merge na integração   (B)
      ├── feat/pc-a1-snapshot            → PR → merge na integração   (A)
      ├── feat/pc-b2-cobranca            → PR → merge na integração   (B)
      ├── feat/pc-a2-parser-migracao     → PR → merge na integração   (A)
      ├── feat/pc-b3-template-fase-b     → PR → merge na integração   (B)
      └── ...uma branch por onda
```

**Uma onda = uma branch = um PR.** O plano já entrega isso pronto: cada onda tem escopo
fechado e um `pronto quando` explícito.

**Por que não commitar os dois na mesma branch:** cada `pull` traria trabalho pela metade
do outro, o CI ficaria vermelho por culpa de quem não sabe, e reverter uma onda levaria a
outra junto. Com 40+ dias e dois devs, isso não se sustenta.

### Quatro regras que evitam o inferno do merge final

1. **`main` → integração toda semana.** O repo está ativo (PR #211 é recente). Branch
   longa que não recebe `main` acumula divergência que explode no fim. Sempre
   `git merge origin/main` **na** integração — nunca o contrário.
2. **Cada onda é PR contra a integração, não commit direto.** Mesmo entre dois. É onde o
   CI roda antes de contaminar a base comum, e onde o outro vê o que entrou.
3. **A integração fica sempre verde.** Se uma onda quebrar, **o dono dela conserta antes
   de qualquer merge novo**. Base comum vermelha por mais de um dia trava os dois.
4. **Ninguém mergeia o PR do outro.** Cada um revisa e mergeia o que é seu. Duas
   exceções que exigem aprovação dos dois: **B0** (segurança) e qualquer PR que toque os
   **contratos S1/S2/S3** — congelados por acordo mútuo.

### O risco clássico da branch longa não se aplica aqui

Branch longa costuma morrer em **conflito de migration**: `main` cria a `0042` em
`finance`, a branch cria outra `0042`, e o merge quebra.

Com D.000 isso quase não pode acontecer: **o corredor só cria migration em
`public_workouts`**, e nenhum outro trabalho do projeto mexe nesse app. As migrations do
box seguem em `main` sem colidir.

A regra de propriedade de diretório, que nasceu para separar os dois devs, protege
também contra o risco maior da branch longa.

### Sequência de partida

1. **Renan + Claude:** `fix/renan-vazamento-dados` → PR → merge em `main`. *(1–2 dias)*
2. **Os dois juntos:** ⇄ S0 — contratos S1/S2/S3 e o JSON Schema. *(meio dia)*
3. **Criar** `feat/produtizacao-corredor` a partir da `main` já corrigida.
4. **Em paralelo:** Renan começa A0; o segundo desenvolvedor começa B1.

---

## D.4 Divisão em duas frentes — propriedade de diretório

**A regra que impede colisão:** cada caminho tem **um dono**. Ninguém edita fora do
seu. Migration só nasce no diretório do dono.

| Caminho | Dono | Observação |
|---|---|---|
| `public_workouts/**` | **A** | inclui `migrations/` |
| ~~`student_app/models.py`~~ | — | **não é mais tocado** (V1) |
| `student_app/management/commands/**` | **A** | seeds e extratores |
| ~~`operations/model_definitions.py`~~ | — | **não é mais tocado** (V2) |
| `public_workouts/views/**` | **B** | movidas de `student_app/views/` (V6) |
| `student_app/public_urls.py` | **B** | |
| `templates/public_workouts/**` | **B** | inclui `sw.js` |
| `static/js/public_workouts/**` | **B** | |
| `static/css/public_workouts/**` | **B** | a deletar na Onda B3 |
| `student_identity/**` | **B** | |
| ~~`finance/**`~~ | — | **não é mais tocado** (V3, V4) |
| ~~`integrations/stripe/**`~~ | — | **não é mais tocado** (S3 + N2); só leitura de `verify_stripe_webhook` |
| `config/settings/**`, `.env.example` | **B** | |
| `tests/golden/public_workouts/**` | **B** | quem renderiza, valida |

**Migrations por app:** **toda migration do corredor nasce em `public_workouts/`** —
pelas duas frentes, sem exceção. `finance`, `student_identity`, `student_app` e
`operations` **não recebem migration deste projeto** (D.000).

### ⚠️ Quando D.4 colide com D.000, quem vence é D.000

Uma onda da **Frente B** pode precisar criar modelo (a B1 precisou:
`PublicWorkoutAccount`, `PublicWorkoutLoginToken`,
`PublicWorkoutLocalStorageBackup`). Lendo D.4 isoladamente — *"`public_workouts/**` é
da Frente A"* — a saída parece ser criar o modelo no diretório da própria frente.
**Não é.** Isso coloca tabela de um produto dentro do app do outro, que é exatamente o
que D.000 proíbe.

| | |
|---|---|
| **D.000** (sobrecarga zero) | **princípio** — dano permanente ao produto se violado |
| **D.4** (propriedade de diretório) | **mecanismo** — evita colisão de merge entre devs |

**Princípio vence mecanismo.** Colisão de migration é inconveniência de processo e se
resolve por sequenciamento; modelo de um produto na tabela do outro é dívida que só sai
com migration de dados entre apps.

**Procedimento quando a Frente B precisa de modelo:**

1. Cria em `public_workouts/models.py` e a migration em `public_workouts/migrations/`.
2. **Avisa a Frente A antes de gerar** — uma mensagem, não um processo.
3. A Frente A rebaseia antes de gerar a próxima.

Na prática o conflito quase não acontece: as ondas que criam modelo estão separadas no
tempo (B1 antes de A1), e o Django resolve numeração sequencial sem drama quando só uma
pessoa gera por vez.

> **Precedente:** a B1 criou os três modelos em `student_identity/` seguindo D.4 ao pé
> da letra, com o raciocínio documentado no código. A leitura foi defensável — a
> ambiguidade estava neste documento, não na implementação. Corrigido em
> `38a971bc`.

**Testes:** cada frente escreve teste no seu diretório. Testes de fronteira
(tenant↔public) são da **Frente A**, porque ela define o contrato.

## D.5 Contratos acordados ANTES de codar

Estes três contratos são escritos e fixados na Onda 0, por escrito, **antes de
qualquer código**. Depois disso as frentes programam contra eles sem se esperar.

### S1 — Leitura do programa ativo
```python
# public_workouts/services.py  (A entrega, B consome)
def get_active_program(*, slug: str) -> dict | None:
    """Payload do programa ativo, já resolvido. None se não existe.
    Roda no schema public. Nunca toca TENANT_APPS."""
```

### S2 — Pacote do aluno
```python
def build_student_package(*, account_id: int, slug: str) -> dict:
    """Última carga por movimento + 1RM + substituições + access_until.
    Sem HTTP, sem request."""
```

### S3 — Escrita de carga
```python
def record_load(*, account_id: int, movement_slug: str,
                weight_kg, reps=None, rir=None, performed_on,
                program_id=None, week_in_program=None,
                idempotency_key: str) -> dict:
    """Idempotente por idempotency_key. Reenvio nunca duplica."""
```

> **Atualização (Onda A1, Fatia B — acordo escrito entre as duas frentes,
> per "Regras de convivência" #3):** S2/S3 foram **re-congelados** trocando
> `student_identity_id: int` por `account_id: int` (`PublicWorkoutAccount.pk`,
> Onda B1). Motivo: a maioria dos clientes do corredor nunca foi aluna de
> box — exigir `student_identity_id` obrigatório deixaria o registro de
> carga inutilizável pra maioria do público real (ver nota de decisão na
> Onda A1). Quem também for aluno de box já carrega essa referência fraca
> em `account.student_identity_id` (Onda B1) — não duplicada em
> `PublicWorkoutLoadLog`.

**Enquanto A não entrega**, a Frente B programa contra um **stub** dessas três
funções, devolvendo payload de exemplo válido pelo schema. Isso desacopla as
frentes desde o dia 1. *(`public_workouts/services_stub.py` — removido na
Onda A1, Fatia B: as três funções já são reais, um onda antes do previsto.)*

---

# A — Ação

Ondas prefixadas por frente. `‖` marca ondas que rodam em paralelo.
`⇄` marca ponto de sincronização.

---

## ⇄ S0 — Contratos e schema (meio dia, **as duas frentes juntas**)

### O que fazer
1. Escrever `public_workouts/schema.py` com o JSON Schema do payload:
   `schema_version`, `program_id`, `program_label`, `started_on`, `weeks`,
   `accent_variant`, dias → blocos → movimentos (`movement_slug`, `reps_spec`,
   `rir_spec`, `is_tracked`, `load_type`, `load_value`, `reference_url`).
2. Congelar as assinaturas S1, S2 e S3 (D.5).
3. Frente B cria o stub das três funções para trabalhar sem bloqueio.

### O que entra
- `public_workouts/schema.py`
- `public_workouts/services_stub.py` (temporário — removido de verdade na
  Onda A1, Fatia B, um onda antes do previsto aqui: S1/S2/S3 já são reais)

### Pronto quando
1. Um payload de exemplo valida contra o schema.
2. As duas frentes conseguem começar sem esperar a outra.

---

## B0 — 🔴 Vazamentos (1–2 dias) — **Renan + Claude, direto em `main`**

> **Fora da branch de integração** (ver D.3b). Branch `fix/renan-vazamento-dados`,
> PR solo, merge em `main` assim que a suíte passar. É a única onda que não segue a
> propriedade de diretório — acontece **antes** de a divisão de frentes começar.

### O que fazer
1. `PublicWorkoutAssessmentsView`: exigir cookie de aluno; sem cookie **404**
   (403 confirmaria que o slug existe).
2. `sw.js`: excluir **todo** path sob `/renan/` que termine em `.json` do
   `PAGE_CACHE`.
3. `sw.js`: `ALLOWLIST` deixa de receber `plan_slugs`; o precache resolve **um**
   slug em runtime.
4. **Bump de `VERSION`** — é o que expurga as cópias já gravadas (R1).
5. `activate`: whitelist de caches válidos em vez de "apaga tudo que não é
   `STATIC_CACHE`" — que hoje mata o `PAGE_CACHE` vigente a cada ativação.

### O que entra
- `student_app/views/public_workout_assessment_views.py`
- `templates/public_workouts/sw.js`
- `student_app/views/public_workout_views.py` (só o contexto do SW)
- 2 testes novos em `student_app/tests.py`

### O que NÃO entra
- nenhuma mudança de modelo, nenhuma migration
- nada de login ainda

### Pronto quando
1. `/renan/<slug>/avaliacoes.json` devolve **404** em aba anônima.
2. Nenhum `.json` sob `/renan/` aparece no `PAGE_CACHE` do DevTools.
3. Em device real: o cache contém **um** slug.
4. `VERSION` mudou e o cache antigo sumiu após uma abertura.

---

## ‖ A0 — Fundação de dados (2–3 dias) — **Frente A · Renan + Claude**

### O que fazer
1. `student_identity_id` nullable em `PublicWorkoutAssessment` + migration.
2. **`PublicWorkoutMovement`** (não `MovementLibrary` — corrigido para bater com
   V1/D.00, escrito depois desta seção): campos `modality`
   (`crossfit`/`strength`/`both`), `movement_pattern`, `status`
   (`active`/`pending`) + migration. Pode ser *semeado a partir de*
   `MovementLibrary` (cópia read-only), nunca escreve nela.
3. `extract_movements_from_html` — varre os 10 HTMLs, extrai os pares
   `(nome, musclewiki_url)` dos `<a class="wiki-btn">`, normaliza slugs.
   Parser escopado por bloco `<div class="ex">` — um regex "nome mais
   próximo do wiki-btn mais próximo" cruza a fronteira de um bloco sem
   wiki-btn (inserts de cardio) e associa o nome errado ao link do
   exercício seguinte.
4. Rodar o extrator e semear; o seed de CrossFit ganha `modality='crossfit'`
   e `status='active'` (lista já curada); o extraído do HTML ganha
   `modality='strength'` e `status='pending'`.

### O que entra
- `public_workouts/models.py` + `migrations/` — `PublicWorkoutMovement`
- `public_workouts/management/commands/extract_movements_from_html.py` *(novo)*

### O que NÃO entra
- `PublicWorkoutProgram` ainda não (Onda A1)
- **`movement_pattern` não é preenchido pelo extrator.** O próprio CORDA
  (R.N) cita essa classificação como decisão que exige "saber treinar" —
  fica como campo livre esperando revisão humana, nunca advinhado por
  script. O item "`reps_spec`/`rir_spec` em `WorkoutTemplateMovement`" que
  esta seção listava foi removido: violava V2/D.00 (modificaria
  `operations/`, app do box) e não tinha critério de pronto próprio — a
  Onda A2 fica dona de extrair os `WorkoutTemplate` reais como follow-up,
  depois do parser determinístico migrar os 10 programas (ver seção A2).
- nenhuma view, nenhum template

### Pronto quando
1. `PublicWorkoutMovement` tem o vocabulário dos 10 treinos com `reference_url`.
2. Migrations aplicam e revertem limpo em banco de teste.
3. Nenhuma linha escrita em `student_app.MovementLibrary` (teste de isolamento).

> **`movement_pattern` por movimento continua em aberto** — critério antigo
> ("preenchido para todo movimento com variação conhecida") não é mais
> "pronto quando" desta onda pelo motivo acima. Fica pendente de revisão do
> Renan antes de a Onda A3 usar `movement_pattern` para substituição de
> exercício.
>
> **Atualização:** `classify_public_workout_movements` (novo comando) preenche
> uma *sugestão* de `movement_pattern` para os 82 movimentos extraídos do
> HTML — classificação biomecânica feita exercício por exercício (taxonomia
> de 20 padrões fechados), não um palpite de script. Continua sendo
> sugestão, não decisão: `status` permanece `pending`, o comando nunca
> sobrescreve um valor já preenchido (edição manual sempre vence), e a
> confirmação (promover `pending` → `active`) segue sendo ação separada,
> do Renan.

---

## ‖ B1 — Config e identidade (3–4 dias) — **Frente B · 2º desenvolvedor**

### O que fazer
1. Google OAuth ligado (`.env`), Apple Pay (domínio no dashboard Stripe).
2. ~~Seam `resolve_stripe_account`~~ — **removido desta entrega** (N2). O corredor tem
   checkout próprio (`public_workouts/stripe_checkout.py`) e resolve a própria conta.
   O seam vira dívida do OctoBox, em PR separado do box.
3. `PUBLIC_WORKOUT_SESSION_COOKIE_AGE=2592000` — **variável própria** (S2).
   `STUDENT_APP_SESSION_COOKIE_AGE` **não é tocada**: governa o app do aluno de box.
4. `StudentConsentDocumentKind.HEALTH_DATA` cobrindo IA, transferência
   internacional e retenção de 12 meses.
5. `PublicWorkoutAccount` + `PublicWorkoutLoginToken` (15 min, uso único, rate limit
   por e-mail). **`StudentIdentityProvider` não ganha valor novo** (S1); a vinculação
   a `StudentIdentity` é por referência fraca, quando a pessoa já for aluno de box.
6. Tela `/treinos/login` — **própria**, reusando o cofre, não a porta do `/aluno/`.
7. `1.7` upload do `localStorage` **bruto** — endpoint que aceita o blob como está.

### O que entra
- `config/settings/base.py`, `.env.example`
- `public_workouts/models.py` + `migrations/` — `PublicWorkoutAccount`,
  `PublicWorkoutLoginToken`, `PublicWorkoutLocalStorageBackup` (ver D.4 §
  "Quando D.4 colide com D.000": nascem aqui, não em `student_identity/`,
  apesar de ser onda da Frente B — a Frente B avisa a Frente A antes de
  gerar a migration)
- `student_identity/models.py` + `migrations/` — só o que continua sendo
  do domínio de identidade de box (ex.: `StudentConsentDocumentKind.HEALTH_DATA`)
- `student_identity/views.py`, `urls.py`
- `templates/treinos/login.html` *(novo)*
- `student_app/views/public_workout_views.py` (endpoint de upload bruto)

### O que NÃO entra
- **fase B do acesso** (login obrigatório) — só na Onda B3
- nenhuma trava ainda

### Pronto quando
1. Aluno entra com Google e continua logado 30 dias depois.
2. Aluno entra por link de e-mail e cai no treino dele.
3. O corredor não importa nada de `integrations/stripe/router.py` nem de `services.py`.
4. O blob de `localStorage` de um aluno real está no banco.

---

## ‖ A1 — Snapshot e publicação (3–4 dias) — **Frente A · Renan + Claude**

### ⚠️ Esta onda saiu dividida em duas fatias — ver nota antes de continuar

Ao implementar, apareceram **duas questões reais e não resolvidas** no que
esta seção já dava como certo. Nenhuma das duas é ambiguidade de redação
(como as de B1/B2/A0, corrigidas nesta mesma sessão) — são decisões de
produto que ninguém tomou ainda:

1. **`student_identity_id` vs `PublicWorkoutAccount`.** S2/S3 (D.5) foram
   congelados na Onda S0 com `student_identity_id: int` **obrigatório** como
   identificador da pessoa. Isso antecede a Onda B1, que criou
   `PublicWorkoutAccount` (conta só-email) exatamente **porque** a maioria
   dos clientes de consultoria não é aluna de box e não tem
   `StudentIdentity`. Implementar S2/S3 como estão congelados deixaria
   registro de carga inutilizável pra quem não é aluno de box — a maioria
   do público real do corredor. Mudar a assinatura exige "acordo escrito
   das duas frentes antes do código" (Regras de convivência #3) — não é
   uma correção unilateral como as anteriores.
2. **`WeeklyWodPlan`/`WorkoutTemplate` não têm relação com os programas do
   corredor.** Os dois são o planejador de WOD **em grupo** do box
   (`student_app.models`/`operations.model_definitions`, por tenant). Os
   programas do corredor (Bruno, Juliana...) são consultoria individual —
   mesociclo, RIR, sem nenhuma ligação com aula em grupo. O payload real só
   vai existir depois do parser determinístico (Onda A2) ler os 10 HTMLs — não tem
   como `publish_program` "ler WeeklyWodPlan/WorkoutTemplate" porque não é
   de lá que o conteúdo vem.

**Fatia A (entregue nesta onda):** tudo que não depende de resolver as duas
questões acima — `PublicWorkoutProgram`, S1 (`get_active_program`) de
verdade, `publish_program`/`activate_program_version` recebendo um payload
já pronto (de onde quer que venha — a Onda A2 decide), e o item 6
(movimento desconhecido vira `pending`, nunca bloqueia).

**Fatia B (decidida e entregue nesta sessão):** o Renan decidiu a questão 1
— S2/S3 trocam `student_identity_id: int` por `account_id: int`
(`PublicWorkoutAccount.pk`, ver D.5 atualizado). `PublicWorkoutLoadLog`, S2
(`build_student_package`) e S3 (`record_load`) de verdade. `publish_program`
ganhando uma fonte de dado real de tenant continua fora do escopo (dependeria
da Onda A2 de qualquer forma — questão 2 é mais um esclarecimento do que um
bloqueio).

### O que fazer (Fatia A)
1. `PublicWorkoutProgram` com `program_id`, `program_label`, `started_on`, `weeks`,
   `version`, `is_active`, `payload` + as duas constraints (única por
   `(program_id, version)`; **parcial** única por `slug` onde `is_active=True`).
2. `get_active_program` (S1) de verdade — deleta o uso do stub p/ essa função.
3. `publish_program(*, slug, payload)` — recebe payload já validado contra o
   schema (de onde vier), resolve `reference_url` por slug, grava no
   `public`, ativa. Movimento desconhecido entra `pending` e **não bloqueia**
   a publicação (item 6 original).
4. `activate_program_version(*, slug, program_id, version)` — reverter é só
   trocar qual linha tem `is_active=True`, nunca `UPDATE` do payload.

### O que fazer (Fatia B)
1. `PublicWorkoutLoadLog` indexado por `(account, movement_slug, performed_on)`
   — FK pra `PublicWorkoutAccount` (Onda B1), nunca `student_identity_id`
   duplicado (quem também é aluno de box já carrega essa referência fraca
   em `account.student_identity_id`).
2. S2 (`build_student_package`)/S3 (`record_load`) de verdade, com a
   assinatura re-congelada (`account_id`, ver D.5); `services_stub.py`
   removido — as três funções (S1 incluído) já são reais.
3. `record_load` idempotente por `idempotency_key`: reenvio da outbox (Onda
   B3) resolve pro registro já existente, nunca duplica linha (banco é a
   trava — `IntegrityError` em cima de `unique=True`, mesmo padrão do
   `PaymentWebhookEvent` da Onda B2).
4. Validação **estrutural** de `weight_kg`/`rir` no serviço, não só no
   model field: não-negativo, mais um **teto de 1000 kg (1 tonelada) em
   `weight_kg`** — decisão do Renan (número de produto, não um palpite de
   script), configurável via `PUBLIC_WORKOUT_MAX_WEIGHT_KG` no `settings`
   (mesmo padrão do guardrail de valor da Onda B2 — faixa ajustável sem
   deploy de código). **Detecção estatística de outlier de verdade**
   (comparar com o histórico do próprio atleta) continua fora daqui — fica
   pra Onda A3, mesmo trabalho de `estimate_one_rep_max`/detecção de platô
   já listado lá.
5. `build_student_package` devolve `one_rep_max_by_movement`/
   `substitutions` **vazios** de propósito — Onda A3 (1RM real e
   substituição por `movement_pattern`), não uma versão "provisória" que
   arrisca virar sugestão errada. `access_until` fica `None` até a Onda B3
   (fase B) ligar a trava de acesso de verdade.

### O que entra
- `public_workouts/models.py` + `migrations/`
- `public_workouts/services.py`
- teste de fronteira tenant↔public (checagem estática: `services.py` nunca
  importa ORM de `student_app`/`operations`)

### O que NÃO entra
- parser de IA (Onda A2)
- qualquer template ou view
- `student_app/application/publish_workout.py` que esta seção listava —
  não existe fonte real pra alimentar isso antes da Onda A2 (questão 2)

### Pronto quando (Fatia A)
1. Publicar v2 e voltar para v1 é `UPDATE` de uma coluna.
2. O banco recusa duas versões ativas para o mesmo slug.
3. Teste de fronteira falha se alguma função tocar ORM de TENANT_APPS.
4. Movimento desconhecido não impede `publish_program` de ativar a versão.

### Pronto quando (Fatia B)
1. `record_load` reenviado com a mesma `idempotency_key` não duplica linha
   (Pronto quando #4 original — era o único item que ficava pendente da
   Fatia B).
2. `weight_kg`/`rir` negativos são recusados no serviço, não só no
   form/model; `weight_kg` acima de 1000 kg também.
3. `build_student_package` devolve as quatro chaves do contrato S2 mesmo
   sem nenhuma carga registrada ainda (`{}`/`None`, nunca erro).
4. Teste de fronteira (services.py nunca importa ORM de TENANT_APPS)
   continua verde com o novo modelo.

---

## ‖ A2 — Parser determinístico + migração dos 10 (4–6 dias) — **Frente A · Renan + Claude**

> **Decisão de arquitetura (atualização pós-pesquisa): não usa IA.** O plano
> original chamava isso de "parser de IA"; a extração acabou não precisando
> de LLM nenhum. `movement_slug` já era resolvido deterministicamente desde
> a Onda A0 (regex no `href` do `wiki-btn`, agora em `musclewiki.py`,
> compartilhado entre A0 e A2); `reps_spec`/`rir_spec` do schema são texto
> livre sem validação de formato, e o HTML já tem — por exercício — um
> resumo escrito pelo próprio treinador (`gym-reps`) que serve quase
> verbatim. Usar LLM aqui trocaria uma extração 100% determinística e
> testável por risco de "chute plausível" de reps/RIR para 10 clientes
> pagantes reais. Ver docstring de `public_workouts/parser.py` para o
> raciocínio completo.

### O que fazer
1. `public_workouts/parser.py` — HTML → payload determinístico
   (`html.parser` da stdlib, sem LLM). Reaproveita a resolução de slug da
   A0. `reps_spec` vem do `gym-reps` verbatim quando existe, senão
   sintetiza da `sets-tbl`; `rir_spec` vem da última linha "Top" (o
   estímulo-alvo do ramp).
2. `public_workouts/management/commands/migrate_legacy_workouts.py` —
   `--dry-run`/`--slug`, mesmo padrão não-interativo de
   `classify_public_workout_movements.py`. Fluxo: rodar 1 slug com
   `--dry-run`, comparar contra o HTML, ajustar o parser se achar erro,
   repetir; só publicar (`publish_program`, já pronto desde a A1) quando
   bater.
3. Rodar nos 10 HTMLs; revisar payload por payload antes de publicar de
   verdade.
4. ~~Extrair ~15 `WorkoutTemplate` dos programas migrados~~ — **adiado**,
   segue como follow-up separado (depende de comparar `movement_slug`s
   entre os 10 já migrados para achar padrão repetido; materializar usa
   `operations/workout_templates.py::create_persisted_template_from_weekly_plan`
   como precedente).
5. ~~Geração de programa novo via IA (job assíncrono)~~ — **adiado**,
   bloqueado em dado que não existe ainda (coleta de anamnese, D4 do plano
   de produto) — onda futura própria.

### O que entra
- `public_workouts/musclewiki.py` *(novo)* — `movement_slug_from_url`
  promovido pra módulo compartilhado com a Onda A0 (evita duplicar a mesma
  regra dentro do mesmo app)
- `public_workouts/parser.py` *(novo)*
- `public_workouts/management/commands/migrate_legacy_workouts.py` *(novo)*
- `public_workouts/test_parser.py` *(novo)* — fixtures sintéticas dos casos
  estruturais reais (normal, biset inline, biset wrapped, alternativa "OU"
  no nível de sessão e dentro de `biset-wrap`, sem `wiki-btn`, RIR nu,
  tabela sem coluna "Tipo" — só `franciele.html` usa esse formato)
- `public_workouts/test_migrate_legacy_workouts.py` *(novo)* — critério de
  aceite contra os 10 HTMLs reais: schema válido, fixture de contagem de
  movimentos por dia, e conteúdo migrado como subconjunto do golden
  versionado
- `scripts/public_workout_signature.py` — `build_payload_signature`/
  `payload_fidelity_report`, função irmã de `build_signature()` que projeta
  o *payload* (não uma página renderizada) e compara como subconjunto

### O que NÃO entra
- 🔴 **regravar golden** — proibido nesta onda (R4)
- nenhuma alteração de template ou view
- os 3 testes de Categoria 3 (`test_*_week_order_reflects_*`,
  `student_app/tests.py`) **não são tocados** — continuam lendo a rota
  `/renan/<slug>` ao vivo (R.T já avisa: "se um deles quebrar durante a
  A2, o parser errou — não o teste"). `test_migrate_legacy_workouts.py`
  cobre o mesmo tipo de requisito de negócio (ordem de dia, exercício
  obrigatório) direto contra o *payload*, como preparação adiantada para
  quando a B3 cortar a rota pra servir do payload — sem relaxar/reescrever
  os originais.
- extração de `WorkoutTemplate` e geração de programa via IA (itens 4/5
  originais) — ver "O que fazer" acima

### Pronto quando
1. Os 10 programas existem como `PublicWorkoutProgram` ativo, payload
   válido pelo `schema.py`.
2. Fixture de contagem de movimentos por dia por programa (conferida à mão
   contra os 10 HTMLs) bate — pega desaparecimento silencioso de exercício.
3. Conteúdo migrado (reps/RIR/`reference_url`) é subconjunto do golden
   **versionado** — nunca inventa nada que não estivesse na página original.
4. `test_parser.py` cobre os casos estruturais reais encontrados nos 10
   HTMLs (biset nos dois "idiomas", alternativa "OU" nos dois lugares onde
   aparece, RIR nu, tabela sem coluna "Tipo").

---

## ‖ B2 — Cobrança (4–6 dias) — **Frente B · 2º desenvolvedor**

> **Atualização (auditoria de status desta sessão):** itens 1–5 confirmados
> no código (não só na doc): modelos, `notify_payment_due`,
> `drain_public_workout_notices` + `octobox-public-workout-notices.timer`
> (systemd já existe), webhook próprio (`/treinos/stripe/webhook/`,
> `stripe_handlers.py`), suspensão D+2 dentro do mesmo `drain_due_notices()`.
> **Item 6 (Customer Portal) fechado nesta sessão** —
> `start_customer_portal_session` (`stripe_checkout.py`) +
> `PublicWorkoutBillingPortalView` (`POST /treinos/billing-portal`,
> `student_identity/public_workout_views.py`). Mesmo padrão de
> `PublicWorkoutSubscribeView`: sessão do corredor exigida, sem template
> próprio (JSON com `portal_url`, a tela fica pra B3/B4). Só funciona pra
> conta com `stripe_customer_id` já preenchido (passou por 1 checkout de
> verdade) — sem isso, 404, não 503 (não é erro de configuração, é que
> ainda não há o que gerenciar). O cancelamento feito pelo aluno dentro do
> portal chega pelo MESMO webhook que já existia
> (`customer.subscription.deleted` → `mark_subscription_canceled`) —
> nenhuma lógica nova de mudança de estado, só a porta de entrada que
> faltava. **Onda B2 completa.**

### O que fazer
1. `PublicWorkoutPayment` (V3) + `PublicWorkoutPaymentNotice` (`payment`, `offset_days`, `scheduled_for`, `sent_at`) com
   unique `(payment, offset_days)`; as 5 linhas nascem com o `Payment`, data já
   resolvida por `brazilian_holidays`.
2. `public_workouts/notifications.py::notify_payment_due(payment, offset_days)` —
   **copia a forma** de `notify_payment_confirmed` e chama os mesmos senders. Não
   edita `finance/` (V4).
3. Management command `drain_public_workout_notices` + **systemd timer**.
4. Assinatura recorrente do aluno em **endpoint de webhook próprio**
   (`/treinos/stripe/webhook/`), handler em `public_workouts/stripe_handlers.py`
   resolvendo `PublicWorkoutSubscription`. `integrations/stripe/router.py` **não muda
   uma linha** (S3).
5. Job `D+2 → PublicWorkoutSubscription.suspended` e volta por
   `invoice.payment_succeeded`. **`StudentBoxMembership` não é tocado.**
6. ✅ Stripe Customer Portal.

### O que entra
- `public_workouts/models.py` + `migrations/` — `PublicWorkoutSubscription`, `PublicWorkoutPayment`, `PublicWorkoutPaymentNotice` (**criados pela Frente B** neste app, por instrução explícita desta seção; ver D.4 § "Quando D.4 colide com D.000")
- `public_workouts/notifications.py` *(novo)* — `notify_payment_due` (V4)
- `public_workouts/management/commands/drain_public_workout_notices.py` *(novo)*
- `public_workouts/stripe_checkout.py`, `stripe_handlers.py` *(novos, Fatia B)* — checkout e webhook próprios do corredor; `integrations/stripe/router.py` e `services.py` **não são tocados** (S3/N2 já decidiram isso — não há mudança neles nesta onda)
- `infra/hostgator-vps/systemd/` — unit do systemd timer

### O que NÃO entra
- `signup/services.py` (assinatura box→plataforma não muda)
- nenhum Celery

### Pronto quando
1. Aluno de teste assina, recebe os 4 avisos nas datas certas, trava em D+2, paga e
   destrava sozinho — sem intervenção.
2. Rodar o drain duas vezes no mesmo dia não duplica envio (P1).
3. Canal que falha **não** deixa `sent_at` preenchido (P2).
4. Pagamento confirmado há 1 minuto **não** é suspenso pelo job de D+2 (P3).
5. Reconciliação reativa o aluno **com o webhook suprimido** (P4).
6. Evento com `metadata.product='coaching'` **não alcança** o caminho que altera
   `Box.status` — e vice-versa (P5, agora regressão de arquitetura).
7. Duplo POST em "assinar" cria **uma** subscription (P6).
8. `amount` fora de faixa é recusado **no serviço**, não só no form (P8).
9. Cartão recusado gera copy diferente de inadimplência.
10. Toda suspensão automática tem `log_audit_event` com motivo.

> Os cinco arquivos de teste de R.P são **critério de entrada** da onda, não de saída:
> escrever o teste que falha antes do código que o faz passar. Em cobrança, teste
> escrito depois tende a assertar o que o código faz, não o que deveria fazer.

---

## ⇄ B3 — Template único, fase B e hard reset (5–7 dias) — **Frente B · 2º desenvolvedor**

**Depende de A1 (S1/S2 reais) e de A2 (os 10 publicados).**

> **Fundação visual já entregue, adiantada, fora da dependência.** Os itens 1
> e 2 ("O que fazer") não precisam de dado publicado de verdade — só do
> contrato de `schema.py` (Onda S0), já congelado. `templates/public_workouts/workout.html`
> existe, renderiza qualquer payload válido pelo schema (testado contra
> `build_example_payload`), compõe os primitives reais do `student_app`
> (`.student-card`, `.student-status-badge`, `tables.css`,
> `interactive-tabs.css`) e implementa o mapeamento `accent_variant` →
> `--theme-accent-premium`/`-support` (nenhum precedente existia no repo —
> o padrão espelha o toggle `body[data-theme]` já usado pro tema claro/escuro).
> **Não está ligado a nenhuma URL/view** (a fundação visual, acima). Os
> itens 3, 4, 6, 7, 9 (apagar os 8 CSS legados, matar o bootstrap de PWA
> antigo, fase B de acesso, `sw.js` novo, outbox, hard reset) continuam
> bloqueados em A1/A2, porque envolvem corte de produção real. `card-decor-glow`
> ainda não está aplicado — decisão de detalhe visual que fica pra quando
> a onda real começar.
>
> **Item 5 (gate de posse, completo) e item 8 base (endpoints HTTP) já
> entregues, fora de dependência de A2 — atualizado nesta sessão:**
> - Gate de posse: sessão de login (Onda B1) dona de outro slug recebe
>   404 em `/renan/<slug>` (`_confirm_login_session_owns_slug_or_404`,
>   `student_app/views/public_workout_views.py`).
> - Redirect pelo login: **não é `/aluno/treino`** (rota já ocupada por
>   `StudentWodView`, o RM prescrito do box) — é `/aluno/consultoria/`
>   (`StudentPublicWorkoutLinkView`, `student_app/views/public_workout_link_views.py`).
>   Resolve/cria `PublicWorkoutAccount` por e-mail do `StudentIdentity`
>   logado (get_or_create simples — `unique=True` em `.email` é a garantia
>   contra duplicata, sem reconciliação elaborada; conta já existente
>   nunca tem `student_identity_id` sobrescrito). Com assinatura ativa,
>   concede a sessão do corredor direto (sem o roundtrip de magic-link —
>   a auth do box já prova a identidade) e redireciona pro `/renan/<slug>`.
>   Sem assinatura, devolve página mínima informativa: não há hoje
>   nenhuma tela de "escolha seu plano" pra redirecionar (`/treinos/subscribe`
>   é uma chamada de API que já exige `plan_slug` conhecido).
> - Item 8 (base, não o item inteiro): `POST /renan/<slug>/carga`
>   (S3/`record_load`), `GET /renan/<slug>/pacote.json` (S2/
>   `build_student_package`, já com 1RM real da Onda A3) e
>   `GET /renan/<slug>/meus-dados.json` (export de dados do titular, Onda
>   A3/LGPD) — todos exigem sessão de login, 401 sem sessão, 404 sem posse.
>
> **Item 8, atualizado nesta sessão — outbox de IndexedDB entregue, UI de
> registro ligada a `workout.html`:** `static/js/public_workouts/load_tracker.js`
> (novo) — cada movimento com `is_tracked=True` ganha uma caixinha própria
> "Registrar carga de hoje" (input de kg + Salvar) logo abaixo da linha do
> exercício. Salvar grava primeiro no IndexedDB (`public-workout-outbox`,
> `idempotency_key` gerada uma vez por registro, reenviada sem trocar em
> toda tentativa) e só depois tenta `POST /renan/<slug>/carga` — offline ou
> erro de rede deixa o registro na fila pra próxima tentativa (`online`,
> próximo carregamento da página), nunca perde o dado. Rascunho em
> `visibilitychange` (campo digitado mas não salvo, tela apagada/app trocado)
> entra na mesma fila. Verificado via Playwright contra o payload real do
> Bruno: sem erro de console, entrada aparece no outbox após "Salvar",
> some depois de uma entrega bem-sucedida.
> Limpeza no logout **continua pendente**: não existe hoje nenhuma rota de
> logout no corredor (só o cookie de posse do B0 e a sessão de login do
> B1) — `window.PublicWorkoutLoadTracker.clearOutbox` já está exportada,
> esperando esse botão nascer.
> **Correção da nota acima**: nome de exercício em PT-BR NÃO precisava de
> campo novo em `schema.py` — achado incorreto, corrigido nesta sessão.
> `PublicWorkoutMovement` (Onda A0, `extract_movements_from_html`) já é um
> catálogo à parte, chaveado por `movement_slug`, com `label_pt` de
> verdade extraído das 10 páginas legadas (85 movimentos) + 44 essenciais
> de CrossFit curados — `publish_program` já garante (via
> `_ensure_movements_exist`) que todo `movement_slug` publicado tem pelo
> menos uma entrada aqui. **Entregue nesta sessão**:
> `services.build_movement_label_lookup(payload)` (1 query em lote) +
> `resolve_movement_display_name` (templatetag) — `workout.html` agora
> mostra o nome PT-BR revisado quando existe, senão o mesmo palpite
> mecânico de sempre. Zero mudança em `schema.py`, zero acordo entre
> frentes necessário.
> **Legenda de tipo de série (Preparatória/Feeder/Top Set/Max Set),
> também entregue**: como v1 pragmático — `reps_spec` já carrega o
> estágio como texto livre (ex. "2-3× Prep → 1× Feeder → 3× Top (6-8)",
> um segmento por estágio); o filtro `highlight_set_stages` reconhece o
> vocabulário fechado (extraído das 10 páginas legadas, `.st-p/.st-f/.st-t/.st-m`)
> e pinta cada palavra-chave, sem inventar dado novo nem mexer no
> contrato. Cores oficiais do design system (`--theme-text-muted`/
> `--theme-accent-warning`/`--brand`/`--theme-accent-danger`), uma legenda
> só pra página inteira. Formalizar como campo estruturado em `schema.py`
> fica pra quando a Frente A mexer no parser de qualquer forma — não
> bloqueia esta entrega.
> **Aba "Suas Cargas" (nova, pedido do Renan)**: recorde (maior peso já
> registrado) por movimento, via filtro `personal_record` sobre o mesmo
> `load_history` que a aba Histórico já usa — sem nova consulta ao banco.
> **Widget de carga redesenhado**: stepper ±2,5kg, dica clicável de
> "última vez: X kg" (busca `GET /renan/<slug>/pacote.json` — já existe —
> e usa `last_load_by_movement`; sem sessão de login, a dica só fica
> vazia, nunca bloqueia o registro), pulso visual de confirmação ao
> salvar. Tudo verificado via Playwright contra o payload real do Bruno
> (nome PT-BR, badges de estágio, stepper, aba nova) — screenshots
> comparados lado a lado com a página legada antes de push.

### O que fazer
1. `workout.html` composto dos primitives do `student_app` — chip, card,
   progress-strip, compact-state, hero-number, tables, interactive-tabs.
2. `accent_variant` → `--theme-accent-premium` (F) / `-support` (M) /
   `-primary` (neutro). Neon em detalhe via `card-decor-topstripe` e
   `card-decor-glow`.
3. Deletar os 8 CSS de `public_workouts/` e o `PUBLIC_WORKOUT_STYLESHEETS`.
4. Matar `_inject_legacy_pwa_head`, `_LEGACY_INSTALL_PROMPT_MARKUP` e
   `_LEGACY_SW_REGISTRATION_SCRIPT` (`public_workout_views.py:328-489`).
5. **Ownership do slug**: identidade da sessão dona do slug, senão **404**.
   `/aluno/treino` redireciona pelo login.
6. **Fase B**: treino de plano pago exige login; `access_until` no pacote.
7. `sw.js`: network-first + **ETag = `<slug>-v<version>`**; chave de assets separada
   da chave de página.
8. Outbox em IndexedDB: rascunho em `visibilitychange`, chave idempotente, dreno
   oportunista, limpeza no logout.
9. **Hard reset**: disparo de link na véspera, bump de `VERSION` no corte.

### O que entra
- `templates/public_workouts/workout.html` *(novo)*, `sw.js`
- `student_app/views/public_workout_views.py`, `public_urls.py`
- `static/js/public_workouts/` (outbox, sync, draft)
- remoção de `static/css/public_workouts/**`
- `tests/golden/public_workouts/**` — revalidação

### O que NÃO entra
- 🔴 regravar golden sem diff aprovado (R4)
- alteração de `templates/student_app/**` ou `static/css/student_app/**` (só leitura)

### Pronto quando
1. ✅ Os 10 renderizam do banco com golden idêntico. Verificado nesta
   sessão: `PublicWorkoutPreviewView` (`GET /renan/<slug>/preview`, novo)
   renderiza `workout.html` contra `PublicWorkoutProgram` de verdade —
   mesmo gate de posse da rota real, mas rota SEPARADA, não linkada em
   lugar nenhum, zero risco à rota que o aluno usa hoje. Os 10 programas
   reais (dado publicado via `migrate_legacy_workouts`, não exemplo)
   renderizaram sem erro, 208/208 exercícios com nome PT-BR, 0 erro de
   console — comparação lado a lado (`/renan/<slug>` vs `/renan/<slug>/preview`)
   feita via Playwright e compartilhada com o Renan.
2. Aluno A logado abrindo slug de B recebe **404** — já valia pra rota
   real (item 5, sessão anterior) e agora também pra `/preview`
   (`test_public_workout_preview_endpoint.py`).
3. Publicar v2 aparece no celular na próxima abertura com rede (device real).
4. Registro feito offline sobe sozinho e não duplica.
5. Nenhum aluno perdeu carga.

> **O que o item 1 acima NÃO prova**: que a rota real (`/renan/<slug>`)
> já está cortada pra servir `workout.html` — ela continua servindo o
> template legado, de propósito (itens 3/4/6/7/9 abaixo continuam sem
> tocar). Também não prova que os 10 programas estão publicados na VPS
> de produção — só que a migração é determinística e reproduz
> identicamente no sandbox local. Confirmação de produção fica por
> conta de quem tem acesso à VPS.

---

## ‖ A3 / B4 — Produto (paralelo, 7–10 dias) — **A: serviços · B: telas**

> **Atualização:** as três primeiras linhas da coluna "Frente A (serviços)"
> foram adiantadas nesta sessão — são engenharia pura (fórmula já
> especificada em `docs/plans/public-workouts-produtizacao-plan.md`
> §4.4, estatística sobre `PublicWorkoutLoadLog` que já existe), sem
> depender dos 10 programas reais nem de julgamento de treino novo.
> `estimate_one_rep_max`/`OneRepMaxEstimate` e
> `detect_one_rep_max_trend`/`OneRepMaxTrend` vivem em
> `public_workouts/one_rep_max.py` (novo); `build_weekly_review` em
> `services.py`. `build_student_package` (S2) já usa
> `estimate_one_rep_max` para popular `one_rep_max_by_movement` de
> verdade (antes vazio de propósito). A janela de detecção de platô/queda
> (3 semanas, banda de 2,5%, queda de 5%) é uma v1 deterministica
> documentada como ajustável — não é uma decisão de treino fechada, é
> limiar de código; ajustar é mudar constante, não arquitetura.
> `build_weekly_review` entrega **só o sinal calculado** (rótulo por
> movimento), nunca chama IA nem lê check-in/anamnese — nenhum dos dois
> tem coleta ainda (D4 do plano de produto: "tudo que alimenta a IA
> começa a coletar antes da IA existir"). O job assíncrono que junta isso
> com Haiku pra virar texto (item 4.5 do plano) continua de fora.
> **Atualização: revisão da A0 concluída, serviço de substituição entregue
> (versão de curto prazo).** Os 82 movimentos extraídos do HTML foram
> revisados um a um contra a sugestão de `classify_public_workout_movements`
> (nenhum erro real — 2 casos de fronteira aceitos e documentados: o
> catálogo não tem categoria própria para eles) e promovidos
> `pending → active`, em dev e produção; mais 2 dos 6 movimentos criados
> pela migração da Onda A2 (`abducao-com-caneleira-3-angulos`,
> `prancha-com-toque-no-ombro`) também foram classificados. Os outros 4
> (protocolos de cardio + a vaga livre do rafael) ficam `pending` de
> propósito — não são exercícios de padrão único. Catálogo final: 128
> `active` / 4 `pending` de 132. `public_workouts/substitutions.py::suggest_substitutes`
> sugere só entre `active` do mesmo `movement_pattern`, sem diferenciar
> equipamento (curto prazo, decisão abaixo) — `S2`/`build_student_package`
> **não foi tocado** nesta entrega: é contrato congelado (D.5), então a
> forma como "UI de troca de exercício" vai consumir isto (endpoint novo
> vs. popular `substitutions` de S2) fica pra quem construir essa tela.
> Serviço de avaliação (US Navy/JP7) já existia desde antes desta Onda —
> `public_workouts/formulas.py`.
>
> **Decisão do Renan sobre a substituição (registrada antes do serviço existir,
> pra não se perder):** o critério de "mesmo `movement_pattern`" sozinho não
> é suficiente a médio/longo prazo. Quando falta o equipamento específico
> de uma sugestão (ex.: sugeriu uma máquina que a academia do aluno não
> tem), trocar por OUTRA máquina do mesmo padrão tem a mesma chance de não
> existir na academia dele. Um exercício **livre** (peso livre/peso
> corporal) do mesmo padrão resolve ~90% desses casos, porque equipamento
> livre é quase universal — academia que não tem hack squat quase sempre
> tem barra e anilha pro agachamento livre.
> - **Curto prazo (quando o serviço for construído):** pode sugerir por
>   `movement_pattern` sem diferenciar por equipamento, incluindo
>   máquina→máquina. Não é a versão final, é a versão que desbloqueia o
>   recurso.
> - **Médio/longo prazo:** a sugestão PRINCIPAL de substituição deveria
>   priorizar uma alternativa livre do mesmo padrão (quando existir uma
>   classificada), não só "qualquer outra do padrão" — resolve o caso mais
>   comum de "não tenho esse equipamento" sem o aluno precisar tentar
>   várias sugestões. Isso implica, quando o serviço for desenhado,
>   alguma forma de marcar/consultar "é exercício livre" por movimento
>   (hoje `PublicWorkoutMovement` não distingue isso — é decisão de schema
>   pra quando essa onda começar, não antes).
> - Ferramenta de apoio à revisão: `PublicWorkoutMovementAdmin` (Django
>   admin) — lista os 82 pendentes com `movement_pattern` sugerido editável
>   inline, link direto pro MuscleWiki pra conferir, e ação em lote pra
>   promover `pending` → `active` depois de revisado.
>
> **Atualização (coluna "Frente B (telas)"):** o gráfico SVG (padrão de
> `assessments.js`) e a aba de histórico de programas já existiam, sem
> rota ainda, em `templates/public_workouts/workout.html` (fundação
> adiantada da Onda B3). Esta sessão conectou os dois pontos que faltavam
> entre o que a Frente A já tinha entregue e o que a tela mostrava:
> `one_rep_max_by_movement` (S2) e `trends_by_movement`
> (`build_weekly_review`) agora aparecem como badge de 1RM estimado +
> sinal de platô/queda/evolução ao lado de cada mini-gráfico
> (`public_workouts/templatetags/public_workouts_extras.py::dict_get`,
> necessário porque o template não indexa dict por chave variável). O
> gráfico também ganhou o marcador de troca de versão de programa (linha
> tracejada + ponto diferenciado onde `program_id` muda entre duas cargas
> consecutivas) — fecha o item 2 do "Pronto quando" abaixo. Continua tudo
> **sem rota real** — mesma fundação adiantada, mesma regra: nenhum dos
> 10 templates legados nem os golden tests mudam uma linha.
>
> **Atualização (formulário de autoavaliação + rota de PDF, esta sessão):**
> os dois itens que faltavam na tabela acima — o formulário HTML da
> autoavaliação online e a rota de download do PDF — foram fechados, **ao
> contrário do gráfico SVG acima**, direto no caminho que já serve tráfego
> real: os templates legados (`bruno.html` etc.), não o `workout.html`
> fundação. Isso funcionou porque a aba "Avaliações" desses templates já
> era 100% injetada em runtime por `assessments.js` (só o botão `<button>`
> da aba é golden-tested; o conteúdo do painel nunca foi) — dá pra estender
> sem tocar em nenhum golden.
> - `PublicWorkoutDownloadPdfView` (`GET /renan/<slug>/treino.pdf`) usa o
>   mesmo tier de auth B0 (cookie de posse) da própria página/`avaliacoes.json`
>   — baixar em PDF o que a tela já mostra não é operação de conta. 404
>   quando `get_active_program` devolve `None`, que é o caso dos 10 slugs
>   reais **hoje** (Onda A2 não migrou os programas ainda) — o botão
>   "Baixar PDF" já está visível no `.top-bar` de produção mesmo assim,
>   consistente com o resto da Onda B4 (a Onda A2 preenche o dado depois,
>   o mecanismo já existe antes).
> - Achado colateral corrigido nesta sessão: **nenhum template deste
>   corredor chamava `{% csrf_token %}`**, e nenhuma view chamava
>   `get_token()` — o cookie CSRF nunca nascia numa visita normal a
>   `/renan/<slug>`, o que quebraria em 403 qualquer POST feito por JS
>   (a autoavaliação nova incluída) num navegador de verdade. Corrigido
>   com uma chamada a `django.middleware.csrf.get_token()` em
>   `PublicWorkoutDetailView.get()`, com teste de regressão.
> - O formulário (`assessments.js`) manda `POST /renan/<slug>/avaliacoes`
>   (exige sessão B1 — 401 sem login) e, no sucesso, refaz o fetch de
>   `avaliacoes.json` pra o aluno ver a própria avaliação nova na hora
>   (silhueta/timeline/gráfico), sem recarregar a página. Verificado de
>   ponta a ponta num Chromium real via Playwright (preenchimento, POST,
>   refresh do relatório, download do PDF) — não só pela suíte pytest.
> - ~~Gap conhecido: `/treinos/login` não aceita `?next=`~~ — **fechado
>   na sessão seguinte.** `PublicWorkoutLoginView` e `request_login_token`
>   agora carregam `next_url` pelos 3 saltos do fluxo (querystring do GET
>   inicial → campo hidden do formulário de e-mail → dentro do link do
>   e-mail, porque o clique pode acontecer num dispositivo diferente de
>   onde o login foi pedido → querystring do GET com `?token=`) e
>   redirecionam pra lá depois do login, em vez de cair na página
>   genérica de confirmação. `_safe_public_workout_next` só aceita path
>   exato de `/renan/<slug>` — não usa `url_has_allowed_host_and_scheme`
>   do Django (que aceitaria qualquer path do mesmo host) de propósito:
>   único destino legítimo é o próprio treino, então restringir ao padrão
>   elimina qualquer superfície de redirecionamento aberto por
>   construção. `assessments.js` já manda `/treinos/login?next=/renan/<slug>`
>   no 401 da autoavaliação.
>
> **Atualização (dobras cutâneas online, terceira entrega desta mesma
> sessão):** a autoavaliação online ganhou um segundo método além do US
> Navy — Jackson-Pollock 7 pontos — mas **gated**, não livre. Decisão do
> Renan (perguntada explicitamente porque contradizia a decisão anterior
> "treinador só presencial coloca as medidas de dobra"): o aluno só vê a
> seção de dobras depois que `has_presencial_skinfold_assessment` confirma
> que o **treinador** já lançou pelo menos 1 avaliação por dobra deste
> plano presencialmente (via `add_public_workout_assessment`) — só confia
> na técnica do aluno pinçando a dobra sozinho depois de ele já ter sido
> calibrado ao vivo. `build_report` expõe isso como
> `skinfold_self_report_unlocked` (bool), revalidado no servidor a cada
> POST — o flag do JSON é só pra tela decidir se MOSTRA a seção, nunca
> autorização de verdade. `body_fat_percent`/`body_fat_source` continuam
> nunca vindo direto do aluno: ele manda `age` + as 7 dobras em mm
> (mesmos nomes do `--dobra-*` do management command), o servidor calcula
> via `estimate_body_fat_jackson_pollock_7site` na hora da escrita (não em
> tempo de leitura como o Navy, porque idade não é persistida em lugar
> nenhum — mesmo padrão do `--age` do comando). Raw folds também não são
> persistidos como dado estruturado, só endereçados numa nota de texto
> (`"Dobras (mm): ..."`) — mesmo padrão que o comando já usava, zero
> mudança de schema. Verificado de ponta a ponta num Chromium real:
> seção escondida enquanto bloqueado, aparece sozinha depois do comando
> presencial rodar (sem reload manual — só na próxima vez que
> avaliacoes.json é buscado), calcula e salva corretamente, idade fica
> lembrada em localStorage entre visitas (evita perguntar de novo, sem
> precisar de coluna nova no banco).
>
> **Atualização (fundação visual "topbar + bottom nav", pedido explícito do
> Renan de aproximar o layout do corredor do app do aluno de box):**
> **exceção documentada a D.4** — Renan autorizou explicitamente a Frente A
> editar `templates/public_workouts/workout.html` + CSS/JS deste app
> (normalmente arquivos da Frente B), depois de revisar o app do aluno de
> box junto com ela. `workout.html` (fundação da Onda B3, ainda sem
> URL/view) ganhou 5 telas de nível superior por bottom nav — **Início,
> Avaliação, Treino, Cargas, Perfil** — REIMPLEMENTADAS do zero (nunca
> importando template/CSS do `student_app`, mesma regra D.00/D.3 de sempre;
> só os tokens `--theme-*` já usados no resto do arquivo são compartilhados):
> - **Início**: topbar com saudação por horário + primeiro nome
>   (`public_workouts_extras.py::workout_greeting`, duplicado deliberado —
>   nem 10 linhas — de `student_shell.student_greeting`, nunca importado
>   entre apps) e avatar com iniciais (fundação pronta pra foto depois, sem
>   campo novo — usa `PublicWorkoutPlan.short_name` já existente, `PublicWorkoutAccount`
>   não guarda nome). Card de resumo do programa é **texto determinístico**
>   (`public_workouts/dashboard.py::build_program_summary`) — decisão do
>   Renan: sem chamada de IA nesta entrega (custo de API e cache ficam pra
>   quando o resumo por Haiku for desenhado de verdade), contrato estável
>   (`headline`/`body`) pra Haiku substituir só o corpo depois. "Sua semana"
>   (`build_week_overview`) usa `day_id` como abreviação real do dia (o
>   parser da Onda A2 já gera seg/ter/qua/...) — sincroniza sozinho, sem
>   pedir input do treinador; "dia completo" olha só se existe
>   `PublicWorkoutLoadLog` na data real daquele dia da semana corrente.
> - **Avaliação**: leitura de `build_report` (S1, já existia) — resumo de
>   peso/indicadores. Não inclui o formulário de lançamento (isso continua
>   sendo `assessments.js` nos templates legados) — fica de fora desta
>   entrega de propósito.
> - **Treino**: mesmos sub-tabs de dia de sempre, movimentos viraram cards
>   estilo WOD do app do aluno (`.student-wod-movement-card`) em vez de
>   tabela — mesmo dado (`reps_spec`/`rir_spec`/`load_type`/`is_tracked`),
>   só troca de marcação/CSS. `load_tracker.js` não mudou uma linha (já era
>   por atributo, não por estrutura de tabela).
> - **Cargas** e **Perfil**: o antigo painel único "Histórico" virou dois —
>   Cargas ficou com a evolução de carga, Perfil com as versões do programa
>   **+ Pagamentos** (link pro `start_customer_portal_session`, Onda B2)
>   **+ Tema** (reusa `static/js/core/shell.js`, script genérico já
>   existente no repo — não é o `student_app/theme.js`, que se autodesliga
>   fora do app do aluno via `data-student-app`).
> - Troca de aba agora acontece em **dois níveis independentes** (painéis
>   de topo + sub-abas de dia dentro de Treino) sem um nível derrubar o
>   outro — script generalizado pra escopar "quem fica destacado" ao nav
>   mais próximo (`closest('[data-workout-tab-nav]')`) e "qual painel
>   aparece" ao container do painel-alvo, reusando o mesmo mecanismo CSS de
>   `interactive-tabs.css` (por filho direto) que já existia.
> - Verificado num Chromium real (servidor Django real + preview isolado
>   pros assets estáticos): as 5 telas, troca de tema, troca de dia dentro
>   de Treino sem perder o destaque de "Treino" no bottom nav, mobile
>   (375px). Continua **sem URL/view real** — mesmo estágio de fundação do
>   resto do arquivo; `student_name`/`assessment_report`/`customer_portal_url`
>   são contexto opcional até uma view de verdade alimentá-los.

> **Atualização (segunda rodada de refinamento visual, pedido explícito do
> Renan após ver a fundação acima — mesma exceção a D.4 já concedida):**
> - **Início**: ícone de chama SVG + trilho de dias gamificado — dia
>   prescrito é `<button>` clicável que pula direto pra Treino no dia certo
>   (`data-workout-jump-panel`/`-jump-day`, mecanismo próprio que só simula
>   `.click()` nos botões reais, nunca duplica o estado `is-active`).
> - **Avaliação**: painel deixou de ser reimplementação própria — passou a
>   **reaproveitar `assessments.js`/`assessments.css` inalterados** (mesmo
>   script/CSS já validado nos 10 templates legados: silhueta SVG, gauges de
>   RCQ/%gordura com bola+gradiente, gráfico de peso, timeline, formulário).
>   `mountPanel()` ganhou suporte a montar em `#workout-panel-avaliacao`
>   (elemento novo) sem tocar o caminho legado (`.tabs`/`#tab-avaliacoes`).
>   IMC/RCQ/%gordura ganharam **delta desde a 1ª avaliação** (seta ▲/▼),
>   estendendo `_build_indicators` (não é um dos 3 contratos congelados
>   S1/S2/S3 — `build_report` pode crescer aditivamente).
> - **Treino**: card de movimento rastreado agora é clicável (`role="button"`,
>   Enter/Espaço) e alterna o widget "registrar carga hoje" (some por padrão,
>   `hidden`). Termos de jargão de treino (RIR, AMRAP, Feeder, Top, Prep —
>   conferidos contra os 10 payloads reais publicados, não adivinhados) viram
>   uma "bolinha" clicável com definição (`glossary_highlight`,
>   `public_workouts_extras.py`), popover `position:fixed` posicionado por
>   `getBoundingClientRect()` (os cards têm `overflow:hidden` pro
>   decor-topstripe — `position:absolute` cortaria o popover).
> - **2 bugs reais achados e corrigidos nesta verificação** (não eram
>   ambíguos — reproduzidos e resolvidos):
>   1. **Alinhamento "comendo o topo" em Cargas/Perfil**: `.workout-block-card`
>      tinha `padding: 0` (pensado só pra tabela de versões, que compensava
>      com padding próprio) + a regra que restaurava padding pros outros
>      cards do antigo painel único "Histórico" (`.workout-history-panel
>      .student-card`) ficou órfã quando esse painel virou Cargas + Perfil
>      separados — nunca foi migrada. Início nunca teve o bug porque usa
>      `.workout-summary-card`, não `.workout-block-card`.
>   2. **Contraste ilegível no tema escuro** (tabela "Versões do programa" +
>      linhas "Pagamentos"/"Tema" em Perfil): `body { color: var(--ink) }`
>      (`tokens.css`) e `td { color: var(--ink) }`/`th { color:
>      var(--legacy-copy-strong) }` (`components/tables.css`) usam aliases
>      "legacy compatibility" resolvidos **uma única vez em `:root`** — CSS
>      custom property herda o VALOR JÁ RESOLVIDO, não a referência, então
>      `--ink` fica travado no tom claro mesmo com `body[data-theme="dark"]`
>      ativo (que só redeclara `--theme-text-primary`, nunca `--ink`) — mesmo
>      bug já documentado em `static/css/access/overview.css` pra outro
>      componente. Resto do template escapa do bug porque usa
>      `--theme-text-*`/`--brand` **direto** (`.student-card h2`, `--brand`
>      via `[data-accent-variant]`, `.workout-movement-copy span`), nunca via
>      alias. Corrigido local (`workout-shell.css`), sem tocar `tokens.css`
>      nem `components/tables.css` (compartilhados, usados por outras telas
>      que não têm esse problema por outro motivo).
> - **Achado, não corrigido (fora de escopo desta rodada)**: o formulário de
>   avaliação (`assessments.js`/`.assess-*`) mantém fundo **branco fixo** no
>   tema escuro — texto continua legível (contraste OK), é só inconsistência
>   visual, não o bug de legibilidade acima. Esse CSS é compartilhado com os
>   10 templates legados em produção — precisa de decisão explícita antes de
>   mexer (blast radius maior que os dois bugs acima).
> - Suíte completa (275 testes) verde após o lote; verificado num Chromium
>   real nos dois temas, incluindo o popover de jargão e os deltas de
>   indicador com dados reais da franciele.

> **Atualização (terceira rodada — Treino "simples demais" + Perfil igual
> ao app dos alunos, pedido explícito do Renan com screenshot de
> referência):**
> - **Achado real, não ambiguidade**: o parser da Onda A2 nunca perdeu a
>   quebra Prep/Feeder/Top/AMRAP — `reps_spec` já guarda o texto verbatim do
>   `gym-reps` legado (ex. `"2-3× Prep → 1× Feeder → 3× Top (6-8)"`,
>   conferido no payload publicado de verdade do bruno). O que sumiu foi
>   só a APRESENTAÇÃO: a fundação B3 original espremia tudo numa linha só
>   de 0.8rem. `reps_phases` (`public_workouts_extras.py`) quebra o texto
>   em "→" e o template desenha um chip colorido por fase (reutiliza as
>   bolinhas de `glossary_highlight` já validadas) — sem tocar
>   parser/schema/dado publicado. `rir_spec` (nota do Top) vira uma linha
>   logo abaixo. `reps_spec` sem "→" continua na linha simples de sempre.
> - **Perfil**: reestruturado pra bater com o Perfil do app do aluno
>   (screenshot de referência do Renan) — cabeçalho avatar grande + nome
>   completo + e-mail, card "Conta" (Dados pessoais/Pagamentos/Tema), card
>   "Versões do programa" no lugar de "Trocar de box"/"Solicitar
>   congelamento"/"Entrar com convite" (conceitos de aluno-de-box sem
>   equivalente no corredor solo — confirmado com o Renan via pergunta
>   direta antes de implementar). "Sair da conta" ganhou view nova
>   (`PublicWorkoutSignOutView`, `POST /renan/<slug>/sair`) que apaga o
>   cookie de posse B0 — o corredor não tem login de sessão ainda (fases
>   B/C), então isto é fundação visual/funcional pronta pra quando essa
>   fase ligar, não uma barreira de acesso de verdade hoje (quem reabrir
>   `/renan/<slug>` recebe o cookie de volta automaticamente).
> - Mais 1 ponto do MESMO bug de alias `--ink` congelado (ver rodada
>   anterior): `.workout-profile-row` usava `color: inherit`, puxando o
>   `body` stale no tema escuro — o valor à direita da linha (e-mail em
>   "Dados pessoais") ficava ilegível. Trocado por `--theme-text-primary`
>   direto, mesmo padrão já aplicado no resto do arquivo.
> - **Investigado, NÃO implementado ainda (fatia separada, dado real em
>   produção)**: "o treino de cardio sumiu" é real pra 8 dos 10 clientes —
>   o parser só extrai blocos `.ex`; blocos de aquecimento/cardio no
>   formato `.c-card`/`.stage-title` ("Etapa 1 - Mobilidade", "Etapa 3 -
>   Cardio") nunca foram capturados. Achado importante: `.c-card` é o MESMO
>   componente usado pra plano alimentar (só no rafael) — confirmado que os
>   cards de refeição ficam estruturalmente FORA de qualquer `.session`,
>   então escopar a extração a "`.c-card` dentro de `.session`" evita
>   ingerir dieta como se fosse exercício, sem precisar inspecionar texto
>   de `.stage-title`. Fica pra uma fatia própria (parser + testes +
>   dry-run comparado contra os 10 HTMLs antes de publicar de verdade,
>   mesmo processo da migração original da Onda A2) — extensão de contrato
>   já "congelado" com republicação de dado real de cliente pagante merece
>   revisão isolada, não misturada com o resto deste lote (puramente
>   visual, sem tocar payload).

> **Nota (go-to-market, 2026-09-17):** a "fatia própria" do plano alimentar citada acima
> deixou de ter um bloqueio de dono — a esposa do Renan é nutricionista com CRN ativo e
> vai assumir essa frente. O trabalho técnico descrito acima (parser + testes + dry-run)
> continua não dimensionado e não iniciado; o que mudou é que agora existe profissional
> habilitada para decidir o conteúdo, então essa fatia pode ser escopada em uma onda
> própria quando fizer sentido, sem o impeditivo legal que valia antes. Ver
> [public-workouts-go-to-market-plan.md](public-workouts-go-to-market-plan.md) §R1 e §6.

> **Atualização (quarta rodada — espaçamento, seletor de dia do Treino
> igual ao "Sua semana", registro de carga em todo exercício, 2 bugs de
> alinhamento):**
> - Espaçamento mais generoso no trilho "Sua semana" (Início, 6px→9px) e na
>   lista de exercícios do Treino (10px→14px) — pedido direto do Renan.
> - Seletor de dia do Treino (`.workout-day-tab`) trocou o formato antigo
>   (rótulo único, ex. "Segunda - Pernas Quadríceps") pelo MESMO padrão
>   "dia curto + palavra-chave" do card de "Sua semana", lado a lado —
>   referência visual enviada pelo Renan. `day_short_label`/`day_keyword`
>   (`dashboard.py`) derivam os dois pedaços: o dia curto vem de `day_id`
>   (nunca de `day.label`, que é texto livre do treinador); a palavra-chave
>   remove o prefixo "<Dia da semana><separador>" de `day.label` SÓ quando
>   ele bate com o nome completo do dia — checado contra os 10 payloads
>   reais, que usam 3 formatos diferentes (hífen "-", travessão "—", ou
>   nenhum prefixo — juliana/henrique já são só a palavra-chave).
> - Registrar carga deixou de exigir `is_tracked`: `record_load`
>   (`services.py`, já existia) nunca validou esse campo — é puramente um
>   sinal de curadoria do treinador (badge "rastreado"), nunca um portão de
>   acesso. O que parecia "só o primeiro exercício registra" era simplesmente
>   o fato de raramente haver mais de 1 `is_tracked=True` por dia nos dados
>   reais — confirmado ao vivo com milene/thaislima (únicos 2 casos de 2
>   rastreados no mesmo dia) que o toggle já funcionava independente por
>   card; a mudança real foi abrir o clique pra QUALQUER exercício.
> - **2 bugs de alinhamento achados e corrigidos**:
>   1. Ícone de tema (Perfil) flutuava no meio da linha em vez de colado à
>      direita — `.theme-toggle-icon` (`design-system/topbar.css`) é
>      `width:100%;height:100%` pensado pra um botão circular pequeno
>      (`.theme-toggle` do topbar), não pra uma linha inteira
>      (`.workout-profile-row`). Override local com tamanho fixo (20px).
>   2. Fundo branco fixo no tema escuro (Avaliação) — `assessments.css` usa
>      `--white`/`--dark`/`--border`/`--muted` com fallback fixo (nunca
>      tiveram valor de tema: `_base.html` legado só define
>      `--accent`/`--accent-bg`/`--accent-dark` por plano, cor de marca, não
>      claro/escuro). Redeclarados sob `body[data-theme="dark"]` dentro do
>      próprio `assessments.css` — inerte nas 10 páginas legadas (nunca têm
>      toggle de tema pra ativar esse seletor), então sem risco de regressão
>      lá.
> - Suíte completa (406 testes, `public_workouts` + `student_app`) verde;
>   verificado num Chromium real nos dois temas, incluindo o clique em
>   exercício não-rastreado abrindo o widget de carga.

> **Atualização (Cardio + Periodização, pedido explícito do Renan com
> referência em `juliana.html`) — extensão aditiva do contrato congelado
> (schema.py), acordo direto com o Renan nesta sessão:**
> - **Schema**: duas chaves opcionais de nível superior, `cardio` e
>   `periodization` — ausentes = cliente sem essas abas no HTML legado
>   (a maioria dos programas já publicados antes desta fatia). Nenhum campo
>   existente muda de forma; `validate_payload` só valida o conteúdo
>   quando a chave está presente.
> - **Parser** (`parse_cardio_tab`/`parse_periodization_tab`,
>   `public_workouts/parser.py`): dois extratores NOVOS e ISOLADOS do
>   parser de dia/exercício já congelado (`_ProgramHTMLParser` não foi
>   tocado — zero risco de regressão no que já está em produção). Cobrem
>   só o formato de **aba dedicada** (`<div id="tab-cardio">`/`<div
>   id="tab-period">`, presente em bruno/juliana/henrique/johnespanha/
>   thaislima para cardio, e em 8 dos 10 clientes para periodização) —
>   **decisão explícita do Renan**: não tenta unificar com o cardio
>   embutido por dia da franciele (`.c-card`/`.stage-title` "Etapa N") nem
>   com o protocolo HIIT da milene (`.hiit-card`), formatos grandes demais
>   pra unificar nesta fatia. O gráfico de periodização vem de um
>   `<script type="application/json" id="period-chart-data">` já pronto no
>   HTML legado (mesmo dado que `app.js::buildChart` já usava no cliente) —
>   extraído por regex direto, sem precisar de parsing de árvore.
> - **Achado importante que reduziu risco**: `.c-card` (cardio embutido) é
>   o MESMO componente usado pro plano alimentar da rafael — confirmado que
>   os cards de refeição ficam estruturalmente FORA de qualquer `.session`,
>   então não haveria colisão mesmo se a fatia futura de cardio embutido
>   fosse implementada.
> - **UI**: pedido explícito do Renan — o botão "Treino" do bottom nav virou
>   um **ciclo de 1 slot só** (Treino → Cardio → Periodização → Treino a
>   cada toque), em vez de 3 botões fixos (a nav não tem espaço pros 5 de
>   sempre + 2 novos). Cardio/Periodização saem do ciclo quando o payload
>   não tem esse dado (`data-cycle-targets` filtrado pelo template). Ícone e
>   rótulo do botão trocam junto (`bonequinho correndo` pra Cardio, barras
>   ascendentes pra Periodização) — chegar de OUTRO botão da nav sempre
>   reseta pro estado Treino; só avança no ciclo quando o próprio botão já
>   está ativo. O atalho de "dia da semana" do Início (que pulava direto
>   pra Treino) foi ajustado pra resetar o ciclo em vez de simular clique
>   (que só avançaria se o ciclo já estivesse em Cardio/Periodização).
> - Gráfico do mesociclo renderizado no SERVIDOR (Django template, cores/
>   altura já vêm prontas do payload) em vez do `buildChart()` client-side
>   do `app.js` legado — mesmo dado, sem duplicar lógica de montagem de DOM
>   em JS.
> - Suíte completa (434 testes) verde; verificado num Chromium real nos
>   dois temas com dado real re-parseado da juliana (não publicado ainda —
>   ver "Pendente" abaixo), incluindo o ciclo completo Treino→Cardio→
>   Periodização→Treino e o reset via atalho de dia da semana.
> - **Pendente, fora deste lote**: republicar de verdade (`migrate_legacy_workouts`
>   sem `--dry-run`) os clientes reais afetados — decisão de tocar dado
>   publicado de cliente pagante fica pra confirmação explícita separada,
>   mesmo processo da migração original da Onda A2.

> **Atualização (nome em português + exercício alternativo, achado real do
> Renan revisando o Treino):**
> - **Nomes em inglês**: `ex.name` (nome em português escrito pelo
>   treinador, ex. "Cadeira extensora") **sempre foi capturado** pelo
>   parser — só nunca foi guardado no payload pra exibição, apenas usado
>   como fallback de slug quando não há `wiki-btn`. O template sempre
>   mostrou `movement_slug` humanizado (ex. `machine-leg-extension` →
>   "Machine leg extension", em inglês) em vez do nome real. Corrigido
>   aditivamente: `movement.name` no payload (`parser.py`), consumido via
>   novo filtro `movement_display_name` (`public_workouts_extras.py`) que
>   prefere `name` e cai pro slug humanizado só quando ausente — movimento
>   publicado antes desta fatia continua funcionando sem quebrar.
> - **Exercício alternativo**: `.ex-var`/`.var-link` (sugestão de variação
>   do treinador, ex. "Supino com halteres" pro Supino com barra) nunca
>   tinha sido capturado. Achado real ao migrar: bruno.html tem um caso
>   com **2** variações no mesmo `.ex-var` (agachamento livre sugerindo
>   hack squat E leg press) — schema modela `variations` como lista, nunca
>   um campo único. Exibido como linha discreta "Variação: `<link>`" logo
>   abaixo do nome do movimento (`.workout-movement-variation`), sem
>   competir visualmente com o nome principal.
> - Suíte completa (339 testes) verde; verificado num Chromium real (dois
>   temas) com dado real re-parseado da juliana — nomes em português e
>   variação exibidos corretamente. Mesmo estágio de "aditivo, não
>   republicado ainda" do restante desta seção.

> **Atualização (variação oculta por padrão, pedido explícito do Renan):**
> A linha "Variação: `<link>`" virou um toggle — colapsada por padrão
> (`data-workout-variation`, `hidden`), um gatilho "Ver variação" revela ao
> clicar (`data-workout-variation-toggle`), mesmo padrão de clique-expande
> já usado no registro de carga (item anterior desta mesma onda B3).
> Disponível em todo exercício com variação, sem depender de nenhuma outra
> flag — mesmo espírito do registro de carga não depender de `is_tracked`.
> Handler do card (`data-workout-load-toggle`) ganhou mais uma exclusão de
> clique/teclado pro toggle de variação não abrir o widget de carga junto.
> Suíte (341 testes) verde; verificado num Chromium real.

> **Atualização (rota de preview do template único, achado do Renan —
> "não to conseguindo ver no preview"):**
> Toda a verificação visual desta onda B3 dependia de eu gerar HTML na mão
> via `manage.py shell` + salvar num arquivo `static/tmp_workout_previewN.html`
> que eu mesmo apagava no fim de cada sessão — se o Renan tentasse abrir
> depois, dava 404 (parecia bug, mas era o arquivo temporário já limpo).
> Criada `GET /renan/<slug>/preview-b3` (`PublicWorkoutTemplatePreviewView`)
> — renderiza `workout.html` contra o payload JÁ PUBLICADO do slug (mesmo
> `get_active_program`/`list_program_versions` de sempre), **só responde
> com `settings.DEBUG=True`** (404 em produção, nunca serve tráfego de
> aluno de verdade, nunca precisa do cookie de posse B0). URL permanente —
> não depende mais de nenhum passo manual meu pra conferir o trabalho.
> 5 testes novos (404 fora de DEBUG mesmo publicado, 200 com conteúdo
> esperado, 404 sem publicação, 404 slug desconhecido, dispensa cookie).
> Suíte completa (457 testes, `public_workouts` + `student_app`) verde;
> `manage.py check` sem problemas.

> **Atualização (terceira colisão de nome PT-BR entre duas sessões — desta
> vez reconciliada por UNIÃO, não por descarte):**
> Depois das duas rodadas anteriores (legenda de série e widget de carga,
> ambas resolvidas descartando a versão mais fraca), o main avançou de
> novo com uma TERCEIRA solução paralela pro mesmo problema de nome PT-BR
> do exercício — desta vez via `movement.name` aditivo direto no payload
> (`schema.py`, escrito pelo parser da Frente A) + filtro
> `movement_display_name`. Diferente das duas rodadas anteriores, as duas
> soluções resolvem problemas DIFERENTES, não competem: `movement.name` é
> o dado mais fresco (a versão do payload que o parser já reprocessou),
> enquanto o catálogo `PublicWorkoutMovement` (`movement_labels`, Onda A0)
> é a cobertura retroativa dos programas publicados ANTES dessa fatia do
> parser — os 10 legados de produção, hoje. Unidas num filtro só,
> `movement_name(movement, movement_labels)`: prioriza `movement.name`,
> senão cai pro catálogo, senão humaniza o slug. `movement_display_name`
> (só cobria os 2 primeiros casos) foi removido — nada mais chamava.
> **Risco de débito técnico anotado, não resolvido nesta sessão**: a
> chamada do filtro (`movement|movement_name:movement_labels`) exige
> `movement_labels` no contexto do template — Django levanta
> `VariableDoesNotExist` (erro 500, não degradação silenciosa) quando o
> ARGUMENTO de um filtro referencia uma chave ausente do contexto, ao
> contrário do valor filtrado em si. Hoje as duas views que renderizam
> `workout.html` (`PublicWorkoutPreviewView` e `PublicWorkoutTemplatePreviewView`,
> a `/preview-b3` documentada acima) passam essa chave — se uma TERCEIRA
> view futura esquecer, quebra com 500 em vez de exibir o slug humanizado.
> Vale um valor padrão centralizado (context processor ou wrapper de view)
> se aparecer mais uma view renderizando este template.
> Também achado nesta reconciliação: a queixa do Renan ("não to
> conseguindo ver no preview", que motivou a criação da `/preview-b3`
> acima) pode ter sido o gate de posse da MINHA `/preview` — se ele abriu
> `/renan/<slug>/preview` sem estar "logado" como dono daquele slug
> (mesmo cookie de sessão do B0 que a rota real exige), a resposta é 404,
> igual a "não aparece nada". Não confirmado com o Renan ainda — vale
> perguntar antes de consolidar as duas rotas de preview em uma só.
> 627 testes verdes (+ os que vieram do main); `manage.py check` sem
> problemas.
> **Atualização (parser cobre `.c-card` embutido por dia — franciele/
> rafael, achado do Renan: "treino da franciele está incompleto... e o
> cardio não aparece"):**
> `_CardioTabParser` já documentava a lacuna de propósito ("não o cardio
> embutido por dia de franciele/milene, formato diferente demais pra
> unificar nesta fatia") — esta é essa fatia. franciele.html/rafael.html
> não têm aba `#tab-cardio` dedicada: cada dia embute "Etapa 1 -
> Mobilidade/Ativação/Coordenação" (rótulo varia, nunca um vocabulário
> fechado) e, em alguns dias, "Etapa 3 - Cardio", cada uma com seu próprio
> `.c-card`. Novo `_EmbeddedStageParser` (`public_workouts/parser.py`)
> escaneia `.c-card` DENTRO de cada `.session` — nunca interfere com
> `_CardioTabParser` (que só olha fora de `.session`, `#tab-cardio`).
> Classificação é **estrutural**, não por texto de rótulo (rafael.html não
> tem `.stage-title` nenhum, o card de cardio vem solto após os `.ex`):
> todo `.c-card` de cardio observado tem `.c-head` (título+badge); todo
> card de mobilidade é só uma lista de `.c-row`, sem `.c-head`. Mobilidade
> vira movimentos leves (sem wiki-btn, slug pela DESCRIÇÃO da linha, nunca
> pelo `.c-lbl` — o mesmo label se repete no mesmo dia com descrições
> diferentes) prependados ao bloco de Força; cardio vira `cardio.sessions`
> (dedup por igualdade exata — franciele repete o mesmo card em 3 dias).
> franciele: 29→49 movimentos (fixture de contagem atualizada
> intencionalmente) + 1 sessão de cardio; rafael: sem mudança na Força
> (cardio nunca tinha sido capturado nem incorretamente, era só ignorado) +
> 4 sessões de cardio novas. 16 testes novos (`test_parser.py`); suíte
> completa (473 testes) verde; `manage.py check` sem problemas.
> **Pendente:** republicar de verdade em produção via o workflow manual
> `publish-legacy-workouts.yml` (PR #253) — só afeta franciele/rafael
> localmente até isso rodar.

> **Atualização (2 achados ao auditar os 10 clientes contra o pedido do
> Renan "corrija de todos os treinos... sem explicação de dias"):**
> 1. O cardio embutido por dia deduplicado (franciele repete o mesmo card
>    em 3 dias) tinha perdido a explicação de EM QUAIS dias ele vale.
>    `_EmbeddedStageParser.cardio_sessions()` agora agrupa por identidade
>    de conteúdo e injeta um detail `"Dias"` na frente (`"Terça, Quinta e
>    Sexta"`) com os dias reais mesclados — novo `dashboard.day_full_label`
>    reaproveitado, não duplicado.
> 2. Auditoria dos 10 revelou giovanna.html: usa a MESMA marcação
>    (`.c-card`+`.c-head`) tanto pra cardio real (sábado, "Corrida 4-5 km")
>    quanto pra notas de orientação do dia de CrossFit ("Orientação do
>    dia", "Regra prática", "Estratégia" — NENHUMA é cardio) nos outros
>    dias. `.c-head` sozinho não bastava. Novo `_looks_like_cardio_title`
>    exige que o TÍTULO nomeie uma modalidade de cardio reconhecida (o
>    treinador sempre precisa dizer o quê fazer pra prescrever cardio) —
>    card com `.c-head` que não bate é descartado por completo (nem
>    cardio, nem exercício — não existe campo pra "nota de orientação").
>    giovanna: 4→1 sessões de cardio (as 3 erradas removidas).
> Auditados os 10 clientes um a um (`build_program_payload_from_html`
> direto contra cada HTML real) — nenhum outro tinha esse tipo de gap.
> 8 testes novos; suíte completa (477 testes) verde; `manage.py check`
> sem problemas.

> **Atualização (Periodização canônica — semana em destaque + carga
> sugerida, implementado):** o plano de periodização canônica ficou pronto
> como documento numa sessão anterior; esta implementou de verdade,
> **com uma correção crítica encontrada ao reanalisar antes de codar**:
>
> A proposta original de "Caminho 3" (fase canônica ativa) recalculava
> `kg = %RM_da_fase × 1RM_estimado` do zero a cada semana. Cruzando contra
> o próprio dado real da Juliana (`vnote`: *"a carga é o que progride
> semana a semana"*; `weeks_table`: incrementos pequenos e relativos —
> "+2,5 kg vs. Semana 1", nunca um número novo desconectado), essa
> premissa quebrava: produziria saltos bruscos entre fases (Volume 67% →
> Intensidade 85% seria +27% relativo numa semana só) desconectados do que
> o aluno realmente levantou — uma sugestão errada e potencialmente
> perigosa. Correção: `periodization.suggest_progressive_load_kg` ancora
> na ÚLTIMA carga REAL registrada nesse movimento dentro do PROGRAMA ATUAL
> (`program_id` bate), escalada pela razão entre o %RM-meio da fase de
> agora e o %RM-meio da fase de quando aquela carga foi registrada — nunca
> recalcula do zero. O 1RM estimado (quando existe) só limita um TETO de
> segurança (nunca deixa a razão sugerir acima do %RM máximo da fase
> atual), protegendo contra um log anômalo se propagando pra sempre.
>
> Entregue: `public_workouts/periodization.py` (`PHASE_PROFILES` — 6 fases,
> %RM/RIR/reps com fonte real NSCA/Prilepin/Bompa/Helms —,
> `current_week_number`/`current_phase_profile` com `today` injetável,
> `build_chart_points_from_weeks`, `suggest_progressive_load_kg`);
> `periodization.weeks` no schema (aditivo, `chart`/`weeks_table` viram
> opcionais só quando `weeks` está presente); `load_suggestion.py`
> (Caminho 4 — estimativa pontual a partir do reps/RIR do PRÓPRIO
> exercício quando não há fase canônica ou não há âncora ainda, nunca
> "chuta" de texto ambíguo); `estimate_working_weight_kg` (inverso de
> `estimate_one_rep_max`) em `one_rep_max.py`; cascata de 5 níveis em
> `movement_load_display` (fixed_kg → percentage_of_rm+1RM → fase
> progressiva → estimativa por texto → "Registre sua carga..."); destaque
> visual da semana atual no gráfico + banner de fase na aba Treino; comando
> `upgrade_periodization_model` (Juliana republicada localmente com as 6
> fases). 62 testes novos; suíte completa (564 testes) verde; `manage.py
> check` sem problemas. Verificado num Chromium real contra o dado
> publicado de verdade da Juliana — inclusive o teto de segurança
> funcionando (razão pura sugeria 80kg partindo de uma carga real de 80kg
> na mesma fase, mas o teto de 62% RM da Adaptação limitou a sugestão
> final a 67,5kg) — e confirmado ZERO mudança visual pro Bruno (não
> migrado).
>
> **Pendente:** curar `periodization.weeks` pras outras 9 clientes (uma de
> cada vez, decisão manual — ver `CURATED_WEEKS_MAPPING` em
> `upgrade_periodization_model.py`); aplicar `sets_multiplier` na UI
> (fundação já pronta, só não ligada ainda — ver docstring do módulo).

> **Atualização (ramp de Prep/Feeder em kg, pedido explícito do Renan — "A
> Ramp, e a sincronia com a periodização dessas cargas"):** as bolinhas de
> glossário de Prep/Feeder (`reps_phases`, chips do exercício) ganharam o
> peso sugerido pra CADA série de aquecimento, não só um número único pro
> Top set. Percentuais com fonte real (BarBend/StrongFirst): Prep ~40-55%
> do peso do Top, Feeder ~60-80% — citação chave: *"once you reach 50-60%
> of your working set weight, the rest of your ramp-up sets should be
> 10-15% increases per set"* e *"any set at or above ~85-90% counts as a
> working set"* (por isso o Feeder nunca pode chegar lá). Estágios com mais
> de 1 série (ex.: "2×Prep") interpolam linearmente do piso ao teto da
> faixa — 1 série só usa o meio da faixa. Top e Max (AMRAP após o Top) usam
> a própria carga do Top (Max é o mesmo peso, não uma fração nova — prática
> padrão de "quantas reps saem nesse peso").
>
> **Sincronia com a periodização é automática por construção, não por
> código extra**: o ramp escala a partir do `top_weight_kg` que
> `movement_load_display` já resolveu pra ESTA semana (fase progressiva
> quando existe, senão %RM explícito ou estimativa por texto — a mesma
> cascata de 5 níveis da atualização acima). Se o Top muda de semana pra
> semana, o ramp muda junto sozinho — não existe um segundo cálculo de
> progressão paralelo. Deliberadamente um módulo novo e separado
> (`public_workouts/warmup_ramp.py`), não uma extensão de
> `periodization.PHASE_PROFILES`: são dois conceitos de "fase" já
> distintos no código — estágio por EXERCÍCIO (Prep/Feeder/Top/Max) vs.
> fase do MESOCICLO (Adaptação/Volume/.../Deload) — e confundi-los
> quebraria a leitura de quem mexer no código depois.
>
> Entregue: `warmup_ramp.py` (`extract_leading_set_count`,
> `stage_ramp_kg`, arredondado pro múltiplo de 2,5kg); `glossary_highlight`
> e `reps_phases` estendidos (`public_workouts_extras.py`) pra aceitar o
> `top_weight_kg` já resolvido e injetar "Peso sugerido: X kg → Y kg." na
> descrição do balão certo (nunca no balão errado); reordenação do
> `movement_load_display` em `workout.html` pra rodar ANTES do bloco que
> desenha os chips (precisa do `load.value_kg` pronto). 16 testes novos em
> `test_warmup_ramp.py` + 11 novos em `test_workout_template.py`; suíte
> completa (592 testes + 110 subtestes) verde; `manage.py check` sem
> problemas. Verificado num Chromium real contra o dado publicado de
> verdade da Juliana com 1RM/histórico simulados: Prep (2 séries, Top a
> 67,5kg) mostrou "27,5 kg → 37,5 kg", Feeder (1 série) mostrou "47,5 kg" —
> batendo com o cálculo manual (faixas 40-55%/60-80% sobre 67,5kg).
>
> **Achado e correção no meio do caminho:** este trabalho descobriu (e
> corrigiu, PR separada) uma regressão real introduzida pela própria
> atualização de periodização acima — o hint "Registre sua carga..."
> tinha sido inserido entre `</article>` e `.workout-load-input`, e o JS
> de toggle acha o widget via `card.nextElementSibling` (não
> `querySelector`), então o clique parou de reabrir o registro de carga
> pra qualquer exercício sem 1RM ainda (o caso mais comum). Corrigido
> nesta mesma fatia (o hint volta a morar dentro de
> `.workout-movement-load`) com um teste de regressão dedicado
> (`test_load_input_widget_is_always_the_immediate_next_sibling_of_the_card`).
>
> **Pendente:** Cargas continua só comparação/histórico (confirmado com o
> Renan — "a gente usar a aba cargas apenas para comparar a evolução"),
> nenhuma entrada de dado nova lá.

> **Atualização (auditoria dos 10 clientes — pedido do Renan: "faça
> exatamente esse template em todos os treinos e todos deixe em português
> o nome dos exercícios" + "algumas coisas da aba cardio e periodização
> regrediram"):** cruzando o payload JÁ PUBLICADO de cada um dos 10
> clientes contra o que o parser ATUAL produziria a partir do mesmo HTML
> legado, achei que **7 dos 10 nunca tinham sido republicados** desde que
> `name` (nome em português) e a extração de `cardio` embutido foram
> adicionados ao parser em fatias anteriores — não é regressão de código,
> é publicação que ficou pra trás:
>
> - henrique/john/johnespanha/juliana/milene/thaislima: `name` ausente em
>   100% dos movimentos (caía no fallback de slug humanizado em inglês,
>   ex. "Machine hack squat" em vez de "Hack Squat na máquina" —
>   inclusive a PRÓPRIA Juliana, usada como prova de conceito da
>   periodização canônica, estava nesse estado).
> - henrique/john/johnespanha/juliana/thaislima: `cardio` inteiro ausente
>   do payload (aba Cardio publicada vazia), apesar do HTML ter conteúdo
>   real prescrito.
> - rafael: `cardio` presente mas sem o detail "Dias" (a fatia que
>   corrigiu isso, PR #254, nunca foi republicada pro Rafael
>   especificamente, só bruno/franciele/giovanna).
> - henrique/john/thaislima: `started_on`/`weeks` desatualizados —
>   ficaram numa versão anterior a `feat(public-workouts): preenche
>   started_on real dos 10 clientes via git log`.
>
> Além da staleness, achei **2 bugs reais no parser** ao investigar por que
> milene continuava sem cardio mesmo depois de republicar:
>
> 1. `milene.html` usa um dialeto de cardio 100% próprio
>    (`.hiit-card`/`.hiit-head`/`.hiit-row`/`.hiit-note`, protocolo de
>    HIIT na esteira) que `_EmbeddedStageParser` nunca reconhecia —
>    nenhuma condição de classe batia, então o card inteiro (incluindo a
>    justificativa fisiológica escrita pelo treinador sobre GH em
>    atletas 44 anos) ficava invisível. Corrigido tratando `.hiit-*` como
>    ALIAS estrutural de `.c-*` (mesma forma: card→head+badge→linhas
>    label/valor→nota), não um parser novo.
> 2. `thaislima.html` usa `.int-badge`/`.hiit-badge` em vez de
>    `.km-badge` em 2 das suas 3 sessões de `#tab-cardio` — como
>    `_CardioTabParser` só reconhecia a classe `km-badge` pra fechar a
>    captura do título e abrir a do badge, o texto do badge ficava
>    GRUDADO no título ("🟡 Dia Médio Quinta · 20 min" numa string só, em
>    vez de título "🟡 Dia Médio" + badge "Quinta · 20 min" separados).
>    Mesmo fix de generalização de classe (`_CARD_BADGE_CLASSES`),
>    aplicado nos DOIS parsers (`_CardioTabParser` e
>    `_EmbeddedStageParser`, já que ambos tinham a mesma checagem estreita
>    copiada).
>
> **Fora de escopo desta fatia, documentado como achado (não corrigido):**
> `thaislima.html` tem um card `.muay-card`/`.muay-body` (dia de Muay
> Thai) com uma prescrição real de cardio bike opcional escrita em prosa
> livre dentro do corpo do texto, não em linhas label/valor estruturadas.
> Extrair isso exigiria parsear prosa (mesmo risco documentado alhures
> neste plano — "chutar dado é pior que não extrair") — nenhum exercício é
> perdido (não é um `.ex`), só uma nota de contexto fica de fora do
> payload estruturado.
>
> Corrigido: os 2 bugs de parser acima + republicação real dos 7 clientes
> defasados (`migrate_legacy_workouts`, sem mudar nenhuma decisão de
> negócio em `LEGACY_PROGRAM_METADATA`) + reaplicação de
> `periodization.weeks` da Juliana via `upgrade_periodization_model`
> (republicar por HTML sempre perde essa curadoria manual, que só existe
> no payload já publicado — não vem do HTML). Novo workflow
> `.github/workflows/upgrade-periodization-model.yml` (mesmo padrão
> auditável e `dry_run`-por-padrão de `publish-legacy-workouts.yml`) pra
> nunca mais depender de SSH manual nesse passo. Resultado: os 10 clientes
> têm 100% dos movimentos com nome em português, e a aba Cardio mostra
> conteúdo real pra todo mundo que tem cardio prescrito no HTML de
> origem. Testes novos em `test_parser.py` (badge alternativo +
> dialeto `.hiit-card`); suíte completa + `manage.py check` verificados
> antes da publicação real.

> **Atualização (periodização canônica pras outras clientes, pedido do
> Renan — "pegue todos os treinos e corrija a periodização igual ou
> semelhante a juliana com o gráfico etc"):** li o `weeks_table` real
> (foco + diretriz de carga + nota do treinador) das 9 clientes restantes
> pra decidir, caso a caso, se a progressão de mesociclo delas é
> compatível com os 6 `phase_type` fechados — a mesma regra de leitura
> humana já usada pra Juliana, nunca correspondência automática por
> palavra-chave.
>
> **3 entraram no mapeamento curado** (`CURATED_WEEKS_MAPPING`):
> - `henrique`: Adaptação→Volume→Intensidade→Pico→**Pico Máximo**→Deload.
>   "Pico Máximo" repete `peak` de propósito — a própria diretriz diz
>   "carga mais alta em todas as séries do ramp", um 2º degrau do MESMO
>   pico, não uma fase nova.
> - `milene`: Adaptação→Volume→Força-Hipertrofia→**Volume Alto**→Peak→
>   Deload. "Volume Alto" repete `volume` pelo mesmo motivo (mesmo eixo,
>   guidance "Bomba e estresse metabólico").
> - `john`: Carga base→**Progressão×3**→Pico→Deload. As 3 semanas de
>   "Progressão" têm o MESMO rótulo no HTML mas incrementos crescentes
>   reais (+2,5kg/+5kg/+7,5kg vs. a mesma semana-base) — mapeadas pra 3
>   fases DIFERENTES e crescentes (volume→força-hiper→intensidade) pra
>   preservar essa progressão na sugestão de carga. Achatar as 3 na mesma
>   fase congelaria a sugestão (razão 1.0), contradizendo o texto real.
>
> **4 ficaram de fora, de propósito — não é trabalho pendente, é conteúdo
> que genuinamente não é periodização de força por %RM:**
> - `giovanna`: vocabulário de CrossFit ("Base técnica"/"Sobrecarga"/
>   **"Metabólico"**/"Peak controlado") — a semana de condicionamento
>   metabólico/AMRAP não tem %RM-alvo real; forçar um `phase_type`
>   baseado em %RM daria sugestão de carga ERRADA justo nessa semana.
> - `bruno`: bloco de CORTE (`vnote` real: *"a meta não é progredir carga
>   — é segurar a carga enquanto o peso corporal cai"*) — "Manutenção"
>   (×3 semanas) e "Teste" não existem no vocabulário fechado hoje.
>   Migrar exigiria **propor phase_type novo ao Renan primeiro** (mesma
>   regra já escrita no plano original: se o objetivo não encaixa em
>   nenhuma chave existente, é sinal de crescer `PHASE_PROFILES`, não de
>   inventar correspondência). Fica pendente de decisão explícita.
> - `franciele`: `weeks_table` é uma progressão de CORRIDA (caminhada →
>   trote → corrida contínua), não periodização de força — %RM/RIR não
>   se aplica.
> - `rafael`: confirmado que NÃO é um parser bug — `#tab-period` dele
>   descreve o RITMO SEMANAL de treino (Dia A/Descanso/Dia B/Coringa
>   condicional), conteúdo genuinamente diferente de fases de mesociclo.
>
> `johnespanha`/`thaislima` continuam sem periodização — nunca tiveram
> `#tab-period` no HTML original, não é regressão nem pendência.
>
> Entregue: `CURATED_WEEKS_MAPPING` estendido (henrique/john/milene, com
> comentário explicando cada decisão de repetição/divergência de rótulo);
> docstring do comando atualizada explicando por que os outros 4 ficam de
> fora; 1 teste novo (`test_newly_curated_slugs_publish_a_schema_valid_canonical_mapping`).
> Suíte completa (595 testes + 110 subtestes) verde; `manage.py check`
> sem problemas. Verificado num Chromium real: henrique mostra "S4 ·
> agora" no gráfico com Pico/Pico Máximo lado a lado e o banner "Semana 4
> de 6 · Pico · alvo 1-3 reps · RIR 0,0 · ~94% RM" na aba Treino.
>
> **Pendente (na época):** decisão do Renan sobre propor `phase_type`
> novo(s) pro bloco de corte do bruno antes de migrá-lo — resolvido, ver
> "Atualização (variação irmã + phase_type novo pro corte do Bruno)"
> mais abaixo. giovanna/franciele/rafael continuam no `chart`/
> `weeks_table` livre indefinidamente (conteúdo não compatível com o
> modelo, não uma migração adiada).

> **Atualização (fechamento do template único — testes de regressão +
> auditoria de QA, pedido do Renan: "o template é basicamente esse, vamos
> fechar com testes... faça um teste de QA pra ver bugs, vulnerabilidades
> e etc"):**
>
> **Gap de teste real encontrado e fechado**: `test_workout_template.py`
> só usava `build_example_payload()`/fixtures sintéticas; `test_migrate_
> legacy_workouts.py` validava o payload dos 10 clientes reais contra o
> SCHEMA mas nunca renderizava esse payload pelo template — um filtro
> (`reps_phases`, `movement_load_display`, `glossary_highlight`) que só
> quebrasse contra um formato de texto real e específico passaria batido
> nos dois. Novo `test_workout_template_real_clients.py`: renderiza o
> payload REAL (parseado do HTML de verdade) dos 10 clientes pelo
> template inteiro — com e sem 1RM/histórico de carga simulados — e,
> pros 4 clientes com periodização canônica curada (henrique/john/
> juliana/milene), injeta o `CURATED_WEEKS_MAPPING` real antes de
> renderizar, exercitando banner de fase + gráfico + ramp de Prep/Feeder
> contra texto de verdade. 4 testes novos, 24 subtestes.
>
> **Vulnerabilidade real encontrada e corrigida**: `reference_url`
> (movimento e variação) vira `href="{{ }}"` direto em `workout.html` —
> o auto-escape do Django escapa caracteres HTML especiais mas NUNCA
> valida o esquema da URL. Um valor `javascript:alert(1)` passaria
> batido pro atributo e executaria ao clicar no link do exercício.
> **Hoje não é explorável**: `reference_url` só vem do HTML legado
> versionado no repo (parser.py) ou de edição via `PublicWorkoutMovementAdmin`
> (staff autenticado) — nunca de input de aluno/anônimo. Corrigido mesmo
> assim como barreira barata antes de qualquer fluxo futuro (edição
> self-service, sugestão de link pelo aluno) tornar isso alcançável por
> alguém não confiável: `schema.py::_is_safe_reference_url` exige
> esquema `http`/`https` (ou `None`), tanto no `movement.reference_url`
> quanto em `variations[].reference_url`. 5 testes novos.
>
> **Revisado e confirmado correto, sem mudança** (auditoria, não achado):
> auth do endpoint de registro de carga (`PublicWorkoutRecordLoadView`
> exige sessão de login + posse do slug, 401/404 nunca 403); assinatura
> de webhook do Stripe verificada antes de processar; CSRF via cookie em
> todo POST do corredor (`load_tracker.js`); `PublicWorkoutTemplatePreviewView`
> (`/preview-b3`) checa `settings.DEBUG` na PRIMEIRA linha do `get()`,
> 404 garantido em produção; `one_rep_max.py`/`load_suggestion.py`/
> `periodization.py`/`warmup_ramp.py` já tinham guarda contra divisão por
> zero e reps/RIR fora de faixa (nenhum bug de cálculo encontrado — os
> guard-rails escritos ao longo da sessão já cobriam isso).
>
> Suíte completa: 600 testes + 134 subtestes verde; `manage.py check`
> sem problemas.

> **Atualização (variação irmã + phase_type novo pro corte do Bruno,
> pedido do Renan em resposta ao mapa de pendências do CORDA — "vamos
> tomar essa frente. Atualize os planos"):**
>
> **Variação irmã (item 3 do "Pronto quando" acima, agora ✅):** novo
> filtro `sibling_variations` (`public_workouts_extras.py`) reusa
> `suggest_substitutes` tal e qual — nenhuma lógica nova, só a exibição
> que faltava. Na aba Cargas, cada gráfico de movimento ganha uma linha
> "Variação: <outros ativos do mesmo `movement_pattern`, linkados>"
> quando o catálogo tem irmã classificada — puramente informativo, nunca
> entra no cálculo de 1RM/tendência daquele `movement_slug` (que
> continua estritamente isolado por slug). Verificado num Chromium real
> contra dado publicado da Bruno: "Agachamento livre com barra" mostra
> "Variação: Agachamento goblet com halter, Agachamento sumô com
> halteres, Hack squat", todos linkados pro MuscleWiki certo.
>
> **`phase_type` novo pro bloco de corte do Bruno — `maintenance`/
> `test`:** ao desenhar os dois, apareceu um problema real que a
> primeira leitura não tinha capturado — `suggest_progressive_load_kg`
> ESCALA a carga pela razão de %RM entre fases, correto pras 6 fases
> originais (todas "suba a intensidade"), mas ERRADO pra uma fase cujo
> objetivo é EXPLICITAMENTE "não progredir carga, segurar a carga"
> (vnote real da Bruno). Escalar teria sugerido ~105kg partindo de 80kg
> ao entrar em Manutenção — o MESMO tipo de salto perigoso que o
> "achado crítico" original deste documento já tinha corrigido pras
> fases de progressão, só que na direção oposta.
>
> Correção: novo campo `PhaseProfile.hold_load` (default `False`,
> retrocompatível com as 6 fases existentes). Quando `True`,
> `suggest_progressive_load_kg` pula a escala por razão inteiramente e
> devolve a ÚLTIMA carga registrada tal e qual — nem precisa resolver a
> fase de quando aquele log foi feito (irrelevante pra "repete o último
> peso"). O %RM/reps/RIR da fase continuam servindo só pro banner
> informativo (fisiologicamente consistente, não uma inconsistência de
> dado: o mesmo peso absoluto vira % relativa mais alta com a
> capacidade de recuperação reduzida em déficit calórico).
>
> `maintenance` (67-80% RM, RIR 1,5, 6-10 reps — zona de
> força-hipertrofia de Prilepin/NSCA, batendo com o RIR 1-2 e a queda de
> reps 8-10→6-8 que a Bruno já tem escrito) e `test` (85-95% RM, RIR 0,
> 1-5 reps — zona de teste quase-máximo, pro AMRAP único de retenção da
> Semana 5) entram em `PHASE_PROFILES`, ambos com `hold_load=True` e
> `sets_multiplier` reduzido (consenso de manter intensidade e cortar
> volume em déficit calórico). `CURATED_WEEKS_MAPPING['bruno']`: S1
> Adaptação → S2-S4 Manutenção → S5 Teste → S6 Deload — mapa 1:1 com o
> `weeks_table` real dela, sem aproximação.
>
> Entregue: `periodization.py` (`hold_load` + 2 fases novas + branch
> dedicado em `suggest_progressive_load_kg`); `CURATED_WEEKS_MAPPING`
> estendido; `sibling_variations` + wiring em `workout.html`/CSS. 6
> testes novos de `hold_load` (`test_periodization.py`) + 2 de
> `sibling_variations` + 2 de render (`test_workout_template.py`) + 1 no
> comando (`test_upgrade_periodization_model.py`) + `bruno` promovido a
> `TestCase` em `test_workout_template_real_clients.py` (a nova
> `sibling_variations` consulta o banco, `SimpleTestCase` não permite
> mais). Suíte completa (616 testes + 135 subtestes) verde; `manage.py
> check` sem problemas. Verificado num Chromium real contra o payload
> publicado de verdade da Bruno (semana 3 real dela = Manutenção):
> banner mostra "Semana 3 de 6 · Manutenção · alvo 6-10 reps · RIR 1,5 ·
> ~74% RM", gráfico destaca "S3 · agora" com as 3 semanas de Manutenção
> lado a lado e Teste/Deload depois, e a carga sugerida do agachamento
> ficou EXATAMENTE nos 90kg do último registro simulado (não escalou),
> confirmando `hold_load` funcionando ponta a ponta.
>
> **Pendente:** publicar de verdade em produção (`upgrade_periodization_model
> --slug=bruno`) — aguardando deploy do código desta fatia primeiro,
> mesmo fluxo de confirmação explícita já usado pras publicações
> anteriores (dado de cliente pagante).

| Frente A (serviços) | Frente B (telas) |
|---|---|
| ✅ `estimate_one_rep_max` + faixas de confiança | ✅ gráfico SVG reusando o padrão de `assessments.js`, com 1RM e sinal de tendência |
| ✅ detecção de platô e queda de 1RM (v1, limiares ajustáveis) | ✅ aba de histórico de programas (online) |
| ✅ `build_weekly_review(...)` — sinais calculados, sem IA ainda | tela de revisão do editor *(depende do editor com IA, Onda A2 — Entrega 4.1 do plano)* |
| ✅ `suggest_substitutes` (`public_workouts/substitutions.py`) — sugestão por `movement_pattern`, só entre `active` | UI de troca de exercício — depende da linha ao lado |
| ✅ serviço de avaliação (US Navy / JP7) — já existia | ✅ endpoint de escrita (`POST .../avaliacoes`, PR #231) **+ formulário HTML** (`assessments.js`, esta sessão) |
| ✅ export de dados do titular — `export_account_data`, `GET /renan/<slug>/meus-dados.json` (JSON) | ✅ `render_program_pdf` (PR #232) **+ rota** `GET /renan/<slug>/treino.pdf` (`PublicWorkoutDownloadPdfView`, esta sessão) |

### Pronto quando
1. ✅ 1RM devolve `None` acima de 15 reps efetivas.
2. ✅ O gráfico mostra marcador de troca de programa no lugar certo.
3. ✅ Variação irmã aparece como referência, rotulada, sem entrar no
   cálculo — ver "Atualização" abaixo.
4. ✅ Review semanal recebe **sinais**, não tabela crua.

---

## Linha do tempo

```
                  Renan + Claude (A)          2o desenvolvedor (B)
                  ~13-18 dias                 ~25-35 dias

dia -2   🔴 B0 vazamentos -> main             (aguarda main limpa)
dia  0   ⇄ S0 contratos + schema  ......................  (os dois juntos)
         │
         └── cria feat/produtizacao-corredor da main corrigida
dia  1   A0 fundação de dados         ‖      B1 identidade e login
dia  4   A1 snapshot e publicação     ‖      B2 cobrança
dia  8   A2 parser + migração dos 10  ‖      B3 template, fase B, hard reset  ⇄
dia 16   A3 serviços de produto       ‖      B4 telas de produto
dia 24   (A concluída)                ‖      B5 escala
```

**Caminho crítico:** A1 → A2 → **B3**. É o único ponto em que B espera A — e a Frente A
foi dimensionada menor justamente para chegar em A2 antes de B precisar.

**A Frente B nunca fica ociosa:** B1 e B2 não dependem de nada da A, e somam 9 a 13 dias
antes do primeiro encontro.

## Regras de convivência

0. **Uma onda = uma branch = um PR contra a integração.** Nomes: `feat/pc-<onda>-<slug>`.
   Ver D.3b para a estratégia completa e a exceção da B0.
1. **Ninguém edita fora do seu diretório** (D.4). Precisou? Abre pedido, não edita.
2. **Migration só no app do dono.** `public_workouts`, `student_app`, `operations`
   são da A; `finance`, `student_identity` da B.
3. **Contratos S1/S2/S3 são congelados.** Mudança exige acordo escrito das duas
   frentes antes do código.
4. **Golden nunca é regravado sem diff aprovado** — vale para as duas frentes.
5. **Rebase diário.** As frentes tocam apps diferentes; conflito é sinal de que
   alguém saiu do seu diretório.
