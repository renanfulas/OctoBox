<!--
ARQUIVO: plano de execução em 5 ondas para atacar os 22 atritos catalogados na simulação de 20 dias.

TIPO DE DOCUMENTO:
- plano ativo de execução

AUTORIDADE:
- alta para a frente atual de resolução de atritos pós-simulação

DOCUMENTO PAI:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

QUANDO USAR:
- quando a dúvida for em qual ordem atacar os atritos da simulação de 20 dias
- quando houver dúvida sobre por que um atrito espera por outro
- quando precisar decidir entre fix local e corte estrutural

POR QUE ELE EXISTE:
- A simulação de 20 dias gerou uma lista de 22 atritos catalogados.
- Uma priorização puramente por dor ignora dependências arquiteturais reais.
- Este plano reordena os atritos respeitando Signal Mesh, ownership cross-module e padrão de snapshots publicados.

O QUE ESTE ARQUIVO FAZ:
1. Define 5 ondas de execução com ordem por dependência arquitetural.
2. Mapeia cada atrito para a camada correta da arquitetura oficial.
3. Fixa decisões integrar-vs-construir (gateway, app nativo, NF, social).
4. Define critérios de aceite por onda para evitar regressão.

PONTOS CRITICOS:
- A Onda 0 não é negociável. Pular ela transforma 5 atritos em hacks que precisarão ser desfeitos.
- Itens marcados como "NÃO construir" são decisões arquiteturais fechadas, não preferência.
- Quando este plano divergir do runtime, o runtime vence; este doc precisa ser atualizado.
-->

# Plano de resolução de atritos — 5 ondas

## Como usar este documento (leia antes de qualquer outra seção)

**Você é:** Claude Code executando uma onda específica deste plano.
**Sua missão:** implementar os itens da onda solicitada respeitando as camadas arquiteturais mapeadas.

**Regra inviolável:** nunca iniciar Onda N sem confirmar que todos os itens do gate da Onda N-1 estão marcados.

**Fallback para path ausente:** se um diretório ou módulo referenciado não existir, criá-lo seguindo o padrão do módulo mais próximo (ex: se `finance/application/use_cases/` não existe, criar seguindo o padrão de `operations/application/`). Registrar a criação no PR description.

**Fallback para código parcial existente:** se o atrito já tem implementação parcial, adaptar sem reescrever o que funciona. Documentar o delta no PR.

---

## Paths esperados vs. paths a criar

| Path | Estado real (verificado em 2026-04-26) |
|------|----------------------------------------|
| `integrations/mesh/` | **Existe** — `SignalEnvelope`, `FailureDecision`, `RetryDecision`, fingerprinting prontos. O nome oficial no código é `integrations/mesh/`, não `signal_mesh/` |
| `integrations/whatsapp/models.py` | **Existe** — `WebhookEvent` com `provider`, `payload`, `status`, `attempts`, `next_retry_at`, `register_failure()`, `mark_processed()`. É o padrão de referência para adicionar canal Stripe |
| `integrations/stripe/services.py` | **Existe parcial** — tem `create_checkout_session` com idempotência mas **não tem webhook receiver**. Onda 0 adiciona o receiver |
| `finance/application/use_cases/` | **Existe** — `use_cases.py`, `commands.py`, `ports.py`, `results.py` presentes |
| `students/application/use_cases/` | **Existe** — mesma estrutura |
| `jobs/` app Django | **Existe** — `AsyncJob` model, dispatcher com registry; `student_import_csv` já registrado (atrito 7 parcialmente resolvido) |
| `student_app/` snapshots | **Existe** — padrão consolidado; seguir convenção atual |
| `quick_sales/application/` | **Verificar** — pode estar em `quick_sales/services/`; mover invariante para camada de application se necessário |

---

## Origem

Este plano nasce do relatório [`docs/reports/simulation_20_days_report.md`](../reports/simulation_20_days_report.md), que catalogou 22 atritos durante simulação de 20 dias com 5 personas (Maria, Carlos, Beto, Roberto, Júlia).

A primeira priorização foi por dor. Esta é a versão revisada por arquitetura, que respeita:

