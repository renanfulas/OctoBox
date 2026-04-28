# 🧠 SIMULAÇÃO MATRIX: 20 Dias no Frontline do OctoBox
**Projeto:** OctoBox Elite CrossFit | **Duração:** 20 Dias Corridos
**Data da execução:** 2026-04-28
**Alvo:** Avaliação de Carga Cognitiva, UX/UI, SecOps e Retenção.

> Simulação conduzida cruzando as 5 personas com os módulos reais do monorepo:
> `access/roles/{owner,manager,coach,reception}.py`, `quick_sales/`, `finance/`,
> `dashboard/`, `student_app/`, `students/`, `reporting/`, `communications/`,
> `integrations/`, `auditing/` e `operations/` (workspaces por papel + WOD).

> **Regra de autoridade aplicada:** runtime, testes e código vencem template.
> Onde o runtime divergia da versão anterior deste relatório, a leitura do runtime atual prevalece.

---

## 🔎 Como esta rodada foi executada

Esta não é um clique-a-clique completo no navegador; é uma simulação operacional baseada em três fontes:

1. leitura cruzada dos docs de autoridade — `README.md`, `docs/reference/documentation-authority-map.md`, `docs/reference/functional-circuits-matrix.md`, `docs/rollout/beta-role-test-agenda.md`;
2. inspeção das superfícies reais por papel em `access/`, `operations/`, `finance/`, `dashboard/`, `catalog/`, `student_app/`;
3. validação automatizada focada nas áreas tocadas pelas personas.

| Evidência | Resultado |
|---|---:|
| `manage.py check --settings=config.settings.test` | sem issues |
| Suite focada de simulação | **149 testes verdes em 23,6s** |
| Branch | `main` (HEAD em `aee7aad`) |
| PR-base de remediação anterior | `#53 — Resolve 22 friction items from 20-day simulation (Ondas 1–4)` |

Suite focada (mesmo set do prompt operacional do report Codex):

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_quick_sales_wave2.py `
  tests/test_quick_sales_wave3.py `
  tests/test_quick_sales_wave4.py `
  tests/test_reporting_facade.py `
  tests/test_catalog_report_exports.py `
  tests/test_dashboard_reading_priority.py `
  tests/test_dashboard_snapshot_serialization.py `
  tests/test_communications_services.py `
  tests/test_communications_inbound_idempotency.py `
  tests/test_shell_and_context.py `
  tests/test_operations_workspace_views.py `
  tests/test_operations_workspace_transport.py `
  tests/test_operations_workspace_signal_mesh.py `
  tests/test_coach_wod_editor.py `
  student_app/tests.py `
  -q --benchmark-disable
```

Ressalvas honestas:

1. é um relatório de simulação operacional + leitura técnica, não substitui smoke manual por papel;
2. o comparativo de mercado usa material publicamente declarado por Nextfit/Tecnofit, não teste real;
3. para liberar beta amplo, complementar com agenda em `docs/rollout/beta-role-test-agenda.md`.

---

## 👥 As Personas em Simulação

*   👱‍♀️ **Maria (Recepção) | 24 anos | 80 QI**
    *   **Perfil:** Habilidade técnica baixa. Clica primeiro, lê depois. Fica nervosa com tabelões de Excel. Só quer que o aluno pare de buzinar na porta.
    *   **Superfícies que usa:** `/operacao/recepcao/`, `/quick-sales/`, `/alunos/` (check-in rápido), shell `access/shell_actions.py` com role `reception`.
*   👨‍💼 **Carlos (Manager) | 30 anos | 100 QI**
    *   **Perfil:** Administrativo padrão. Resolve as confusões da Maria. Precisa ver números fáceis para gerar relatórios, fechar matrículas e configurar aulas.
    *   **Superfícies que usa:** `/dashboard/`, `/financeiro/` (queue, overdue, follow-ups), `/operacao/relatorios/`, `/catalog/` (planos/aulas), role `manager`.
*   🏋️‍♂️ **Beto (Coach) | 28 anos | 102 QI**
    *   **Perfil:** Habilidade técnica nula por escolha. Odeia olhar pra tela, quer olhar pro aluno. Gosta de praticidade extrema no Box, na beira do ringue.
    *   **Superfícies que usa:** `/operacao/coach/` (workspace + chamada), `/operacao/wod/editor/`, `student_app` mirror (RMs, WOD), shell coach via `access/roles/coach.py`.
