# Produtização do corredor público de treinos (`/renan/`)

**Status:** proposta · **Data:** 2026-09-12 · **Dono:** Renan · **Revisão:** 6

**Vender isso (branding, oferta, preço, landing page):** [public-workouts-go-to-market-plan.md](public-workouts-go-to-market-plan.md)
**Construir a venda (Entrega 5 concretizada + Entrega 6 nutrição):** [public-workouts-escala-e-nutricao-corda.md](public-workouts-escala-e-nutricao-corda.md)

---

# SUMÁRIO EXECUTIVO

## O problema

O `/renan/` atende clientes de personal e consultoria online hoje, e os alunos
gostam — mas ele é feito à mão. Cada aluno é um arquivo HTML de 400 a 1.400
linhas onde o treino está escrito dentro do código. Trocar uma série na
quarta-feira exige editar arquivo e publicar. Aceitar um cliente novo custa um
dia de trabalho. A carga que o aluno registra mora no navegador dele e some se
trocar de celular. Não há login, não há cobrança, e não há como acompanhar se
ele treinou.

Além disso, **dois vazamentos de dado pessoal estão ativos agora** (A1 e A4).

## O que muda para o aluno

| Hoje | Depois |
|---|---|
| Abre o link e treina | Entra uma vez por mês; nos outros dias abre e treina igual |
| Anota carga; some se trocar de celular | Carga guardada na conta, com gráfico de evolução |
| Avaliação física por WhatsApp | Tira as medidas no app e vê o resultado na hora |
| Não sabe quando vence | Avisado 7 dias, 3 dias, 1 dia antes e no dia |
| "Minha academia não tem essa máquina" → WhatsApp | Troca por alternativa que você aprovou |
| Treino igual até o Renan reescrever | Review semanal com carga sugerida e sinal de deload |
| Seu peso e %gordura no celular de outros alunos | Só no seu |

## O que muda para o Renan

| Hoje | Depois |
|---|---|
| Escreve HTML e faz deploy | Dita o treino, a IA estrutura, você revisa e publica |
| Cada programa novo começa do zero | Biblioteca de templates: adapta um que já funciona em segundos |
| IA não sabe nada do aluno | Anamnese de 7 campos no prompt — incluindo motivação e maior dificuldade, que é o que faz o treino ser seguido |
| Cobra no WhatsApp, um por um | Consultoria cobra sozinha (R$ 89,90/mês); presencial por orçamento |
| Quem não pagou continua treinando | Acesso trava sozinho depois de 2 dias de carência |
| Não vê se o aluno treinou | Check-in, carga, RIR e evolução |
| Descobre por WhatsApp que o treino venceu | Fila: "estes 4 terminam o mesociclo esta semana" |
| Cada cliente novo custa um dia seu | Onboarding self-service: assina, responde, cai na fila |

## Escopo — seis entregas

| # | Entrega | O que ganha | Prazo |
|---|---|---|---|
| 0 | **Fundação + correção dos vazamentos** | Fecha dado pessoal exposto hoje. Destrava o resto. | 5–6 d |
| 1 | **Identidade e anamnese** | Aluno entra com a própria conta; você sabe objetivo, restrição, equipamento — e o que faz ele desistir | 5–7 d |
| 2 | **Cobrança automática + hard reset** | Assinatura, lembrete, trava e destrava sem você tocar | 4–6 d |
| 3 | **Treino vira dado + front reusado** | Monta programa sem escrever código; carga e check-in no banco; front composto dos primitives do app do aluno | 11–15 d |
| 4 | **Produto** | Editor com IA, avaliação, gráficos, substituição, review | 7–10 d |
| 5 | **Escala** | Onboarding, fila de revisão, painel, portabilidade, vídeo | 8–11 d |

**Total: 40–55 dias.**

> A Entrega 3 subiu de 8–11 para 12–16 dias: transcrever 10 arquivos de 400 a 1.400
> linhas para dado estruturado e conferir um a um contra os goldens tem você como
> gargalo, não a máquina. A estimativa anterior era otimista.

### Linha de corte

Se o tempo apertar, **0 + 1 + 2 + 3 (25–34 dias)** já entrega o essencial: os
vazamentos fecham, a cobrança roda sozinha e você para de escrever HTML. As
Entregas 4 e 5 são upside e podem ser financiadas pela receita que a 2 destrava.

> ⚠️ **Dois itens da Entrega 0 não podem esperar priorização** — ver A1 e A4.

## Custo em dinheiro

| Item | Custo |
|---|---|
| Apple Pay, login Google, WhatsApp (Evolution), push | R$ 0 |
| IA (Haiku + prompt cache) | centavos por treino gerado |
| Stripe | ~4% + taxa fixa no cartão; PIX bem mais barato |
| WhatsApp Cloud API oficial (se migrar — ver DI-1) | por conversa; só quando houver faturamento |
| Storage de vídeo (só Entrega 5) | único item com custo recorrente novo |

## O que fica de fora

- **Sign in with Apple** — US$ 99/ano. Sem faturamento que justifique. *Apple Pay
  não depende disso e entra agora.*
- **Stripe Connect / repasse de 10%** — não se constrói agora, mas a Entrega 0
  deixa o encaixe pronto.
- **Trocar Evolution API por outro gateway** — ver DI-1.
- **Agente de atendimento 24/7 (Hermes / supportfaqagent)** — escopo separado, ver DI-2.
- **Chat interno, gamificação, app nativo** — WhatsApp já resolve; badges são ruído
  para público adulto pagante; o PWA entrega.

## A decisão de sequência

**0 → 1 → 2 → 3 → 4 → 5.** Cobrança antes do treino novo, porque cobrança gera o
faturamento que paga o resto. Você já cobra esses alunos hoje, só que na mão.

---

# PLANO TÉCNICO

## O QUE JÁ EXISTE (e não está sendo usado no `/renan/`)

| Capacidade | Onde | Estado |
|---|---|---|
| Jackson-Pollock 3 e 7 dobras | `public_workouts/formulas.py:131,163` | Pronto |
| US Navy + IMC + RCQ | `public_workouts/formulas.py` | Pronto e em uso |
| Trava por inadimplência | `SUSPENDED_FINANCIAL` + `student_app/middleware/student_auth.py:122` | Pronto |
| Push VAPID | `student_identity/push_notifications.py` | Pronto (2 mensagens) |
| Stripe assinatura + webhooks + PIX async | `signup/services.py`, `integrations/stripe/` | Pronto (box→plataforma) |
| Cobrança de aluno com vencimento | `finance.Payment` | Pronto |
| WhatsApp outbound (Evolution API) | `integrations/whatsapp/` | Pronto, custo R$ 0 |
| Convite com token + entrega auditada | `StudentAppInvitation`, `StudentInvitationDelivery` | Pronto |
| Cookie de sessão do aluno (stateless, assinado) | `student_identity/infrastructure/session.py` | Pronto — 7 d hoje |
| Sign in with Apple / Google | `student_identity/oauth_providers.py:163` | Código pronto, desligado |
| IA estruturando treino (Haiku) | `operations/services/wod_session_llm_parser.py` | Pronto — é o molde |
| PAR-Q | `student_identity/parq_questions.py` | Pronto |
| Catálogo de movimentos com link | `student_app.MovementLibrary` | Pronto |
| Registro de carga com histórico e delta | `StudentExerciseMax` + `StudentExerciseMaxHistory` | Pronto |
| Prescrição estruturada | `WeeklyWodPlan → … → PlanMovement` | Pronto |
| Telemetria de aluno | `StudentAppActivity` | Pronto |
| Onboarding com wizard | `onboarding/`, `signup/` | Pronto |

**Login sem senha é a única peça que realmente não existe.**

---

## VARREDURA FRENTE A FRENTE — o que o OctoBox já resolveu

Auditoria sistemática de cada frente do produto contra o que já existe no repo.
✅ reuso direto · 🟡 base existe, falta adaptar · ❌ construir.

### Infraestrutura — quase toda pronta

| Frente | Status | Onde |
|---|---|---|
| Login social (Google/Apple) | ✅ | `oauth_providers.py:163` — só faltam credenciais |
| Token de uso único + entrega auditada | ✅ | `StudentAppInvitation`, `StudentInvitationDelivery` |
| Sessão longa stateless | ✅ | `infrastructure/session.py` — 30 d é **1 variável** |
| Aluno paga própria fatura | ✅ | `StudentPayInvoiceView` (DA-7) |
| Ownership de fatura | ✅ | `resolve_payable_student_invoice` |
| Rate limit financeiro | ✅ | `fintech_throttles.checkout_rate_limit_exceeded` |
| Trava por inadimplência | ✅ | `SUSPENDED_FINANCIAL` + `student_auth.py:122` |
| Regras de atraso | ✅ | `finance/overdue_metrics.py` |
| Notificação e-mail + push + WhatsApp | ✅ | `notify_payment_confirmed` — molde da régua |
| Push VAPID (cliente **e** servidor) | ✅ | `pwa.js` + `push_notifications.py` |
| WhatsApp outbound | ✅ | `integrations/whatsapp/` (Evolution) |
| E-mail transacional | ✅ | Resend + `signup.email_sender.send_html_email` |
| **Job agendado** | ✅ | **systemd timer + management command** — padrão já em uso (`run_due_async_job_retries`, timer noturno de lead import) |
| Job assíncrono em background | ✅ | `shared_support/background_jobs.py` |
| PWA: install, standalone, iOS | ✅ | `pwa.js` + `_pwa_activation.html` |
| Service worker com estratégias | ✅ | `templates/student_app/sw.js` |
| Design system + primitives de aluno | ✅ | 3.803 linhas (DA-5) |
| Auditoria + **scrubber de PII** | ✅ | `auditing/services.py`, `auditing/scrubber.py` |
| Geração de PDF | ✅ | `reportlab==4.4.1` + `reporting/infrastructure/http_exports.py` |

### Domínio de treino — mais pronto do que eu supunha

| Frente | Status | Onde |
|---|---|---|
| Prescrição estruturada | ✅ | `WeeklyWodPlan → DayPlan → PlanBlock → PlanMovement` |
| **Templates de programa** | ✅ | `WorkoutTemplate` + blocks + movements (DA-6) |
| **Gate de aprovação** | ✅ | `WorkoutApprovalPolicySetting` — 3 políticas por box |
| Prescrição por %RM | ✅ | `load_type='percentage_of_rm'` + `load_value` |
| **Calculadora de carga por %** | ✅ | `_rm_calculator.html` — chips 60/70/80/90% |
| Registro de RM + histórico com delta | ✅ | `StudentExerciseMax` + `StudentExerciseMaxHistory` |
| IA estruturando treino | ✅ | `wod_session_llm_parser.py` |
| Biblioteca de movimentos | 🟡 | existe, mas vocabulário é CrossFit (3.0) |
| Check-in e aderência semanal | ✅ | `_progress_strip.html` + `StudentAppActivity` + `Attendance` |

### Avaliação e visualização — o achado que eu não esperava

| Frente | Status | Onde |
|---|---|---|
| Fórmulas (US Navy, JP3, **JP7**, IMC, RCQ) | ✅ | `public_workouts/formulas.py` |
| **Gráfico de avaliação em SVG** | ✅ | `assessments.js` — **silhueta corporal com medidas ancoradas, labels com conectores anti-sobreposição, gauges, badges de classificação, delta visual** |
| Gráfico de barras | ✅ | `app.js buildChart()` — periodização |
| PAR-Q | ✅ | `parq_questions.py` |
| Consentimento versionado | ✅ | `StudentConsent` + `StudentConsentDocumentKind` |

> O gráfico da aba Avaliações é sofisticado — silhueta com conectores e empilhamento
> de rótulos é trabalho de dias. **O 4.4 não começa do zero:** o padrão de SVG inline,
> sem CDN, no contexto exato, já está resolvido. Falta aplicá-lo à série de carga.

### O que realmente falta construir

| Frente | Por quê não existe |
|---|---|
| **Snapshot publicado no schema public** | é o núcleo deste projeto (DA-1) |
| **Carga indexada por pessoa + movimento** | `StudentExerciseMax` é por RM e é TENANT; falta a série temporal cross-programa (DA-4) |
| **1RM estimado (Epley/Brzycki)** | `formulas.py` tem composição corporal, não força |
| **Anamnese física** | o `onboarding/` existente é comercial (leads), não anamnese |
| **Substituição de exercício pelo aluno** | nada equivalente no repo |
| **Review semanal por IA** | o parser existe; o analisador não |
| Assinatura recorrente aluno → box | a existente é box → plataforma |
| `PaymentNotice` + régua de datas | o disparo existe; o agendamento não |

### A leitura

**Praticamente todo o encanamento está pronto e em produção.** O que falta é o
**núcleo de domínio** deste produto — e isso é bom sinal: o trabalho restante é
pensar o produto, não reconstruir infraestrutura.

---

## O QUE JÁ ESTÁ QUEBRADO HOJE

### 🔴 A1 — Avaliação física é pública e o slug é o nome do aluno

`PublicWorkoutAssessmentsView` (`student_app/views/public_workout_assessment_views.py:24`)
**não tem autenticação**. Qualquer pessoa que abra `/renan/franciele/avaliacoes.json`
lê peso, percentual de gordura, circunferências e notas. Os slugs são os primeiros
nomes dos alunos — adivinhar é trivial.

Dado sensível de saúde (LGPD art. 5º, II) em URL pública. **Está no ar.** E a
Entrega 4, que deixa o aluno registrar as próprias medidas, multiplica o volume.

