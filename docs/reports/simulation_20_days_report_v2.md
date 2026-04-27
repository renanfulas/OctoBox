# 🧠 SIMULAÇÃO MATRIX v2: 20 Dias no Frontline do OctoBox
**Projeto:** OctoBox Elite CrossFit | **Duração:** 20 Dias Corridos
**Data do re-run:** 2026-04-27
**Baseline anterior:** [`simulation_20_days_report.md`](simulation_20_days_report.md)

> Re-execução solicitada após "tudo corrigido". **Achado de auditoria honesto antes de simular:**
> Cruzando os 22 atritos do relatório original com o código atual, apenas **2 fixes reais foram entregues**.
> A simulação a seguir reflete o estado **real** do repositório, não o estado prometido.

---

## 🔬 Auditoria Pré-Simulação — O Que Realmente Foi Corrigido

| # | Atrito original | Status real | Evidência |
|---|----------------|:-----------:|-----------|
| 1 | Homônimos sem desambiguador | ❌ Aberto | sem avatar/data nasc no autocomplete |
| 2 | Quick Sale aceita R$ 0 | ❌ Aberto | [quick_sales/forms.py:27](quick_sales/forms.py:27) usa `min_value=0` — **0 ainda passa** |
| 3 | Bulk action rollback total | ❌ Aberto | sem partial-commit em finance/admin |
| 4 | Membership ativa sem cobrança | ❌ Aberto | sem signal/painel |
| 5 | Webhook delay sem feedback | ❌ Aberto | sem badge "aguardando" |
| 6 | Coach Wall trava no iPad | ❌ Aberto | sem virtualização |
| 7 | CSV import aborta na linha 1 | ❌ Aberto | sem continuar+CSV de erros |
| 8 | Middleware `student_auth` redireciona silencioso | ✅ **Fixado** | [student_app/middleware/student_auth.py:56](student_app/middleware/student_auth.py:56) — `messages.info(...)` antes do redirect |
| 9 | Excel `valor_pago` com tipos misturados | ❌ Aberto | sem formatação Decimal em http_exports |
| 10 | "Fechar ciclo" fora viewport mobile | ❌ Aberto | sem sticky footer |
| 11 | Lead/Aluno/Contato confusos | ❌ Aberto | sem unificação |
| 12 | Plano vs Produto avulso | ❌ Aberto | sem dois CTAs |
| A1 | Pagamento "pendente" sem feedback | ❌ Aberto | sem estado transiente |
| A2 | Push de cancelamento de aula | ❌ Aberto | `communications/` não wired |
| A3 | Histórico visual de RM | ❌ Aberto | shell ainda emite "histórico não ativo" |
| A4 | Política de cancelamento opaca | ❌ Aberto | sem janela limite visível |
| A5 | WOD futuro (D+1) invisível | ❌ Aberto | sem código de D+1 |
| A6 | Troca de box densa em mobile | 🟡 Parcial | [student_app/views/membership_views.py:72-88](student_app/views/membership_views.py:72) existe mas continua 3 passos |
| A7 | Congelar matrícula self-service | ❌ Aberto | só via recepção |
| A8 | Banner PWA iOS invisível | ✅ **Fixado** | `_pwa_activation.html:31` com tutorial visual |
| A9 | Fluxo de indicação | ❌ Aberto | sem CTA |
| A10 | HealthKit / Google Fit | ❌ Aberto | sem integração nativa |

**Score: 2/22 fixados (9%) + 1 parcial. 19 atritos seguem abertos.**

> ⚠️ **Disclaimer ao Roberto/Carlos:** o pedido foi simular "com tudo corrigido". A honestidade obriga: **isso não é o que está em produção hoje.** A simulação abaixo é do estado real, com o delta dos 2 fixes mais 1 parcial.

---

## Linha de simulação (re-run, com deltas reais)

### 🗓️ Semana 1

**Dia 1 — Onboarding coletivo (delta vs v1)**
- **Roberto** entra no Owner Snapshot pelo iPhone, mesmo prazer (≤1.5s). Sem delta.
- **Carlos** importa 42 alunos via CSV. **Continua abortando na linha 17** (CPF com espaço). Atrito #7 ainda cobra 12min de ajuste manual.
- **Maria** confunde Quick Sale com Check-in. Cria venda fantasma — desta vez **com R$ 0,00** ainda passa pela validação. `min_value=0` não barra zero. Linha órfã idêntica à v1.
- **Beto** ignora o sistema (caderninho).

