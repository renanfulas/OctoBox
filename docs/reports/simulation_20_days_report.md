# 🧠 SIMULAÇÃO MATRIX: 20 Dias no Frontline do OctoBox
**Projeto:** OctoBox Elite CrossFit | **Duração:** 20 Dias Corridos
**Alvo:** Avaliação de Carga Cognitiva, UX/UI, SecOps e Retenção.

> Simulação conduzida cruzando as 4 personas com os módulos reais do monorepo:
> `access/roles/{owner,manager,coach,reception}.py`, `quick_sales/`, `finance/`,
> `dashboard/`, `student_app/`, `students/`, `reporting/`, `communications/`,
> `integrations/` e `auditing/`.

---

## 👥 As Personas em Simulação

*   👱‍♀️ **Maria (Recepção) | 24 anos | 80 QI**
    *   **Perfil:** Habilidade técnica baixa. Clica primeiro, lê depois. Fica nervosa com tabelões de Excel. Só quer que o aluno pare de buzinar na porta.
    *   **Superfícies que usa:** `/recepcao/`, `/quick-sales/`, `/alunos/` (check-in rápido), shell `access/shell_actions.py` com role `reception`.
*   👨‍💼 **Carlos (Manager) | 30 anos | 100 QI**
    *   **Perfil:** Administrativo padrão. Resolve as confusões da Maria. Precisa ver números fáceis para gerar relatórios, fechar matrículas e configurar aulas.
    *   **Superfícies que usa:** `/dashboard/`, `/finance/` (queue, overdue, follow-ups), `/reporting/`, `/catalog/` (planos/aulas), role `manager`.
*   🏋️‍♂️ **Beto (Coach) | 28 anos | 102 QI**
    *   **Perfil:** Habilidade técnica nula por escolha. Odeia olhar pra tela, quer olhar pro aluno. Gosta de praticidade extrema no Box, na beira do ringue.
    *   **Superfícies que usa:** `/coach/` (wall + chamada), `student_app` mirror (RMs, WOD), shell coach via `access/roles/coach.py`.
*   🤵 **Roberto (Owner - Master Node) | 35 anos | 108 QI**
    *   **Perfil:** Executivo. Fica pouco no Box físico. Opera pelo iPhone. Quer ver o dinheiro cair e saber se ninguém está roubando a academia.
    *   **Superfícies que usa:** `dashboard/dashboard_snapshot_panels.py` (owner workspace), `finance/overdue_metrics.py`, `auditing/`, `security/`.

---

## Linha de simulação (Highlights)

### 🗓️ Semana 1 — Aquecimento e atrito inicial

**Dia 1 (Seg) — Onboarding coletivo**
- **Roberto** entra em `/dashboard/` pelo iPhone 15, vê o **Owner Snapshot** (MRR, inadimplência, headcount ativo). Sorri. Fecha o app em 38s.
- **Carlos** cadastra 42 alunos remanescentes via `/alunos/importar/`. Import CSV aborta na linha 17 (CPF com espaço). Log só diz *"erro ao processar"*. Carlos grunhe e corrige à mão.
- **Maria** tenta fazer o primeiro check-in. Procura botão "ENTRAR ALUNO". Não acha. Clica em "Quick Sale" achando que é. Cria uma venda fantasma de R$ 0,00. `quick_sales/services/` gera linha órfã.
- **Beto** ignora o sistema. Usa caderninho.

**Dia 2 (Ter) — Primeiro WOD**
- **Beto**, forçado pelo Carlos, abre `/coach/wall/`. Gosta: tela grande, nomes grandes, sem Excel. Dá ✔ em 18 alunos em 40 segundos. ADORA.
- **Maria** descobre o atalho `F` no teclado da recepção pra focar busca de aluno. Pra ela é mágica.
- **Carlos** cadastra o primeiro plano em `/catalog/`. Confunde "Plano" com "Produto avulso". Cria "Mensalidade Black" como produto. `finance/` depois não cobra recorrência.
- **Roberto** recebe push: *"Novo aluno matriculado: Júlia S."* Fica feliz.

**Dia 3 (Qua) — Primeiro pagamento**
- **Maria** recebe aluno atrasado (Pedro). Tenta cobrar no terminal. Não encontra "gerar link de pagamento". Liga pro Carlos.
- **Carlos** manda Maria usar `/quick-sales/novo/`. Funciona. Link WhatsApp sai em 11s. Maria fica orgulhosa.
- **Beto** bate a chamada via coach wall. 22/25 presença. Aluno "Lucas" marcado falta — era gêmeo, veio o outro. `student_identity` não tem confirmação facial.
- **Roberto** zero interação (viajando).