> Consentimento não resolve: autoriza você a *tratar* o dado, não a publicá-lo.

### 🔴 A4 — O celular de cada aluno guarda o peso e o %gordura de todos os outros

O service worker monta o `ALLOWLIST` com **todos** os slugs da biblioteca
(`sw.js:6-13`, alimentado por `plan_slugs = tuple(PUBLIC_WORKOUT_LIBRARY)`) e no
install faz `cache.add()` de cada um (`sw.js:38`).

E os HTMLs contêm dado pessoal no cabeçalho:

```html
<div class="stat"><div class="stat-l">Idade</div><div class="stat-v">27 anos</div></div>
<div class="stat"><div class="stat-l">Body fat</div><div class="stat-v">23,6%</div></div>
<div class="stat"><div class="stat-l">Peso</div><div class="stat-v">48,5 kg</div></div>
```

Resultado: **o celular da Giovanna tem o peso e o percentual de gordura do Bruno,
da Juliana, do Rafael — gravado em disco, offline, sem ela saber.** E vice-versa,
nos 10 dispositivos.

Alcance pior que o A1: não exige nem adivinhar URL. O dado já está no aparelho.

**Correção:** o precache passa a conter **apenas o slug do próprio aluno**,
resolvido em runtime, não a lista inteira renderizada no servidor.

### 🔴 A2 — O service worker serve treino velho depois de publicar

`sw.js:100-105` é **cache-first** para tudo sob `/renan/`: busca da rede, atualiza
o cache, mas **retorna o cacheado**. E a chave (`VERSION`) vem do **mtime dos
CSS/JS** — não muda quando o treino muda.

Você publica a v2 e o aluno continua vendo a v1. A Entrega 3 não funciona sem isto.

### 🔴 A3 — A trava financeira não alcança `/renan/`, e o offline a contorna

`student_auth.py` protege `/aluno/`; `/renan/` está em `PUBLIC_SCHEMA_PATHS` e
nunca passa pelo gate. E mesmo corrigindo a view, o PWA tem a página em cache —
aluno inadimplente em modo avião treina.

Aceite explicitamente: **a trava é de servidor, não de dispositivo.**

---

## DECISÃO ARQUITETURAL 1: prescrever no tenant, publicar snapshot no public

O `/renan/` roda **sem tenant**, no schema `public`. A prescrição e
`MovementLibrary` são **TENANT_APPS**. Essa é a fronteira.

| Opção | Problema |
|---|---|
| (a) Modelar treino de novo em `public_workouts` (SHARED) | **Segunda verdade** de prescrição. Com o 2º personal, treinos caem no mesmo namespace global. Capa o futuro. |
| (b) Mover `/renan/` para dentro do tenant | Exige login para tudo, de uma vez. |
| (c) **Prescrever no tenant, publicar snapshot imutável no public** | ✅ Escolhida |

```
[box do personal — schema tenant]        [schema public]
WeeklyWodPlan → DayPlan → PlanBlock          PublishedWorkout
  → PlanMovement                              - slug (congelado)
  + MovementLibrary (links)                   - box_id
         │                                    - version (imutável)
         │  publicar()                        - is_active  ← qual versão serve
         └──────────────────────────────────▶ - payload JSONB
                                                     │
                                       /renan/<slug> lê isto, sem tenant
```

**Por quê:** uma verdade só; versionamento de graça (o aluno no meio do mesociclo
não vê o treino mudar embaixo dele); rollback é `UPDATE` de uma coluna; nenhuma
query cross-schema; não capa o multi-personal; o padrão já existe no repo
(`SessionWorkout` é "snapshot de WOD"); offline de graça.

### Um schema, quatro usos

O JSON Schema do `payload` é escrito **uma vez** e serve para: (1)
`output_config.format` do Haiku — a API **garante** o formato; (2) validação antes
de gravar; (3) contrato do template único; (4) o que o service worker precacheia.

### O que o snapshot é — e o que não é

**É:** a prescrição congelada. **Não é:** estado do aluno.

Tudo que o aluno produz — carga, check-in, substituição — vive **fora** do
snapshot, referenciando `(slug, version, exercise_ref)`. Ver conflito D1.

---

## DECISÃO ARQUITETURAL 2: acesso em duas fases

> Esta seção resolve uma contradição das revisões anteriores. O sumário prometia
> "o hábito não muda" enquanto a trava financeira dependia de login. **Eram
> incompatíveis:** se a página é pública, o inadimplente abre igual — e qualquer
> um com o link treina de graça. O link *é* o produto.

| Fase | Entra em | Estado |
|---|---|---|
| **A** | Entrega 1 | Página **continua pública** + banner "crie seu acesso". Carga, avaliação e gráficos exigem login. **Ninguém bate em parede.** |
| **B** | Entrega 2, junto com a cobrança | Treino de **plano pago** exige login. Legados/cortesia: sua decisão, por flag no plano. |

**O "abre e treina" não morre — muda de forma.** Com o cookie de 30 dias (0.7),
depois do primeiro login o PWA abre direto por um mês. O aluno prova identidade
~12 vezes por ano; nos outros 353 dias a experiência é idêntica à de hoje.

**Quatro coisas que a fase B cobra e que só existem por causa dela:**

1. O precache do SW (A4) precisa rodar **depois** do login, não no install —
   senão grava a tela de login como se fosse o treino e o offline quebra.
2. O PWA já instalado tem a página em cache. Ligar a fase B exige **bump de
   `VERSION`** para invalidar, senão o aluno nem vê a tela de login.
3. `start_url` do manifest é `/renan/<slug>?source=pwa`. O redirect de login
   precisa voltar para ele, senão o ícone da tela inicial vira porta de entrada
   para uma tela de erro.
4. **Login não é autorização** — ver abaixo.

### Autenticado ≠ autorizado

Com a fase B, `/renan/juliana` exige login. Mas **estar logado não faz de você o
dono daquele slug**: sem checagem, o Bruno autentica e vê o treino da Juliana.
Trocaríamos "qualquer um com o link" por "qualquer aluno com o link" — melhor, e
ainda errado.

**Regra:** a view resolve a identidade da sessão, confirma que ela é dona do slug,
e devolve **404** quando não é. Não 403 — 403 confirma que o slug existe, o mesmo
erro que 0.0 corrige no `avaliacoes.json`.

**E isso simplifica a UX:** com login, o aluno não precisa mais saber o slug. Uma
rota `/aluno/treino` resolve pela sessão e redireciona para o treino dele. O link
antigo segue funcionando para quem já tem; quem entra novo nunca vê um slug.

### São dois produtos: tela de login separada, mecanismo compartilhado

O corredor de treinos e o app de box (`/aluno/`) são **produtos diferentes que
dividem infraestrutura**. O aluno de consultoria online não é aluno de box e não
deve ver a cara do app da academia para entrar no treino dele.

Mas separar a *experiência* não obriga a duplicar o *mecanismo*:

| Camada | Decisão |
|---|---|
| Rota, tela, branding, copy | **Separado** — `app.octoboxfit.com/treinos/login` |
| Token de uso único, expiração, rate limit, auditoria de entrega | **Compartilhado** — `StudentAppInvitation` + `StudentInvitationDelivery` |
| Cookie de sessão | **Compartilhado** — `signing.dumps`, 30 dias, mesmo formato |

Dois produtos de verdade, e ainda assim **um** sistema de token de uso único — não
dois rate limits para manter em sincronia, não duas auditorias, não dois lugares
para errar expiração.

`?next=` leva de volta ao treino de origem.

> Revisões anteriores diziam "reusar a tela de `/aluno/`". Estava errado do ponto
> de vista de produto: era o **cofre** que valia compartilhar, não a porta.

### `/renan/` é namespace de personal — e isso dá isolamento de graça

A rota fica. Ela não é só o endereço dos links já distribuídos: é o **namespace do
personal**, e o padrão escala para `/joao/<slug>` ao lado de `/renan/<slug>`.

Consequência boa: o **escopo do service worker passa a ser por personal**, então o
aparelho de um aluno do João nunca divide balde de cache com aluno seu. Fronteira
real, não convenção.

Duas coisas a **projetar agora, implementar depois**:

- `PUBLIC_WORKOUT_SCOPE = '/renan/'` é constante (`public_workout_views.py:44`) —
  precisa nascer derivado do box.
- Manifest e service worker passam a ser **um por personal**, não um global.

Nada disso muda nesta rodada. Só evita que a Entrega 3 crave `/renan/` em lugares
novos e cobre o dobro depois.

### Sobre o nome `public_workouts`

O app se chama assim porque vive no **schema `public`** (SHARED_APPS) — não porque
o acesso é aberto. Ver o docstring de `public_workouts/models.py:9`. O nome segue
correto depois da fase B.

### Treino aberto × dado de saúde aberto

Duas categorias com tratamentos diferentes, de propósito:

| | Risco se exposto | Decisão |
|---|---|---|
| **Prescrição** (séries, reps, exercícios) | baixo — descobrir a série de outro não causa dano | aberto na fase A; atrás de login na fase B |
| **Avaliação física** (peso, %gordura, dobras) | alto — dado sensível de saúde, LGPD art. 5º, II | **fechado desde já** (0.0), em qualquer fase |

---

## DECISÃO ARQUITETURAL 3: o Postgres é a verdade; o aparelho guarda o casco e o rascunho

> Requisito: **cada aluno tem, no aparelho dele, o treino dele e mais nada.**
> E: **o que ele digitou não pode se perder se o app fechar.**

A revisão anterior propunha namespace de cache por identidade. **Era complexidade
desnecessária** — o projeto já resolveu isso no app do aluno, com um desenho mais
simples, e o `/renan/` é que está fora do padrão.

### O padrão que já existe em `/aluno/`

`templates/student_app/sw.js` cacheia **apenas o casco do app** — CSS, JS, ícones,
manifest e a tela de offline (`ALLOWLIST`, linhas 5-18). Nenhuma página, nenhum
dado. Quando cai a rede, `networkFirst` devolve a **tela de offline**, não uma
cópia de dado do aluno. Estratégias nomeadas e separadas: `staleWhileRevalidate`
para assets, `networkFirst` para navegação.

O `/renan/` faz o oposto: cacheia páginas inteiras **com peso e %gordura dentro**.
Essa divergência é a raiz do A4.

**Decisão: alinhar o `/renan/` ao padrão do `/aluno/`.** Três camadas, cada uma com
um dono claro:

| Camada | O que é | Onde vive | Se perder |
|---|---|---|---|
| **Verdade** | Carga, avaliação, check-in, assinatura | **PostgreSQL** | nada se perde — é o original |
| **Casco** | CSS, JS, ícones, tela offline, **prescrição do próprio aluno** | Cache Storage | rebusca na próxima rede |
| **Pacote do aluno** | Cópia enxuta do **próprio** histórico, para ler offline | IndexedDB | rebusca na próxima rede |
| **Rascunho** | O que o aluno digitou e **ainda não subiu** | IndexedDB (outbox) | **perde trabalho — inaceitável** |

Consequências diretas, e todas simplificam:

- **Dado de terceiro nunca vai para o aparelho.** O que vai é só do dono da sessão.
- **Não existe namespace por identidade**, porque cada aparelho tem uma sessão e o
  logout limpa tudo. Some o hash, some a orquestração de troca de identidade.
- **GodMode não cacheia nada** — nem casco de outro aluno, nem pacote. O `no-store`
  vira cinto de segurança, não mecanismo.
- **A prescrição pode ser cacheada** porque, depois de 0.2 e 3.4, o aparelho só
  recebe o slug do próprio aluno e a página não carrega mais idade/peso/%gordura
  no corpo.

### O pacote do aluno — ler offline sem virar um segundo A4

O aluno abre o app na academia sem sinal e quer ver quanto levantou na semana
passada. Para isso o dado precisa **já estar** no aparelho.

**Mecanismo principal: sync oportunista no foreground.** Toda abertura com rede
baixa o pacote — carga recente do slug ativo, 1RM já calculado no servidor (O4),
substituições ativas, `access_until`. Alguns KB.

O caso real é esse: ele sai de casa no wifi, abre no ônibus, chega sem sinal. O
pacote tem 20 minutos de idade.

**Por que não um envio semanal por push:**

| | Push semanal | Sync ao abrir |
|---|---|---|
| Frescor | até 7 dias — e ele treina 5x/semana | minutos |
| iOS | só com PWA instalado na tela inicial (16.4+) | **sempre** |
| Permissão | precisa | não precisa |
| Garantia | best-effort | determinístico |

**O push entra como invalidação, não como transporte.** "Seu treino mudou" → o SW
marca stale → a próxima abertura baixa. Push pequeno, sem dado de saúde trafegando
por FCM/APNs, sem esbarrar em limite de payload.

No Android, **Periodic Background Sync** pode atualizar sem o app abrir. No iOS ela
não existe — entra como bônus para quem tem, nunca como base.

**Três cuidados que vêm junto:**

1. **Expiração local** — 30 dias sem sync e o pacote se apaga sozinho. Sem isso,
   quem cancelou fica com cópia vitalícia do próprio histórico no bolso.
2. **Logout apaga o pacote**, junto com o outbox e o cookie.
3. **`access_until` viaja dentro do pacote** — fecha parte do buraco da trava
   offline (A3): expirou, a página degrada mesmo sem rede.

O pacote é **cópia de leitura descartável**, nunca fonte de verdade. Conflito entre
pacote e Postgres resolve sempre a favor do Postgres.

