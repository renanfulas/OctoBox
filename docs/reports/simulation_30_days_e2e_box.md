<!--
ARQUIVO: relatorio da simulacao E2E de 30 dias de operacao de um box.

POR QUE ELE EXISTE:
- Registra o resultado de uma simulacao executada contra o app rodando
  (runserver + PostgreSQL), por HTTP, com 4 personas de staff e 88 alunos.
- Serve de baseline de qualidade percebida e de lista priorizada de correcoes.

O QUE ESTE ARQUIVO FAZ:
1. Descreve o metodo e o que foi realmente exercitado.
2. Da nota por papel, com atributos, e a percepcao de cada persona.
3. Lista crashes, bugs, bloqueios e friccoes — todos verificados no runtime.

DOCUMENTO:
- relatorio de simulacao; nao e especificacao. Runtime e testes vencem.
-->

# Simulação E2E — 30 dias de operação do CrossFit Serra Norte

**Data da execução original:** 30/08/2026
**Data da reverificação:** 30/08/2026 (mesmo dia, após 3 commits de correção)
**Ambiente:** `runserver` + PostgreSQL 16 local, Django 6.0.8, DEBUG=True
**Harness:** `tools/simulations/e2e_box_30d/` (HTTP real, com CSRF e sessão, sem atalho por ORM)

---

## 0. Reverificação pós-correção (Segurança e Recuperação de erro)

Depois da simulação original, três commits corrigiram os achados mais graves:
`ac3fce4` (S1, B1, e o primeiro guard do bulk-action), `d77548b` (o `AttributeError`
residual que a correção do bulk-action tinha deixado passar) e `ade6c4b` (8 pontos
de recuperação de erro: C1, C3, B4, 404 customizado, mensagem da recepção,
mensagem de conflito de reserva, e o reenvio self-service do e-mail — S4).

Esta seção reverifica **apenas** os achados de Segurança (§7) e Recuperação de
erro (§5, §6, §9) contra o código atual, com o mesmo runtime real (não é
releitura de código): 4 papéis de staff logados, um cadastro novo criado para
testar o reenvio de e-mail, e reservas reais provocadas de propósito para
disparar o conflito.

| # | Achado | Status | Evidência da reverificação |
|---|---|---|---|
| S1 | Sessão gravada em texto puro em `playwright_debug.log` a cada 403 | ✅ **Corrigido** | 5 negações de permissão seguidas (Coach em `/financeiro/`, Recepção em `/operacao/owner/`) — o arquivo nunca foi criado |
| S2 | App do aluno (`/aluno/`) fora do rate limit de escrita | ⚠️ **Não endereçado** | `WRITE_PATH_PREFIXES` continua sem `/aluno/`. Check-in, RM e congelamento de matrícula seguem sem throttle |
| S3 | Rate limit de login por IP (compartilhado pelo box inteiro) | ⚠️ **Não endereçado** | `_get_actor_token()` ainda usa `f'ip:{...}'` para usuário anônimo — comportamento inalterado |
| S4 | Cliente pago sem caminho quando o e-mail de ativação falha | ✅ **Corrigido** | Criei um cadastro novo, marquei como pago via webhook, e testei o botão de reenvio: 404 para pending inexistente, 502 tratado (não 500) quando o SMTP real está fora do ar, **429 no reenvio imediato seguinte** (rate limit próprio funcionando), e o botão aparece na tela de sucesso |
| C1 | `GET` no checkpoint semanal quebrava com `ImproperlyConfigured` (500) | ✅ **Corrigido** | Um F5 simulado na URL agora responde 200/302 (redireciona de volta ao planner) |
| C2 | `bulk-action` com corpo malformado ou JSON válido não-objeto → 500 | ✅ **Corrigido** | Corpo truncado e `null` retornam 400 os dois, sem traceback |
| C3 | `payment-link` vazava o texto bruto do erro da Stripe num 500 | ✅ **Corrigido** | Com o egress de rede ainda bloqueado neste ambiente (mesma causa raiz do achado original), a rota agora responde **502** com mensagem de negócio (*"Não foi possível gerar o link agora... confirme o pagamento pelo balcão"*), não mais 500 cru |
| B4 | Workspace do Manager desativado devolvia 404 mudo | ✅ **Corrigido (parcial)** | O 404 agora explica o motivo (`ManagerWorkspaceAvailabilityMixin`). A funcionalidade em si **continua desligada** por padrão (`OPERATIONS_MANAGER_WORKSPACE_ENABLED=False`) — decisão de produto, não um bug |
| — | Rota inexistente sem 404 customizado (nota da seção 9) | ⚠️ **Parcial** | `templates/404.html` on-brand foi criado e está corretamente amarrado (convenção padrão do Django, ativa só com `DEBUG=False`). Mas o catch-all de autenticação de `/rota-que-nao-existe-xyz/` **continua redirecionando para `/login/`** em vez de chegar a um 404 — o soft-404 da seção 9 não foi tocado |
| — | Recepção: erro de baixa de pagamento sempre citava os 3 campos | ✅ **Corrigido** | Com só o método inválido, a mensagem agora diz exatamente *"Revise metodo."* em vez de sempre citar vencimento, método e referência |
| — | Aluno: mensagem de conflito de reserva sem dizer qual aula/horário | ✅ **Corrigido** | Mensagem nova: *"Você já tem uma reserva ativa em CrossFit 19h (amanhã às 19:00). Cancele-a para reservar esta, ou espere ela terminar."* — nomeia a aula, o horário, e oferece a saída. A regra de negócio por trás (P3, uma reserva ativa por vez) **continua a mesma** — só a comunicação do bloqueio melhorou |