**Dia 4 (Qui) — Primeiro atrito sério**
- **Maria** confunde dois alunos homônimos ("João Silva"). Cobra o errado. `finance/follow_up_tracker.py` dispara WhatsApp pro João-correto que pagou em dia. João-correto reclama.
- **Carlos** precisa estornar. Busca "estorno" no menu. Não acha (está em `/finance/queue/` → ação contextual). Leva 9 minutos.
- **Roberto** vê no snapshot que houve estorno. Liga pro Carlos. Carlos jura que estava sob controle.

**Dia 5 (Sex) — Aula lotada**
- **Beto** precisa trocar aluno de turma. Abre `/coach/` no celular, entra em lista. Interface mobile esmaga colunas. Dá zoom, dá scroll horizontal. Reclama.
- **Maria** vende 4 avulsos num intervalo de 12 min. Quick sale voa. Melhor momento da semana pra ela.
- **Carlos** roda relatório de semana 1 em `/reporting/`. Exporta Excel. Carrega em 14s. Imprime. Mostra pro Roberto no sábado.

**Dia 6–7 — Fim de semana**
- Beto dá 1 aula no sábado. Tudo ok.
- Roberto passa no box, abre `/auditing/` pra "checar se ninguém roubou". Vê todos os eventos de estorno do Carlos. Confia.

### 🗓️ Semana 2 — Velocidade de cruzeiro

**Dia 8–10**
- **Maria** já memorizou 4 atalhos do shell de recepção. Faz check-in em 3s/aluno. `access/shell_actions.py` é o melhor amigo dela.
- **Carlos** configura WhatsApp template em `communications/` para cobrança D+3. Primeiro disparo em batch: 18 alunos em atraso, 11 respondem em 2h. Cobrança recuperada: R$ 3.840.
- **Beto** descobre o modo "WOD ativo" no display wall (`docs/experience/front-display-wall.md`). Coloca TV da sala ligada nele. Alunos amam. Beto amou mais ainda.

**Dia 11 — Webhook pagou mas sistema não atualizou**
- Aluno paga PIX, comprovante chega, mas o webhook do provedor atrasou 6 minutos. Maria vê "pendente" no sistema. Desconfia. Manda aluno esperar. Aluno se irrita.
- **Roberto** recebe no grupo do WhatsApp do Box: *"Sistema tá travado?"*. Abre `/integrations/` no iPhone. Vê `webhook_pagamento` com status OK mas delay. Identifica gargalo. Manda Carlos criar painel de retries.

**Dia 12 — Bulk action quebra**
- **Carlos** tenta reajustar preço de 180 planos de uma vez via admin. A mutação falha em 12 itens (permissões mistas). Rollback total. Perde 20 min de configuração.
- Sugere para si mesmo: ver `TICKETS_PRIORIZADOS.md` e criar "partial-commit bulk".

**Dia 13–14 — Fim de semana 2**
- Tráfego baixo. Snapshot do Owner mostra MRR subindo 4.2%. Roberto tira print, manda no grupo dos sócios.

### 🗓️ Semana 3 — Maturidade e limite do produto

**Dia 15 — Pico de matrículas (campanha)**
- Carlos roda campanha. 23 leads entram em 4h via `/onboarding/`. Fluxo `student_app/views/onboarding_views.py` segura bem, mas 2 leads travam no step "fingerprint/CPF" (middleware `student_auth.py` retorna redirect silencioso sem msg).
- Maria precisa converter manualmente via `/recepcao/leads/`. Ela se perde entre "lead", "aluno", "contato". Modelo conceitual confuso pra QI80.

**Dia 16 — Coach wall trava**
- Beto, em horário de pico (18h), abre 3 aulas simultâneas em abas. Navegador trava no iPad antigo. CSS do `coach/` não virtualiza lista. Beto volta pro caderninho por 20 min.

**Dia 17 — Owner audita**
- Roberto faz o primeiro "pente fino" mensal. Abre `/auditing/` + `/reporting/finance/` + `dashboard/dashboard_snapshot_queries.py` (owner view). Encontra 1 aluno com membership "ativa" sem pagamento há 43 dias (Carlos esqueceu de ativar cobrança). Pede correção.
- Confiança no sistema cresce, mas Roberto nota: **sem alerta proativo para "membership ativa sem cobrança"**.

**Dia 18 — Mobile Owner**
- Roberto opera 100% do iPhone no aeroporto. Aprova 3 estornos, valida snapshot mensal, responde 4 WhatsApps. Experience score pessoal: 9/10. Único atrito: botão de "Fechar ciclo financeiro" fica fora do viewport mobile.