### O rascunho: escrita local nunca é cache

A distinção que faltava no plano:

| | Cache de leitura | Outbox / rascunho |
|---|---|---|
| Guarda | cópia do que o servidor já tem | o que **só existe no aparelho** |
| Fonte de verdade | Postgres | o aluno, até sincronizar |
| Se perder | rebusca | **perde o trabalho dele** |
| Onde | Cache Storage | IndexedDB |

O aluno digita 3 séries no meio do treino, o celular trava ou ele troca de app.
Ao voltar, tem que estar lá.

1. **Rascunho salvo enquanto digita** — `input` com debounce curto, e flush em
   `visibilitychange` (padrão já usado em `static/js/student_app/pwa.js:571` e
   `static/js/catalog/student_form_lock.js:263`). Não depende de o aluno apertar
   "Salvar".
2. **Ao salvar, vira item de outbox** com chave idempotente
   `(identity, slug, version, exercise_ref, week)` — reenvio nunca duplica linha.
3. **Dreno oportunista:** ao voltar a rede, ao abrir o app, ao ficar visível.
4. **Sincronizou → apaga o local.** O Postgres passa a ser a única cópia.
5. **Logout apaga o outbox e o rascunho** — junto com o cookie, não depois.

Nenhuma dessas etapas guarda dado que o servidor já tem. O aparelho só segura o
que ainda não conseguiu entregar.

### Conta é individual — e dá para detectar quando não é

Compartilhar login não é caso de uso a suportar: a consultoria custa R$ 89,90 e a
proposta é uma pessoa, um treino, uma anamnese, uma progressão.

O cookie **já carrega `device_fingerprint`** (`session.py:38`) e o campo não é usado
para nada hoje. Dá para contar dispositivos distintos por identidade e sinalizar o
que foge do padrão — sem bloquear ninguém automaticamente, porque trocar de celular
é normal. Sinal para você olhar, não trava automática.

Isso resolve o problema real (receita) sem pagar o custo de arquitetar multi-usuário
por aparelho, que não é a proposta do produto.

---

## DECISÃO ARQUITETURAL 6: `WorkoutTemplate` é a biblioteca de programas

`operations/model_definitions.py:274` já tem um sistema de **templates de treino
reutilizáveis** — e ele responde ao problema econômico central deste produto.

### Por que isso importa mais que o editor com IA

Você troca o programa de cada aluno a cada 4–6 semanas: **5 a 12 programas por aluno
por ano**. Com 10 alunos, são ~100 programas/ano. Gerar 100 do zero com IA é caro em
tempo de revisão **sua**, mesmo com o parser pronto.

Mas você não tem 100 programas diferentes — tem ~15 que funcionam, adaptados. Os
arquivos de arquivo provam: *"Quadríceps & Glúteo 4 Dias"*, *"Posterior Dominante ·
Joelho-Friendly"*, *"Upper/Lower Mesociclo 6 Semanas"* são **templates**, não
one-offs.

| Caminho | Custo por programa |
|---|---|
| Escrever HTML (hoje) | horas |
| Gerar com IA e revisar | minutos de revisão |
| **Adaptar template confiável** | **segundos** |

### O que já existe

```python
class WorkoutTemplate(TimeStampedModel):          # operations/model_definitions.py:274
    name, description
    source_workout   # FK SessionWorkout — deriva template de um treino que deu certo
    is_active, is_featured, is_trusted
    usage_count, last_used_at                     # telemetria de uso
    archived_at, archived_by
```

`WorkoutTemplateBlock` (kind, title, notes, sort_order) e `WorkoutTemplateMovement`
(**`movement_slug`**, label, sets, reps, `load_type`, `load_value`, notes) completam a
árvore.

**Três achados dentro disso:**

1. **`WorkoutApprovalPolicySetting`** (`:246`) já implementa o gate que este plano
   escrevia como regra de prosa — e melhor, com três modos por box:

   | Política | Comportamento |
   |---|---|
   | `strict` | aprovação obrigatória (nosso default para saída de IA) |
   | `trusted_template` | **template marcado `is_trusted` publica direto** |
   | `coach_autonomy` | coach confiável publica direto |

   Ou seja: programa gerado por IA cai em `strict`; programa vindo de template que
   você já validou publica sem fila. **A regra "nada de IA sem revisão" continua
   valendo — e deixa de custar revisão no caso em que não precisa.**

2. **`WorkoutTemplateMovement.load_type = 'percentage_of_rm'` + `load_value`** — a
   prescrição por percentual do RM **já é modelada**. Fecha o ciclo com o 1RM estimado
   (4.4) e a calculadora do app do aluno (DA-5): o template diz "80% do RM", o sistema
   resolve o número para *aquele* aluno.

3. **`movement_slug` já é a chave** nos três modelos (`PlanMovement`,
   `SessionWorkoutMovement`, `WorkoutTemplateMovement`). DA-4 não é invenção nossa —
   é o padrão já adotado no projeto.

### A limitação real, e ela é pequena

`WorkoutTemplateMovement.reps` é `PositiveIntegerField` — **não representa faixa**. Os
treinos deste corredor são de hipertrofia: *"8-12 reps, RIR 1-2"*, *"10 / 6"*.

O próprio projeto já divergiu nisso: `PlanMovement.reps_spec`
(`student_app/models.py:288`) é **CharField** e suporta faixa; `WorkoutTemplateMovement`
e `SessionWorkoutMovement` usam inteiro.

**Correção:** adicionar `reps_spec` e `rir_spec` (CharField) ao
`WorkoutTemplateMovement`, alinhando com o que `PlanMovement` já faz. Migration
pequena, e conserta uma inconsistência que já existe — não cria uma nova.

### Consequência para as entregas

- **Programa de aluno = `WorkoutTemplate` aplicado + ajustes.** O `PublishedWorkout`
  (3.1) continua sendo o snapshot publicado; o template é a **origem** dele.
- **A migração (3.4) rende templates de brinde:** transcrever os 10 HTMLs produz ~15
  templates reutilizáveis, não só 10 programas migrados. O trabalho paga duas vezes.
- **A fila de aprovação (3.0b) e o gate de IA (E6) passam a usar
  `WorkoutApprovalPolicySetting`** em vez de lógica nova.
- `usage_count` e `last_used_at` alimentam de graça o "quais programas eu mais uso".

> `ClassType` (`operations:29`) tem `cross`, `mobility`, `oly`, `strength`, `open_gym`,
> `other` — cobre CrossFit e força, sem entrada específica para consultoria online.
> Não é bloqueio: a separação consultoria × presencial é do **plano de cobrança**
> (2.1/2.2), não do tipo de treino.

---

## DECISÃO ARQUITETURAL 5: reusar o app do aluno, não só o design system

O `/aluno/` não tem apenas tokens — tem **3.803 linhas de CSS organizadas em
`primitives / screens / shell`** e 145 classes `student-*`. É o design system do
OctoBox **já aplicado ao contexto exato** deste projeto: aluno, celular, treino.

### O que já existe e resolve item do nosso plano

| Nosso item | O que já existe | Onde |
|---|---|---|
| Push da régua de cobrança (2.3) | **subscribe/unsubscribe VAPID, `urlBase64ToUint8Array`, sync com backend, permissão, detecção de iOS e standalone** | `static/js/student_app/pwa.js` |
| Instalação do PWA | prompt + estado persistido + recuperação de subscription legada | `pwa.js` + `_pwa_activation.html` + `primitives/pwa-activation.css` |
| Check-in e aderência semanal (3.6) | **"Sua semana": 7 dias, check por dia treinado, "3 de 7 dias com treino"** — com `aria-label` e `aria-current` | `_partials/_progress_strip.html` + `primitives/progress-strip.css` |
| Carga sugerida por %1RM (4.4) | **calculadora com chips 60/70/80/90%, RM base editável, resultado ao vivo** | `_partials/_rm_calculator.html` + `screens/rm.css` |
| Registro e histórico de carga | formulário, hero e lista de RM | `_rm_form.html`, `_rm_hero.html`, `_rm_list.html` |
| Badges de série (Top Set, Feeder…) | primitive de chip | `primitives/chip.css` |
| Cards de exercício | primitive de card | `primitives/card.css` |
| **Modo Academia** | primitive de estado compacto | `primitives/compact-state.css` |
| Número grande (carga, 1RM) | `hero-number` | `primitives/hero-number.css` |
| Renderização de treino | duas variantes (rica e crua) | `screens/wod.css`, `screens/wod-rich.css`, `_wod_rich.html`, `_wod_raw.html` |
| Abas / navegação | nav mobile | `shell/mobile-nav.css` |
| Formulários (anamnese 1.5, avaliação 4.2) | 299 linhas de form primitives | `static/css/student_app/forms.css` |
| Shell, topbar, responsivo | 5 arquivos | `shell/` |

**O push é o ganho mais concreto:** eu estimei a régua de cobrança assumindo
construir o lado cliente. Ele está pronto — inclusive a parte chata (VAPID
base64→Uint8Array, recuperação de subscription em standalone legado, CSRF).

### A regra de reuso — e onde ela quebra

`/aluno/` é **TENANT**; `/renan/` roda no **schema public sem tenant**. Isso cria três
níveis de segurança de reuso:

| Camada | Reuso | Por quê |
|---|---|---|
| **CSS** (`primitives/`, `screens/`, `shell/`, `forms.css`) | ✅ **livre** | arquivo estático, não toca banco |
| **JS** (`pwa.js`) | ✅ **livre**, com revisão de endpoints | roda no cliente; só as URLs de subscribe mudam |
| **Templates** (`_partials/*.html`) | ⚠️ **verificar templatetag** | `_progress_strip.html` faz `{% load student_shell %}` e usa `complete_count` |
| **Views / context** | ❌ **não reusar** | resolvem `Student` em contexto de tenant |

> 🔴 **O risco concreto:** copiar um partial do `/aluno/` arrasta o `{% load %}` dele.
> Se a templatetag consultar modelo de TENANT_APPS, quebra no schema public — e
> `public_workout_views.py` já documenta que esse erro **passa no teste** (o
> `conftest` força `schema_context`) **e só aparece em produção**.
>
> **Procedimento:** ao reusar um partial, reescrever o `{% load %}` e passar dado já
> serializado pelo contexto. O HTML e as classes vêm de graça; a origem do dado é
> sempre nossa.

### Consequência para as entregas

- **3.3** deixa de "escrever sobre o DS genérico" e passa a **compor primitives do
  `student_app`** — menos decisão de design, mais montagem.
- **2.3** perde o trabalho de cliente do push.
- **3.6** e **4.4** ganham tela pronta; falta o dado por trás.
- O precache do service worker passa a apontar para assets **já compartilhados** com
  o `/aluno/` — sem duplicar bytes no aparelho.

---

## DECISÃO ARQUITETURAL 4: o eixo do dado é a pessoa e o movimento — não o treino

> **"A carga do aluno é dele. Ele só muda o treino e a memória persiste para ir
> evoluindo."** — e ele troca de treino 5 a 12 vezes por ano.

Um aluno recebe um **programa novo a cada 4–6 semanas**. Se o histórico de carga
ficar pendurado no treino, a série de força de cada aluno se parte em até 12
pedaços por ano e nenhum gráfico de evolução presta.

```
Hip thrust da Juliana ──────────────────────────────────▶ (contínuo, para sempre)
   │        │           │              │
   └ Prog.1 └ Prog.2    └ Prog.3       └ Prog.4   ← programas são marcadores na linha
```

**`exercise_ref` é o slug do movimento** (`hip-thrust`), que já existe em
`MovementLibrary` — nunca a posição no treino (`ter-A1`), que muda a cada programa.
A carga atravessa programas porque nunca pertenceu a nenhum.

### As três camadas do dado do aluno

| Camada | O que é | Vida | Indexado por |
|---|---|---|---|
| **Prescrição** | o que fazer | efêmera — troca a cada 4–6 semanas | programa + versão |
| **Execução** | kg, reps, RIR | **eterna** | **pessoa + movimento + data** |
| **Composição** | peso, dobras, %BF | **eterna** | **pessoa + data** |

As duas camadas eternas **compartilham o eixo tempo**. É isso que permite, sem
refazer fundação:

- **Força × tempo** — a linha de um movimento desde sempre, com marcadores de troca
  de programa
- **Composição × tempo** — já existe hoje
- **Força × composição** — *"ganhou 2 kg de massa magra e subiu 15 kg no agachamento
  no mesmo trimestre"*. É o gráfico que vende consultoria, e só existe se as duas
  camadas dividirem o eixo do tempo **desde o primeiro registro**
- **Aderência × resultado** — check-in cruzado com as duas

Nada disso entra agora. Mas `movement_slug`, `reps` e `rir` precisam entrar na
Entrega 3: **histórico não se recupera retroativamente.**

### Programa é entidade, não "versão"

Os arquivos de arquivo mostram o padrão real: a Juliana passou por *4× Perna + 1×
Superior* → *Posterior Dominante · Joelho-Friendly* → *Quadríceps & Glúteo 4 Dias*
→ *Pernas & Quadríceps 6 Semanas*. Nomes, objetivos e estruturas diferentes — não
versões de uma mesma coisa.

Dois níveis, e a distinção é **explícita na publicação**, nunca inferida do
conteúdo: ao publicar você escolhe **novo programa** ou **corrigir o atual**.

- **Programa** — `label`, `started_on`, `weeks` (4/5/6), `is_active`
- **Versão** — correção dentro do programa; a numeração reinicia a cada programa

