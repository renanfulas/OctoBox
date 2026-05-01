# 🧠 SIMULAÇÃO MATRIX CODEX: 20 Dias no Frontline do OctoBox
**Projeto:** OctoBox Elite CrossFit | **Duração:** 20 Dias Corridos  
**Data da simulação Codex:** 2026-04-28  
**Alvo:** Avaliação de carga cognitiva, UX/UI, SecOps, retenção, operação por papel e vantagem competitiva.

> Simulação conduzida no estilo de `docs/reports/simulation_20_days_report.md`, mas ancorada na regra de autoridade atual:
> runtime real, testes e código vencem quando o template antigo diverge.
>
> Superfícies cruzadas: `access/`, `operations/`, `quick_sales/`, `catalog/`, `finance/`,
> `dashboard/`, `student_app/`, `students/`, `reporting/`, `communications/`,
> `integrations/`, `auditing/`, `knowledge/` e docs de rollout.

---

## 🔎 Como o Codex rodou a simulação

Esta simulação não é um teste manual visual completo no navegador. Ela é uma simulação operacional com três fontes:

1. leitura do doc-base `docs/reports/simulation_20_days_report.md`;
2. cruzamento com docs vivos: `README.md`, `docs/reference/documentation-authority-map.md`, `docs/reference/functional-circuits-matrix.md`, `docs/rollout/beta-role-test-agenda.md`;
3. validação automatizada focada nas áreas da simulação.

Evidência operacional usada:

| Evidência | Resultado |
|---|---:|
| RAG interno local | 1384 documentos ativos, 11514 chunks, 0 embeddings |
| `manage.py check --settings=config.settings.test` | sem issues |
| Suite focada de simulação | 149 testes passaram |

Suite focada:

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

Ressalva honesta:

1. isto é um relatório de simulação e leitura técnica, não um relatório canônico de arquitetura;
2. o comparativo de mercado usa recursos publicamente declarados, não teste real em ambiente Next Fit/Tecnofit;
3. para liberar beta, este relatório deve ser complementado por smoke manual por papel.

---

## 👥 As Personas em Simulação

* 👱‍♀️ **Maria (Recepção) | 24 anos | 80 QI**
  * **Perfil:** habilidade técnica baixa. Clica primeiro, lê depois. Quer resolver a fila e não virar analista de sistema.
  * **Superfícies reais:** `operacao/recepcao/`, `quick-sales/`, `alunos/`, atalhos em `access/shell_actions.py`.

* 👨‍💼 **Carlos (Manager) | 30 anos | 100 QI**
  * **Perfil:** administrativo padrão. Quer ver número, resolver matrícula, organizar aula e cobrar sem drama.
  * **Superfícies reais:** `dashboard/`, `financeiro/`, `reporting/`, `catalog/`, `operacao/gerente/`.

* 🏋️‍♂️ **Beto (Coach) | 28 anos | 102 QI**
  * **Perfil:** habilidade técnica nula por escolha. Quer olhar para a turma, não para o notebook.
  * **Superfícies reais:** `operacao/coach/`, WOD, chamada, ocorrências, ponte WOD/RM e app do aluno.

* 🤵 **Roberto (Owner - Master Node) | 35 anos | 108 QI**
  * **Perfil:** executivo. Opera muito pelo iPhone. Quer saber dinheiro, risco, crescimento e se a operação está limpa.
  * **Superfícies reais:** `dashboard/`, snapshots do dashboard, `financeiro/`, auditoria, segurança e rotas privadas.

* 👱‍♀️ **Júlia (Aluna) | 32 anos | 85 QI**
  * **Perfil:** curiosa, ansiosa leve, social, abre Instagram todo dia, quer saber treino, turma e evolução.
  * **Superfícies reais:** `aluno/`, `aluno/grade/`, `aluno/wod/`, `aluno/rm/`, PWA/offline, convite e troca de box.

---

## Linha de simulação (Highlights)

### 🗓️ Semana 1 — Aquecimento, primeira confiança e atrito de borda

**Dia 1 — Onboarding coletivo**