**Dia 19 — Reporting fechamento de mês**
- Carlos gera fechamento. `reporting/` entrega PDF + Excel. Números batem com o que está no Owner Snapshot. Carlos exulta (salva 3h vs planilha antiga).
- Única ressalva: export Excel vira colunas misturadas (numérico como texto) em campos `valor_pago`.

**Dia 20 — Retrospectiva**
- Roberto reúne equipe. Pergunta: *"Voltariam pro sistema antigo?"*
  - Maria: "não, mas queria botão MAIOR pra check-in".
  - Carlos: "não, mas bulk action tá perigoso".
  - Beto: "não, mas não mexam no coach wall NUNCA".
  - Roberto: "dobro a aposta".

---

## 🩺 DIAGNÓSTICO PROFUNDO (O que funcionou e o Atrito)

### IMPACTOS POSITIVOS (UX/UI e Pagamento)

| # | Área | Observação | Persona beneficiada |
|---|------|------------|---------------------|
| 1 | **Owner Snapshot mobile** (`dashboard/dashboard_snapshot_panels.py`) | Carrega em <1.5s no iPhone, mostra MRR/inadimplência/headcount em 1 viewport | Roberto |
| 2 | **Quick Sale + link WhatsApp** (`quick_sales/services/`) | Fluxo de venda avulsa em ≤12s, gera link curto. Mataria a concorrência | Maria |
| 3 | **Coach Wall / Display Wall** | Zero fricção para chamada; nomes grandes, check em 1 tap | Beto |
| 4 | **Atalhos de teclado da Recepção** (`access/shell_actions.py`) | `F` para focar busca, Enter para check-in — Maria ganhou 2s/aluno | Maria |
| 5 | **Auditing trail** (`auditing/`) | Roberto detectou a membership "fantasma" em 4 cliques | Roberto |
| 6 | **Reporting de fechamento** | PDF + Excel batendo com Owner Snapshot — confiança nos números | Carlos |
| 7 | **Onboarding wizard** (`student_app/views/onboarding_views.py`) | Aguentou pico de 23 leads em 4h sem degradar | Carlos |
| 8 | **Follow-up de cobrança** (`finance/follow_up_tracker.py`) | Recuperou R$ 3.840 em 2h no primeiro disparo | Carlos/Roberto |

### ATRITOS IDENTIFICADOS (Para Polir no Futuro)

| # | Severidade | Atrito | Módulo | Fix sugerido |
|---|-----------|--------|--------|--------------|
| 1 | 🔴 Alta | **Homônimos**: Maria cobrou João-errado. Sem desambiguador visual | `students/facade` + recepção | Avatar + data nasc. inline no autocomplete |
| 2 | 🔴 Alta | **Quick Sale de R$ 0,00** passa sem validação | `quick_sales/services/` | Bloquear submit com valor ≤ 0 e clarificar que "Quick Sale ≠ Check-in" |
| 3 | 🔴 Alta | **Bulk action com rollback total** em permissões mistas | admin / `finance/` | Partial-commit + relatório itemizado (ver `REPORT_20_days.md:35`) |
| 4 | 🔴 Alta | **Membership ativa sem cobrança vinculada** (fantasma) não dispara alerta | `students/` + `finance/` | Sinal + painel Owner "Memberships sem contrato ativo" |
| 5 | 🟠 Média | **Webhook de pagamento com delay** sem feedback na UI | `integrations/` | Badge "aguardando confirmação" + estado transiente explícito |
| 6 | 🟠 Média | **Coach Wall trava com múltiplas aulas abertas em iPad antigo** | `coach/` templates/JS | Virtualização de lista (ver `mobile-virtualization-by-css-contract-2026-03-14.md`) |
| 7 | 🟠 Média | **CSV import** aborta em linha única, sem relatório itemizado | `students/` import | Continuar + CSV de erros (já previsto em `TICKETS_PRIORIZADOS.md`) |
| 8 | 🟠 Média | **Middleware `student_auth.py`** redireciona silenciosamente em onboarding (passo CPF/fingerprint) | `student_app/middleware/` | Flash message explicando por que o redirect aconteceu |
| 9 | 🟡 Baixa | **Export Excel** mistura tipos em `valor_pago` | `reporting/` | Forçar `Decimal` → string formatada + number format na célula |
| 10 | 🟡 Baixa | **"Fechar ciclo financeiro"** fora do viewport no iPhone | `finance/` mobile | Sticky footer no breakpoint ≤430px |
| 11 | 🟡 Baixa | **Conceitos Lead/Aluno/Contato** confusos para QI80 | `onboarding/` + recepção | Unificar rótulos + tour inline na primeira semana |
| 12 | 🟡 Baixa | **"Plano" vs "Produto avulso"** ambíguo no catálogo | `catalog/` | Dois CTAs distintos no wizard de criação |