Sem isso, "corrigi um typo" e "nova fase de periodização" viram o mesmo evento — e
o gráfico de evolução não sabe onde desenhar o marcador de troca.

### Histórico de programas: online, nunca no aparelho

O aluno tem uma aba para revisitar programas anteriores. **Ela exige internet.**

O pacote offline (DA-3) leva só o necessário para treinar hoje: o programa ativo e,
para cada movimento dele, a **última execução + o 1RM**. Não N semanas de histórico
— a última carga de cada movimento é o que ele consulta entre séries.

Isso mantém o aparelho enxuto e o histórico completo fora dele.

---

## ENTREGA 0 — fundação + correção dos vazamentos (5–6 dias)

| # | O que | Onde ataca |
|---|---|---|
| **0.0** | 🔴 **Fechar `/renan/<slug>/avaliacoes.json`** | `public_workout_assessment_views.py:24`. Exigir cookie de aluno; sem cookie, **404** (403 confirmaria que o slug existe). |
| **0.1** | 🔴 **Excluir `/renan/*.json` do cache do SW** | `sw.js:93`. Hoje qualquer path sob `/renan/` entra no `PAGE_CACHE`, inclusive JSON com dado de saúde. |
| **0.2** | 🔴 **Precache só do próprio aluno + expurgo** | `sw.js:6-13,38` + `public_workout_views.py:576`. Hoje o `ALLOWLIST` traz todos os slugs. Passa a resolver em runtime. **O bump de `VERSION` é a parte urgente** — corrigir o código não apaga as cópias já gravadas nos 10 aparelhos. |
| 0.3 | Ligar Google OAuth | `.env` (`STUDENT_GOOGLE_OAUTH_*`). Código pronto. |
| 0.4 | Apple Pay no Checkout | Dashboard Stripe: registrar domínio. Não exige Apple Developer Program. |
| 0.5 | Seam do Stripe Connect | `integrations/stripe/auth.py:16` e `services.py:18` setam `stripe.api_key` **no import**. Trocar por `resolve_stripe_account(box)` por requisição. |
| 0.6 | Consentimento LGPD — incluindo IA e transferência internacional | `StudentConsentDocumentKind.HEALTH_DATA` (`student_identity/models.py:134`). Ver D2. |
| 0.7 | `student_identity_id` nullable em `PublicWorkoutAssessment` | `public_workouts/models.py:24` |
| 0.8 | Cookie do aluno para 30 dias | `STUDENT_APP_SESSION_COOKIE_AGE=2592000` no `.env`. Uma linha — o cookie é stateless (`signing.dumps`), não depende de Redis. |

**0.0, 0.1 e 0.2 são a mesma falha vista de três lados**: o dado está exposto na
rede, gravado no cache do próprio aluno, e replicado no cache dos outros. Fechar
só a view deixa cópias em 10 aparelhos. **Mesmo PR, antes de tudo.**

**Pronto quando:** `/renan/<slug>/avaliacoes.json` devolve 404 em aba anônima;
nenhum JSON sob `/renan/` aparece no `PAGE_CACHE` do DevTools; o cache de um
device contém **um** slug; aluno entra com Google; Apple Pay aparece no iPhone;
`grep` não acha mais `stripe.api_key` em escopo de módulo.

---

## ENTREGA 1 — identidade e anamnese (5–7 dias)

> A trava (Entrega 2) precisa saber quem é o aluno. O editor com IA (Entrega 4)
> precisa saber quem ele é *fisicamente*. As duas coisas se coletam no mesmo momento.

| # | O que | Onde ataca |
|---|---|---|
| 1.1 | Os 10 alunos viram `Student` + `StudentIdentity` num box "Renan Personal" | `control.Box`, `students`, `student_identity` |
| 1.2 | Login por token de e-mail — **estendendo `StudentAppInvitation`** | `student_identity/models.py:388` |
| 1.3 | **Fase A**: `/renan/<slug>` público + banner; dados pessoais exigem login | `public_urls.py`, `public_workout_views.py` |
| 1.6 | **Tela de login própria** do produto de treinos (`/treinos/login`) + `?next=` | View e template novos, reusando `StudentAppInvitation` e o cookie — ver DA-2 |
| **1.7** | 🔴 **Upload da carga do `localStorage` — antes do hard reset** | Endpoint que aceita o blob bruto e grava como está. Normalizar fica para 3.5. Ver F-B. |
| 1.4 | PAR-Q obrigatório antes de publicar para aluno remoto | `parq_questions.py` (pronto) |
| 1.5 | **Anamnese** — 7 campos (ver 1.5) | Novo. Formato pensado para virar prompt (4.1). **Revalidação a cada programa novo** — uma pergunta, não o formulário inteiro (E12). |

### 1.2 — por que estender e não construir

`StudentAppInvitation` já tem `token` (UUID único indexado), `expires_at`,
`accepted_at` e entrega auditada por e-mail/WhatsApp. Um magic link é 80% disso.
Construir um `StudentLoginToken` paralelo cria **dois** sistemas de token de uso
único, dois rate limits e duas auditorias para o mesmo problema.

**Dois prazos diferentes, de propósito:**

- **Token do e-mail: 15 minutos.** Prova identidade. Curto porque e-mail pode ser
  lido por outra pessoa.
- **Cookie: 30 dias** (0.8). Mantém logado. Longo porque o aluno está na academia.

Rate limit por e-mail é obrigatório — sem ele o endpoint vira ferramenta de spam
e de enumeração de quem é aluno.

### 1.3 — o cookie tem `path='/aluno/'`

`session.py:84` restringe o cookie a `/aluno/`, então ele **não é enviado** em
`/renan/<slug>`.

Não troque o path para `/` — espalha o cookie por todo o site sem precisar.
A página fica em `/renan/`, e **os dados do aluno vêm de endpoints sob `/aluno/`**.
Uma página em `/renan/juliana` fazendo `fetch('/aluno/api/cargas')` envia o cookie
normalmente: ele é escolhido pelo path da **requisição**, não pelo da página.

### 1.5 — os sete campos, e por que dois deles não são técnicos

São exatamente as perguntas que o profissional já faz hoje a um aluno novo:

| # | Campo | Alimenta | Natureza |
|---|---|---|---|
| 1 | **Objetivo** | seleção de exercício, volume, faixa de reps | técnico |
| 2 | **Restrições** | exclusão de movimento, escolha de variação | técnico |
| 3 | **Há quanto tempo treina** (ou nunca treinou) | complexidade, volume inicial, velocidade de progressão | técnico |
| 4 | **Quantos dias tem para treinar** | split, frequência por grupo | técnico |
| 5 | **Onde vai treinar** | equipamento disponível → alimenta a substituição (4.3) | técnico |
| 6 | **Motivação para começar** | tom da comunicação; o que o review reforça | **comportamental** |
| 7 | **Maior dificuldade no treino ou em manter a rotina** | duração da sessão, densidade; o que o review monitora | **comportamental** |

**Os campos 6 e 7 são a diferença entre um treino correto e um treino que a pessoa
faz.** Não entram em nenhum cálculo — entram na *forma* do programa e no que o sistema
observa depois. Concretamente:

- *"Não consigo passar de 50 minutos"* → o programa nasce com menos acessórios e mais
  séries compostas. Não porque é melhor em teoria: porque é o que cabe.
- *"Quero voltar a subir escada sem cansar"* → o review semanal fala disso, não de
  percentual de gordura.
- *"Perco a rotina quando viajo"* → a substituição (4.3) precisa cobrir variação sem
  equipamento, e o check-in (3.6) vira o sinal mais importante do review.

**Consequência para 4.1:** o prompt recebe os **sete** campos, não quatro. Com objetivo,
nível, dias e equipamento apenas, o Haiku gera treino **tecnicamente correto que a
pessoa abandona**.

**Consequência para 4.5:** o review cruza aderência (3.6) com o **campo 7**. A pergunta
que ele responde não é *"como foi a semana"* — é *"a dificuldade que ela declarou está
acontecendo?"*.

**Formato:** campos 1–5 estruturados (enum/inteiro), para validar e alimentar regra;
6 e 7 **texto livre curto** — a resposta literal da pessoa vale mais que uma categoria,
e é ela que vai para o prompt.

### 1.5b — a anamnese não duplica o PAR-Q

| | PAR-Q | Anamnese |
|---|---|---|
| Pergunta | Você pode treinar com segurança? | Como devo montar o seu treino? |
| Natureza | Triagem de risco, padronizada | Insumo de prescrição |
| Já existe | ✅ `parq_questions.py` | ❌ novo |

**Pronto quando:** os 10 existem como `Student`; um entra pelo link do WhatsApp
sem senha e continua logado 30 dias depois; `/renan/juliana` abre em aba anônima;
a anamnese serializa para o formato que o prompt vai consumir.

---

## DECISÃO ARQUITETURAL 7: o fluxo de pagamento do aluno já existe

### O que está pronto

| Peça | Onde | O que resolve |
|---|---|---|
| **Aluno paga a própria fatura** | `student_app/views/payment_views.py:33` `StudentPayInvoiceView` | checkout Stripe iniciado pelo aluno, com `StudentIdentityRequiredMixin` |
| **Rate limit de checkout** | `shared_support/security/fintech_throttles.py` `checkout_rate_limit_exceeded` | impede abuso do endpoint de pagamento |
| **Ownership da fatura** | `student_payments_presentation.py:52` `resolve_payable_student_invoice(student, payment_id)` | garante que o aluno só paga fatura **dele** — a mesma classe de checagem que DA-2 exige para o slug |
| **Lista de faturas do aluno** | `build_student_payment_rows(student, limit=24)` + `count_open_payments` | tela de "minhas cobranças" |
| **Telas de retorno** | `pay_success.html`, `pay_cancel.html` + views | pós-checkout |
| **Tela de suspensão** | `suspended_financial.html` | o que o inadimplente vê |
| **Regras de atraso** | `finance/overdue_metrics.py` | `is_overdue_payment`, `count_overdue_students`, `sum_overdue_amount` |
| **Notificação multicanal** | `finance/payment_notifications.py:29` `notify_payment_confirmed` | **e-mail + push + WhatsApp**, cada canal isolado em try/except, resultado por canal |

Um detalhe já resolvido que costuma custar caro descobrir: o payment_views documenta
que **"o aluno não é `request.user` do Django"** e que `create_checkout_session` já
trata isso. Nossa Entrega 2 herda a solução em vez de tropeçar nela.

### `notify_payment_confirmed` é o molde exato da régua

A régua (2.3) precisa de "mande por 3 canais, não falhe se um cair, registre o que
foi". É literalmente a forma dessa função:

```python
result = {'email': 'skipped', 'push': 'skipped', 'whatsapp': 'skipped'}
# cada canal em try/except isolado, resultado por canal
```

`notify_payment_due(payment, offset_days)` nasce como irmã dela — mesma estrutura,
copy diferente por marco (D-7, D-3, D-1, D0, D+2). E o e-mail reusa
`signup.email_sender.send_html_email`; o push reusa
`student_identity/push_notifications.py`.

### O que realmente falta construir

| Item | Por quê ainda não existe |
|---|---|
| Assinatura recorrente **aluno → box** | o `mode='subscription'` existente é **box → plataforma** (`signup/services.py:106`) |
| `PaymentNotice` + job diário | a régua de datas materializada (2.3) |
| Roteador de webhook para `StudentBoxMembership` | o atual resolve `Box` (`router.py:306-419`) |
| Stripe Customer Portal | cancelamento self-service (2.5) |
| Fase B do acesso | gate de login para plano pago (DA-2) |

O resto é composição do que já roda em produção.

---

## ENTREGA 2 — cobrança automática + hard reset (4–6 dias)

### 2.1 Assinatura R$ 89,90 (consultoria online)

`signup/services.py:106` já cria `stripe.checkout.Session(mode='subscription')`
— mas para **box→plataforma**. O roteamento em `router.py:306-419` resolve
**`Box`**. Falta um segundo roteador que resolva **`StudentBoxMembership`**.
O de box é o mapa — mesma forma, outro alvo.

### 2.2 Presencial com preço por orçamento

> **A separação consultoria × presencial é do plano de cobrança, não do tipo de
> treino.** O programa do aluno online e do presencial tem a mesma natureza — mesma
> prescrição, mesma página, mesmo registro de carga; o presencial usa a página **ao
> lado do Renan**. O que difere é *como ele paga*: assinatura recorrente de R$ 89,90
> versus `Payment.amount` livre por orçamento.
>
> Por isso a distinção vive em `MembershipPlan` / `Enrollment` / `Payment`, e **não**
> em `ClassType` (`operations:29` — `cross`, `mobility`, `oly`, `strength`,
> `open_gym`, `other`), que não tem nem precisa de entrada para consultoria.
>
> Consequência prática: nada nas Entregas 3 e 4 precisa saber se o aluno é online ou
> presencial. Só a Entrega 2 precisa.

`Payment.amount` já é por pagamento e **não herda de `MembershipPlan.price`**.
O modelo aguenta preço variável **sem mudança de schema**.

- Online → `MembershipPlan` R$ 89,90 + Stripe Subscription
- Presencial → mesmo plano-guarda-chuva, valor em `Payment.amount`, link avulso

### 2.3 Régua — materializada na criação, não recalculada por cron

> **Infra de agendamento já existe:** o padrão do projeto é **management command +
> systemd timer** (`run_due_async_job_retries`, timer noturno de import de leads,
> `/etc/cron.d/octobox-backup`). O job diário da régua segue o mesmo molde — não há
> Celery a introduzir nem scheduler a escolher.