**Resultado líquido:** dos 4 achados de Segurança, **2 corrigidos** (S1, S4) e
**2 seguem abertos** (S2, S3 — nenhum dos dois estava no escopo dos commits de
correção). Dos 3 crashes, **os 3 foram corrigidos**. Das fricções de mensagem
citadas nas notas de Recuperação de erro por persona, **todas as testadas
foram corrigidas**, exceto o soft-404 (fora do escopo dos commits) e os
bloqueios de produto que são decisão consciente (P3, P4, B4-a-funcionalidade-
em-si) — esses continuam de propósito, só a comunicação ao redor deles melhorou.

Suíte automatizada relevante após a reverificação: **236 testes, 0 falhas**
(`tests/test_signup_resend_activation.py`, `tests/test_error_scenarios.py`,
`tests/test_workout_weekly_governance.py`, `boxcore/tests/test_catalog.py`,
`student_app/tests.py`, `access/tests/`, `integrations/`,
`tests/test_payment_views_coverage.py`).

---

## 1. O que foi realmente executado

| | |
|---|---|
| Chamadas HTTP registradas | **7.566** (30 dias) + 79 na varredura funcional |
| Personas de staff | Maria (Recepção, QI 89), Eric (Coach, QI 95), Diego (Manager, QI 102), Fernando (Owner, QI 110) |
| Alunos | **88** com app ativo (meta 90; 2 travaram no cadastro) |
| Aulas na grade | **161** em 6 semanas |
| Cobranças geradas | **1.056** · baixadas **90** · **R$ 104.995,80** recebidos |
| WODs publicados | 48 (2 por dia útil) |
| RMs registrados pelos alunos | 333 |
| Leads de balcão | 15 |
| Reservas de aula | **88 em 30 dias** ← ver achado #14 |
| Crashes (5xx) no loop de 30 dias | **0** |
| Latência | p50 **88 ms** · p95 **176 ms** · p99 **193 ms** |

O fluxo do dia 0 foi feito de ponta a ponta pelo produto: checkout público →
webhook Stripe assinado (HMAC) → `PendingSignup` marcado como pago → wizard de
onboarding → **provisionamento do schema `box_crossfit-serra-norte`** → box ativo.

---

## 2. Nota por papel