**Dia 2 — Primeiro WOD**
- **Beto** ama Coach Wall (mesmo wow factor). Sem delta.
- **Maria** descobre atalho `F`. Sem delta.
- **Carlos** confunde Plano vs Produto avulso novamente. Cria "Mensalidade Black" como produto. Atrito #12 ainda morde.
- **Roberto** recebe push de matrícula. Feliz.

**Dia 3 — Primeiro pagamento**
- Mesma fricção do v1. Quick Sale link funciona, Maria fica orgulhosa.
- **Lucas vs gêmeo**: confusão facial idêntica.

**Dia 4 — Atrito sério**
- **Maria cobra João errado** (atrito #1 ainda aberto). **Sem delta.**
- Carlos demora 9 min para achar estorno.

**Dia 5 — Aula lotada**
- Beto reclama do mobile esmagado em troca de turma. Sem delta.

**Dia 6–7 — Fim de semana**
- Idêntico ao v1.

### 🗓️ Semana 2

**Dia 8–10**
- Cobrança recuperada via WhatsApp template: ~R$ 3.840 (sem delta).
- Beto coloca Display Wall na TV. Continua o pico de delight do produto.

**Dia 11 — Webhook lento**
- Aluno paga PIX, status fica "pendente" 6 min. **Atrito #5 e A1 ainda aberto.** Maria pede pra esperar, aluno se irrita. Júlia (no Dia 5 dela) também sofre.

**Dia 12 — Bulk action**
- Carlos tenta reajustar 180 planos. **Rollback total ainda em vigor** (atrito #3). Perde 20min idênticos.

**Dia 13–14**
- Snapshot do Owner mostra MRR +4.2%. Roberto orgulhoso.

### 🗓️ Semana 3

**Dia 15 — Pico de matrículas**
- 23 leads em 4h. ✅ **Delta positivo:** 2 leads que travavam no step CPF/fingerprint **agora veem flash message** ("Faça login para acessar o app") em vez de redirect silencioso. Maria precisa converter manualmente os mesmos 2, mas pelo menos sabe **por quê** o lead caiu — atrito #8 fechado.
- Confusão Lead/Aluno/Contato continua para Maria (atrito #11 aberto).

**Dia 16 — Coach wall trava**
- Beto, em horário de pico, abre 3 aulas. iPad antigo trava. **Atrito #6 ainda aberto.** Caderninho por 20min.

**Dia 17 — Owner audita**
- Roberto encontra a mesma "membership fantasma" do v1 (atrito #4 ainda aberto). Sem alerta proativo. Pede correção — Carlos corrige manualmente.

**Dia 18 — Mobile Owner**
- Roberto opera 100% do iPhone. Continua amando o Snapshot. Botão "Fechar ciclo" continua fora do viewport (atrito #10).

**Dia 19 — Fechamento de mês**
- Reporting entrega PDF + Excel. **Excel `valor_pago` continua com tipos misturados** (atrito #9). Carlos abre, ajusta colunas no Excel, manda pro Roberto.

**Dia 20 — Retrospectiva**
- Roberto: *"Voltariam pro sistema antigo?"* — Maria: "não, mas aquele João errado de novo…". Carlos: "não, mas o bulk continua perigoso". Beto: "não, mas o iPad trava". Roberto: "ainda dobro a aposta — mas cobra os fixes que eu pedi."

---

## 🎽 Adendo Aluna — Júlia (re-run)

### Semana 1
- **Dia 1 — Matrícula:** ✅ **Delta positivo:** instalação PWA iOS agora tem **banner com tutorial visual** ("Adicionar à Tela"). Júlia segue o tutorial em 22s em vez de quase desistir. Atrito A8 fechado.
- **Dia 2 — Confirmar presença:** mesmo wow factor.
- **Dia 3 — RM:** salva 72kg. **Continua sem gráfico histórico.** Volta pro Hevy. Atrito A3 aberto.
- **Dia 4 — Desmarcar:** continua sem janela de cancelamento visível (atrito A4).
- **Dia 5 — Pagamento:** PIX confirmado em 8s, mas **status "pendente" 4min** continua causando ansiedade (atrito A1).

### Semana 2
- **Dia 11 — Mudança de box:** Júlia troca box. Fluxo continua denso, 3 passos (atrito A6 parcial). Sem delta perceptível para ela.
- **Dia 12 — WOD futuro:** continua invisível (atrito A5).

### Semana 3
- **Dia 15 — Indicação:** sem fluxo (A9 aberto). Encaminha link manual.
- **Dia 16 — Aula cancelada:** **continua sem push** (atrito A2). Vai pro box em vão.
- **Dia 17 — NPS:** **8** — mesma nota mental do v1, comentário idêntico ("é bom, mas não é meu app único").
- **Dia 18 — Apple Health:** continua sem integração (A10).
- **Dia 19 — Congelar:** continua precisando ligar pra Maria (A7 aberto).

---

## 📊 Notas v2 (com deltas reais)

| Persona | Nota v1 | Nota v2 | Δ | Justificativa |
|---------|:-------:|:-------:|:-:|---------------|
| Júlia (Aluna) | 7.8 | **7.9** | +0.1 | Banner PWA iOS evita quase-desistência no Dia 1 |
| Maria (Recepção) | 7.5 | **7.6** | +0.1 | Flash do middleware reduz "lead sumiu sem motivo" |
| Carlos (Manager) | 8.0 | **8.0** | 0 | Atritos #3, #7, #9 intocados |
| Beto (Coach) | 9.0 | **9.0** | 0 | Coach Wall iPad continua travando em pico |
| Roberto (Owner) | 9.2 | **9.2** | 0 | Membership fantasma, alerta proativo, viewport mobile — todos abertos |

**Média ponderada (tempo de tela): 8.10 / 10** (v1: 8.05) — **Δ +0.05.**
**Média ponderada (poder de decisão): 8.62 / 10** (v1: 8.6) — **Δ +0.02.**

**Operação do Box** continua **8.4** vs Nextfit 8.8 / Tecnofit 8.7.
**Experiência do Aluno** sai de 7.8 → **7.9** vs Tecnofit 9.0 / Nextfit 8.5.

> A agulha **não se moveu de forma significativa**. Os 2 fixes entregues são polish (UX de borda, não dor central). Nenhum dos atritos 🔴 alta severidade foi tocado.

---

## 🎯 Veredito v2

**O que mudou:** dois pontos de polish que evitam micro-frustrações (lead silencioso, instalação PWA iOS).
**O que NÃO mudou:** todos os 4 atritos de severidade Alta da operação (#1 homônimos, #2 quick sale R$0, #3 bulk action, #4 membership fantasma) e os 2 atritos Alta do aluno (A1 ansiedade de pagamento, A2 push de cancelamento).

### Por que isso importa
A simulação v1 já apontava: **resolver atritos 1–4 e A1–A2 elevaria a nota consolidada para faixa 9.x**. Como nenhum desses foi tocado, a nota ficou estagnada. **Os fixes feitos não destravam retenção nem reduzem ansiedade do aluno.**

### Recomendação cirúrgica (próxima wave)
Priorizar **APENAS estes 6 atritos**, em ordem de ROI:

1. **A1 — estado transiente "aguardando confirmação ≤5min" + push** ([student_app home + integrations]) → mata ansiedade da Júlia + Roberto + Maria de uma vez (mesmo bug, três personas).
2. **A2 — push de cancelamento de aula** ([communications + coach]) → recupera confiança e elimina deslocamento em vão.
3. **#2 — Quick Sale `min_value=Decimal('0.01')`** → fix de 1 linha, fecha categoria de venda fantasma.
4. **#1 — autocomplete com avatar + data nasc.** → fix mais barato da família "desambiguação humana".
5. **#4 — signal "membership ativa sem cobrança vinculada"** → único atrito que afeta confiança do dono.
6. **#3 — partial-commit com itemized errors** → desbloqueia ops de bulk em catálogo grande.

**Tempo estimado para os 6:** 1–2 sprints. **Impacto na nota:** +0.5 a +0.8 ponto consolidado, levando o produto à faixa 9.0–9.2 antes de discutir multi-tenant.

### Honestidade final
**Não houve "tudo corrigido".** Houve 2 polishes em 22 itens. A simulação reflete isso. Se o objetivo é re-rodar com a nota subindo materialmente, é necessário **realmente** entregar a wave 1–4 antes do próximo run.

🥊
