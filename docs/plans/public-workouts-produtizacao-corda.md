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
| `test_public_workout_content_signature_is_stable` | `:2265` | compara assinatura do HTML com o golden — o template único muda o HTML; e assere `len(slugs) == 10` em `PUBLIC_WORKOUT_LIBRARY`, que deixa de existir | trocar a fonte dos slugs de dict para query em `PublishedWorkout`; **diff aprovado à mão antes de regravar** (R4) |
| `test_public_workout_manifest_is_dynamic_per_slug` | `:2069` | `theme_color` / `background_color` / `short_name` saem do dataclass `PublicWorkoutPlan` e passam a vir do banco | fixture de `PublishedWorkout` no `setUp` |
| `test_public_workout_page_renders_install_cta` | `:2118` | o install prompt sai do `_base.html` e da injeção legada para o template único | asserção pelo `id="public-workout-install"`, que é contrato, não pela classe CSS |
| `public_workouts/tests.py` — validação de slug | `:125` | `_validate_plan_slug` importa `PUBLIC_WORKOUT_LIBRARY` **de dentro da função** (para evitar import circular); a fonte passa a ser `PublishedWorkout` | testes de serviço criam fixture no banco em vez de depender do dict |

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

### Ordem de execução recomendada

1. **Antes de tocar código:** rodar a suíte inteira e **guardar a saída**. Sem baseline,
   não há como distinguir "eu quebrei" de "já estava quebrado".
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
   `PaymentNotice`, `sent_at` gravado no mesmo commit do resultado do envio. Nem antes
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
  ✓ evento de assinatura de ALUNO nao altera Box.status   (P5)
  ✓ evento de assinatura de BOX nao altera membership     (P5)
  ✓ evento sem discriminador e recusado, nao adivinhado

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

## D.3 Onde mexe / onde NÃO mexe (visão geral)

### Mexe

**Domínio de treino (Frente A)**
- `public_workouts/models.py` — `PublishedWorkout`, `StudentLoadLog`, `student_identity_id` em `PublicWorkoutAssessment`
- `public_workouts/services.py` — `get_active_program`, `publish_program`, `build_student_package`
- `public_workouts/formulas.py` — `estimate_one_rep_max` + `OneRepMaxEstimate`
- `public_workouts/migrations/` — **dono exclusivo**
- `public_workouts/schema.py` *(novo)* — JSON Schema do payload
- `public_workouts/parser.py` *(novo)* — HTML/texto → payload via Haiku
- `student_app/models.py` — `MovementLibrary`: `modality`, `movement_pattern`, `status`
- `student_app/management/commands/seed_movement_library.py` — vocabulário de musculação
- `student_app/management/commands/extract_movements_from_html.py` *(novo)*
- `operations/model_definitions.py` — `reps_spec`/`rir_spec` em `WorkoutTemplateMovement`

**Acesso, dinheiro e entrega (Frente B)**
- `student_app/views/public_workout_assessment_views.py` — fechar (A1)
- `student_app/views/public_workout_views.py` — ownership, render do snapshot, matar legado
- `templates/public_workouts/sw.js` — allowlist, estratégias, ETag
- `templates/public_workouts/workout.html` *(novo)* — template único sobre o DS
- `student_app/public_urls.py` — rotas novas
- `student_identity/` — provider de e-mail, tela `/treinos/login`, ownership
- `finance/` — `PaymentNotice`, `notify_payment_due`
- `integrations/stripe/auth.py`, `services.py`, `router.py` — seam de conta + roteador de aluno
- `config/settings/base.py`, `.env.example` — Google OAuth, cookie 30 d
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

## D.4 Divisão em duas frentes — propriedade de diretório

**A regra que impede colisão:** cada caminho tem **um dono**. Ninguém edita fora do
seu. Migration só nasce no diretório do dono.