### Maria — Recepção (QI 89) · ~~6,4~~ → **7,2 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 8 | O painel da recepção mostra a fila de pagamentos do dia sem ela precisar procurar |
| Velocidade | 9 | p50 56 ms, p95 119 ms — a tela nunca a fez esperar |
| Autonomia | 3 | **Não pode fazer check-in de ninguém** (403) e não pode ver o financeiro — inalterado, fora do escopo desta correção |
| Recuperação de erro | ~~6~~ → **9** | ✅ Reverificado: com só o método inválido, a mensagem agora diz *"Revise metodo."* em vez de sempre citar os 3 campos possíveis |
| Confiança no sistema | 6 | Nada quebrou na frente dela em 30 dias |

### Eric — Coach (QI 95) · ~~7,6~~ → **8,4 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 8 | Editor de WOD, planner, biblioteca de templates e histórico são coerentes entre si |
| Velocidade | 9 | p50 68 ms, p95 144 ms; salvar WOD em 124 ms |
| Autonomia | 8 | É o único papel que consegue dar check-in; controla WOD, blocos, prescrição por 1RM e ocorrência técnica |
| Recuperação de erro | ~~6~~ → **8** | ✅ Reverificado: um F5 no checkpoint semanal agora redireciona em vez de derrubar a tela com 500. Salvar WOD sem `intent` continua mudo (não estava no escopo desta correção) |
| Confiança no sistema | ~~7~~ → **9** | O crash que mais o abalava (checkpoint semanal) não existe mais |

### Diego — Manager (QI 102) · ~~5,8~~ → **6,8 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 7 | Dashboard e financeiro com filtro de inadimplência entregam o que ele precisa |
| Velocidade | 9 | p50 60 ms, p95 146 ms |
| Autonomia | 4 | **O workspace do Manager continua desligado por padrão** (agora um 404 explicado, não um 404 mudo) — ligar `OPERATIONS_MANAGER_WORKSPACE_ENABLED` é decisão de produto, fora do escopo desta correção |
| Recuperação de erro | ~~4~~ → **9** | ✅ Reverificado nos dois pontos: o 404 agora diz "espaço de trabalho do Manager está desativado neste box" em vez de vir mudo; e a API de ação em lote responde 400 tratado a qualquer corpo malformado (era 500) |
| Confiança no sistema | ~~5~~ → **6** | A tela do cargo dele ainda não abre — mas agora pelo menos ela conta o porquê, em vez de parecer quebrada |

### Fernando — Owner (QI 110) · ~~6,0~~ → **7,4 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 8 | Workspace do owner, resumo executivo e relatórios contam a história do box |
| Velocidade | 9 | p50 60 ms, p95 110 ms — o mais rápido de todos |
| Autonomia | ~~3~~ → **6** | ✅ O painel de webhooks agora abre pra ele (era 403 por um erro de capitalização). **Ainda não consegue cadastrar a própria equipe pelo app** — P1 segue fora do escopo |
| Recuperação de erro | ~~5~~ → **9** | ✅ Reverificado de ponta a ponta: reenvio de e-mail responde 404 pra cadastro inexistente, 502 tratado quando o envio falha (não 500), **429 num segundo pedido imediato** (rate limit próprio), e o botão de reenvio aparece na tela de sucesso |
| Confiança no sistema | 7 | O provisionamento do box funcionou na primeira, e isso vale muito |

### Alunos (90 · QI médio 93) · ~~5,2~~ → **5,8 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 9 | Home, grade, WOD e RM em telas curtas; PWA com manifest, service worker e página offline |
| Velocidade | 8 | p50 88 ms, p95 176 ms em 6.415 chamadas |
| Autonomia | 2 | **Só entram com Google.** Sem provider configurado, ninguém entra e a mensagem manda "falar com a recepção" — que não tem como liberar. Inalterado, fora do escopo |
| Recuperação de erro | ~~6~~ → **8** | ✅ Reverificado: a mensagem de conflito agora nomeia a aula e o horário e oferece cancelar (*"Você já tem uma reserva ativa em CrossFit 19h (amanhã às 19:00). Cancele-a..."*) em vez de só travar |
| Confiança no sistema | ~~4~~ → **5** | A regra de fundo (uma reserva ativa por vez, P3) **não mudou** — só a comunicação em volta dela. 88 alunos continuam limitados a 1 aula reservada por vez |