1. ordem de dependências reais entre atritos
2. camadas oficiais da arquitetura ([Signal Mesh](../architecture/signal-mesh.md), [Center Layer](../architecture/center-layer.md), [Mobile](../architecture/octobox-mobile-architecture.md))
3. princípio de evoluir sem reescrever (matriz de ownership ainda em transição)

## Tese estrutural

Cinco atritos da lista original (4, 5, A1, A2 e parte de 7) **assumem implicitamente que a Signal Mesh existe em runtime**. Hoje a Signal Mesh é apenas conceito formalizado (signal-mesh.md:548-550). Por isso o plano insere uma **Onda 0 de fundação** antes de qualquer fix dependente.

Sem a Onda 0, esses fixes recriam exatamente os anti-padrões que a Mesh existe para impedir: webhook em view, callback direto em service, retry improvisado, payload externo vazando para o núcleo.

## Decisões integrar-vs-construir (fixadas)

| Frente | Decisão | Razão |
|--------|---------|-------|
| Gateway de pagamento próprio | ❌ **Integrar** (manter Stripe + adicionar Asaas/Pagar.me se necessário) | Growth plan Fase 5; construir gateway é meses de eng. financeira/regulatória |
| App nativo iOS/Android | ❌ **NÃO construir** | Conflita com [octobox-mobile-architecture.md:33](../architecture/octobox-mobile-architecture.md). Solução para A8 é Camada 1 do doc oficial |
| Emissão de NF | ✅ **Integrar** (NFE.io ou similar) | Adapter na Signal Mesh, não regra no domínio |
| Contrato eletrônico | ✅ **Integrar** (ZapSign / D4Sign) | Mesma razão |
| Timeline social com fotos/comentários | ❌ **NÃO construir** | Viola Front Display Wall; viola identidade do produto; UGC + moderação + LGPD não cabem |
| **Ranking semanal de WOD por categoria** | ✅ **Construir** (Onda 4) | Snapshot público read-only, padrão arquitetural já existente, respeita identidade CrossFit, esforço ~1 sprint |
| Apple Health / Google Fit | ✅ **Integrar** | Adapter de saída na borda |

---

## 🌊 Onda 0 — Foundation: canal Stripe na Signal Mesh

**Duração:** 1 sprint
**Contexto real:** `integrations/mesh/` já existe com `SignalEnvelope`, `FailureDecision` e `RetryDecision`. `WebhookEvent` já existe para WhatsApp em `integrations/whatsapp/models.py`. Onda 0 **não constrói a Mesh do zero** — adiciona o canal de pagamento Stripe seguindo o padrão WhatsApp já estabelecido.

**Por que primeiro:** os atritos 4, 5, A1, A2 dependem de um `WebhookEvent` de pagamento com retry e observabilidade. Sem isso, viram hack que precisará ser desfeito.

### Referência de implementação

Seguir `integrations/whatsapp/models.py` como padrão. O `WebhookEvent` de WhatsApp tem `provider`, `payload`, `status`, `attempts`, `max_retries`, `next_retry_at`, `register_failure()`, `mark_processed()`. Replicar para Stripe sem generalizar ainda.

### Entregas

| Entrega | Arquivo alvo | Critério de aceite |
|---------|-------------|--------------------|
| `PaymentWebhookEvent` model (espelho do WhatsApp `WebhookEvent`) | `integrations/stripe/models.py` | Persiste com `provider="stripe"`, `event_type`, `payload`, `status`, `attempts`, `idempotency_key` |
| Receiver HTTP para eventos Stripe | `integrations/stripe/webhook_handler.py` | Recebe POST do Stripe, verifica assinatura (`STRIPE_WEBHOOK_SECRET`), cria `PaymentWebhookEvent`, retorna 200 |
| Roteador que chama `finance/application/use_cases/ReconcilePayment` | `integrations/stripe/router.py` | Use case recebe envelope normalizado, não payload bruto do Stripe |
| View e rota `/integrations/webhooks/` | `integrations/views.py` + URL | Lista `PaymentWebhookEvent` com status, lag, retry_count; botão retry manual |
| Quota por canal como constante configurável | `integrations/stripe/limits.py` | `MAX_RETRIES = 5`, `BACKOFF_BASE_SECONDS = 60` configuráveis via settings |