- Roberto acessa `dashboard/` pelo iPhone e entende o básico: caixa, inadimplência, headcount e alertas.
- Carlos usa `alunos/` e `financeiro/` para organizar remanescentes. Não sente que está numa planilha.
- Maria cai em `operacao/recepcao/`; entende as filas principais, mas ainda depende dos nomes dos botões.
- Beto abre `operacao/coach/`; quer só ver aula e registrar algo rápido.
- Júlia entra pelo convite no app do aluno e quer chegar logo no WOD.

**Leitura Codex:** o sistema já tem “rua principal” clara. O risco está nas placas pequenas. Para usuário iniciante, um CTA mal nomeado vira um cruzamento sem semáforo.

**Dia 2 — Primeiras vendas e cobranças**

- Maria vende avulso pelo Quick Sales sem entrar em fluxo longo.
- Carlos confere cobrança e status no financeiro.
- Roberto vê pressão financeira sem pedir relatório.

**O que funcionou:** Quick Sales conectado ao financeiro reduz muito carga cognitiva da recepção.

**Atrito:** quando algo dá errado, Maria precisa de microcopy mais explícita: “o que aconteceu, por quê, e o que faço agora”.

**Dia 3 — Aula cheia**

- Beto precisa registrar presença e ocorrência sem perder contato visual com a turma.
- A estrutura de operações e coach segura o fluxo, mas qualquer texto longo na tela vira ruído.

**Leitura Codex:** coach precisa de interface de semáforo: verde, amarelo, vermelho. Se ele tiver que ler manual, perdeu.

**Dia 4 — Primeiro lead importado**

- Carlos testa fluxo de lead/importação.
- O pipeline de importação existe, mas precisa sempre mostrar progresso e erro por linha em volume real.

**Atrito:** import sem progresso é “panela de pressão sem válvula”: você não sabe se está cozinhando ou prestes a explodir.

**Dia 5 — Fechamento de semana**

- Roberto pede leitura curta: “ganhamos ou perdemos a semana?”.
- Dashboard entrega direção, mas a narrativa ainda pode ficar mais executiva: causa, impacto, próxima ação.

**Dia 6-7 — Fim de semana**

- Júlia olha o WOD antes da aula. Se a tela carrega com clareza, ela se engaja.
- Se a turma/horário não aparece com confiança, ela volta para WhatsApp.

---

### 🗓️ Semana 2 — Velocidade de cruzeiro e pressão operacional

**Dia 8 — Maria ganha memória muscular**

- Maria memoriza os atalhos de recepção e quick sale.
- O shell por papel vira mapa mental.

**Impacto:** a operação começa a parecer simples. Isso é muito forte comercialmente.

**Risco:** se os atalhos do shell apontarem para âncoras quebradas, a confiança despenca rápido.

**Dia 9 — Carlos organiza follow-up financeiro**

- Carlos usa a fila financeira, leitura de inadimplência e comunicação semiautomática.
- A parte financeira já tem força: status, follow-up, retenção e churn aparecem como camada visual.

**Atrito:** follow-up financeiro precisa evitar “piloto automático perigoso”. Mensagem errada em cobrança parece erro humano, mesmo quando foi sistema.

**Dia 10 — Beto usa WOD/RM**

- Beto cruza WOD com RM e quer carga sugerida.
- O dado já tem ponte WOD/RM, mas a simulação mostra que o ouro está no preview de prescrição e no autocomplete.

**Débito técnico avisado:** se WOD/RM crescer com telas irmãs demais e sem narrativa única, o coach volta a digitar na mão. Isso cria dívida de UX e de regra.

**Dia 11 — Roberto olha auditoria**

- Roberto quer saber se ninguém mexeu em coisa crítica.
- Auditoria, roles, admin privado e hardening existem, mas precisam virar linguagem executiva.

**Boa tradução para usuário:** “Quem mexeu? O que mudou? Teve risco? Preciso agir?”

**Dia 12 — Júlia começa a voltar pelo app**

- Ela abre `aluno/wod/`, `aluno/grade/` e `aluno/rm/`.
- O PWA/offline cria sensação de aplicativo de verdade.

**Atrito:** falta mais cola social: quem vai, conquista, indicação, reação da turma, mini-loop de comunidade.

**Dia 13-14 — Operação sem fundador**

- Owner não está fisicamente no box.
- Manager e recepção conseguem operar sem pedir intervenção.