*   🤵 **Roberto (Owner - Master Node) | 35 anos | 108 QI**
    *   **Perfil:** Executivo. Fica pouco no Box físico. Opera pelo iPhone. Quer ver o dinheiro cair e saber se ninguém está roubando a academia.
    *   **Superfícies que usa:** `dashboard/dashboard_snapshot_panels.py` (owner workspace), `operations/owner_workspace_queries.py`, `finance/overdue_metrics.py`, `auditing/`, `security/`.
*   👱‍♀️ **Júlia (Aluna) | 32 anos | 85 QI**
    *   **Perfil:** Habilidade técnica média/baixa. Clica primeiro, lê depois. Gosta de coisas fáceis, ansiosa não-patológica, social, abre Instagram todo dia, senso de comunidade. O Box é extensão de saúde e prazer.
    *   **Superfícies que usa:** `/aluno/` (Home, Grade, WOD, RM, Settings, PWA, convite, troca de box).

---

## Linha de simulação (Highlights)

### 🗓️ Semana 1 — Aquecimento e primeira confiança

**Dia 1 — Onboarding coletivo do box**

- Roberto entra em `/dashboard/` pelo iPhone. Dashboard snapshot já entrega caixa, inadimplência, headcount e alertas sem precisar abrir 10 abas.
- Carlos abre `/financeiro/` e `/alunos/` para reorganizar remanescentes da migração; o student directory já carrega KPIs de 30 dias e atalhos de ação.
- Maria entra em `/operacao/recepcao/`; o shell por papel mostra fila de intake + fila de pagamento pendente sem ela precisar saber Django.
- Beto cai em `/operacao/coach/`; quer só ver aula e registrar ocorrência rápida.
- Júlia entra pelo convite no `/aluno/entrar-com-convite/` e quer chegar logo no WOD.

**Leitura:** a "rua principal" por papel está definida e estável — risco mora nas placas pequenas (microcopy de erro, tooltip, estado vazio).

**Dia 2 — Primeiras vendas e cobranças**

- Maria roda Quick Sales sem entrar em fluxo longo. Após Onda 1 do PR #53, valor ≤ 0 está bloqueado tanto no form quanto na camada de serviço (`quick_sales/services`), o que reduz ticket fantasma.
- Carlos confere cobrança e status no financeiro; rótulos "Assinar Plano" e "Produto avulso" já não confundem mais.
- Roberto vê pressão financeira no snapshot do dashboard sem pedir relatório.

**O que funcionou:** Quick Sales conectado ao financeiro reduz muito carga cognitiva da recepção.
**Atrito residual:** copy de erro em integrações externas (Stripe, WhatsApp) ainda usa traduções genéricas — pendente refinamento.

**Dia 3 — Aula cheia, primeira chamada estressada**

- Beto registra presença e ocorrência sem perder contato visual. `coach.css` agora usa `content-visibility:auto` em `.coach-session-card`, o que tirou o jank em scroll de turma cheia.
- WOD aparece sem precisar abrir outra tela, via ponte `coach-session-workout-editor`.

**Leitura:** coach já tem interface "semáforo" mais clara depois da onda 6.1 (WOD day-apply, template archive, Smart Paste Monday snap).

**Dia 4 — Primeiro lead importado em volume**

- Carlos testa import via `operations/services/student_importer.py`. O `_flush_create/_flush_update` com fallback row-by-row em savepoints e o retorno `error_rows` (Onda 3) já entregam falha por linha, mas a UI ainda não exibe progresso percentual em tempo real.

**Atrito:** import sem barra de progresso continua sendo "panela de pressão sem válvula" para campanha grande.

**Dia 5 — Fechamento de semana**

- Roberto pede leitura curta: "ganhamos ou perdemos a semana?". `OperationsExecutiveSummaryView` + `dashboard_snapshot_panels` já entregam direção, mas a narrativa ainda não é "causa, impacto, próxima ação" em uma frase.

**Dia 6-7 — Fim de semana**

- Júlia abre o app, vê WOD, RM (com sparkline SVG depois da Onda 4 quando há ≥2 pontos de histórico) e Grade.
- Onda 4 também trouxe o hint de política de cancelamento ("até 2h antes") no hero e no botão da grade — Júlia entende a regra sem perguntar no WhatsApp.