### O que NÃO fazer nesta onda

1. Não generalizar `WebhookEvent` em modelo abstrato compartilhado antes de ter 2+ canais prontos
2. Não migrar WhatsApp para usar o novo modelo
3. Não criar circuit breaker distribuído — constante de quota é suficiente agora

### Gate de conclusão — Onda 0 (todos obrigatórios antes de avançar)

- [ ] `PaymentWebhookEvent` existe em `integrations/stripe/models.py` com migração aplicada
- [ ] POST em `/api/v1/integrations/stripe/webhook/` persiste evento e retorna `200`; payload bruto do Stripe não atravessa para `finance/`
- [ ] `finance/application/use_cases/ReconcilePayment` recebe `SignalEnvelope` normalizado
- [ ] Painel em `/integrations/webhooks/` exibe status, lag e retry_count por evento Stripe
- [ ] Nenhum `import stripe` aparece fora de `integrations/stripe/`; verificar via `grep -r "import stripe" --include="*.py"` excluindo `integrations/stripe/`
- [ ] `MAX_RETRIES` e backoff configuráveis via `settings.py`

---

## 🌊 Onda 1 — Sangria local sem dependência estrutural

**Duração:** 1–2 sprints
**Critério de inclusão:** fixes que não exigem Signal Mesh nem cross-module.

| # | Atrito | Camada correta | Implementação |
|---|--------|----------------|---------------|
| 1 | Quick Sale R$ 0 | `quick_sales/application/` | Invariante de domínio rejeita `total <= 0` na construção do command; service levanta `ValidationError` antes de persistir |
| 2 | Homônimos no autocomplete | `students/facade` + template do autocomplete em `recepcao/` | Avatar + data nasc + últimos 4 dígitos CPF no item do dropdown |
| 9 | Excel `valor_pago` mistura tipos | `reporting/` — localizar função de export | Forçar `Decimal` → string formatada + `number_format` na célula Excel via openpyxl |
| 10 | Sticky footer "Fechar ciclo financeiro" | template `finance/` + CSS mobile | `position: sticky; bottom: 0` ativo no breakpoint `≤430px` |
| 11 | Lead/Aluno/Contato confuso | templates de recepção + onboarding | Unificar rótulos para "Aluno" em toda a superfície de recepção; tour inline ativado na primeira sessão de login da Maria |
| 12 | Plano vs Produto avulso | `catalog/` — view e template de criação | Wizard com 2 CTAs distintos no topo: "Criar Plano Recorrente" e "Criar Produto Avulso"; cada um abre form específico |

### Gate de conclusão — Onda 1 (todos obrigatórios antes de avançar)

- [ ] `quick_sales` levanta `ValidationError` (ou equivalente) quando `total <= 0`; coberto por teste unitário
- [ ] Autocomplete de aluno exibe foto/inicial + data de nascimento + CPF mascarado; dois "João Silva" são distinguíveis visualmente
- [ ] Export Excel de `valor_pago` retorna coluna com tipo numérico, não string; verificável abrindo o arquivo gerado
- [ ] Botão "Fechar ciclo financeiro" visível sem scroll em iPhone 14 (375px) e iPhone SE (375px)
- [ ] Nenhum desses fixes tocou em `integrations/`, `communications/` ou cruzou módulos; verificar via `git diff --stat`

---

## 🌊 Onda 2 — Capacidades estruturais

**Duração:** 2–3 sprints
**Pré-requisito:** Onda 0 concluída.

