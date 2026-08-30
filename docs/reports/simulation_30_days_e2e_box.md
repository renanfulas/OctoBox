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

**Data da execução:** 30/08/2026
**Ambiente:** `runserver` + PostgreSQL 16 local, Django 6.0.8, DEBUG=True
**Harness:** `tools/simulations/e2e_box_30d/` (HTTP real, com CSRF e sessão, sem atalho por ORM)

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

### Maria — Recepção (QI 89) · **6,4 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 8 | O painel da recepção mostra a fila de pagamentos do dia sem ela precisar procurar |
| Velocidade | 9 | p50 56 ms, p95 119 ms — a tela nunca a fez esperar |
| Autonomia | 3 | **Não pode fazer check-in de ninguém** (403) e não pode ver o financeiro |
| Recuperação de erro | 6 | As mensagens existem e são em português, mas dizem "revise vencimento, método e referência" sem apontar o campo |
| Confiança no sistema | 6 | Nada quebrou na frente dela em 30 dias |

### Eric — Coach (QI 95) · **7,6 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 8 | Editor de WOD, planner, biblioteca de templates e histórico são coerentes entre si |
| Velocidade | 9 | p50 68 ms, p95 144 ms; salvar WOD em 124 ms |
| Autonomia | 8 | É o único papel que consegue dar check-in; controla WOD, blocos, prescrição por 1RM e ocorrência técnica |
| Recuperação de erro | 6 | Salvar sem `intent` devolve 200 sem dizer nada; a tela de checkpoint semanal quebra com 500 no F5 |
| Confiança no sistema | 7 | Só o 500 do checkpoint abalou |

### Diego — Manager (QI 102) · **5,8 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 7 | Dashboard e financeiro com filtro de inadimplência entregam o que ele precisa |
| Velocidade | 9 | p50 60 ms, p95 146 ms |
| Autonomia | 4 | **O workspace do Manager não existe por padrão** (404); ele cai no dashboard genérico |
| Recuperação de erro | 4 | 404 cru em vez de "recurso desativado"; API de ação em lote responde 500 a corpo malformado |
| Confiança no sistema | 5 | Descobriu que a tela do cargo dele simplesmente não abre |

### Fernando — Owner (QI 110) · **6,0 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 8 | Workspace do owner, resumo executivo e relatórios contam a história do box |
| Velocidade | 9 | p50 60 ms, p95 110 ms — o mais rápido de todos |
| Autonomia | 3 | **Não consegue cadastrar a própria equipe pelo app** e o painel de webhooks dá 403 para ele |
| Recuperação de erro | 5 | Pagou, o e-mail de ativação falhou, e a tela continuou dizendo "você vai receber um e-mail" |
| Confiança no sistema | 7 | O provisionamento do box funcionou na primeira, e isso vale muito |

### Alunos (90 · QI médio 93) · **5,2 / 10**

| Atributo | Nota | Por quê |
|---|---|---|
| Clareza da tela | 9 | Home, grade, WOD e RM em telas curtas; PWA com manifest, service worker e página offline |
| Velocidade | 8 | p50 88 ms, p95 176 ms em 6.415 chamadas |
| Autonomia | 2 | **Só entram com Google.** Sem provider configurado, ninguém entra e a mensagem manda "falar com a recepção" — que não tem como liberar |
| Recuperação de erro | 6 | "Esta aula já está com todas as vagas preenchidas" é claro; "você já tem uma reserva ativa" é claro mas não oferece saída |
| Confiança no sistema | 4 | 88 alunos conseguiram reservar **1 aula em 30 dias** |

---

## 3. Facilidade de uso — **6,2 / 10**

O produto é rápido, bonito e bem escrito em português. O que derruba a nota não
é complexidade: é **falta de caminho**. Três das quatro pessoas do box esbarram
em algo que o app simplesmente não oferece (equipe, check-in, workspace de
manager), e o aluno depende de um provider externo que, se não estiver
configurado, zera o produto inteiro para 90 pessoas.

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

## Estão mais felizes?

**Eric e Fernando, sim.** O coach ganhou uma ferramenta que ele não tinha e o dono
ganhou visibilidade sem cobrar relatório de ninguém.
**Maria, não.** Ela tem menos poder no app do que tinha no caderno: não dá baixa
em presença e não vê o financeiro que ela mesma cobra.
**Diego, não.** O cargo dele não tem tela.
**Os alunos, divididos.** Quem entrou adorou o app; a reserva de aula — o motivo
número um de abrir o app — está travada.

---

## 5. O que crashou (5xx verificado)

| # | Rota | Erro | Impacto |
|---|---|---|---|
| C1 | `GET /operacao/wod/aprovacoes/checkpoint-semanal/` | `ImproperlyConfigured: TemplateResponseMixin requires either a definition of 'template_name'...` | A view é só POST e não tem `template_name`. Um F5, um "voltar" ou um link salvo derruba a tela com 500 |
| C2 | `POST /api/v1/finance/payments/bulk-action/` e `POST /api/v1/finance/freeze-student/` | `json.decoder.JSONDecodeError` em `api/v1/bulk_views.py:21` | `json.loads(request.body)` sem guarda: corpo não-JSON vira **500 em vez de 400**. Com JSON válido, ambas respondem 200/400 corretamente |
| C3 | `GET /api/v1/finance/payment-link/<id>/` | 500 devolvendo o texto bruto do erro da Stripe no corpo | Falha de gateway deveria ser 502 com mensagem de negócio, não 500 vazando detalhe interno. *(Causa raiz aqui: egress bloqueado no ambiente.)* |

**Status (2026-08-30):** C1, C2 e C3 corrigidos e com teste de regressão
(`tests/test_workout_weekly_governance.py`, `tests/test_error_scenarios.py`,
`tests/test_payment_views_coverage.py`).