---

## 🏁 CONCLUSÃO FORENSE

Em 20 dias, o OctoBox **sustentou a operação completa de um box CrossFit** sem que nenhuma persona pedisse para voltar ao sistema antigo — métrica qualitativa mais forte do relatório. Os fluxos críticos de **dinheiro** (Quick Sale, Follow-up, Owner Snapshot) e **pista** (Coach Wall, check-in da Recepção) performaram acima da expectativa para suas personas-alvo.

Os 12 atritos catalogados concentram-se em **três famílias**:
1. **Desambiguação humana** (homônimos, lead/aluno, plano/produto) — custo: Maria.
2. **Feedback de estado assíncrono** (webhook, bulk action, membership fantasma) — custo: Carlos e Roberto.
3. **Mobile/performance em dispositivos marginais** (iPad antigo, iPhone viewport) — custo: Beto e Roberto.

**Ranking de dor por persona:**
- 🥇 Maria → itens 1, 2, 11 (desambiguação e modelo conceitual).
- 🥈 Carlos → itens 3, 4, 7 (bulk e import/export).
- 🥉 Beto → item 6 (coach wall em pico).
- 🏅 Roberto → itens 4, 5, 10 (confiança + mobile ergonomia).

**Veredito:** produto em **estado shipável para 1 box**. Antes de escalar para multi-tenant, priorizar itens 1–4 da tabela de atritos. Itens 5–8 podem entrar em wave seguinte. Itens 9–12 são polish.

🚀

---

# 🎽 ADENDO: SIMULAÇÃO DO ALUNO — 20 DIAS EM `/aluno/`

> Continuidade narrativa: **Júlia** é a aluna cuja matrícula gerou o push do Dia 1 para o Roberto.
> Superfícies reais avaliadas: `student_app/views/{shell_views,membership_views,onboarding_views,pwa_views}.py`,
> `student_identity/`, `templates/student_app/{home,layout}.html`, `static/css/student_app/app.css`,
> PWA manifest/service worker, `/aluno/presenca/confirmar/`, `/aluno/rm/`, `/aluno/grade/`, `/aluno/wod/`.

## 👤 Persona

*   🎽 **Júlia (Aluna) | 27 anos | 95 QI**
    *   **Perfil:** Profissional, treina 4×/semana, usa iPhone 12. É fit-tracker friendly: já usou Strava, MyFitnessPal, Hevy. Não quer "mais um app", mas se o app poupar WhatsApp e planilha do coach, adota.
    *   **Objetivos:** (1) saber o WOD do dia antes de sair de casa; (2) bater RM sem planilha; (3) não perder aula por esquecimento de agenda; (4) pagar sem estresse.

---

## Linha de simulação — Júlia (Highlights)

### 🗓️ Semana 1 — Primeiro contato

**Dia 1 (Seg) — Matrícula**
- Maria cadastra Júlia na recepção. Envia link `/aluno/auth/login/` por WhatsApp.
- Júlia clica do iPhone. Cai no login. Digita CPF. Recebe SMS (via `student_identity`). Entra.
- Primeira tela: **home** em modo `schedule_default` (via `GetStudentDashboard` em `use_cases.py`). Vê grade da semana. **Gosta.**
- Tenta instalar PWA. iOS não mostra prompt automático. Precisa "Adicionar à Tela de Início" manual. Quase desiste. Acha por tentativa.

**Dia 2 (Ter) — Primeira aula**
- Abre app 18h. Home mudou sozinha para `wod_active`. Mostra WOD da próxima aula (19h). **Impressionada** — "como ele sabia?".
- Confirma presença em `/aluno/presenca/confirmar/`. Botão grande, 1 tap. ✅
- Chega no box. Beto já sabe que ela vem (apareceu no coach wall). Zero fricção.

**Dia 3 (Qua) — RM**
- Beto manda turma registrar RM de back squat. Júlia abre `/aluno/rm/`.
- Interface: lista de exercícios + input. Salva em `StudentExerciseMax`.
- Ela faz 72kg. Digita. Salva. Quer ver histórico. **Não acha histórico visual (gráfico).** Só lista. 🟠
- Volta pro Hevy pra plotar curva. Atrito.