| Caminho | Dono | Observação |
|---|---|---|
| `public_workouts/**` | **A** | inclui `migrations/` |
| `student_app/models.py` | **A** | só `MovementLibrary` |
| `student_app/management/commands/**` | **A** | seeds e extratores |
| `operations/model_definitions.py` | **A** | só `WorkoutTemplateMovement` |
| `student_app/views/**` | **B** | todas as views |
| `student_app/public_urls.py` | **B** | |
| `templates/public_workouts/**` | **B** | inclui `sw.js` |
| `static/js/public_workouts/**` | **B** | |
| `static/css/public_workouts/**` | **B** | a deletar na Onda B3 |
| `student_identity/**` | **B** | |
| `finance/**` | **B** | inclui `migrations/` |
| `integrations/stripe/**` | **B** | |
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

## B0 — 🔴 Vazamentos (1–2 dias) — **prioridade máxima, começa já**

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

## ‖ A0 — Fundação de dados (2–3 dias)

### O que fazer
1. `student_identity_id` nullable em `PublicWorkoutAssessment` + migration.
2. `MovementLibrary`: campos `modality` (`crossfit`/`strength`/`both`),
   `movement_pattern`, `status` (`active`/`pending`) + migration.
3. `extract_movements_from_html` — varre os 10 HTMLs, extrai os pares
   `(nome, musclewiki_url)` dos `<a class="wiki-btn">`, normaliza slugs.
4. Rodar o extrator e semear; o seed de CrossFit ganha `modality='crossfit'`.
5. `reps_spec` e `rir_spec` (CharField) em `WorkoutTemplateMovement` + migration.

### O que entra
- `public_workouts/models.py` + `migrations/`
- `student_app/models.py` + `migrations/`
- `student_app/management/commands/extract_movements_from_html.py` *(novo)*
- `student_app/management/commands/seed_movement_library.py`
- `operations/model_definitions.py` + `migrations/`

### O que NÃO entra
- `PublishedWorkout` ainda não (Onda A1)
- nenhuma view, nenhum template

### Pronto quando
1. `MovementLibrary` tem o vocabulário dos 10 treinos com `reference_url`.
2. `movement_pattern` preenchido para todo movimento com variação conhecida.
3. Migrations aplicam e revertem limpo em banco de teste.

---

## ‖ B1 — Config, seam e identidade (3–4 dias)

### O que fazer
1. Google OAuth ligado (`.env`), Apple Pay (domínio no dashboard Stripe).
2. `resolve_stripe_account(box)` substituindo `stripe.api_key` em escopo de módulo
   (`auth.py:16`, `services.py:18`) — chamada **por requisição**.
3. `STUDENT_APP_SESSION_COOKIE_AGE=2592000`.
4. `StudentConsentDocumentKind.HEALTH_DATA` cobrindo IA, transferência
   internacional e retenção de 12 meses.
5. Provider de login por e-mail estendendo `StudentAppInvitation` (token 15 min,
   uso único, rate limit por e-mail).
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
3. `grep` não acha `stripe.api_key` em escopo de módulo.
4. O blob de `localStorage` de um aluno real está no banco.

---

## ‖ A1 — Snapshot e publicação (3–4 dias)

### O que fazer
1. `PublishedWorkout` com `program_id`, `program_label`, `started_on`, `weeks`,
   `version`, `is_active`, `payload` + as duas constraints (única por
   `(program_id, version)`; **parcial** única por `slug` onde `is_active=True`).
2. `StudentLoadLog` indexado por `(student_identity_id, movement_slug, performed_on)`,
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

## ‖ A2 — Parser de IA + migração dos 10 (4–6 dias)

### O que fazer
1. `public_workouts/parser.py` — HTML → payload, molde de
   `wod_session_llm_parser.py` (timeout, fallback silencioso, validação de slug),
   com `output_config.format` no schema de S0.
2. Biblioteca inteira no system prompt **cacheado** (~2.250 tokens; `modality`
   como dica, nunca filtro).