| # | Atrito | Implementação correta |
|---|--------|----------------------|
| 4 | Membership fantasma sem cobrança | `students/application/use_cases/CheckMembershipBilling` → publica evento → job nightly em `jobs/check_membership_billing` → snapshot `MembershipsWithoutBillingSnapshot` exposto no Owner workspace |
| 5 | Painel de webhook + retries | Expandir `/integrations/webhooks/` com filtro por status, botão de retry manual e coluna de lag; baseline já existe da Onda 0 |
| A1 | Status "aguardando confirmação" no app aluno | Criar `PaymentReconciliationStatus` snapshot consumido em `student_app/home` — **não** adicionar lógica de webhook diretamente na view |
| A2 | Push de cancelamento de aula | `CancelClass` use case publica evento `class_cancelled` → `signal_mesh` roteia → `communications` envia push para todos com presença confirmada |
| 3 | Bulk action partial-commit | `finance/application/use_cases/BulkPriceUpdate`: iterar por item dentro de `try/except` individual; coletar erros; retornar relatório `{success: N, failed: [{id, reason}]}`; admin dispara e exibe relatório |
| 7 | CSV import com relatório de erros | View de import retorna `202 Accepted` + enfileira `jobs/import_students_csv`; job processa linha a linha, coleta erros, gera CSV de erros para download; nenhuma linha de parsing na view |
| 8 | Middleware `student_auth` redirect silencioso | Mover validação de CPF/fingerprint para `student_app/application/use_cases/ValidateStudentIdentity`; middleware chama use case e faz redirect **com** flash message de motivo |

### Gate de conclusão — Onda 2 (todos obrigatórios antes de avançar)

- [ ] Nenhum import de payload Stripe/Pix aparece fora de `signal_mesh/`; verificar via `grep -r "stripe\." --include="*.py"` excluindo `signal_mesh/`
- [ ] CSV import view retorna `202` e não executa parsing; verificar via teste de view que confirma job enfileirado
- [ ] `BulkPriceUpdate` retorna relatório itemizado mesmo quando alguns itens falham; coberto por teste unitário com mix de sucesso/erro
- [ ] Push de cancelamento chega para aluno que confirmou presença; verificar via teste de integração em `communications/`
- [ ] Owner workspace exibe lista de memberships sem cobrança; snapshot existe e é populado pelo job nightly

---

## 🌊 Onda 3 — Snapshots novos (read-only)

**Duração:** 1–2 sprints
**Pré-requisito:** nenhum estrutural; padrão de snapshot já existe em [student_app smart snapshots](../../README.md).

| # | Atrito | Snapshot |
|---|--------|----------|
| A3 | Gráfico histórico de RM | Snapshot `StudentExerciseMaxHistory` por exercício; surface em `/aluno/rm/` com Chart.js (já presente); janelas de seleção: 30/90/365d |
| A5 | WOD futuro visível | Expandir `use_cases.py` `GetStudentDashboard` para incluir `wod_tomorrow` quando coach tiver publicado D+1; card condicional na home |
| A4 | Política de cancelamento opaca | Campo `cancel_deadline_label` no snapshot da grade (`"Cancela sem perder crédito até 2h antes"`); exibir inline no botão de desmarcar |
| A6 | Troca de box mobile densa | Redesign de `membership_views.py` troca-de-box: colapsar 3 passos em 1 selector + confirm; sem novo modelo |

### Gate de conclusão — Onda 3 (todos obrigatórios antes de avançar)

- [ ] `/aluno/rm/` exibe gráfico de linha para pelo menos 1 exercício com dados reais; verificar em dispositivo mobile
- [ ] Home do aluno exibe card "Amanhã" quando WOD D+1 está publicado; desaparece quando não há publicação
- [ ] Botão "Desmarcar" na grade exibe prazo de cancelamento sem necessidade de clique adicional
- [ ] Troca de box completa em 1 passo + confirmação; sem redirect intermediário desnecessário

---

## 🌊 Onda 4 — Capacidades self-service, vício e integrações de borda

**Duração:** 2–3 sprints
**Pré-requisito:** Ondas 0–2 concluídas (Mesh para eventos, snapshots para leitura).