**Dia 4 (Qui) — Desmarcar aula**
- Amanhece doente. Quer desmarcar 6h da manhã. Abre `/aluno/grade/`. Procura "desmarcar". Acha. Confirma.
- Recebe toast "Presença cancelada." Sem explicação de política de cancelamento (até que horas pode cancelar sem perder crédito).
- Liga pra Maria às 10h perguntando se perdeu aula. Maria também não sabe.

**Dia 5 (Sex) — Pagamento**
- Chega cobrança mensal. Link do Quick Sale cai no WhatsApp. Abre, paga PIX em 8s. Volta pro app, status ainda "pendente" (webhook delay — mesmo bug do Dia 11 do Roberto).
- Fica 4 minutos achando que o PIX não caiu. Manda print pro Maria. **Ansiedade.** 🔴

**Dia 6–7 — Fim de semana**
- Abre app no sábado só pra ver segunda. Satisfeita que carrega offline (PWA cached). ✅

### 🗓️ Semana 2 — Incorporação ao hábito

**Dia 8–10**
- Hábito: abre app 18h todo dia útil. Vê WOD. Confirma. Treina. Registra RM se bateu.
- Melhor momento: Dia 9, bate 75kg no back squat, salva, mostra pro namorado. Orgulho.
- Pior momento: Dia 10, app demora 4s pra abrir em 4G fraca. PWA cached resolveria, mas primeiro request ainda depende de rede (home com WOD dinâmico não é totalmente offline).

**Dia 11 — Mudança de box**
- Júlia viaja, vai treinar em box parceiro. Precisa trocar box ativo.
- Abre `/aluno/configuracoes/`. Encontra troca de box (`membership_views.py`). Funciona, mas a UX é densa — 3 passos, texto pequeno no iPhone. 🟠

**Dia 12 — WOD antecipado**
- Quer saber WOD de amanhã. Home só mostra o de hoje. Grade mostra horários, não WODs futuros.
- Manda mensagem pro Beto no WhatsApp. Beto responde "relax, é AMRAP de burpee". Ela reclama: "podia estar no app". 🟠

**Dia 13–14 — Fim de semana 2**
- Abre 1x no sábado. PWA bem. Nada a reportar.

### 🗓️ Semana 3 — Aluna madura

**Dia 15 — Campanha de matrícula**
- Júlia vê story do box com amiga nova. Tenta indicar. **Não existe fluxo de indicação no app.** 🟡
- Encaminha link de matrícula por WhatsApp manual.

**Dia 16 — Notificação perdida**
- Beto cancelou aula das 7h (caiu chuva, aquecimento seria ao ar livre). Avisou no grupo do WhatsApp.
- Júlia não viu o grupo (muda notificação). Foi pro box. Aula cancelada.
- **App não enviou push de cancelamento.** `communications/` não está wired com cancelamento de aula. 🔴

**Dia 17 — Feedback**
- Júlia responde pesquisa NPS (se existisse). Dá **8**. Comentário mental: "é bom, mas podia ser meu único app fitness, e ainda não é".

**Dia 18 — Apple Health**
- Depois do treino, queria que RM fosse pro Apple Health automaticamente. **Sem integração HealthKit.** 🟡
- Exportou manual. Desistiu em 2 dias.

**Dia 19 — Congelamento**
- Vai viajar 3 semanas. Quer congelar matrícula. Abre `/aluno/configuracoes/` → não acha "congelar".
- Liga pra Maria. Maria congela via admin. Júlia acha estranho que a ação dela precisa passar pela recepção. 🟠

**Dia 20 — Retrospectiva**
- Resumo da Júlia: *"Uso toda semana. Paguei 4 cobranças sem drama. Bati 2 RMs. Mas ainda abro Hevy pro gráfico e WhatsApp pro coach."*

---

## 🩺 DIAGNÓSTICO — ALUNO

### O QUE FUNCIONA (Valor percebido pela aluna)

| # | Área | Observação |
|---|------|------------|
| 1 | **Home dinâmica** (`schedule_default` ⇄ `wod_active` em `use_cases.py`) | Aluna percebe como "inteligência"; não parece tela de ERP |
| 2 | **Confirmar presença em 1 tap** (`/aluno/presenca/confirmar/`) | Fricção zero; compete com Strava em simplicidade |
| 3 | **PWA offline parcial** | Resolve cenário de 4G fraco ao chegar no box |
| 4 | **Registro de RM** (`StudentExerciseMax`) | Salva, persiste, sincroniza — base sólida |
| 5 | **Pagamento via Quick Sale link** | PIX em 8s sem login adicional |
| 6 | **Layout shell compartilhado** (`layout.html` + `app.css`) | Consistência visual entre home/grade/wod/rm/config |

### ATRITOS — ALUNO