```python
class PaymentNotice(models.Model):
    payment = models.ForeignKey(Payment, ...)
    offset_days = models.SmallIntegerField()   # -7, -3, -1, 0, +2
    scheduled_for = models.DateField(db_index=True)
    sent_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [UniqueConstraint(fields=['payment', 'offset_days'], name='unique_payment_notice')]
```

As 5 linhas nascem com o `Payment`, data já resolvida (pulando feriado/domingo via
`student_app/brazilian_holidays.py`). O job diário só drena
`scheduled_for <= hoje AND sent_at IS NULL`.

**Por que é melhor que o cron que recalcula:** idempotente por construção (a unique
constraint impede disparo duplo — não depende do job rodar exatamente uma vez);
auditável; replanejável; testável sem viajar no tempo.

### 2.4 Fase B do acesso + trava, carência e destrava

Aqui entra o gate de login para plano pago (Decisão Arquitetural 2), junto com:

- job `D+2 → suspende`
- caminho de volta (`invoice.payment_succeeded → ACTIVE`, já mapeado para box em
  `router.py:308`)
- `access_until` no payload; a view recusa servir snapshot novo para suspenso; o
  JS degrada a página quando a data passa

**Ver A3.** Não é inviolável e **não deve ser vendido como se fosse**.

### 2.6 Hard reset dos alunos atuais

O corte acontece **uma vez, com tudo estabilizado**, não gradualmente:

1. **Véspera:** disparo de WhatsApp + e-mail para os 10 com o link de ativação. Quem
   clicar entra já ativado, cookie de 30 dias, e **não encontra tela nenhuma** no dia
   seguinte.
2. **Corte:** bump de `VERSION` do service worker. Na primeira abertura, o SW expurga
   todo cache antigo — inclusive as cópias cruzadas do A4.
3. **Quem não clicou antes** encontra a tela de login. Digita o e-mail, recebe o
   link, cai direto no treino dele — **sem precisar saber o slug** (`/aluno/treino`
   resolve pela sessão, ver DA-2).

Pré-enviar o link é o que transforma "parede no dia do deploy" em "não aconteceu
nada" para a maioria. E treino é rotina diária ou semanal: quem não abriu hoje abre
em dois dias.

**Sem verificação remota do expurgo.** Não há telemetria de cache hoje, e não vale
construir. O sinal prático é o login: aluno que logou, passou pelo SW novo.

### 2.5 Stripe Customer Portal

Cancelamento self-service (CDC). ~2h. Sem isso, cancelar vira WhatsApp para você.

**Cartão recusado ≠ inadimplente.** Mensagem diferente. Ativar Smart Retries.

**Pronto quando:** um aluno de teste assina, recebe os 4 avisos nas datas certas,
trava 2 dias após o vencimento, paga e destrava sozinho — sem intervenção manual.

---

## ENTREGA 3 — treino vira dado + front reusado (11–15 dias)

### 3.0 Uma biblioteca, duas modalidades

O `seed_movement_library` atual tem ~50 movimentos de **CrossFit** (`clean`,
`snatch`, `clean-and-jerk`) apontando para `crossfit.com`. Os treinos deste corredor
são musculação apontando para MuscleWiki.

**Não são duas tabelas — é uma tabela com duas modalidades.** O profissional mistura
as duas no mesmo programa: a Giovanna hoje treina *"CrossFit em seg, qua e sex +
musculação em ter e qui + corrida no sábado"*. Filtrar a biblioteca por modalidade do
programa não funcionaria — a modalidade é atributo do **movimento**, não do programa.

Dois campos novos em `MovementLibrary`:

| Campo | Valores | Para quê |
|---|---|---|
| `modality` | `crossfit` \| `strength` \| `both` | contexto para o prompt e organização da busca na UI |
| `movement_pattern` | `hip-hinge`, `squat`, `horizontal-push`, `knee-flexion`… | agrupa variações (F-D) e alternativas de substituição (4.3) |