---

## 3. Facilidade de uso — ~~6,2~~ → **7,0 / 10**

O produto é rápido, bonito e bem escrito em português. O que derrubava a nota
não era complexidade: era **falta de caminho** — e boa parte desse "falta de
caminho" era, na verdade, mensagem de erro capenga em cima de uma
funcionalidade que já existia (a baixa de pagamento da recepção sempre
funcionou; ela só não dizia qual campo estava errado). Essa parte foi
corrigida e reverificada (§0). O que **continua** faltando é caminho de
verdade — funcionalidade que simplesmente não existe: o Owner não consegue
cadastrar a própria equipe pelo app (P1), o aluno depende de um provider
externo sem plano B (P2), a Recepção não pode dar check-in (P4), e o Manager
segue sem workspace ligado por padrão (P4/B4-produto). Esses quatro seguem
sem solução nesta rodada — são decisão de produto, não bug de mensagem.

---

## 4. O que o app resolveu de verdade

- **Matou a planilha de cobrança.** 1.056 cobranças geradas automaticamente na
  matrícula, fila do dia pronta na tela da recepção, R$ 104.995,80 baixados em
  90 operações de balcão com método, vencimento e referência registrados.
- **Deu ao coach um lugar único para o WOD.** 48 treinos publicados, com blocos,
  prévia de prescrição por 1RM da turma e histórico versionado.
- **Deu ao dono números sem pedir para ninguém.** Resumo executivo e relatórios
  abrem em ~60 ms sem exportar nada.
- **Colocou o treino no bolso do aluno.** 333 RMs registrados pelos próprios
  atletas em 30 dias — dado que antes não existia em lugar nenhum.
- **Isolou o box de verdade.** O schema `box_crossfit-serra-norte` foi criado no
  provisionamento e a fronteira de papéis segurou: anônimo cai no login em toda
  rota protegida, Maria toma 403 no financeiro, Eric toma 403 em entradas, Diego
  toma 403 no workspace do owner.
- **Aguentou 30 dias sem cair.** 7.566 requisições, zero 5xx no loop diário.

## Estão mais felizes? *(atualizado após a correção)*

**Eric e Fernando, mais ainda.** O coach ganhou uma ferramenta que ele não tinha
e não é mais interrompido pelo crash do checkpoint semanal; o dono ganhou
visibilidade sem cobrar relatório de ninguém e agora vê o painel de webhooks
que antes tomava 403 dele.
**Maria, sim — dentro do que a tela permite.** Ela continua sem poder dar
baixa em presença ou ver o financeiro que ela mesma cobra (isso não mudou),
mas parou de adivinhar qual campo errou numa baixa de pagamento.
**Diego, sim — mas o cargo dele ainda não tem tela.** Agora pelo menos sabe
por quê (404 explicado em vez de mudo), e a API de ação em lote não crasha
mais nele.
**Os alunos, ainda divididos, mas menos frustrados.** A reserva de aula — o
motivo número um de abrir o app — **continua travada em 1 por vez** (decisão
de produto, P3). O que mudou é que agora, quando trava, o app diz qual aula
está no caminho e oferece cancelar — antes só travava.

---

## 5. O que crashou (5xx verificado) — ✅ os 3 corrigidos e reverificados (§0)