| # | Severidade | Atrito | Módulo | Fix sugerido |
|---|-----------|--------|--------|--------------|
| A1 | 🔴 Alta | **Status de pagamento com delay de webhook** gera ansiedade na aluna | `integrations/` + `student_app` home | Estado "aguardando confirmação (≤5min)" explícito + push quando confirmar |
| A2 | 🔴 Alta | **Sem push de cancelamento de aula** | `communications/` + `coach/` | Wire cancelamento → push para quem confirmou presença |
| A3 | 🟠 Média | **Sem histórico visual de RM** (gráfico) | `/aluno/rm/` templates | Gráfico de linha por exercício (30/90/365 dias) |
| A4 | 🟠 Média | **Política de cancelamento opaca** | `/aluno/grade/` | Mostrar janela limite ("cancela sem perder crédito até 2h antes") |
| A5 | 🟠 Média | **WOD futuro não visível** | `use_cases.py` + home | Expor WOD de D+1 quando coach publicar |
| A6 | 🟠 Média | **Troca de box ativa densa em mobile** | `membership_views.py` | Redesign 3-passos → 1-passo com selector |
| A7 | 🟠 Média | **Congelar matrícula só via recepção** | `membership_views.py` | Auto-serviço com aprovação assíncrona |
| A8 | 🟡 Baixa | **Instalação PWA no iOS invisível** | `pwa_views.py` + `sw.js` | Banner "Adicionar à Tela" com tutorial visual |
| A9 | 🟡 Baixa | **Sem fluxo de indicação** | novo | CTA "Indicar amigo" → link de matrícula com tag UTM |
| A10 | 🟡 Baixa | **Sem integração HealthKit/Google Fit** | `student_app` + integrações nativas | Export RM/presença → Apple Health |

---

## 🎯 Nota da Júlia

**Nota da Júlia: 7.8 / 10**

Justificativa em uma linha: *"Uso toda semana e recomendaria, mas ainda divido atenção com Hevy e WhatsApp — não virou meu app único."*

**Decomposição:**
- Fluxo básico (ver WOD, confirmar, pagar): **9.0**
- Tracking de evolução (RM, histórico, gráfico): **6.5** ← o buraco.
- Comunicação com o box (cancelamento, indicação, congelar): **6.0** ← o outro buraco.
- Performance/PWA: **8.5**

---

## 🧾 Nota OctoBox atualizada (incluindo Júlia)

| Persona | Peso tempo-de-tela | Nota |
|---------|-------------------|------|
| Júlia (Aluna) | 30% | 7.8 |
| Maria (Recepção) | 25% | 7.5 |
| Carlos (Manager) | 20% | 8.0 |
| Beto (Coach) | 18% | 9.0 |
| Roberto (Owner) | 7% | 9.2 |

**Média ponderada (tempo de tela): 8.05 / 10**
**Média ponderada (poder de decisão — Roberto 40%, Carlos 25%, Beto 15%, Júlia 15%, Maria 5%): 8.6 / 10**

> A entrada da Júlia **puxou a nota pra baixo** — é a persona cujo app ainda tem mais gap entre "funciona" e "vicia". Os atritos A1 (ansiedade de pagamento) e A2 (push de cancelamento) são os que, resolvidos, elevariam a nota do aluno para 8.5+ e a nota consolidada do produto para a faixa de 9.

🎽

---

# 🥊 COMPARATIVO DE MERCADO — OctoBox vs Nextfit vs Tecnofit

> Baseado em pesquisa pública de abril/2026 nos sites oficiais, Play Store, App Store e centrais de ajuda dos concorrentes. OctoBox avaliado pelas simulações anteriores. **Ressalva honesta:** não testei Nextfit e Tecnofit em ambiente real — comparativo é de *feature parity declarada*, não de qualidade de execução.

## 📊 Tabela 1 — Operação do Box (Recepção, Coach, Manager, Owner)