3. Rodar nos 10 HTMLs; revisar payload por payload.
4. Extrair **~15 `WorkoutTemplate`** dos programas migrados.
5. Geração de programa novo (texto + anamnese) como **job assíncrono**, nunca
   request — timeout de 10 s não serve para mesociclo.

### O que entra
- `public_workouts/parser.py` *(novo)*
- `public_workouts/management/commands/migrate_legacy_workouts.py` *(novo)*
- `operations/` — criação de `WorkoutTemplate` a partir do payload

### O que NÃO entra
- 🔴 **regravar golden** — proibido nesta onda (R4)
- nenhuma alteração de template ou view

### Pronto quando
1. Os 10 programas existem como `PublishedWorkout` ativo.
2. Comparação contra o golden **versionado** não acusa perda de conteúdo.
3. ~15 templates reutilizáveis existem.
4. Teste trava o piso de 4.096 tokens do prompt cache.

---

## ‖ B2 — Cobrança (4–6 dias)

### O que fazer
1. `PaymentNotice` (`payment`, `offset_days`, `scheduled_for`, `sent_at`) com
   unique `(payment, offset_days)`; as 5 linhas nascem com o `Payment`, data já
   resolvida por `brazilian_holidays`.
2. `notify_payment_due(payment, offset_days)` — irmã de `notify_payment_confirmed`,
   mesma estrutura de 3 canais isolados.
3. Management command `drain_payment_notices` + **systemd timer**.
4. Assinatura recorrente aluno→box; roteador de webhook resolvendo
   `StudentBoxMembership` (molde: `router.py:306-419`).
5. Job `D+2 → SUSPENDED_FINANCIAL` e volta por `invoice.payment_succeeded`.
6. Stripe Customer Portal.

### O que entra
- `finance/models.py` + `migrations/`, `payment_notifications.py`
- `finance/management/commands/drain_payment_notices.py` *(novo)*
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
6. Evento de assinatura de aluno **não altera `Box.status`** — e vice-versa (P5).
7. Duplo POST em "assinar" cria **uma** subscription (P6).
8. `amount` fora de faixa é recusado **no serviço**, não só no form (P8).
9. Cartão recusado gera copy diferente de inadimplência.
10. Toda suspensão automática tem `log_audit_event` com motivo.

> Os cinco arquivos de teste de R.P são **critério de entrada** da onda, não de saída:
> escrever o teste que falha antes do código que o faz passar. Em cobrança, teste
> escrito depois tende a assertar o que o código faz, não o que deveria fazer.

---

## ⇄ B3 — Template único, fase B e hard reset (5–7 dias)

**Depende de A1 (S1/S2 reais) e de A2 (os 10 publicados).**

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

## ‖ A3 / B4 — Produto (paralelo, 7–10 dias)

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
dia  0   ⇄ S0 contratos
     1   B0 vazamentos 🔴      ‖  A0 fundação de dados
     4   B1 identidade         ‖  A1 snapshot
     8   B2 cobrança           ‖  A2 parser + migração
    14   ⇄ B3 template, fase B, hard reset   ‖  A3 serviços de produto
    21   B4 telas de produto   ‖  A3 continua
```

**Caminho crítico:** A1 → A2 → B3. A Frente B nunca fica ociosa porque B0, B1 e B2
não dependem da A.

## Regras de convivência

1. **Ninguém edita fora do seu diretório** (D.4). Precisou? Abre pedido, não edita.
2. **Migration só no app do dono.** `public_workouts`, `student_app`, `operations`
   são da A; `finance`, `student_identity` da B.
3. **Contratos S1/S2/S3 são congelados.** Mudança exige acordo escrito das duas
   frentes antes do código.
4. **Golden nunca é regravado sem diff aprovado** — vale para as duas frentes.
5. **Rebase diário.** As frentes tocam apps diferentes; conflito é sinal de que
   alguém saiu do seu diretório.