**O Haiku recebe a biblioteca inteira**, não um subconjunto. ~150 movimentos × ~15
tokens = ~2.250 tokens — entra no system prompt **cacheado**, junto com a skill. A
`modality` entra como dica ("este bloco é CrossFit, prefira movimentos dessa
modalidade"), nunca como restrição rígida: um programa híbrido precisa alcançar as
duas.

**Semear é barato porque o dado já está no repo:** cada
`<a class="wiki-btn" href="https://musclewiki.com/...">` nos 10 HTMLs é um par
`(nome, URL de referência)` pronto. Um script varre, normaliza em slugs e gera o
seed — meia diária, não uma semana catalogando. O seed de CrossFit permanece como
está, só ganha `modality='crossfit'`.

`movement_pattern` serve **duas** features de uma vez: a substituição de exercício
(4.3) e o agrupamento de gráficos (F-D).

### 3.0b Movimento desconhecido não bloqueia — entra em fila

Quando o parser ou você usarem um movimento fora da biblioteca, a publicação **não
falha**: o movimento entra como `pending`, o programa publica normalmente, e ele
aparece numa fila de aprovação. Você aprova (ou funde com um existente) e ele vira
canônico.

A biblioteca cresce com o uso em vez de exigir catalogação completa antes de
começar. E nenhum programa fica preso porque faltou cadastrar "abdução de quadril
na máquina".

### 3.1 `PublishedWorkout` no `public_workouts` (SHARED)

```python
class PublishedWorkout(models.Model):
    slug = models.SlugField(max_length=50, db_index=True)   # congelado — identifica o ALUNO
    box_id = models.IntegerField(null=True, db_index=True)  # referência fraca
    program_id = models.UUIDField(db_index=True)            # agrupa versões do mesmo programa
    program_label = models.CharField(max_length=140)        # "Quadríceps & Glúteo — 4 Dias"
    started_on = models.DateField()
    weeks = models.PositiveSmallIntegerField()              # 4 | 5 | 6
    version = models.PositiveIntegerField()                 # correção; reinicia a cada programa
    is_active = models.BooleanField(default=False)
    payload = models.JSONField()   # schema_version, access_until, movimentos por movement_slug
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['program_id', 'version'], name='unique_program_version'),
            UniqueConstraint(fields=['slug'], condition=Q(is_active=True), name='one_active_program_per_slug'),
        ]
```

- **`program_id` + `version`** — dois níveis (DA-4). Publicar é escolha explícita
  entre *novo programa* e *corrigir o atual*; o sistema nunca infere do conteúdo.
- **`is_active`** — sem isso não existe rollback. "Servir sempre a maior versão"
  obrigaria a *deletar* para voltar atrás, destruindo o histórico que é a razão de
  ser do snapshot.
- **`schema_version`** no payload — snapshots vivem anos. Sem ele, a primeira
  mudança de formato quebra todo treino já publicado.
- **`started_on` + `weeks`** — insumo da fila de revisão (5.2) e dos marcadores de
  troca de programa no gráfico de evolução.
- **Cada movimento do payload carrega `movement_slug`** de `MovementLibrary` — é a
  chave que liga prescrição a execução (DA-4).
- **`is_tracked`** por movimento — marca os principais do dia (hoje é o que ganha
  tracker no HTML: "A1 · Glúteo máximo"). **Só os marcados entram no gráfico de
  evolução**, senão a tela vira 50 linhas para quem tem um ano de histórico (E8).
- **`weeks` é informativo, nunca expiração** — o programa ativo serve
  indefinidamente. Só o financeiro tira acesso (E10, F-A).

> **`access_until` NÃO entra no payload.** Revisões anteriores colocavam — e isso
> contradizia a imutabilidade do snapshot: a data de acesso muda a cada pagamento,
> o que obrigaria a **republicar o programa toda vez que o aluno renova**. Ela vive
> no **pacote do aluno** (DA-3), que é efêmero e ressincronizado — lugar certo para
> dado mutável. Ver F-A.

### 3.2 Serviço de publicação (no tenant)

`student_app/application/publish_workout.py` — lê `WeeklyWodPlan`, resolve
`MovementLibrary.reference_url` por slug, monta o payload, valida contra o schema,
grava no `public` e ativa.

**Os links do MuscleWiki hardcoded nos 10 HTMLs viram `MovementLibrary.reference_url`.**
Como o link entra *dentro* do snapshot, a página pública não alcança a tabela tenant.

### 3.3 Template único — escrito **já sobre o design system**

`templates/public_workouts/workout.html` substitui os 10 arquivos.

> **Mudança de estratégia (revisão 18).** Revisões anteriores escreviam o template
> com CSS próprio e retematizavam depois, na 4.7. Isso era retrabalho garantido: o
> design system já tem todos os componentes de que esta página precisa. O template
> nasce nele.

| `/renan/` hoje | Componente do DS |
|---|---|
| `.tabs` / `.tab` (Treinos, Cardio, Periodização, Avaliações) | `components/interactive-tabs.css` |
| badges de série (`st-p`, `st-f`, `st-t`, `st-m`) | `components/pills.css` |
| `.sets-tbl` (tabela de séries) | `components/tables.css` |
| `.ex`, `.c-card` (cards de exercício) | `components/cards.css` + `card-variants.css` |
| barra do tracker (`.tracker-prog`) | padrão `*-progress-track` / `*-progress-fill` |
| `.prog-name` / `.prog-title` | `components/hero.css` |
| `.stats` (idade, peso, BF) | `components/quick-cards.css` |
| `.mode-btn` (Modo Academia) | `components/actions.css` |
| glow, faixa de destaque | `neon.css` — `card-decor-topstripe`, `card-decor-glow`, `@keyframes neon-pulse` |
| grid, espaçamento, breakpoints | `spacing.css`, `responsiveness.css`, `shell.css` |

**Morrem os 8 CSS próprios de `public_workouts/`** (~800 linhas): `tokens`, `layout`,
`components`, `tracker`, `period`, `install-prompt`, `assessments`, `mobile`. Junto
com eles morre o `PUBLIC_WORKOUT_STYLESHEETS` e a tupla que alimenta o precache do
service worker — que passa a reusar os assets do DS, já cacheados por `/aluno/`.

**Mata também:** `_inject_legacy_pwa_head` e as ~110 linhas de
`_LEGACY_INSTALL_PROMPT_MARKUP` + `_LEGACY_SW_REGISTRATION_SCRIPT`
(`public_workout_views.py:328-489`). Hoje `rafael`, `franciele` e `johnespanha`
recebem `<head>` e service worker por **substituição de string**.

**O que o "Modo Academia" vira:** hoje é `body.simplified` + regras próprias em
`components.css`. Sobre o DS, é um estado — `components/states.css` — aplicado às
mesmas classes. O comportamento (esconder nota, tabela e glossário; mostrar
`.gym-card`) não muda; a implementação deixa de ser CSS paralelo.

### 3.4 Migrar os 10 alunos — **com o parser de IA, não à mão**

> Esta é a maior economia encontrada na revisão 13. Ver S1.

O plano anterior colocava o editor com IA na Entrega 4 e a migração na 3 — ou seja,
**transcrever 10 arquivos de 400 a 1.400 linhas na mão** e só depois construir a
ferramenta que faz exatamente isso.

**Invertido:** o parser HTML→JSON (4.1) é construído **aqui**, e a migração é o
primeiro trabalho dele.

Três ganhos, e o terceiro é o melhor:

1. Você **revisa JSON estruturado** em vez de transcrever HTML. Corta a maior parte
   do gargalo — que é você, não a máquina.
2. O parser nasce testado em **10 casos reais**, não em exemplo inventado.
3. **Os goldens são gabarito automático.** `tests/golden/public_workouts/*.json` já
   existe para os 10: republicar a partir do JSON e comparar com o golden diz, sem
   você olhar, se a transcrição perdeu alguma coisa. Um caso de uso de IA onde a
   resposta certa já está no repo.

> 🔴 **Nunca regravar o golden durante a migração.** A baseline é regravável por env
> var (`UPDATE_PUBLIC_WORKOUT_GOLDEN=1`). Regravar antes de conferir o diff **apaga a
> rede de segurança sem aviso** e o erro de transcrição entra em produção como se
> fosse o esperado. Compara-se contra o versionado; a baseline só muda depois que
> você aprovou a diferença, em commit separado. Ver E11.

Rollback por aluno = `is_active` no programa anterior.

**Dado pessoal sai do corpo da página** (ver A4): idade, peso e %gordura passam a
vir do endpoint autenticado, não do HTML.

### 3.5 Carga sai do `localStorage` — por upload oportunista, com `reps` e `rir`

Hoje `app.js:136-148` guarda `{"ter-A1-s1": 60}` — **só kg**.

> **Um script de migração server-side é impossível: o dado está no celular do
> aluno, nunca esteve no servidor.**

O cliente empurra: na primeira visita o JS lê o `localStorage`, faz
`POST /aluno/api/cargas`, marca flag de "já subiu" — e **não apaga nada**.

```python
class StudentLoadLog(models.Model):
    """Execução: eterna, indexada por pessoa + movimento. Ver DA-4."""
    student_identity_id = models.IntegerField(db_index=True)
    movement_slug = models.SlugField(max_length=64, db_index=True)  # ← a espinha dorsal
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    reps = models.PositiveSmallIntegerField(null=True)  # ← D3
    rir = models.PositiveSmallIntegerField(null=True)   # ← D3
    performed_on = models.DateField(db_index=True)
    # contexto — nunca chave:
    program_id = models.UUIDField(null=True, db_index=True)
    week_in_program = models.PositiveSmallIntegerField(null=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['student_identity_id', 'movement_slug', 'performed_on'],
                         name='student_movement_timeline'),
        ]
```

**Validação na entrada (E9):** carga que destoa da última do mesmo movimento acima
de um limiar **pede confirmação** ("800 kg? Você registrou 80 kg da última vez").
Não bloqueia — confirma. Um registro errado envenena o 1RM, achata o gráfico inteiro
e vira insumo do review semanal. Barato de prevenir, caro de limpar.

O índice `(aluno, movimento, data)` é a série temporal de força — a consulta que
todo gráfico de evolução vai fazer, atravessando programas.

`program_id` fica como **contexto**: serve para desenhar o marcador de troca de
programa no gráfico e para explicar uma queda ("mudou de fase"), nunca para
particionar o histórico.

**`rir` sem fricção:** a tabela já exibe o RIR prescrito ("Top Set · 8-12 · RIR
1-2"). O campo entra com esse valor como padrão e o aluno só mexe se foi diferente.

### 3.6 Check-in de treino

Um botão "fiz hoje". `StudentAppActivity` já existe com os kinds certos.

**Por que aqui e não na Entrega 4:** o review semanal (4.5) precisa de **histórico**.
Ligar coleta e consumo juntos produz um primeiro review vazio. Ver D4.

**Precisa funcionar offline** — fila local drenada quando volta a rede. Sem isso o
dado tem buracos justamente em quem treina onde o sinal é ruim.

### 3.7 🔴 Corrigir a estratégia de cache do service worker

Sem isto, a Entrega 3 **não funciona** — ver A2.

Alinhar ao padrão de `templates/student_app/sw.js`, que já separa
`staleWhileRevalidate` (assets) de `networkFirst` (navegação):

| Recurso | Hoje | Depois |
|---|---|---|
| CSS/JS/ícones | cache-first, chave `asset_version` | igual — **chave separada** (O2) |
| Prescrição do próprio aluno | cache-first, chave = mtime do CSS | **network-first + ETag** (O1) |
| `/renan/*.json` (público) | cacheado no `PAGE_CACHE` | **nunca cacheado** (0.1) |
| Histórico do próprio aluno | — | **pacote em IndexedDB**, sync ao abrir com rede (DA-3) |
| Dado de qualquer outra pessoa | páginas de todos no cache | **nunca** chega ao aparelho |
| Escrita não sincronizada | `localStorage` cru | **outbox em IndexedDB**, idempotente (DA-3) |
| Precache no install | todos os slugs | só o do aluno, resolvido em runtime (0.2) |
| Sem rede, sem cache | página em branco | tela de offline, como em `/aluno/` |

**Pronto quando:** os 10 renderizam do banco com golden idêntico; publicar v2 e
voltar atrás leva um comando; nenhum aluno perdeu carga; **publicar v2 aparece no
celular do aluno na próxima abertura com rede** — verificado em device real.

---

## ENTREGA 4 — produto (7–10 dias)

### 4.1 Editor com Haiku + `expert-ef` + anamnese

> O **parser** HTML→JSON já foi construído na 3.4 e validado contra os 10 goldens.
> Aqui ele ganha o outro lado: gerar programa novo a partir de texto ditado +
> anamnese. Mesma saída, mesmo schema, mesma validação contra `MovementLibrary`.

```
Você dita/cola + anamnese do aluno → Haiku + expert-ef → revisão → Publicar
                                                                      │
                                        PublishedWorkout v(N+1) + push + WhatsApp
```

- Molde: `wod_session_llm_parser.py` (timeout 10s, fallback silencioso, validação de slug)
- `output_config.format` com o schema — a API **garante** o JSON
- Validar movimentos contra `MovementLibrary` antes de aceitar
- Prompt cache TTL 1h no system prompt
- **Os 7 campos da anamnese (1.5) entram no prompt** — inclusive motivação e maior
  dificuldade. Sem os dois comportamentais, o Haiku gera treino tecnicamente correto
  que a pessoa abandona.

**Pegadinha do cache:** Haiku 4.5 só cacheia prompts acima de **4.096 tokens**.
A skill inteira dá ~6.700 — passa. Se um dia enxugarem abaixo disso, **o cache
para de funcionar sem erro nenhum**. Teste que trave o piso.

### 4.2 Avaliação física

Fórmulas prontas; falta UI e o campo `protocol`. Aluno online → US Navy; você,
presencial → Jackson-Pollock 7 dobras (`formulas.py:163`).

### 4.3 Substituição de exercício pelo aluno

"Minha academia não tem essa máquina" — dor nº 1 de consultoria online.

`MovementLibrary` já tem os slugs; falta agrupar por padrão de movimento e deixar
o aluno escolher entre alternativas **que você aprovou**.

**Vive fora do snapshot** (`StudentExerciseSubstitution`, referenciando
`exercise_ref`) e é aplicada na renderização. Ver D1.

### 4.4 Gráficos de evolução + 1RM estimado

SVG inline — **sem CDN** (a CSP e o modo offline não toleram script externo).

> **Não começa do zero.** `static/js/public_workouts/assessments.js` já desenha em SVG
> puro, no contexto exato: silhueta corporal com medidas ancoradas, empilhamento de
> rótulos anti-sobreposição (`stackLabels`), conectores (`connectorPath`), gauges,
> badges de classificação e delta visual. E `app.js buildChart()` já faz barras
> (`.chart-col`). **Reusar o padrão** — falta aplicá-lo à série temporal de carga.

```python
@dataclass(frozen=True)
class OneRepMaxEstimate:
    value_kg: float
    formula: str         # 'brzycki' | 'blend' | 'epley'
    confidence: str      # 'high' | 'moderate' | 'low'
    effective_reps: int  # reps + rir


def estimate_one_rep_max(*, weight_kg, reps, rir=0) -> OneRepMaxEstimate | None:
    """Estimativa de 1RM. Retorna None acima de 15 reps efetivas."""
```

| Reps efetivas | Fórmula | Confiança |
|---|---|---|
| ≤ 6 | Brzycki — `peso × 36 / (37 − reps)` | alta |
| 7–10 | média de Brzycki e Epley | moderada |
| 11–15 | Epley — `peso × (1 + reps/30)` | baixa |
| > 15 | **`None`** | — |

Três decisões que fazem o número prestar:

1. **Reps efetivas = reps + RIR.** As fórmulas assumem falha concêntrica (RIR 0).
   Este corredor prescreve RIR 1-2 — usar reps cruas **subestima sistematicamente**.
2. **Recusar acima de 15 reps efetivas.** Ali se mede resistência à fadiga, não
   força máxima. Segue a postura que o módulo já adota para BF%. (Brzycki, além
   disso, divide por zero em 37 reps.)
3. **Nunca comparar 1RM entre exercícios diferentes.** Membro inferior sustenta
   mais reps na mesma %1RM (leg press é o pior caso). Na série temporal do **mesmo**
   exercício o viés é constante e some.

Correção por padrão de movimento fica **fora da v1** — exigiria tabela de fatores
difícil de defender.

**O valor está na tendência, não no número:** platô objetivo (1RM estável 3 semanas
mesmo com carga subindo); **1RM caindo = fadiga acumulada**, gatilho de deload mais
confiável que "tô cansado"; comparação justa entre semanas mesmo mudando a faixa
de reps. A confiança sobe para a UI como rótulo.

### 4.5 Review semanal por IA

Job semanal: carga + reps + RIR + tendência de 1RM + check-in + avaliações +
anamnese → Haiku → texto e carga sugerida → push.

A tendência entra como **sinal calculado, não número cru**: o prompt recebe "platô
de 3 semanas no hip thrust" ou "1RM caindo há 2 semanas, considerar deload".
Determinístico onde dá; IA só onde agrega.

### 4.6 Exportar treino em PDF

Reduz atrito no cancelamento e vira argumento de venda ("o treino é seu").

`reportlab==4.4.1` já está em `requirements.txt` e em uso por
`reporting/infrastructure/http_exports.py` — a lib e o padrão de export existem.

### 4.7 Tema Luxo Futurista 2050

O design system oficial vive em `static/css/design-system/tokens.css` e se declara
**a única autoridade de tokens do tema**. O `/renan/` tem tokens próprios em
`static/css/public_workouts/tokens.css` — que nasceram para unificar 7 cópias
divergentes, não para competir com o tema.

| Eixo | Tema oficial | `/renan/` hoje |
|---|---|---|
| Tipografia | Manrope variável + Object Sans (display) | system-ui |
| Fundo | `#f5f7fb` + `--theme-bg-atmosphere` (4 radial-gradients) | bege/off-white chapado |
| Superfície | translúcida (`rgba` + gradiente + `color-mix`) | sólida |
| Profundidade | `--theme-card-glow` + sombras em duas camadas | sombra simples |
| Motion | 120/180 ms, `cubic-bezier(0.2, 0.8, 0.2, 1)` | ad-hoc |

### Accent: decidido — duas variantes neon, tokens do próprio tema

O accent por aluno (10 cores diferentes) **sai**. Entram **duas variantes por
gênero**, usando tokens que o design system já tem:

| Variante | Token | Cor |
|---|---|---|
| Feminino | `--theme-accent-premium` | `#d96bc3` — magenta neon |
| Masculino | `--theme-accent-support` | `#5f8ff7` — azul neon |
| **Não informado** | `--theme-accent-primary` | `#68d9ee` — ciano neon |

Nenhuma cor nova é inventada — é literalmente "seguindo as cores do OctoBox".

**A terceira variante não é opcional:** `Student.gender` (`StudentGender`:
`male`/`female`) é **`blank=True`** — pode estar vazio, e está vazio para a maioria
dos 10 hoje. Sem um neutro declarado, esses alunos cairiam num accent indefinido.

**Não usar `--theme-accent-danger` (`#ff5f7e`)** para o feminino, apesar de ser
rosado: é o token de erro. Reusar semântica de alerta como branding deixaria um aviso
de falha indistinguível do accent da página.

**O payload carrega a variante, não o gênero.** `accent_variant: 'feminine' |
'masculine' | 'neutral'` — a cor chega ao template sem que o dado pessoal precise
circular no snapshot.

**Simplificação:** `PublicWorkoutAccent` (dataclass de 5 campos × 10 alunos) deixa de
existir, junto com os 10 blocos de accent em `PUBLIC_WORKOUT_LIBRARY`. Um campo no
lugar de cinquenta valores.

> **Dívida registrada:** hoje existem dois campos com o mesmo conteúdo conceitual —
> `Student.gender` (`male`/`female`, canônico do domínio) e
> `PublicWorkoutPlan.assessment_sex` (`M`/`F`, usado pelas fórmulas de BF%). A cor sai
> de `Student.gender`; as fórmulas continuam em `assessment_sex`. Unificar é limpeza
> para a Entrega 3, não agora.

### Como o OctoBox faz neon — e por que isso encerra a dúvida do fundo claro

`neon.css` mostra o padrão já escolhido pelo projeto:

| Utilitário | O que faz |
|---|---|
| `.card-decor-topstripe` | faixa de 3 px na cor do `--brand` no topo do card |
| `.card-decor-glow` | sombra suave, opt-in, não animada |
| `@keyframes neon-pulse` | brilho pulsante por `color-mix` com transparência |

**Neon em detalhe, sobre fundo claro** — não fundo neon. Era a primeira das duas
saídas que eu tinha levantado, e o projeto já a escolheu. **Não há shell escuro a
construir nem `color-scheme` a divergir.** As variantes de accent (magenta / azul /
ciano) entram justamente nesses detalhes: faixa do card, preenchimento da barra de
progresso, pill de Top Set, estado ativo da aba.

### Duas verificações que continuam abertas

1. **Peso no PWA.** Manrope variável entra no precache. Object Sans e Aptos Display
   precisam existir no repo ou ter fallback declarado — fonte que falha offline degrada
   pior que fonte simples. *Mitigado:* os assets do DS já são cacheados por `/aluno/`,
   então o custo é compartilhado, não novo.
2. **Custo de GPU na academia.** Translucidez, gradientes e `backdrop-filter` pesam em
   celular modesto, com a tela suada, **em pé entre séries**. Medir num aparelho real —
   o `/aluno/` já roda com esses estilos, então há base de comparação.

### O que sobra para a 4.7

Como o template nasce no DS (3.3), esta entrega **deixa de ser "aplicar tema"** e
passa a ser polimento:

- as três variantes de accent ligadas aos detalhes neon
- hero do programa (`hero-variants.css`) com o nome e o foco do mesociclo
- revisão de contraste e de toque em aparelho real, na academia
- ajuste de densidade para uso em pé (alvos de toque, tamanho de fonte entre séries)

**A entrega encolhe de ~3 dias para ~1–2**, e o retrabalho de retematizar desaparece
— não existe CSS próprio para substituir.

### 4.8 GodMode auditado

**`control.Membership` é por box** — "ver todos os treinos" precisa ser papel de
plataforma, não membership. Toda entrada gera registro no `auditing`. Resposta em
modo impersonação leva `Cache-Control: no-store` (DA-3).

---

## ENTREGA 5 — escala (8–11 dias)

### 5.1 Onboarding self-service de consultoria

Link público: a pessoa assina R$ 89,90, responde PAR-Q + anamnese, cai na sua fila.
Reusa `signup/` e `onboarding/`. **É o que muda seu teto** — e é pré-requisito
prático de vender a outros personais.

### 5.2 Fila de revisão

"Estes 4 terminam o mesociclo esta semana." Sai de `mesocycle_weeks` + `started_on`
(3.1).

### 5.4 Painel do personal *(registrado, não obrigatório)*

Quem está progredindo, quem estagnou, quem sumiu — os 10 (ou 30) numa tela.

Com 10 alunos você sabe de cabeça; com 30, não. E é exatamente quando o onboarding
self-service (5.1) começa a trazer gente. Os dados já existem depois da Entrega 3
(carga, check-in, 1RM, tendência), então **é tela, não fundação** — pode esperar sem
custo de retrabalho.

### 5.6 Financeiro do corredor *(escopo revelado pelo isolamento)*

Ao separar `PublicWorkoutPayment` de `finance.Payment` (V3), a receita de consultoria
**deixou de aparecer** em `overdue_metrics`, no dashboard e nos relatórios do box. Isso
é o comportamento correto — e cria a necessidade de uma tela própria: quem pagou, quem
está atrasado, quanto entrou no mês.

Provavelmente é a **mesma tela** do painel do personal (5.4). O custo é real e estava
escondido atrás de uma decisão de arquitetura.

### 5.5 Portabilidade e retenção *(obrigação legal)*

- **Exportar tudo do titular** — programas, cargas, avaliações — em formato legível
  (LGPD art. 18). O PDF (4.6) exporta o programa; isto exporta o histórico.
- **Retenção pós-cancelamento: 12 meses**, informada no consentimento (0.6), com
  exclusão imediata a pedido.

Os 12 meses não são só conformidade: aluno que volta em 6 meses reencontra o
histórico inteiro, o que é argumento de retenção. Ver E13.

### 5.3 Vídeo de execução enviado pelo aluno

Justifica pagar consultoria em vez de baixar planilha. **Único item com custo
recorrente novo** (storage) e o que exige retenção mais rígida — o consentimento
(0.6) precisa cobrir prazo de guarda e exclusão a pedido.

---

## DECISÕES DE INFRAESTRUTURA REGISTRADAS

### DI-1 — Manter Evolution API; Cloud API oficial depois; não trocar de framework

| | Evolution (hoje) | Hermes Agent (Nous Research) |
|---|---|---|
| Categoria | Gateway de mensagens | Framework de agente que **embute** gateway |
| WhatsApp | WhatsApp Web, não-oficial | **Baileys** (não-oficial) ou Cloud API oficial |
| No OctoBox | Integrado e rodando | Zero |

**Decisão: não trocar.** Trocar Evolution por Hermes-com-Baileys não resolve nada
— Baileys é a mesma tecnologia, mesmo risco de ban — e joga fora integração que
funciona (`integrations/whatsapp/` com contracts, services, poll_processor,
reprocessing), da qual a régua (2.3) depende.

**O risco de ban é real.** A resposta certa é migrar para a **WhatsApp Business
Cloud API oficial**, que não depende do Hermes e pluga no que já existe. Tem custo
por conversa → fazer quando houver faturamento. Até lá, **e-mail é sempre o
fallback, nunca o contrário**.

### DI-2 — Agente de atendimento é escopo separado

O Hermes é relevante para o "supportfaqagent" que você mencionou — agente 24/7 que
responde alunos. Mas é **feature nova**, não substituição: entraria como Entrega 6
e não toca cobrança nem login.

Dois avisos: (1) um agente que conversa com aluno vai falar sobre treino, lesão e
dor — precisa de guardrail explícito (não prescreve, não dá conselho médico, escala
para você); (2) você já tem Claude integrado — um FAQ agent dá para construir com o
que existe, sem mais um serviço para manter na VPS.

---

## CONFLITOS RESOLVIDOS

### D1 — Substituição de exercício × snapshot imutável
Se o aluno troca um exercício, **não pode gravar no snapshot**.
**Resolução:** o snapshot é a *prescrição*; o que o aluno produz vive fora,
referenciando `(slug, version, exercise_ref)`. Exige `exercise_ref` **estável entre
versões** — senão a substituição se perde a cada publicação.

### D2 — Anamnese no prompt do Haiku × LGPD
Lesões e restrições são dado sensível. Enviá-los à API da Anthropic é tratamento por
terceiro **e transferência internacional**.
**Resolução:** o consentimento (0.6) menciona explicitamente. Alternativa: enviar só
o derivado ("evitar impacto em joelho") em vez do diagnóstico. Decisão sua.

### D3 — 1RM estimado × formato do registro de carga
Faltam **duas** colunas, não uma: sem `rir`, a estimativa subestima todo aluno que
treina com reserva — o padrão prescrito aqui.
**Resolução:** `reps` e `rir` desde a 3.5. **Histórico de carga não é recuperável
retroativamente.**

### D4 — Check-in × coleta antes do consumo
**Resolução:** check-in sobe para a 3.6, semanas antes da 4.5. Regra geral: **tudo
que alimenta a IA começa a coletar antes da IA existir.**

### F-A — `access_until` × snapshot imutável *(revisão 13)*
O snapshot é imutável; `access_until` muda a cada pagamento. Dentro do payload,
**renovar assinatura obrigaria republicar o programa**.
**Resolução:** vive no pacote do aluno (DA-3), que é efêmero e ressincronizado.
Regra derivada: **nada mutável entra no snapshot.** Se muda por evento de negócio,
o lugar é outro.

**Comportamento confirmado:** falta de pagamento faz o aluno **perder o acesso** — o
treino deixa de ficar visível. O programa publicado não é alterado, não é
despublicado e não é reescrito; quando o pagamento entra, o acesso volta ao mesmo
programa, na mesma versão, com o histórico intacto. A assinatura controla **a porta**,
nunca o conteúdo.

### F-B — Upload da carga acontecia *depois* do hard reset *(revisão 13)*
O hard reset é 2.6; o upload do `localStorage` estava em 3.5. Entre as duas entregas,
qualquer aluno que limpasse os dados do site **perderia o histórico sem backup** — e
o `localStorage` é a única cópia que existe.
**Resolução:** o upload sobe para 1.7, aceitando o blob **bruto** (normalizar fica
para 3.5). Salvar primeiro, entender depois.

### F-C — `MovementLibrary` semeado com CrossFit *(revisão 13)*
~50 movimentos de CrossFit apontando para crossfit.com; os treinos são musculação
apontando para MuscleWiki. Pré-requisito invisível da Entrega 3.
**Resolução:** 3.0 — extrair o vocabulário dos próprios HTMLs, onde os pares
`(nome, URL)` já existem.

### F-D — Variação de exercício × continuidade do histórico *(revisão 13, refinada na 14)*
Hip thrust com barra e na máquina são o mesmo `movement_slug`? Um slug único dá
histórico contínuo mas **mistura cargas incomparáveis** (a máquina permite mais
carga); slugs separados dão comparação limpa mas deixariam o aluno **sem referência
nenhuma** ao estrear uma variação.

**Resolução — armazenar separado, exibir por semelhança:**

| | Regra |
|---|---|
| **Armazenamento** | slugs separados. `hip-thrust-barbell` ≠ `hip-thrust-machine`. |
| **Cálculo (1RM, platô, deload)** | **nunca cruza variações** — comparar 100 kg na máquina com 80 kg na barra produziria número falso |
| **Exibição** | mostra **todas as variações do mesmo `movement_pattern`**, rotuladas e com cores distintas |

Na prática: o aluno vai registrar hip thrust na máquina pela primeira vez e a tela já
mostra *"com barra: 80 kg × 8 (há 5 dias)"* como referência. Ele nunca começa no
escuro, e o sistema nunca soma o que não se soma.

Quando a variação nova tem poucos registros, a referência da variação irmã aparece
com o rótulo de que é **outra variação** — não como se fosse a mesma carga.

> *Possibilidade futura, fora do escopo:* com histórico suficiente **do mesmo aluno**
> nas duas variações, dá para derivar a razão pessoal entre elas (ex.: máquina ≈
> 1,25× a barra, para aquela pessoa) e ancorar a sugestão de carga na estreia. Só
> vale com dado real — razão de tabela genérica erra mais do que ajuda.

---

## ENGENHARIA REVERSA — o sistema rodando

Sete cenários simulados com o plano implementado. Cada um que quebra virou item.

### E1 — Juliana abre o PWA na academia, sem sinal

**Leitura:** o SW serve a prescrição do casco, e o **pacote do aluno** (DA-3) já
tem a carga das últimas semanas e o 1RM — baixado na última vez que ela abriu com
rede, tipicamente minutos antes. Ela vê o que precisa.

Se o pacote estiver velho ou ausente, a seção mostra a idade do dado ("atualizado
há 3 dias") em vez de fingir que está fresco.

**Escrita:** ela registra 3 séries sem sinal. O rascunho persiste enquanto digita,
vira item de outbox ao salvar, e sobe sozinho quando a rede volta.

Nenhum dos dois caminhos falha, e nenhum guarda dado de terceiro.

### E2 — Você publica um programa novo enquanto ela está offline há 3 dias

Ela volta, o SW busca, pega o programa novo. A carga que ela registrou offline
aponta para `movement_slug` — que **existe independentemente do programa** (DA-4).

Nada fica órfão: o registro entra na série temporal do movimento e aparece no
gráfico com o marcador de troca de programa no lugar certo. Se o movimento não está
no programa novo, o histórico dele continua íntegro e volta a aparecer no dia que o
movimento voltar.

Era exatamente esse cenário que o `exercise_ref` por posição quebrava.

### E3 — Duas pessoas dividindo uma conta

**Não é caso de uso a suportar** — a consultoria custa R$ 89,90 e a proposta é uma
pessoa, uma anamnese, uma progressão. Dividir login descaracteriza o produto e
corrói a receita.

Como o cache não guarda dado pessoal (DA-3), trocar de pessoa no mesmo aparelho não
vaza nada. O que resta é o problema comercial, e para ele o `device_fingerprint`
que já está no cookie serve de sinal — sem trava automática, porque trocar de
celular é normal.

### E4 — Você abre o treino de 6 alunos em GodMode

Com o desenho da DA-3, **não há o que cachear**: o aparelho guarda o casco e a
prescrição do dono da sessão, e dado pessoal nunca. O `no-store` em modo
impersonação continua valendo como cinto de segurança, mas deixa de ser o
mecanismo que segura o problema.

### E5 — Você monta um treino pelo celular, no 4G da academia

O molde (`wod_session_llm_parser.py`) tem **timeout de 10s** — dimensionado para
*estruturar* um WOD curto. **Gerar um mesociclo inteiro com anamnese é outra ordem
de grandeza** e vai estourar.

**Correção:** a geração (4.1) é **job assíncrono**, não requisição. Você dita,
recebe "montando…", e o push avisa quando está pronto para revisar. O parser
síncrono continua servindo para o caso curto.

Isso também conserta o caso do elevador: você fecha o app e o trabalho continua.

### E6 — O Haiku prescreve agachamento profundo para quem tem lesão no joelho

**Regra dura: nada gerado por IA é publicado sem sua revisão.** O botão "Publicar"
é sempre seu. Isso já estava implícito no fluxo; vira explícito porque é o gate de
segurança do produto — e porque ninguém deve poder desligá-lo "para agilizar".

### E7 — Review semanal roda para todo mundo

Gasta token com quem está suspenso e manda push de treino para quem não pagou.

**Correção:** filtrar por membership ativa **antes** de montar o prompt.

### E8 — Um ano depois: Juliana tem 10 programas e ~400 registros

A tela de evolução tenta desenhar **todos** os movimentos que ela já fez — 40 a 60
linhas. Ilegível.

**O conceito que resolve já existe nos templates atuais:** só o exercício principal
do dia tem tracker ("A1 · Glúteo máximo"). Os acessórios não.

**Correção:** o payload marca `is_tracked: true` nos principais, e **só eles entram
no gráfico**. O resto continua registrável, mas fora da tela de evolução. Sem isso, a
feature nasce inutilizável exatamente para quem tem mais histórico — o aluno antigo,
que é o mais valioso.

### E9 — Carga digitada errada (800 em vez de 80)

Envenena três coisas de uma vez: o 1RM estimado explode, o gráfico ganha um pico que
achata todo o resto, e o review semanal comenta em cima do lixo.

**Correção:** validação contra a última carga do **mesmo movimento**. Variação acima
de um limiar pede confirmação ("800 kg? Você registrou 80 kg da última vez"). Não
bloqueia — confirma. Barato de fazer, caro de limpar depois.

### E10 — Você fica doente, de férias, ou só atrasa

Alunos com mesociclo terminando ficam sem programa novo. Se `weeks` funcionar como
**expiração**, eles perdem o acesso ao treino por culpa sua.

**Regra:** `weeks` é **informativo**, nunca expiração. O programa ativo continua
servindo indefinidamente; a fila de revisão (5.2) avisa você, e não trava ninguém.
O único mecanismo que tira acesso é o financeiro (F-A).

### E11 — O parser erra na migração e ninguém percebe

Os goldens são a rede — mas são **regraváveis** por env var
(`UPDATE_PUBLIC_WORKOUT_GOLDEN=1 pytest …::PublicWorkoutContentSignatureTests`).
Se alguém regravar a baseline antes de conferir o diff, a rede some sem aviso e o
erro entra em produção como se fosse o esperado.

**Regra dura na migração (3.4): nunca regravar o golden.** Compara-se contra o que
está versionado. A baseline só é regravada depois que **você** aprovou a diferença,
e num commit separado que diz isso.

### E12 — A anamnese envelhece

Ela responde em janeiro, machuca o ombro em abril. O Haiku segue gerando programa
com informação de janeiro.

**Correção:** a cada novo programa, uma pergunta única — *"mudou algo desde a última
vez? (lesão, equipamento, rotina)"*. Ela responde "não" em um toque na maioria das
vezes, e quando responde "sim" você descobre antes de prescrever, não depois.

O mesmo vale para o PAR-Q: revalidação anual.

### E13 — O aluno pede os dados dele, ou cancela e volta

**Portabilidade (LGPD art. 18):** o titular pode pedir os dados em formato legível.
O PDF (4.6) exporta o programa, não o histórico. Falta exportação completa —
programas, cargas, avaliações — num JSON ou CSV.

**Retenção pós-cancelamento:** o plano não diz por quanto tempo o dado fica depois
que o aluno sai. Guardar para sempre sem justificativa é problema; apagar na hora
destrói o histórico de quem volta em 6 meses — o que é comum.

**Proposta:** manter por 12 meses após o fim do vínculo, informado no consentimento
(0.6), com exclusão imediata a pedido. Se ele volta dentro da janela, o histórico
inteiro volta com ele — o que é um argumento de retenção, não só conformidade.

### E14 — Você quer ver os 10 alunos de uma vez

Não existe no plano. O GodMode (4.8) é "entrar no treino de um aluno"; a fila de
revisão (5.2) é "quem precisa de programa novo". Falta o panorama: **quem está
progredindo, quem estagnou, quem sumiu.**

Com 10 alunos você sabe de cabeça. Com 30 não — e é exatamente o momento em que a
Entrega 5 (onboarding self-service) começa a trazer gente.

**Fica registrado como 5.4**, não como item obrigatório: os dados para montá-lo já
existem depois da Entrega 3 (carga, check-in, 1RM), então é tela, não fundação.

### E15 — Mesmo aluno, dois personais *(futuro)*

`StudentIdentity` já é cross-box, e o `StudentLoadLog` é indexado por
`student_identity_id` (DA-4) — ou seja, **o histórico é da pessoa, não do box**.

Isso está certo para o aluno (a força dele é dele) e levanta uma questão para o dia
que existir um segundo personal: ele veria o histórico gerado com você.

**Decisão a tomar antes do segundo personal, não agora:** o histórico é da pessoa,
mas a **visibilidade** deve ser por vínculo ativo — cada profissional vê o período
em que atendeu, e o aluno vê tudo. Registrado para não ser descoberto tarde.

---

## OTIMIZAÇÕES QUE FALTAVAM

### O1 — ETag = versão do snapshot (resolve A2 sem bumpar o SW)

A correção anterior para o A2 era incluir a versão do snapshot na `VERSION` do
service worker. Funciona, mas é grosseiro: **toda publicação invalidaria o SW
inteiro**, forçando o aluno a rebaixar tudo.

Melhor: a resposta do treino carrega `ETag: "<slug>-v<version>"`. O SW faz
network-first com `If-None-Match`.

| | Sem ETag | Com ETag |
|---|---|---|
| Treino inalterado | rebaixa a página inteira | **304, ~200 bytes** |
| Treino publicado | rebaixa | rebaixa (correto) |
| Offline | fallback no cache | fallback no cache |

Network-first deixa de ser caro. E a versão do snapshot já é o ETag natural — não
inventa identificador novo.

### O2 — Separar a chave dos assets da chave da página

Hoje `VERSION` é uma só. Se ela passar a depender do snapshot, **o CSS e o JS são
rebaixados toda vez que você publica um treino** — centenas de KB por nada.

`STATIC_CACHE` continua keyed pelo `asset_version` (mtime dos arquivos);
`PAGE_CACHE` passa a ser keyed por identidade (DA-3). São ciclos de vida
diferentes e não devem compartilhar chave.

### O3 — O JSON do snapshot não vai para o cliente

A página continua sendo **HTML renderizado no servidor**, como hoje. O payload é
contrato interno entre publicação e template.

Dois ganhos: menos bytes no aparelho, e o cache guarda só o que a pessoa precisa
ver — não a estrutura inteira com metadados.

### O4 — 1RM calculado no servidor, entregue junto com o histórico

Determinístico, testável em `formulas.py`, e o gráfico funciona offline porque o
valor veio cacheado junto. Recalcular no cliente duplicaria a regra em JavaScript —
e a primeira divergência entre as duas versões seria impossível de depurar.

### O5 — Uma chamada por página, não uma por exercício

`/aluno/api/treino/<slug>/estado` devolve carga + check-in + 1RM + substituições
numa resposta só. Um round-trip, um item de cache, uma invalidação.

---

## ONDE ESTÁ SÓLIDO E ONDE É FRÁGIL

### Sólido — decisões que eu defenderia em revisão

| Decisão | Por quê |
|---|---|
| Snapshot publicado (DA-1) | Resolve a fronteira tenant↔public sem segunda verdade; padrão já usado no repo |
| Postgres é a verdade; aparelho guarda casco + pacote do dono (DA-3) | Dado de terceiro deixa de existir no aparelho, sem sacrificar o uso offline |
| Eixo do dado é pessoa + movimento (DA-4) | A memória de força atravessa 5–12 programas por ano sem se fragmentar |
| Parser de IA como ferramenta de migração (3.4) | Os goldens já são o gabarito — IA num trabalho onde a resposta certa está no repo |
| Nada mutável dentro do snapshot (F-A) | Renovar assinatura não obriga a republicar programa |
| Movimento desconhecido não bloqueia (3.0b) | A biblioteca cresce com o uso; nenhum programa fica preso por falta de cadastro |
| Uma biblioteca, duas modalidades (3.0) | O profissional mistura CrossFit e musculação no mesmo programa — a Giovanna já faz |
| Reusar os primitives do app do aluno (DA-5) | 3.803 linhas de CSS e o push VAPID completo já existem, testados em produção |
| CSS/JS livre, template com revisão, view nunca (DA-5) | Impede que reuso arraste templatetag de TENANT para o schema public |
| `WorkoutTemplate` como biblioteca de programas (DA-6) | ~100 programas/ano saem de ~15 templates; `is_trusted` publica sem fila |
| Gate de IA via `WorkoutApprovalPolicySetting` (DA-6) | Política já modelada e por box, em vez de regra de prosa |
| Reusar o fluxo de pagamento do aluno (DA-7) | Checkout, rate limit, ownership de fatura e notificação multicanal já rodam |
| `notify_payment_confirmed` como molde da régua (DA-7) | 3 canais com degradação isolada já resolvidos e em produção |
| Consultoria × presencial é do plano de cobrança (2.2) | Entregas 3 e 4 não precisam saber qual é qual |
| Armazenar separado, exibir por semelhança (F-D) | O aluno nunca estreia uma variação sem referência, e o 1RM nunca soma o que não se soma |
| Assinatura controla a porta, não o conteúdo (F-A) | Suspender e reativar não toca em programa publicado nem em histórico |
| Sync ao abrir em vez de push semanal | Frescor em minutos, funciona no iOS, não depende de permissão |
| Push invalida, não transporta | Dado de saúde não trafega por FCM/APNs; sem limite de payload |
| Outbox idempotente para escrita (DA-3) | O que o aluno digitou nunca se perde, e reenvio não duplica |
| ETag = versão do snapshot (O1) | Frescor sem custo de banda; não inventa identificador novo |
| GodMode com `no-store` | Você vê tudo e não guarda nada — casa com a trilha do `auditing` |
| Geração por IA como job assíncrono (E5) | Timeout de 10s não serve para gerar mesociclo |
| `is_active` + constraint parcial | Rollback vira `UPDATE`; o banco garante uma ativa por slug |
| Régua materializada na criação | Idempotente por construção, não por disciplina operacional |
| Estender `StudentAppInvitation` | Evita dois sistemas de token, dois rate limits, duas auditorias |
| `reps` + `rir` desde a Entrega 3 | Dado não recuperável retroativamente |
| Coleta antes do consumo (D4) | Evita primeiro review vazio |
| Upload oportunista da carga | Único mecanismo possível — o dado está no celular |
| Recusar 1RM acima de 15 reps | Honestidade estatística; segue a cultura do `formulas.py` |
| Manter Evolution (DI-1) | Trocar por Baileys não resolveria o problema alegado |

### Frágil — assumido conscientemente, com o preço na mesa

| Ponto | Por que é frágil | O que fazemos |
|---|---|---|
| **Trava offline (A3)** | PWA com cache é contornável em modo avião | Mitigação parcial via `access_until`. **Não vender como inviolável.** |
| **Push no iOS** | Só funciona com PWA instalado na tela inicial (16.4+) | WhatsApp/e-mail é o canal principal; push é bônus |
| **Evolution não-oficial** | Ban derruba o canal | E-mail sempre como fallback; Cloud API quando houver receita |
| **Repasse de 10%** | Número não validado com mercado | Revisitar com dados reais antes do 2º personal |
| **Prazos** | São estimativas minhas, não medições | Reavaliar após a Entrega 0, que é a mais previsível |
| **Correção do 1RM por exercício** | Fora da v1 por falta de base defensável | Só comparar série temporal do mesmo exercício |
| **Entregas 0 e 1 invisíveis** (~10 d) | Nenhuma novidade para o aluno | Aceito: curtas e destravam tudo |

### O que ainda não sabemos

- Se o Haiku + `expert-ef` + anamnese gera programa que você publicaria sem reescrever
- Quanto da anamnese os 10 alunos atuais vão preencher sem você cobrar um a um
  (sem ela, o editor com IA só serve para cliente novo)
- Se 4/5/6 semanas cobre todos os casos ou se aparece programa de duração livre

### Resolvido nas revisões 11–12

| Dúvida | Resposta |
|---|---|
| Presencial usa a página de treino? | **Sim**, ao lado do Renan — nada a cortar do escopo |
| Carga atravessa programas? | **Sim** — é a razão da DA-4 |
| Frequência de troca de programa | 4 a 6 semanas → **5 a 12 programas/aluno/ano** |
| Aluno vê programas antigos? | **Sim**, aba própria, **online** — nunca no aparelho |
| Presencial é mensal? | **Sim** — mesma régua do online, valor livre |
| Adoção do login preocupa? | **Não** — treino é rotina diária/semanal; ver 2.6 |

---

## DEPENDÊNCIAS REAIS

```
Entrega 0 ──┬──▶ 1 (identidade + anamnese) ──▶ 2 (cobrança + fase B) ──▶ 5 (escala)
            │                 │                                            ▲
            └──▶ 3 (treino) ──┴──▶ 4 (produto) ────────────────────────────┘
```

- **A Entrega 2 não depende da 3.** O gate financeiro funciona com o HTML atual —
  é o que permite faturar antes de refazer o treino.
- **A Entrega 2 depende da 1**, não o contrário. Sem identidade não há o que travar.
- **4.1 depende de 1.5** (anamnese) e de 3.1 (schema do payload).
- **4.4 depende de 3.5 com `reps` e `rir`.**
- **4.5 depende de 3.6 ter rodado por semanas.**
- **5.2 depende de `mesocycle_weeks` no payload (3.1).**
- **4.7 (tema) só fica barato depois de 3.3.**

## MÉTRICAS DE SUCESSO

| Métrica | Hoje | Meta |
|---|---|---|
| Endpoints com dado pessoal exposto | 2 (A1, A4) | 0 |
| Tempo para criar treino de aluno novo | ~1 dia | < 30 min |
| Tempo seu por cliente novo de consultoria | ~1 dia | ~0 (self-service) |
| Alunos com histórico de carga preservado | 0 | 100% dos ativos |
| Cobranças feitas na mão | todas | 0 nas de consultoria |
| Inadimplência detectada sem você olhar | 0 | 100% |
| Linhas de template | ~16.000 | < 1.000 |

## O QUE CAPA O FUTURO (resolver agora, é barato)

1. `PublicWorkoutAssessment.plan_slug` string solta → 0.7
2. `store_key` como identidade — é namespace de `localStorage`. Não construir sobre ele.
2b. **`/renan/` cravado como constante** — é namespace de personal e vai ter irmãos
   (`/joao/`, `/maria/`). Não cravar em código novo; derivar do box. Ver DA-2.
3. Chave Stripe global no import → 0.5
4. Dois sistemas de token de uso único → 1.2
5. Snapshot sem `schema_version` → 3.1
6. Carga sem `reps`/`rir` → 3.5 — **não recuperável retroativamente**
7. `exercise_ref` instável entre versões → 3.1 (D1)

## TESTES

Postgres obrigatório (`django-tenants` não tem caminho SQLite). Ver
[docs/testing/README.md](../testing/README.md).

- Goldens de `tests/golden/public_workouts/` são a rede da migração (3.4)
- `/renan/<slug>/avaliacoes.json` devolve **404** sem cookie (0.0)
- O `ALLOWLIST` do SW contém **um** slug, não todos (0.2)
- **Aluno A logado abrindo o slug do aluno B recebe 404**, não 403 nem o treino (DA-2)
- `/aluno/treino` redireciona para o slug do aluno da sessão (DA-2)
- Piso de 4.096 tokens do prompt cache (4.1)
- **Fronteira:** nenhuma view de `/renan/` toca modelo de TENANT_APPS — o
  `conftest` força `schema_context`, então esse erro **passa no teste e só quebra
  em produção**
- Rollback: publicar v2, voltar para v1, conferir que o aluno vê v1
- `exercise_ref` sobrevive a uma republicação (D1)
- 1RM devolve `None` acima de 15 reps efetivas (4.4)