| Capacidade | 🐙 OctoBox | 🟢 Nextfit | 🔵 Tecnofit |
|------------|:----------:|:---------:|:----------:|
| **Gateway de pagamento próprio** | ❌ (integra 3rd party) | ✅ **Next Fit Pay** (recorrência + retentativa inteligente) | ✅ (boletos, NF com poucos cliques) |
| **Cobrança recorrente automática** | 🟡 parcial (follow-up tracker) | ✅ nativo | ✅ nativo |
| **Emissão de NF automática** | ❌ | ✅ | ✅ |
| **Contrato eletrônico / assinatura** | ❌ | ✅ | 🟡 (não confirmado) |
| **Dashboard de inadimplência** | ✅ Owner Snapshot | ✅ (promete -80% inadim.) | ✅ (com CTA de negociação) |
| **Follow-up de cobrança via WhatsApp** | ✅ template configurável | ✅ lembretes automáticos | ✅ automatizado |
| **Integração com catraca** | ❌ | ✅ (parceiros) | 🟡 (não confirmado) |
| **Coach Wall / Display grande** | ✅ **diferencial** | 🟡 genérico | 🟡 não destacado |
| **Chamada/check-in em 1 tap** | ✅ | ✅ | ✅ |
| **Quick Sale (venda avulsa)** | ✅ link WhatsApp 12s | 🟡 via sistema geral | 🟡 via sistema geral |
| **Owner Snapshot mobile executivo** | ✅ **diferencial** | 🟡 dashboard padrão | 🟡 dashboard padrão |
| **Auditing trail granular** | ✅ | 🟡 logs básicos | 🟡 logs básicos |
| **Bulk actions seguras** | 🔴 rollback total em erro | ✅ maduro | ✅ maduro |
| **Import CSV robusto** | 🔴 aborta em linha única | ✅ com relatório | ✅ com relatório |
| **Multi-unidade / multi-box** | 🟡 não testado | ✅ redes | ✅ redes |
| **Módulo nutricional** | ❌ | ✅ | 🟡 parcial |
| **Avaliação física com fotos** | ❌ | ✅ | ✅ comparativo de fotos |
| **Maturidade de produto (anos)** | ~1–2 | 10+ | 10+ |
| **Base instalada** | 1 box (você) | 1M+ alunos/dia | Referência BR |

### Leitura da Tabela 1

- **Onde OctoBox ganha:** Owner Snapshot mobile, Coach Wall/Display, Quick Sale com link WhatsApp, auditing trail. São features onde o **opinionated design** venceu o "tudo pra todos" dos concorrentes.
- **Onde OctoBox perde por ausência:** gateway próprio (Next Fit Pay é vantagem competitiva séria), emissão fiscal automática, contrato eletrônico, integração catraca, módulo nutricional, avaliação física. Isso é **feature gap real**, não opinião.
- **Onde OctoBox perde por imaturidade:** bulk actions, import CSV, multi-tenant. Isso é *time on market*, resolve-se com waves de hardening.

---

## 🎽 Tabela 2 — Experiência do Aluno

| Capacidade | 🐙 OctoBox (Júlia) | 🟢 Nextfit | 🔵 Tecnofit Box |
|------------|:-----------------:|:---------:|:---------------:|
| **Ver WOD do dia** | ✅ home dinâmica | ✅ | ✅ timeline WOD |
| **Ver WOD de amanhã** | ❌ (atrito A5) | ✅ grade semanal | ✅ Agenda WOD |
| **Check-in de presença** | ✅ 1 tap | ✅ | ✅ |
| **Registro de RM / PR** | ✅ salva | ✅ com histórico | ✅ direto no app |
| **Gráfico histórico de RM** | ❌ (atrito A3) | ✅ progressão de carga | ✅ **evolução de movimentos e cargas** |
| **Pagar mensalidade no app** | ✅ via link Quick Sale | ✅ **in-app PIX/cartão/boleto** | ✅ in-app |
| **Status de pagamento claro** | 🔴 delay webhook causa ansiedade (A1) | ✅ confirmação imediata | ✅ confirmação imediata |
| **Push de cancelamento de aula** | ❌ (atrito A2) | ✅ | ✅ |
| **Avaliação do WOD / coach / RPE** | ❌ | ✅ | ✅ **+ NPS pós-WOD** |
| **Ranking do dia / gamificação** | ❌ | 🟡 parcial | ✅ **ranking + pontos de fitness level** |
| **Timeline social (fotos/vídeos)** | ❌ | 🟡 limitado | ✅ **timeline completa** |
| **Vídeos de execução de exercício** | ❌ | ✅ biblioteca | ✅ |
| **Avaliação física com comparativo fotos** | ❌ | ✅ | ✅ |
| **Congelar matrícula self-service** | ❌ (atrito A7) | ✅ | ✅ |
| **Indicação de amigo** | ❌ (atrito A9) | ✅ | ✅ |
| **PWA / App nativo** | 🟡 PWA (sem prompt iOS) | ✅ **app nativo iOS + Android** | ✅ **app nativo iOS + Android** |
| **Integração Apple Health / Google Fit** | ❌ (atrito A10) | 🟡 não confirmado | 🟡 não confirmado |
| **Acompanhamento nutricional** | ❌ | ✅ | 🟡 |

### Leitura da Tabela 2