**Métrica qualitativa:** ninguém pede para voltar para WhatsApp/planilha.

---

### 🗓️ Semana 3 — Maturidade, campanha e limite do produto

**Dia 15 — Campanha de matrícula**

- Entram muitos leads em pouco tempo.
- A arquitetura suporta pipeline e domínio, mas a experiência precisa ser implacável: progresso, duplicata, falha por linha, reprocessamento.

**Risco:** campanha é onde produto bom parece ruim se import/export parecer caixa-preta.

**Dia 16 — Aula cancelada**

- Beto cancela/ajusta aula.
- Júlia precisa ser avisada no app/fluxo certo.

**Atrito:** se a notificação útil não fecha o loop, o WhatsApp volta a ser o sistema nervoso real do box.

**Dia 17 — Inadimplência sobe**

- Financeiro identifica pressão.
- Carlos age; Roberto enxerga.

**Ponto forte:** a leitura financeira já está mais madura do que CRUD comum.

**Ponto a polir:** cobrança precisa separar “lembrete educado”, “risco real” e “ação de bloqueio”. Tudo com tom humano.

**Dia 18 — Coach propõe WOD**

- Beto monta WOD.
- Manager/Owner aprova quando necessário.

**Ponto forte:** trilha de aprovação evita publicar treino sem governança.

**Risco:** permissão frouxa aqui vira bug grave. WOD publicado errado é visível para aluno e afeta confiança.

**Dia 19 — Owner faz leitura executiva**

- Roberto pergunta: “qual gargalo está me custando dinheiro?”.
- O sistema consegue juntar alunos, financeiro, operação e dashboard.

**Próximo salto:** transformar leitura em “próxima melhor ação” por papel.

**Dia 20 — Fechamento forense**

- Maria opera.
- Carlos organiza.
- Beto dá aula.
- Roberto decide.
- Júlia volta.

**Conclusão da semana 3:** o OctoBox já se comporta como sistema operacional do box, não só cadastro bonito.

---

## 🩺 DIAGNÓSTICO PROFUNDO

### IMPACTOS POSITIVOS (UX/UI, operação e pagamento)

| # | Área | Observação | Persona beneficiada |
|---:|---|---|---|
| 1 | Shell por papel | Reduz decisão e evita menu genérico demais | Maria, Carlos, Beto |
| 2 | Dashboard snapshot | Dá leitura rápida para dono sem abrir 10 telas | Roberto |
| 3 | Quick Sales | Vende rápido sem transformar recepção em financeiro avançado | Maria |
| 4 | Financeiro visual | Inadimplência e follow-up aparecem como trabalho, não só tabela | Carlos, Roberto |
| 5 | WOD/Coach | Fluxo tem base forte para autoria, aprovação e ponte com RM | Beto |
| 6 | App do aluno | Grade, WOD, RM e PWA já criam hábito potencial | Júlia |
| 7 | Auditoria/SecOps | Roles, admin privado, throttles e logs elevam confiança | Roberto |
| 8 | RAG interno | Ajuda Codex/agentes a navegar docs e código rapidamente | Time técnico |
| 9 | Page payloads/presenters | Reduz acoplamento visual e deixa tela mais governável | Engenharia |
| 10 | Testes focados | 149 testes verdes nas áreas da simulação dão boa confiança local | Produto |

### ATRITOS IDENTIFICADOS (Para Polir no Futuro)

| Severidade | Atrito | Impacto | Direção recomendada |
|---|---|---|---|
| Alta | Smoke visual por papel ainda precisa ser rodado antes de beta | teste automatizado não prova sensação real da tela | seguir `docs/rollout/beta-role-test-agenda.md` |
| Alta | Import/export pode virar caixa-preta em campanha | Carlos perde confiança em volume | progresso, ETA, falha por linha, reprocessamento |
| Alta | Notificação do aluno ainda é ponto sensível | WhatsApp volta a dominar | evento crítico precisa fechar loop no app |
| Média | Microcopy de erro precisa ser mais humana | Maria trava em exceção simples | mensagens com causa + próxima ação |
| Média | WOD/RM precisa seguir narrativa única | coach pode voltar ao manual | autocomplete, preview e CTA único por política |
| Média | Auditoria precisa de leitura executiva | owner não quer log bruto | “quem, o que, risco, ação” |
| Baixa | Comparativo de mercado ainda é feature parity | não prova qualidade contra concorrente | futuro benchmark real com trial/demo |

