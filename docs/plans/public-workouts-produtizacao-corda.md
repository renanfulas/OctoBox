# C.O.R.D.A. — Produtização do corredor de treinos (`/renan/`)

**Plano de produto (o "porquê"):** [public-workouts-produtizacao-plan.md](public-workouts-produtizacao-plan.md)
**Este documento:** execução técnica, dividida em duas frentes paralelas.

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
| Nenhuma view de `/renan/` toca TENANT_APPS | A1 | **R2** — o `conftest` força `schema_context`, então hoje o erro passa em CI e só quebra em produção. Sem esse teste, DA-1 não tem rede. |
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
20. `Nenhuma migration do corredor nasce fora de public_workouts/.`

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

**Migrations por app:** `public_workouts`, `student_app`, `operations` → **A**.
`finance`, `student_identity` → **B**. Nenhum app recebe migration de duas frentes.

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
def build_student_package(*, student_identity_id: int, slug: str) -> dict:
    """Última carga por movimento + 1RM + substituições + access_until.
    Sem HTTP, sem request."""
```

### S3 — Escrita de carga
```python
def record_load(*, student_identity_id: int, movement_slug: str,
                weight_kg, reps=None, rir=None, performed_on,
                program_id=None, week_in_program=None,
                idempotency_key: str) -> dict:
    """Idempotente por idempotency_key. Reenvio nunca duplica."""
```

**Enquanto A não entrega**, a Frente B programa contra um **stub** dessas três
funções, devolvendo payload de exemplo válido pelo schema. Isso desacopla as
frentes desde o dia 1.

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
- `public_workouts/services_stub.py` (temporário, deletado na Onda A2)

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
  Onda A2 já é dona de extrair os `WorkoutTemplate` reais via parser de IA.
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
- `integrations/stripe/auth.py`, `services.py`
- `student_identity/models.py` + `migrations/`, `views.py`, `urls.py`
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

### O que fazer
1. `PublicWorkoutProgram` com `program_id`, `program_label`, `started_on`, `weeks`,
   `version`, `is_active`, `payload` + as duas constraints (única por
   `(program_id, version)`; **parcial** única por `slug` onde `is_active=True`).
2. `PublicWorkoutLoadLog` indexado por `(student_identity_id, movement_slug, performed_on)`,
   com `reps`, `rir`, `program_id` e `week_in_program` como contexto.
3. `publish_program(...)` no tenant: lê `WeeklyWodPlan`/`WorkoutTemplate`, resolve
   `reference_url` por slug, valida contra o schema, grava no `public`, ativa.
4. Implementar S1, S2 e S3 de verdade; deletar o stub.
5. `record_load` idempotente por `idempotency_key`; validação de outlier contra a
   última carga do mesmo movimento.
6. Movimento desconhecido entra `pending` e **não bloqueia** a publicação.

### O que entra
- `public_workouts/models.py` + `migrations/`
- `public_workouts/services.py`
- `student_app/application/publish_workout.py` *(novo)*
- testes de fronteira tenant↔public

### O que NÃO entra
- parser de IA (Onda A2)
- qualquer template ou view

### Pronto quando
1. Publicar v2 e voltar para v1 é `UPDATE` de uma coluna.
2. O banco recusa duas versões ativas para o mesmo slug.
3. Teste de fronteira falha se alguma função tocar TENANT_APPS.
4. `record_load` reenviado com a mesma chave não duplica linha.

---

## ‖ A2 — Parser de IA + migração dos 10 (4–6 dias) — **Frente A · Renan + Claude**

### O que fazer
1. `public_workouts/parser.py` — HTML → payload, molde de
   `wod_session_llm_parser.py` (timeout, fallback silencioso, validação de slug),
   com `output_config.format` no schema de S0.
2. Biblioteca inteira no system prompt **cacheado** (~2.250 tokens; `modality`
   como dica, nunca filtro).
3. Rodar nos 10 HTMLs; revisar payload por payload.
4. Extrair **~15 `WorkoutTemplate`** dos programas migrados.
5. Geração de programa novo (texto + **os 7 campos da anamnese**, incluindo
   motivação e maior dificuldade) como **job assíncrono**, nunca
   request — timeout de 10 s não serve para mesociclo.

### O que entra
- `public_workouts/parser.py` *(novo)*
- `public_workouts/management/commands/migrate_legacy_workouts.py` *(novo)*
- `operations/` — criação de `WorkoutTemplate` a partir do payload

### O que NÃO entra
- 🔴 **regravar golden** — proibido nesta onda (R4)
- nenhuma alteração de template ou view

### Pronto quando
1. Os 10 programas existem como `PublicWorkoutProgram` ativo.
2. Comparação contra o golden **versionado** não acusa perda de conteúdo.
3. ~15 templates reutilizáveis existem.
4. Teste trava o piso de 4.096 tokens do prompt cache.

---

## ‖ B2 — Cobrança (4–6 dias) — **Frente B · 2º desenvolvedor**

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
6. Stripe Customer Portal.

### O que entra
- `public_workouts/models.py` — `PublicWorkoutSubscription`, `PublicWorkoutPaymentNotice` (**criados pela Frente A** a pedido da B; ver D.4)
- `public_workouts/notifications.py` *(novo)* — `notify_payment_due` (V4)
- `public_workouts/management/commands/drain_public_workout_notices.py` *(novo)*
- `integrations/stripe/router.py`, `services.py`
- `deploy/` — unit do systemd timer

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
> **Não está ligado a nenhuma URL/view** — os itens 3–9 (apagar os 8 CSS
> legados, matar o bootstrap de PWA antigo, fase B de acesso, `sw.js` novo,
> outbox, hard reset) continuam bloqueados em A1/A2 como o texto original já
> dizia, porque envolvem corte de produção real, não fundação visual.
> `card-decor-glow` ainda não está aplicado — o primitive não é
> accent-aware por padrão (`--neon-default-rgb` fixo), decisão de detalhe
> visual que fica pra quando a onda real começar.

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
1. Os 10 renderizam do banco com golden idêntico.
2. Aluno A logado abrindo slug de B recebe **404**.
3. Publicar v2 aparece no celular na próxima abertura com rede (device real).
4. Registro feito offline sobe sozinho e não duplica.
5. Nenhum aluno perdeu carga.

---

## ‖ A3 / B4 — Produto (paralelo, 7–10 dias) — **A: serviços · B: telas**

| Frente A (serviços) | Frente B (telas) |
|---|---|
| `estimate_one_rep_max` + faixas de confiança | gráfico SVG reusando o padrão de `assessments.js` |
| detecção de platô e queda de 1RM | aba de histórico de programas (online) |
| `build_weekly_review(...)` — sinais calculados | tela de revisão do editor |
| serviço de substituição por `movement_pattern` | UI de troca de exercício |
| serviço de avaliação (US Navy / JP7) | formulários sobre `forms.css` |
| export de dados do titular | PDF via `reportlab` |

### Pronto quando
1. 1RM devolve `None` acima de 15 reps efetivas.
2. O gráfico mostra marcador de troca de programa no lugar certo.
3. Variação irmã aparece como referência, rotulada, sem entrar no cálculo.
4. Review semanal recebe **sinais**, não tabela crua.

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