| # | Atrito | Implementação |
|---|--------|---------------|
| A7 | Congelar matrícula self-service | `MembershipFreeze` use case em `students/application/`; view em `membership_views.py` com form de solicitação; job ou sinal notifica manager para aprovação; status "pendente/aprovado/rejeitado" visível para o aluno |
| 6 | Coach Wall trava com múltiplas aulas | Implementar Published Snapshot + Ghost Resume para Coach Wall seguindo [octobox-mobile-architecture.md:151-191](../architecture/octobox-mobile-architecture.md); **não** aplicar virtualização CSS ad-hoc |
| A8 | PWA install no iOS invisível | Banner "Adicionar à Tela Inicial" com tutorial de 2 passos; disparado após 3ª visita; seguir Camada 1 de `octobox-mobile-architecture.md` |
| A9 | Indicação de amigo | `ReferralLink` use case gera URL com UTM `source=referral&ref={student_id}`; CTA "Indicar amigo" na home do aluno |
| A10 | Apple Health / Google Fit | Adapter de saída em `integrations/health/`; exporta `StudentExerciseMax` e `Attendance` para HealthKit via JavaScript bridge no PWA |
| **NEW** | **Ranking semanal de WOD por categoria** | Ver [wod-ranking-system-plan.md](wod-ranking-system-plan.md) — implementar apenas após snapshot de WODResult existir |

### Por que Coach Wall vai para o fim

Atrito 6 parece urgente, mas a solução arquitetural correta (Published Snapshot + Ghost Resume) só faz sentido depois que o padrão de snapshots estiver consolidado pelas Ondas 2 e 3. Patch de virtualização agora seria reescrito depois.

### Gate de conclusão — Onda 4 (todos obrigatórios antes de encerrar o plano)

- [ ] Aluno consegue solicitar congelamento em `/aluno/configuracoes/` sem contato com a recepção; manager recebe notificação
- [ ] Coach Wall abre com 3 aulas simultâneas em iPad (Safari) sem travar; snapshot publicado é a fonte de leitura
- [ ] Banner de instalação PWA aparece no iOS após 3ª visita; tutorial tem pelo menos 2 passos visuais
- [ ] URL de indicação gerada contém `utm_source=referral`; UTM é rastreável no funil de onboarding
- [ ] Export de RM para Apple Health funciona em iPhone via PWA sem instalação adicional

---

## Validação geral do plano

Aplicando o checklist do [growth plan](../architecture/architecture-growth-plan.md), após Ondas 0+1+2 o sistema deve mostrar:

✅ Toda nova feature de pagamento entra pela Signal Mesh
✅ Signal Mesh tem 1 canal real funcionando (não só doc)
✅ Cross-module finance↔students passa por evento, não signal Django
✅ Bulk operations têm contrato claro (per-item ou all-or-nothing)
✅ Snapshots públicos como padrão para leitura mobile
✅ Request web não fica mais pesado (CSV migrado para jobs)

Sinal de doença a vigiar:
- Mais de uma feature exige tocar 3+ módulos ao mesmo tempo
- Integração externa entrando direto em view ou template
- Lógica de negócio aparecendo em middleware

## O que este plano explicitamente NÃO faz

1. Não move state ownership de `boxcore` ([matriz de ownership](../architecture/domain-model-ownership-matrix.md) já diz: split de estado é projeto separado)
2. Não constrói app nativo
3. Não constrói gateway próprio
4. Não constrói timeline social (substituído por ranking)
5. Não cria Signal Mesh "completa" — apenas o canal pagamento na Onda 0; outros canais entram puxados por demanda

## Documentação a atualizar após cada onda

| Após onda | Atualizar |
|-----------|-----------|
| Onda 0 | [signal-mesh.md](../architecture/signal-mesh.md) seção "Estado atual": trocar "conceito formalizado" por "baseline implementado para canal pagamento" |
| Onda 2 | [promoted-public-facades-map.md](../architecture/promoted-public-facades-map.md): registrar novos use cases como facades |
| Onda 4 | [wod-ranking-system-plan.md](wod-ranking-system-plan.md): registrar `RecordWODResult` em promoted-public-facades-map; criar `student-engagement-mechanics.md` |

## Tese final

O plano original era trocar pisos, pintar paredes e instalar portas em 5 cômodos — todos ligados a uma tubulação que ainda não existe. A versão em 5 ondas passa a tubulação primeiro (Onda 0), faz só os cômodos que não dependem dela (Onda 1), e só então toca nos que precisam de água/esgoto (Onda 2+).

Um sprint a mais no começo. Meses de retrabalho economizados depois.