### 🗓️ Semana 2 — Velocidade de cruzeiro e pressão operacional

**Dia 8 — Maria ganha memória muscular**

- Os atalhos do shell por papel viram mapa mental. Maria não precisa mais "procurar onde está o botão" — encontra por hábito.
- Risco: se algum atalho do `access/shell_actions.py` apontar para âncora quebrada, a confiança despenca rápido. Os testes `test_shell_and_context.py` passaram, mas isso é contrato; não é smoke visual.

**Dia 9 — Carlos organiza follow-up financeiro**

- Carlos usa fila financeira + leitura de inadimplência + comunicação semiautomática. `finance/overdue_metrics.py` + `finance/follow_up_tracker.py` já tratam status, follow-up, retenção e churn como camada visual, não tabela.
- `PaymentBulkActionView` (Onda 3) com partial-commit HTTP 207 permite cobrança em lote sem bloquear tudo se uma linha falhar.

**Atrito:** follow-up automatizado precisa evitar "piloto automático perigoso". Mensagem errada em cobrança parece erro humano mesmo quando foi sistema.

**Dia 10 — Beto usa WOD/RM e Smart Paste**

- Beto cola WOD do WhatsApp em `/operacao/wod/paste/`; o Smart Paste já normaliza para o template canônico (PR #56 + #57).
- Cruzamento WOD↔RM já existe; `WorkoutPrescriptionPreview` está em `operations/workout_prescription_preview.py`, mas o autocomplete de carga sugerida ainda é o ponto de maior alavanca não-resolvido.

**Débito técnico avisado:** se o editor crescer com telas irmãs demais e sem narrativa única (publicar, agendar, replicar, arquivar), o coach volta a digitar na mão.

**Dia 11 — Roberto olha auditoria**

- Roles, admin privado e hardening existem (`access/admin.install_admin_site_gate`). `auditing/` registra eventos. PR #53 acrescentou `AuditEvent` para pedido de congelamento (Onda 4), o que é bom sinal de cobertura crescente.
- Falta linguagem executiva: a leitura de auditoria ainda é "log bruto". Roberto quer "Quem mexeu? O que mudou? Teve risco? Preciso agir?".

**Dia 12 — Júlia começa a voltar pelo app**

- Banner iOS de instalação PWA (Onda 4 — `_pwa_activation`) aparece em Safari não-standalone; Júlia instala e vira atalho na home screen.
- `student_tomorrow_wod` (Onda 2) expõe o WOD de D+1 quando publicado — Júlia se planeja para amanhã.

**Atrito:** falta camada social (quem vai treinar, reação, indicação). É o teto de retenção atual do app.

**Dia 13-14 — Operação sem fundador**

- Roberto não está fisicamente. Maria, Carlos e Beto operam sem pedir intervenção.
- Métrica qualitativa: ninguém pediu para "voltar para WhatsApp/planilha" durante o fim de semana.

### 🗓️ Semana 3 — Maturidade, campanha e limite do produto

**Dia 15 — Campanha de matrícula**

- Volume alto de leads em pouco tempo. O pipeline em `operations/services/lead_import_*` segura, mas a experiência ainda precisa ser implacável: progresso em tempo real, duplicata destacada, falha por linha visível, reprocessamento em 1 clique.
- O `error_rows` da Onda 3 já existe; só falta UI tratá-lo de forma clara.

**Dia 16 — Aula cancelada**

- Beto cancela aula. Onda 4 entregou `send_session_cancelled_push()` documentado — push para o app dispara.
- Júlia recebe a notificação no PWA. Loop fechou.

**Atrito menor:** ainda não há fallback escalonado (push → email → WhatsApp) por canal preferido do aluno.

**Dia 17 — Inadimplência sobe**

- Financeiro identifica pressão. Carlos age via `PaymentBulkActionView`; Roberto enxerga no snapshot.
- `StudentFreezeView` agora usa bulk UPDATE (Onda 3), o que reduz carga no banco quando o congelamento é em massa.

**Ponto a polir:** cobrança precisa separar "lembrete educado", "risco real" e "ação de bloqueio". Tudo com tom humano.

**Dia 18 — Coach propõe WOD para a semana**

- Beto monta WOD em `/operacao/wod/editor/`, usa templates de `/operacao/wod/templates/`.
- Manager/Owner aprova quando necessário via `WorkoutApprovalBoardView` + `workout_approval_policy.py`.
- A trilha de aprovação evita publicar treino errado para o aluno.

**Risco:** permissão frouxa aqui vira bug grave — WOD errado é visível e mina confiança.

**Dia 19 — Owner faz leitura executiva**

- Roberto pergunta: "qual gargalo está me custando dinheiro?". O sistema cruza alunos, financeiro, operação e dashboard — `OperationsExecutiveSummaryView` + `owner_workspace_queries.ghost_enrollment` (Onda 2) destacam matrículas sem cobrança como métrica e card.

**Próximo salto:** transformar leitura em "próxima melhor ação por papel".

**Dia 20 — Fechamento forense**

- Maria opera sem ajuda.
- Carlos organiza inadimplência, plano e turma.
- Beto dá aula sem olhar pro notebook.
- Roberto decide pelo iPhone.
- Júlia volta pelo app — sparkline do RM mostrando evolução é gancho emocional novo.

**Conclusão da semana 3:** o OctoBox se comporta como sistema operacional do box, não cadastro bonito.

---

## 🩺 DIAGNÓSTICO PROFUNDO (O que funcionou e o Atrito)

### IMPACTOS POSITIVOS (UX/UI e Pagamento)

| # | Área | Observação | Persona beneficiada |
|---:|---|---|---|
| 1 | Shell por papel | `access/shell_actions.py` reduz decisão e evita menu genérico — testes `test_shell_and_context.py` cobrem | Maria, Carlos, Beto |
| 2 | Dashboard snapshot | `dashboard_snapshot_panels.py` entrega leitura rápida sem 10 telas | Roberto |
| 3 | Quick Sales endurecido | bloqueio de valor ≤ 0 + autocomplete com data nasc. + CPF mascarado (Onda 1) | Maria |
| 4 | Financeiro com follow-up | `overdue_metrics` + `follow_up_tracker` + bulk action HTTP 207 | Carlos, Roberto |
| 5 | WOD/Coach maduro | Smart Paste, Day Apply/Undo, Template Archive (PRs #56/#57) e prescription preview | Beto |
| 6 | App do aluno expandido | sparkline RM, hint de cancelamento, banner PWA iOS, congelamento self-service, WOD D+1 | Júlia |
| 7 | Auditoria/SecOps | roles, admin privado, throttles, AuditEvent expandido para congelamento | Roberto |
| 8 | Importer resiliente | savepoint row-by-row + `error_rows` no retorno | Carlos |
| 9 | Performance em coach | `content-visibility:auto` no `.coach-session-card` | Beto |
| 10 | Page payloads | `shared_support/page_payloads.py` + presenters reduzem acoplamento visual | Engenharia |

### ATRITOS IDENTIFICADOS (Para Polir no Futuro)

| Severidade | Atrito | Impacto | Direção recomendada |
|---|---|---|---|
| Alta | Smoke visual por papel ainda não rodado nesta rodada | testes automatizados não provam sensação de tela | seguir `docs/rollout/beta-role-test-agenda.md` antes do beta amplo |
| Alta | Import em campanha sem barra de progresso visível | Carlos perde confiança em volume real | UI consumindo `error_rows` + ETA + reprocessamento |
| Alta | Notificação do aluno precisa de fallback multi-canal | push só não cobre todos os perfis | escalonamento push → email → WhatsApp por preferência |
| Média | Microcopy de erro genérica em integrações externas | Maria trava em exceção simples (Stripe/WhatsApp) | mensagens com causa + próxima ação |
| Média | Autocomplete de carga sugerida no editor WOD | coach digita carga na mão para aluno novo | usar `WorkoutPrescriptionPreview` + RM histórico |
| Média | Auditoria precisa de leitura executiva | owner não quer log bruto | sumário "quem, o que, risco, ação" |
| Média | Camada social no app do aluno | retenção atinge teto | turma, reação, presença, indicação |
| Baixa | Comparativo de mercado é feature parity declarada | não prova qualidade contra concorrente real | benchmark futuro com trial real |

---

## 🏁 CONCLUSÃO FORENSE

Em 20 dias simulados (com 22 atritos da rodada anterior já resolvidos via PR #53 — Ondas 1–4), o OctoBox sustenta uma operação realista de box sem depender de planilha como cérebro principal.

Quatro pilares estão vivos:

1. operação por papel (recepção, coach, manager, owner) com shell estável;
2. financeiro com leitura de ação (queue, overdue, follow-up, bulk com partial-commit);
3. app do aluno com Grade, WOD, RM (sparkline), PWA (banner iOS), congelamento self-service e WOD D+1;
4. SecOps base (roles, admin privado, throttles, AuditEvent crescente).

**Nota desta rodada da operação interna: 8.4/10** (vs 8.2 do Codex de 2026-04-28 antes de eu confirmar todas as remediações em runtime).

> O OctoBox saiu de "casa com estrutura" para "casa com placas pintadas". Falta agora trocar as fechaduras das portas críticas (notificação, import campanha, auditoria executiva) e ensinar a criança onde fica a cozinha (camada social do aluno).

---

# 🎽 ADENDO: SIMULAÇÃO DO ALUNO — 20 DIAS EM `/aluno/`

## 👤 Persona

**Júlia | 32 anos | aluna recorrente | social, curiosa, ansiosa leve, comunidade**

Ela não abre o app porque ama software. Ela abre se o app responder três perguntas:

1. Qual é o treino de hoje (e amanhã)?
2. Que horas e com quem eu treino?
3. Estou evoluindo?

Se o app responder com prazer, ela volta.

---

## Linha de simulação — Júlia (Highlights)

### 🗓️ Semana 1 — Descoberta

- **Dia 1:** entra por convite (`/aluno/entrar-com-convite/`). Token mágico, pouca fricção.
- **Dia 2:** vê grade e WOD. Hint "cancelar até 2h antes" (Onda 4) tira dúvida silenciosa.
- **Dia 3:** consulta RM. Sente que existe histórico, mesmo sem entender 100%.
- **Dia 4:** abre PWA de novo; banner iOS apareceu e ela instalou na home screen.
- **Dia 5-7:** usa para conferir treino mais que para interagir.

Nota da semana 1: **7.7/10**.

### 🗓️ Semana 2 — Hábito

- **Dia 8:** abre antes da aula.
- **Dia 9:** quer saber turma/horário; `StudentSessionAttendeesView` já entrega lista de inscritos.
- **Dia 10:** compara RM atual com treino sugerido — sparkline aparece quando há 2+ pontos.
- **Dia 11:** sente falta de "quem é amigo na turma".
- **Dia 12-14:** PWA virou utilitário diário; ainda não virou comunidade.

Nota da semana 2: **8.0/10**.

### 🗓️ Semana 3 — Retenção

- **Dia 15:** quer indicar a amiga; fluxo de indicação ainda é oportunidade.
- **Dia 16:** aula muda; recebe push (Onda 4 — `send_session_cancelled_push`). Loop fechou.
- **Dia 17:** vê WOD de D+1 (Onda 2) e decide ir mesmo cansada.
- **Dia 18:** quer rir/comentar/reagir — não tem onde.
- **Dia 19-20:** percebe progresso pela sparkline. Fica.

Nota da semana 3: **8.2/10**.

---

## 🩺 DIAGNÓSTICO — ALUNO

### O que vicia de forma saudável

1. WOD fácil de abrir (Home + WOD D+1).
2. Grade confiável com regra de cancelamento explícita.
3. RM com sparkline = progresso visível.
4. PWA/offline reduz atrito.
5. Congelamento self-service em 1 passo dá sensação de adulto.

### ATRITOS — ALUNO

| Atrito | Por que importa | Direção |
|---|---|---|
| Falta camada social | CrossFit é comunidade, não treino solitário | turma, reação, presença, indicação |
| Notificação precisa de fallback multi-canal | push só não basta para todo mundo | escalonamento push → email → WhatsApp |
| WOD/RM ainda parece técnico em pontos | Júlia não pensa em "slug" ou unidade | tradução humana de carga e progresso |
| Falta motivo diário emocional | sem loop diário vira só consulta | streak leve, próxima aula, conquista da turma |

---

## 🎯 Nota da Júlia

**8.0/10** (subiu de 7.8 do Codex graças a sparkline + WOD D+1 + push de cancelamento + congelamento).

O app já é útil e começa a virar emocional. Para ficar viciante, precisa social.

---

## 🧾 Nota OctoBox atualizada (incluindo Júlia)

| Persona | Peso tempo-de-tela | Nota |
|---|---:|---:|
| Júlia (Aluna) | 30% | 8.0 |
| Maria (Recepção) | 25% | 7.8 |
| Carlos (Manager) | 20% | 8.3 |
| Beto (Coach) | 18% | 8.9 |
| Roberto (Owner) | 7% | 9.2 |

**Média ponderada: 8.27/10**

Leitura curta:

1. excelente base para beta assistido — pode rodar com 1 box parceiro;
2. para beta amplo, falta smoke visual por papel + UI de progresso no import;
3. para retenção do aluno, falta camada social + fallback multi-canal de notificação;
4. para owner, falta auditoria em linguagem executiva.

---

# 🥊 COMPARATIVO DE MERCADO — OctoBox vs Nextfit vs Tecnofit

> Baseado em pesquisa pública de abril/2026 nos sites oficiais, Reclame Aqui, Play Store, App Store e centrais de ajuda dos concorrentes. OctoBox avaliado pelas simulações anteriores + esta rodada.
> **Ressalva honesta:** não testei Nextfit e Tecnofit em ambiente real — comparativo é de *feature parity declarada*, não de qualidade de execução.

## 📊 Tabela 1 — Operação do Box (Recepção, Coach, Manager, Owner)

| Capacidade | 🐙 OctoBox | 🟢 Nextfit | 🔵 Tecnofit |
|---|:---:|:---:|:---:|
| Operação por papel | ✅ shell forte e contextual | ✅ declarado app/gestão | ✅ declarado app/gestão |
| Quick sale / venda rápida | ✅ integrado ao financeiro, com guard-rail de valor | ✅ venda de planos/produtos | ✅ pagamento manual/automático |
| Financeiro visual com follow-up | ✅ overdue metrics + follow-up + bulk 207 | ✅ recorrência/pay | ✅ conta digital/financeiro |
| Recorrência própria madura | 🟡 via Stripe + integrações | ✅ Nextfit Pay | ✅ Conta Digital/Gateway |
| PIX automático recorrente declarado | 🟡 depende de evolução | ✅ declarado | 🟡 boleto/PIX declarado |
| WOD/RM específico para box | ✅ Smart Paste + Day Apply + Editor + Approval | 🟡 treinos genéricos | 🟡 treinos genéricos |
| Auditoria/SecOps avançada | ✅ roles + admin privado + AuditEvent crescente | ? não avaliado | ? não avaliado |
| RAG/agentes para engenharia | ✅ diferencial interno | ❌ não observado | ❌ não observado |
| Import resiliente em campanha | ✅ row-by-row + error_rows | 🟡 declarado | 🟡 declarado |

### Leitura da Tabela 1 — Experiência da Equipe

Nextfit e Tecnofit parecem mais maduros em meios de pagamento e ecossistema SaaS fitness consolidado.

O OctoBox se diferencia onde o assunto é **operação específica de box**: recepção de fluxo curto, coach de WOD/RM, owner snapshot executivo, auditoria, segurança e capacidade de evoluir com agentes.

Tese estratégica: se tentar competir como "sistema genérico de academia", perde tempo. Como **cérebro operacional premium para box**, tem espaço claro.

---

## 🎽 Tabela 2 — Experiência do Aluno

| Capacidade | 🐙 OctoBox | 🟢 Nextfit | 🔵 Tecnofit |
|---|:---:|:---:|:---:|
| App do aluno | ✅ PWA próprio em evolução | ✅ app declarado | ✅ app declarado |
| Pagamento pelo app | 🟡 integrado/roadmap | ✅ declarado | ✅ declarado |
| Treino/WOD do dia | ✅ específico para box, com D+1 | ✅ treinos declarados | ✅ treinos declarados |
| RM/progresso | ✅ sparkline visível com 2+ pontos | ✅ evolução de carga declarada | 🟡 acompanhamento declarado |
| Comunidade | ❌ ainda oportunidade | ✅ interação declarada | 🟡 comunicação declarada |
| Offline/PWA | ✅ diferencial técnico (banner iOS) | ? não avaliado | ? não avaliado |
| Indicação/social loop | ❌ oportunidade | ? não avaliado | ? não avaliado |
| Congelamento self-service | ✅ formulário + AuditEvent | 🟡 declarado | 🟡 declarado |
| Notificação crítica de aula | ✅ push (cancelamento) | ✅ declarado | ✅ declarado |

### Leitura da Tabela 2

O aluno é onde a guerra fica mais perigosa. Nextfit já comunica app com pagamento, treino, evolução e comunidade. Tecnofit comunica app customizado, planos, produtos e comunicação.

OctoBox precisa ganhar pela **especificidade do box**:

1. WOD do dia (e amanhã) sem fricção;
2. RM explicado como progresso visível (sparkline já entrega isso);
3. turma e presença como comunidade (gap principal);
4. notificações com fallback multi-canal;
5. indicação simples para amiga.

---

## 🏆 Verdict — Notas Comparativas

### Operação do Box (dono/manager/coach/recepção)

| Produto | Nota | Motivo |
|---|---:|---|
| OctoBox | **8.4** | forte em operação específica, WOD/RM, roles, auditoria, importer e engenharia |
| Nextfit | 8.5 | forte em ecossistema, app, pagamentos e maturidade comercial declarada |
| Tecnofit | 8.3 | forte em gestão ampla, financeiro e app declarado |

### Experiência do Aluno

| Produto | Nota | Motivo |
|---|---:|---|
| OctoBox | **8.0** | útil, PWA, RM com progresso, congelamento e push. Falta social/indicação |
| Nextfit | 8.6 | app com pagamento, treinos, evolução e comunidade declarados |
| Tecnofit | 8.2 | app e comunicação declarados; qualidade real não testada |

---

## 🎯 Conclusão Estratégica Honesta

O OctoBox não deve tentar ser "Nextfit menor" nem "Tecnofit clone".

A tese forte é:

> OctoBox é o **cockpit premium do box**: owner decide pelo iPhone, manager organiza, recepção executa sem virar analista, coach treina sem olhar pro notebook, aluno volta porque o app responde rápido.

Prioridade de evolução pós esta rodada:

1. smoke manual por papel (`docs/rollout/beta-role-test-agenda.md`);
2. UI de progresso + reprocessamento no import de campanha;
3. fallback multi-canal de notificação do aluno (push → email → WhatsApp);
4. camada social/indicação no app (turma, reação, indicação);
5. WOD/RM com autocomplete de carga sugerida usando histórico do aluno;
6. auditoria executiva para owner ("quem, o que, risco, ação");
7. pagamentos recorrentes mais nativos, sem esconder dependência de Stripe.

---

## 🧪 Próximo smoke recomendado

| Papel | Rota inicial | O que provar |
|---|---|---|
| Owner | `/dashboard/` | leitura geral, atalhos, alertas, admin privado quando aplicável |
| Recepção | `/operacao/recepcao/` | intake, pagamento pendente, ida e volta com Alunos |
| Coach | `/operacao/coach/` | ocorrência, chamada/WOD, feedback visível |
| Manager | `/operacao/manager/` | cards, contadores, CTAs, partial de boards |
| Alunos | `/alunos/` | busca, ficha, matrícula, pagamento, autocomplete |
| Financeiro | `/financeiro/` | inadimplência, cobrança, comunicação, bulk action |
| Aluno app | `/aluno/` | Grade, WOD, RM (sparkline), Settings (congelamento), PWA |

---

**Sources:**

### Fontes internas

1. `README.md`
2. `docs/reports/simulation_20_days_report.md` (template — este arquivo)
3. `docs/reports/simulation_20_days_codex.md` (rodada Codex de 2026-04-28)
4. `docs/reference/documentation-authority-map.md`
5. `docs/reference/functional-circuits-matrix.md`
6. `docs/rollout/beta-role-test-agenda.md`
7. PR `#53 — Resolve 22 friction items from 20-day simulation (Ondas 1–4)`
8. PRs `#56`, `#57`, `#58` (WOD corridor + Onda 6.1 + smoke stabilization)

### Fontes externas públicas

1. Nextfit — `https://nextfit.com.br/`
2. Nextfit Pay recorrência — central de ajuda Nextfit
3. Tecnofit Conta Digital — central de ajuda Tecnofit
4. Tecnofit pagamento do aluno — central de ajuda Tecnofit