---

## 🏁 CONCLUSÃO FORENSE

Em 20 dias simulados, o OctoBox sustenta uma operação realista de box sem depender de planilha como cérebro principal. Isso é grande.

O produto já tem quatro pilares vivos:

1. operação por papel;
2. financeiro com leitura de ação;
3. app do aluno com Grade/WOD/RM/PWA;
4. segurança/auditoria suficientes para começar a falar sério de beta.

Nota Codex da operação interna: **8.2/10**.

Tradução simples:

> O OctoBox já é uma casa com estrutura, porta, luz e água. Agora precisamos pintar as placas, testar as fechaduras e garantir que uma criança consiga achar a cozinha sem chamar o arquiteto.

---

# 🎽 ADENDO: SIMULAÇÃO DO ALUNO — 20 DIAS EM `/aluno/`

## 👤 Persona

**Júlia | 32 anos | aluna recorrente | social, curiosa, ansiosa leve**

Ela não abre o app porque ama software. Ela abre se o app responder três perguntas:

1. Qual é o treino?
2. Que horas e com quem eu treino?
3. Estou evoluindo?

Se o app responder isso com prazer, ela volta.

---

## Linha de simulação — Júlia (Highlights)

### 🗓️ Semana 1 — Descoberta

- Dia 1: entra por convite. Se o token/convite parecer mágico e sem fricção, ganha confiança.
- Dia 2: vê grade e WOD. Se precisa perguntar no WhatsApp, o app perdeu a primeira batalha.
- Dia 3: consulta RM. Ainda não entende tudo, mas sente que existe histórico.
- Dia 4: abre PWA de novo. Se carrega rápido, vira atalho mental.
- Dia 5-7: usa mais para conferir treino do que para interagir.

Nota da semana 1: **7.5/10**.

### 🗓️ Semana 2 — Hábito

- Dia 8: abre antes da aula.
- Dia 9: quer saber turma/horário.
- Dia 10: compara RM com treino.
- Dia 11: sente falta de “quem vai treinar”.
- Dia 12-14: app vira utilitário, mas ainda não vira comunidade.

Nota da semana 2: **7.9/10**.

### 🗓️ Semana 3 — Retenção

- Dia 15: quer indicar amiga; fluxo de indicação ainda é oportunidade.
- Dia 16: aula muda; notificação precisa ser certeira.
- Dia 17: vê WOD e decide ir mesmo cansada.
- Dia 18: quer rir/comentar/reagir.
- Dia 19-20: se percebe progresso, fica.

Nota da semana 3: **8.0/10**.

---

## 🩺 DIAGNÓSTICO — ALUNO

### O que vicia de forma saudável

1. WOD fácil de abrir.
2. Grade confiável.
3. RM como progresso pessoal.
4. PWA/offline reduz atrito.
5. Troca de box e identidade deixam base pronta para expansão.

### ATRITOS — ALUNO

| Atrito | Por que importa | Direção |
|---|---|---|
| Falta camada social | CrossFit é comunidade, não só treino | turma, reação, presença, indicação |
| Notificação crítica precisa fechar loop | mudança de aula sem aviso quebra confiança | eventos com push/email/WhatsApp conforme canal |
| WOD/RM pode parecer técnico demais | Júlia não pensa em “slug” | traduzir carga e progresso em linguagem humana |
| App precisa dar motivo diário | sem loop diário, vira só consulta | streak leve, próxima aula, conquista, lembrete |

---

## 🎯 Nota da Júlia

**7.8/10**

O app do aluno já é útil. Para ficar viciante, precisa virar social, emocional e progressivo.

---

## 🧾 Nota OctoBox atualizada (incluindo Júlia)

| Persona | Peso tempo-de-tela | Nota |
|---|---:|---:|
| Júlia (Aluna) | 30% | 7.8 |
| Maria (Recepção) | 25% | 7.6 |
| Carlos (Manager) | 20% | 8.1 |
| Beto (Coach) | 18% | 8.8 |
| Roberto (Owner) | 7% | 9.1 |