O aluno é o eixo onde **OctoBox está mais atrás**. Os concorrentes evoluíram 10 anos mirando engajamento do aluno (Tecnofit especialmente, com timeline social, ranking, NPS, evolução visual). OctoBox entrega o "essencial que funciona" (ver WOD, confirmar, pagar, registrar RM), mas não tem **nenhum dos pilares de vício**:
- 🔴 **Social/ranking** (vicia o aluno competitivo — é o tipo de aluno que CrossFit atrai)
- 🔴 **Gráfico de evolução** (vicia o aluno tracker — compete com Hevy/Strava)
- 🔴 **App nativo** (vicia pela presença na home do iPhone)

---

## 🏆 Verdict — Notas Comparativas

### Operação do Box (dono/manager/coach/recepção)

| Sistema | Nota | One-liner |
|---------|:----:|-----------|
| 🟢 **Nextfit** | **8.8** | Maturidade + gateway próprio + fiscal + catraca. Mata por cobertura. |
| 🔵 **Tecnofit** | **8.7** | Foco em CrossFit nativo (Tecnofit Box), fluxo operacional polido. |
| 🐙 **OctoBox** | **8.4** | Owner Snapshot e Coach Wall são superiores; perde em fiscal/gateway/catraca. |

### Experiência do Aluno

| Sistema | Nota | One-liner |
|---------|:----:|-----------|
| 🔵 **Tecnofit Box** | **9.0** | Timeline social + NPS + ranking + evolução visual. Aluno vicia. |
| 🟢 **Nextfit** | **8.5** | Completo, nutrição integrada, pagamento in-app sólido. |
| 🐙 **OctoBox (Júlia)** | **7.8** | Essencial funciona, mas sem gatilhos de vício (social, gráfico, app nativo). |

---

## 🎯 Conclusão Estratégica Honesta

**OctoBox compete hoje em uma faixa de 8.0–8.5** — acima da média do mercado de ERPs de academia, mas **abaixo dos dois líderes consolidados** (Nextfit/Tecnofit) em cobertura de features. Duas leituras possíveis:

### 🅰️ Leitura pessimista (cabeça de produto corporativo)
*"Estamos 3–5 anos atrás em feature parity. Gateway próprio, app nativo, timeline social, fiscal, catraca — são anos de engenharia. Não vence no varejo."*

### 🅱️ Leitura otimista (cabeça de product-market-fit focado)
*"Nextfit/Tecnofit são suítes inchadas tentando servir academia tradicional + box + estúdio. OctoBox é **opinionated para box pequeno/médio** — Owner Snapshot mobile, Coach Wall, auditing sério, Quick Sale. Para o dono que desconfia da equipe e quer números honestos no iPhone, OctoBox **já é superior**."*

**Minha leitura:** a 🅱️ é defensável **se** OctoBox aceitar não competir em nutrição/avaliação física/timeline social e **dobrar** em:
1. **Confiança do dono** (Owner Snapshot, auditing, alertas proativos como "membership fantasma") ← já é diferencial.
2. **Velocidade operacional** (Quick Sale, Coach Wall, atalhos da recepção) ← já é diferencial.
3. **Integrar, não reimplementar**: plugar em gateway (Asaas/Pagar.me) em vez de construir; plugar em Hevy/Apple Health em vez de construir gráfico próprio; plugar em assinatura eletrônica (ZapSign/D4Sign) em vez de fazer contrato.

Se OctoBox tentar competir em **cobertura** com Nextfit/Tecnofit, perde. Se competir em **foco + honestidade de números + velocidade operacional**, ganha o segmento "dono-operador desconfiado de box único/rede pequena".

🥊

**Sources:**
- [Next Fit — Sistema para academias, estúdios e boxes](https://nextfit.com.br/)
- [Next Fit — Como utilizar o app do aluno](https://ajuda.nextfit.com.br/support/solutions/articles/69000555043-como-utilizar-o-aplicativo-do-aluno-geral-)
- [Next Fit Pay — Gestão financeira](https://nextfit.com.br/next-fit-pay/)
- [Tecnofit — Sistema de Gestão](https://www.tecnofit.com.br/)
- [Tecnofit Box — Google Play](https://play.google.com/store/apps/details?id=br.com.tecnofit.tecnofitBox)
- [Tecnofit — Experiência do Aluno](https://www.tecnofit.com.br/nossas-funcionalidades/experiencia-do-aluno/)
- [Tecnofit — FAQ Aplicativos](https://ajuda.tecnofit.com.br/pt-BR/support/solutions/articles/67000325049-faq-aplicativos-tecnofit)