| # | Rota | Erro | Impacto | Status |
|---|---|---|---|---|
| C1 | `GET /operacao/wod/aprovacoes/checkpoint-semanal/` | `ImproperlyConfigured: TemplateResponseMixin requires either a definition of 'template_name'...` | A view é só POST e não tem `template_name`. Um F5, um "voltar" ou um link salvo derruba a tela com 500 | ✅ Corrigido — `get()` agora redireciona |
| C2 | `POST /api/v1/finance/payments/bulk-action/` e `POST /api/v1/finance/freeze-student/` | `json.decoder.JSONDecodeError` em `api/v1/bulk_views.py:21` | `json.loads(request.body)` sem guarda: corpo não-JSON vira **500 em vez de 400**. Com JSON válido, ambas respondem 200/400 corretamente | ✅ Corrigido — 2 rodadas (JSON malformado + JSON válido não-objeto) |
| C3 | `GET /api/v1/finance/payment-link/<id>/` | 500 devolvendo o texto bruto do erro da Stripe no corpo | Falha de gateway deveria ser 502 com mensagem de negócio, não 500 vazando detalhe interno. *(Causa raiz aqui: egress bloqueado no ambiente.)* | ✅ Corrigido — agora 502 com mensagem de negócio |

## 6. O que bugou (sem 5xx, mas quebrado)

| # | Achado | Evidência | Status |
|---|---|---|---|
| B1 | **Painel de webhooks é inacessível para todo mundo** | `integrations/views.py:29,56` usa `allowed_roles=('owner','manager','dev')` minúsculo; `get_user_role().slug` devolve `Owner`/`Manager`/`DEV`. Fernando (Owner) toma 403 | ✅ Corrigido — matriz de papéis reverificada: Owner e Manager 200, Coach e Recepção 403 (inalterado, correto) |
| B2 | **Vazamento entre boxes no seletor de coach** | Criei `coach_de_outro_box` com Group `Coach` e **zero Membership neste box**; ele aparece na lista de coaches de Fernando. `_get_class_coach_queryset()` filtra só por Group, e `auth_user` vive no schema `public` — sem filtro por Box | ⚠️ Não endereçado |
| B3 | **A origem do papel está partida ao meio** | O papel vem de `Membership` (é o que o checkout cria), mas o seletor de coach lê `Group`. O Owner criado pelo próprio fluxo de venda nasce sem Group e nunca aparece como coach. Eric só apareceu depois de eu atribuir o Group na mão | ⚠️ Não endereçado |
| B4 | **Workspace do Manager não existe por padrão** | `OPERATIONS_MANAGER_WORKSPACE_ENABLED=False`. `/operacao/manager/` devolve **404 cru** para o próprio Manager, e `/operacao/` o joga no dashboard genérico | ⚠️ Parcial — o 404 agora explica o motivo; a funcionalidade continua desligada (decisão de produto) |
| B5 | **Export xlsx devolve 404** | `/alunos/exportar/xlsx/` e `/financeiro/exportar/xlsx/`. CSV e PDF funcionam | ⚠️ Não endereçado |
| B6 | **Rotas de fragmento respondem 405 sem corpo** | `GET /alunos/<id>/drawer/profile/` — 90 ocorrências no journal. Sem mensagem, sem `Allow` legível para o usuário | ⚠️ Não endereçado |

## 7. Segurança (o que mais me preocupou) — 2 de 4 corrigidos e reverificados (§0)

| # | Achado | Detalhe | Status |
|---|---|---|---|
| S1 | **Cookie de sessão gravado em disco em texto puro** | `access/permissions/mixins.py` grava `playwright_debug.log` a **cada negação de permissão**, com `sessionid`, `csrftoken` e todos os headers. Não é protegido por `DEBUG`, não tem rotação e cresce sob varredura. Verificado: o arquivo existe e contém `sessionid=mljl62yp5ne6v8xksk2dfecfhnkhsfr2` | ✅ Corrigido — 5 negações de permissão seguidas, o arquivo nunca foi criado |
| S2 | **App do aluno fora do rate limit de escrita** | `/aluno/` não está em `WRITE_PATH_PREFIXES`. Check-in, RM e congelamento de matrícula não têm throttle nenhum | ⚠️ Não endereçado — confirmado no código atual |
| S3 | **Rate limit de login é por IP** | 8 tentativas / 5 min. Um box atrás de um NAT compartilha esse orçamento entre Maria, Eric, Diego, Fernando e os 90 alunos no wi-fi. Aconteceu comigo na simulação | ⚠️ Não endereçado — confirmado no código atual |
| S4 | **Cliente que pagou fica sem caminho** | O e-mail de ativação falhou (SMTP fora do ar) e a tela de sucesso continuou dizendo *"em instantes você vai receber um e-mail"*. Sem link, sem botão de reenviar, sem status. O log diz "operador pode reenviar pelo Django admin" — o cliente não sabe disso | ✅ Corrigido — reenvio self-service com rate limit próprio (404/502/429 testados) |