**Média ponderada:** **8.05/10**

Leitura:

1. excelente base para beta assistido;
2. falta smoke visual por papel;
3. falta transformar aluno em loop de comunidade;
4. falta polir import/export/notificações para carga real.

---

# 🥊 COMPARATIVO DE MERCADO — OctoBox vs Next Fit vs Tecnofit

> Baseado em pesquisa pública de abril/2026 em fontes oficiais.  
> Ressalva honesta: não testei Next Fit nem Tecnofit em ambiente real; comparativo é de *feature parity declarada*, não de qualidade de execução.

## 📊 Tabela 1 — Operação do Box (Recepção, Coach, Manager, Owner)

| Capacidade | 🐙 OctoBox | 🟢 Next Fit | 🔵 Tecnofit |
|---|:---:|:---:|:---:|
| Operação por papel | ✅ forte e contextual | ✅ declarado app/gestão | ✅ declarado app/gestão |
| Quick sale / venda rápida | ✅ integrado ao financeiro | ✅ venda de planos/produtos | ✅ pagamento manual/automático |
| Financeiro visual com follow-up | ✅ forte no repo | ✅ recorrência/pay | ✅ conta digital/financeiro |
| Recorrência própria madura | 🟡 via integrações/Stripe | ✅ Next Fit Pay | ✅ Conta Digital/Gateway |
| PIX automático/recorrente declarado | 🟡 depende evolução | ✅ declarado | 🟡 boleto/PIX e automações declaradas |
| WOD/RM para box | ✅ direção específica | 🟡 treinos genéricos declarados | 🟡 treinos genéricos declarados |
| Auditoria/SecOps avançada | ✅ diferencial técnico | ? não avaliado | ? não avaliado |
| RAG interno para engenharia/produto | ✅ diferencial interno | ❌ não observado | ❌ não observado |

### Leitura da Tabela 1 — Experiência da Equipe

Next Fit e Tecnofit parecem mais maduros em meios de pagamento e ecossistema SaaS fitness consolidado.

O OctoBox se diferencia quando o assunto é operação específica de box: recepção, coach, WOD/RM, owner snapshot, auditoria, segurança e capacidade de evoluir com agentes/RAG.

Se tentar competir como “sistema genérico de academia”, perde tempo. Se competir como **cérebro operacional premium para box**, tem tese.

---

## 🎽 Tabela 2 — Experiência do Aluno

| Capacidade | 🐙 OctoBox | 🟢 Next Fit | 🔵 Tecnofit |
|---|:---:|:---:|:---:|
| App do aluno | ✅ PWA próprio em evolução | ✅ app declarado | ✅ app declarado |
| Pagamento pelo app | 🟡 integrado/roadmap | ✅ declarado | ✅ declarado |
| Treino/WOD | ✅ específico para box | ✅ treinos declarados | ✅ treinos declarados |
| RM/progresso | ✅ direção específica | ✅ evolução de carga declarada | 🟡 treino/acompanhamento declarado |
| Comunidade | 🟡 oportunidade | ✅ interação declarada | 🟡 app/comunicação declarados |
| Offline/PWA | ✅ diferencial técnico | ? não avaliado | ? não avaliado |
| Indicação/social loop | ❌ oportunidade | ? não avaliado | ? não avaliado |

### Leitura da Tabela 2

O aluno é onde a guerra fica mais perigosa. Next Fit já comunica app com pagamento, treino, evolução e comunidade. Tecnofit comunica app customizado, planos, produtos e comunicação.

O OctoBox precisa ganhar pela especificidade do box:

1. WOD do dia sem fricção;
2. RM explicado como progresso;
3. turma e presença como comunidade;
4. notificações realmente úteis;
5. indicação simples.

---

## 🏆 Verdict — Notas Comparativas

### Operação do Box

| Produto | Nota Codex | Motivo |
|---|---:|---|
| OctoBox | 8.2 | forte em operação específica, WOD/RM, roles, auditoria e engenharia |
| Next Fit | 8.5 | forte em ecossistema, app, pagamentos e maturidade comercial declarada |
| Tecnofit | 8.3 | forte em gestão ampla, financeiro e app declarado |

### Experiência do Aluno