## 6. O que bugou (sem 5xx, mas quebrado)

| # | Achado | Evidência |
|---|---|---|
| B1 | **Painel de webhooks é inacessível para todo mundo** | `integrations/views.py:29,56` usa `allowed_roles=('owner','manager','dev')` minúsculo; `get_user_role().slug` devolve `Owner`/`Manager`/`DEV`. Fernando (Owner) toma 403 |
| B2 | **Vazamento entre boxes no seletor de coach** | Criei `coach_de_outro_box` com Group `Coach` e **zero Membership neste box**; ele aparece na lista de coaches de Fernando. `_get_class_coach_queryset()` filtra só por Group, e `auth_user` vive no schema `public` — sem filtro por Box |
| B3 | **A origem do papel está partida ao meio** | O papel vem de `Membership` (é o que o checkout cria), mas o seletor de coach lê `Group`. O Owner criado pelo próprio fluxo de venda nasce sem Group e nunca aparece como coach. Eric só apareceu depois de eu atribuir o Group na mão |
| B4 | **Workspace do Manager não existe por padrão** | `OPERATIONS_MANAGER_WORKSPACE_ENABLED=False`. `/operacao/manager/` devolve **404 cru** para o próprio Manager, e `/operacao/` o joga no dashboard genérico |
| B5 | **Export xlsx devolve 404** | `/alunos/exportar/xlsx/` e `/financeiro/exportar/xlsx/`. CSV e PDF funcionam |
| B6 | **Rotas de fragmento respondem 405 sem corpo** | `GET /alunos/<id>/drawer/profile/` — 90 ocorrências no journal. Sem mensagem, sem `Allow` legível para o usuário |

**Status (2026-08-30):**
- B1, B2, B3, B5 corrigidos e com teste de regressão.
- B4: já tinha a mitigação certa disponível (tela de "recurso desativado" em
  vez do 404 cru — ver `docs/reports/simulation_30_days_e2e_box.md` PR de
  recuperação de erro); ligar `OPERATIONS_MANAGER_WORKSPACE_ENABLED` por
  padrão continua sendo decisão de produto, não bug.
- **B6 investigado e reclassificado: não é bug do produto.** `/alunos/<id>/drawer/profile/`
  é POST-only por design (salvar edição rápida do drawer); a leitura/abertura
  da ficha é `GET /alunos/<id>/drawer/fragments/` (`StudentDrawerFragmentsView`),
  usada de verdade pelo JS do diretório. As 90 ocorrências vinham do próprio
  harness (`tools/simulations/e2e_box_30d/run_30d.py`) chamando a rota errada
  para simular "abrir ficha do aluno" — corrigido no harness. Nenhum caminho
  real de UI navega para a rota de save via GET.

## 7. Segurança (o que mais me preocupou)

| # | Achado | Detalhe |
|---|---|---|
| S1 | **Cookie de sessão gravado em disco em texto puro** | `access/permissions/mixins.py` grava `playwright_debug.log` a **cada negação de permissão**, com `sessionid`, `csrftoken` e todos os headers. Não é protegido por `DEBUG`, não tem rotação e cresce sob varredura. Verificado: o arquivo existe e contém `sessionid=mljl62yp5ne6v8xksk2dfecfhnkhsfr2` |
| S2 | **App do aluno fora do rate limit de escrita** | `/aluno/` não está em `WRITE_PATH_PREFIXES`. Check-in, RM e congelamento de matrícula não têm throttle nenhum |
| S3 | **Rate limit de login é por IP** | 8 tentativas / 5 min. Um box atrás de um NAT compartilha esse orçamento entre Maria, Eric, Diego, Fernando e os 90 alunos no wi-fi. Aconteceu comigo na simulação |
| S4 | **Cliente que pagou fica sem caminho** | O e-mail de ativação falhou (SMTP fora do ar) e a tela de sucesso continuou dizendo *"em instantes você vai receber um e-mail"*. Sem link, sem botão de reenviar, sem status. O log diz "operador pode reenviar pelo Django admin" — o cliente não sabe disso |

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

| Prioridade | Ação | Custo | Destrava |
|---|---|---|---|
| 1 | Remover a escrita de `playwright_debug.log` (ou trocar por log estruturado sem cookies) | minutos | Vazamento de sessão |
| 2 | Corrigir `allowed_roles` minúsculo em `integrations/views.py` | minutos | Painel de webhooks para todos os papéis |
| 3 | `try/except` em `json.loads` nas views de `api/v1/` → 400 | minutos | 2 crashes |
| 4 | `template_name` (ou `HttpResponseNotAllowed`) no checkpoint semanal | minutos | 1 crash |
| 5 | Filtrar o seletor de coach por `Membership` do box ativo | horas | Vazamento entre boxes + coach que não aparece |
| 6 | Permitir N reservas futuras (limite por plano, não por "uma") | horas | O loop principal do app do aluno |
| 7 | Liberar check-in para Recepção e Owner | horas | Autonomia da Maria |
| 8 | Tela de sucesso do checkout com link de ativação + botão de reenviar | horas | Cliente que pagou não fica órfão |
| 9 | Fallback de login do aluno (código por e-mail ou WhatsApp) | dias | Remove o ponto único de falha dos 90 atletas |
| 10 | CRUD de equipe para o Owner | dias | Onboarding sem depender do fornecedor |
| 11 | Ligar `OPERATIONS_MANAGER_WORKSPACE_ENABLED` por padrão, ou dar tela de "recurso desativado" | horas | Cargo do Manager |
| 12 | Throttle de escrita com bypass para importação em lote | horas | Mutirão de cadastro no dia 1 |

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