## 8. Bloqueios de produto (não é bug, é ausência)

| # | Achado | Consequência medida |
|---|---|---|
| P1 | **O Owner não consegue cadastrar a equipe** | Não existe rota de gestão de staff. Maria, Eric e Diego só existem porque eu os criei fora do app (CLI/admin). Todo box novo depende do fornecedor no dia 1 |
| P2 | **Aluno só entra com Google** | `/aluno/auth/login/`: *"O login social está em manutenção. Fale com a recepção do seu box."* A recepção não tem ferramenta para liberar. 90 atletas dependem de um provider externo, sem plano B |
| P3 | **Uma reserva ativa por vez** | `attendance_workflows.py`: bloqueia se existir outra reserva cujo fim ainda está no futuro. Resultado medido: **88 alunos × 30 dias × 161 aulas = 88 reservas**. O atleta não consegue marcar segunda, quarta e sexta de uma vez — que é exatamente o ritual de um box |
| P4 | **Check-in é exclusivo do Coach** | `AttendanceActionView.allowed_roles = (ROLE_COACH,)`. Recepção, Manager e Owner tomam 403. Quem está na porta não pode registrar quem entrou |
| P5 | **Cadastro em massa esbarra no throttle** | 30 escritas/min por usuário. Maria tomou **5× 429** ao cadastrar os 88 alunos pelo formulário. Existe importação por CSV, mas a tela `/alunos/importar/` responde 405 no GET — só o POST funciona |
| P6 | **Cota de export: 2 por hora por usuário** | Diego e Fernando fechando mês juntos se bloqueiam |

## 9. Atritos menores

- O planner da grade recusa a aula toda quando `anchor_date`/`interval_days`
  (rodízio, que só vale para sábado/domingo) chega junto com dias úteis. O erro
  fica escondido no campo; o topo só diz "Confira os campos".
- O seletor de coach mostra `username` (`eric`, `diego`) em vez do nome.
- Salvar WOD sem `intent` devolve 200 sem mensagem nenhuma — no-op silencioso.
- `/aluno/onboarding/` redireciona para o login mesmo com sessão de aluno válida.
- Rota inexistente redireciona para `/login/` em vez de 404 — soft-404 mascara link quebrado.

---

## 10. Escala de percepção

**Brilhante**
- **O provisionamento multi-tenant.** Pagar, escolher senha e ter um schema
  PostgreSQL próprio, migrado e ativo, em uma única requisição, funcionando de
  primeira e de forma idempotente. É a parte mais difícil do produto e é a que
  está mais pronta.

**Genial**
- **A prescrição de carga por 1RM do aluno dentro do WOD.** O coach escreve o
  treino uma vez e cada atleta vê o peso dele. É o que nenhuma planilha faz.
- **A guarda de ordenação de eventos da Stripe** (`billing_event_at`): impede que
  um `invoice.payment_succeeded` atrasado reative um box cancelado.

**Excelente**
- Performance: p95 de 176 ms com 88 alunos, 161 aulas e 1.056 cobranças.
- Estabilidade: 7.566 requisições, zero 5xx no loop de 30 dias.
- Fronteira de papéis: todo 403 que apareceu apareceu na hora certa.
- O PWA do aluno completo — manifest, service worker, offline, push e telas de
  estado (sem box, suspenso financeiro, aguardando aprovação).