| Produto | Nota Codex | Motivo |
|---|---:|---|
| OctoBox | 7.8 | útil e promissor; precisa social/retention loop |
| Next Fit | 8.6 | app do aluno com pagamento, treinos, evolução e comunidade declarados |
| Tecnofit | 8.2 | app e comunicação declarados; qualidade real não testada |

---

## 🎯 Conclusão Estratégica Honesta

O OctoBox não deve tentar ser “Next Fit menor” nem “Tecnofit clone”.

A tese forte é:

> OctoBox é o cockpit premium do box: owner decide, manager organiza, recepção executa, coach treina e aluno volta.

Prioridade de evolução:

1. smoke manual por papel;
2. import/export com progresso e falha por linha;
3. notificações críticas do aluno;
4. camada social/indicação no app;
5. WOD/RM com autocomplete e preview;
6. auditoria executiva para owner;
7. pagamentos recorrentes mais maduros, sem esconder dependências externas.

---

## 🧪 Próximo smoke recomendado

Use `docs/rollout/beta-role-test-agenda.md` e registre:

| Papel | Rota inicial | O que provar |
|---|---|---|
| Owner | `dashboard/` | leitura geral, atalhos, alertas, admin privado quando aplicável |
| Recepção | `operacao/recepcao/` | intake, pagamento pendente, ida e volta com Alunos |
| Coach | `operacao/coach/` | ocorrência, chamada/WOD, feedback visível |
| Gerente | `operacao/gerente/` | cards, contadores, CTAs |
| Alunos | `alunos/` | busca, ficha, matrícula, pagamento |
| Financeiro | `financeiro/` | inadimplência, cobrança, comunicação |
| Aluno app | `aluno/` | Grade, WOD, RM, offline/PWA |

---

## 🧠 Prompt operacional para repetir esta simulação

```text
Você é o Codex dentro do repo OctoBOX.

Objetivo:
Rode uma simulação de 20 dias de uso real do OctoBox por Maria (Recepção),
Carlos (Manager), Beto (Coach), Roberto (Owner) e Júlia (Aluna).

Regras:
1. Leia README.md, docs/reference/documentation-authority-map.md,
   docs/reference/functional-circuits-matrix.md e docs/rollout/beta-role-test-agenda.md.
2. Use docs/reports/simulation_20_days_report.md como estilo, não como verdade absoluta.
3. Se houver divergência entre template e runtime, runtime vence.
4. Consulte o RAG interno com search_project_knowledge quando precisar localizar ownership.
5. Rode manage.py check e uma suíte focada nas áreas simuladas.
6. Escreva relatório com:
   - personas;
   - highlights por semana;
   - impactos positivos;
   - atritos;
   - diagnóstico do app do aluno;
   - nota ponderada;
   - comparativo de mercado com ressalva;
   - próximos smokes recomendados.
7. Avise explicitamente qualquer risco de débito técnico.
```

---

## Sources

### Fontes internas

1. `README.md`
2. `docs/reports/simulation_20_days_report.md`
3. `docs/reference/documentation-authority-map.md`
4. `docs/reference/functional-circuits-matrix.md`
5. `docs/rollout/beta-role-test-agenda.md`
6. `knowledge/management/commands/search_project_knowledge.py`

### Fontes externas públicas

1. Next Fit — `https://nextfit.com.br/`
2. Next Fit Pay recorrência — `https://ajuda.nextfit.com.br/support/solutions/articles/69000556570-como-receber-na-recorr%C3%AAncia-por-boleto-pix-e-cart%C3%A3o-de-cr%C3%A9dito-`
3. Next Fit Pay Pix Automático — `https://ajuda.nextfit.com.br/support/solutions/articles/69000872321-como-funciona-o-pix-autom%25C3%25A1tico-no-next-fit-pay-`
4. Tecnofit Conta Digital — `https://ajuda.tecnofit.com.br/pt-BR/support/solutions/articles/67000747548-conta-digital-tecnofit-quais-as-vantagens-de-cobrar-com-boleto-pix-`
5. Tecnofit pagamento do aluno — `https://ajuda.tecnofit.com.br/pt-BR/support/solutions/articles/67000732964-como-receber-o-pagamento-do-meu-aluno-`