**Bom**
- Mensagens de validação específicas e em português ("Escolha a origem de
  aquisicao antes de continuar").
- Fila de pagamentos da recepção e baixa de balcão com método/vencimento/referência.
- Central de intake com lead e intake separados no mesmo funil.

**Regular**
- Mensagens de erro que citam três campos sem dizer qual ("revise vencimento,
  método e referência").
- 404 cru para recurso desligado por feature flag.
- Export xlsx que só some.

**Ruim**
- Manager sem workspace e Owner sem gestão de equipe: dois cargos com o app
  incompleto por padrão.
- Reserva única ativa: a funcionalidade mais usada do app do aluno entrega 1
  reserva por mês por atleta.
- Recepção sem check-in.

**Muito ruim**
- `playwright_debug.log` gravando cookie de sessão em texto puro a cada 403.
- Cliente que pagou e não recebe o e-mail fica sem nenhum caminho na tela.
- Login do aluno com dependência única de Google, sem plano B, com mensagem que
  aponta para uma recepção que não pode ajudar.

---

## 11. O que eu faria primeiro

| Prioridade | Ação | Custo | Destrava | Status |
|---|---|---|---|---|
| 1 | Remover a escrita de `playwright_debug.log` (ou trocar por log estruturado sem cookies) | minutos | Vazamento de sessão | ✅ Feito |
| 2 | Corrigir `allowed_roles` minúsculo em `integrations/views.py` | minutos | Painel de webhooks para todos os papéis | ✅ Feito |
| 3 | `try/except` em `json.loads` nas views de `api/v1/` → 400 | minutos | 2 crashes | ✅ Feito (2 rodadas: malformado + JSON válido não-objeto) |
| 4 | `template_name` (ou `HttpResponseNotAllowed`) no checkpoint semanal | minutos | 1 crash | ✅ Feito |
| 5 | Filtrar o seletor de coach por `Membership` do box ativo | horas | Vazamento entre boxes + coach que não aparece | ⚠️ Pendente |
| 6 | Permitir N reservas futuras (limite por plano, não por "uma") | horas | O loop principal do app do aluno | ⚠️ Pendente (decisão de produto; mensagem de bloqueio já melhorou) |
| 7 | Liberar check-in para Recepção e Owner | horas | Autonomia da Maria | ⚠️ Pendente |
| 8 | Tela de sucesso do checkout com link de ativação + botão de reenviar | horas | Cliente que pagou não fica órfão | ✅ Feito, com rate limit próprio |
| 9 | Fallback de login do aluno (código por e-mail ou WhatsApp) | dias | Remove o ponto único de falha dos 90 atletas | ⚠️ Pendente |
| 10 | CRUD de equipe para o Owner | dias | Onboarding sem depender do fornecedor | ⚠️ Pendente |
| 11 | Ligar `OPERATIONS_MANAGER_WORKSPACE_ENABLED` por padrão, ou dar tela de "recurso desativado" | horas | Cargo do Manager | ⚠️ Parcial — deu a tela de "desativado"; ligar por padrão é decisão de produto |
| 12 | Throttle de escrita com bypass para importação em lote | horas | Mutirão de cadastro no dia 1 | ⚠️ Pendente |

**Ainda fora desta rodada, mas não estava na fila original:** S2 (app do aluno
fora do rate limit de escrita) e S3 (rate limit de login por IP) — vale
adicioná-los à próxima fila de prioridade.

---

## 12. Como reproduzir

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements_test.txt
service postgresql start && su postgres -c "createdb octobox_control"
cp .env.example .env   # DATABASE_URL local, DJANGO_DEBUG=True, STRIPE_WEBHOOK_SECRET próprio
.venv/bin/python manage.py migrate_schemas --shared
.venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload

PYTHONPATH=. DJANGO_SETTINGS_MODULE=config.settings \
  .venv/bin/python tools/simulations/e2e_box_30d/run_30d.py
PYTHONPATH=. DJANGO_SETTINGS_MODULE=config.settings \
  .venv/bin/python tools/simulations/e2e_box_30d/feature_sweep.py
```
