# Runbook operacional — Curva / Public Workouts

## Cadência mínima

- A cada minuto: `python manage.py drain_public_workout_outbox --limit 50`.
- A cada hora: `python manage.py reconcile_public_workout_operations`.
- Diariamente, depois da meia-noite: `python manage.py capture_public_workout_metrics`.
- Após o snapshot diário: `python manage.py evaluate_public_workout_growth_gate`.
- Antes de ativar uma flag: `python manage.py check --deploy` e
  `python manage.py reconcile_public_workout_operations --dry-run`.

Na VPS, instalar as três cadências com:

```bash
sudo OCTOBOX_REPO_DIR=/srv/octobox/app \
  /srv/octobox/app/scripts/linux/install_public_workout_operations_timers.sh
```

Os comandos são idempotentes. A outbox recupera mensagens presas em `processing`
após dez minutos e move para `dead` depois de cinco falhas. Mensagens `dead` podem
ser reabertas no Django Admin depois de corrigir a causa.

## Ordem de rollout

1. Migrar banco com todas as flags desligadas.
2. Configurar `PUBLIC_WORKOUT_PUBLIC_BASE_URL` com HTTPS e os três Price IDs.
3. Ligar `PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED` e observar o funil.
4. Configurar a capacidade semanal, em minutos, de cada profissional.
5. Rodar reconciliação em `--dry-run`; então ligar `PUBLIC_WORKOUT_OPERATIONS_ENABLED`.
6. Manter `PUBLIC_WORKOUT_CAPACITY_MODE=observe` por no mínimo quatro semanas.
7. Passar para `warn`; só usar `enforce` se todos os pools exigidos estiverem
   configurados e o snapshot diário confirmar a medição.

## Gate de crescimento

O snapshot diário fica em `PublicWorkoutMetricSnapshot` no Admin:

- `GREEN`: capacidade configurada, sem atraso operacional e com amostra mínima;
- `YELLOW`: faltam dados ou alguma capacidade ainda não foi configurada;
- `RED`: há work item vencido ou um pool ultrapassou o limite configurado.

Não aumentar mídia com gate vermelho. Gate amarelo exige decisão humana documentada.

Antes de elevar o orçamento, execute também:

```bash
python manage.py evaluate_public_workout_growth_gate --strict
```

O comando não altera dados. Ele exige 28 snapshots diários contínuos, 14 dias verdes
consecutivos, SLO interno de pelo menos 95% e atribuição conhecida em pelo menos 70% dos
pagamentos. Em caso de amostra insuficiente ou falha, retorna código não-zero e os motivos
no JSON; não é permitido substituir essa evidência por interpretação manual.
O `ExecStartPost` do serviço de métricas roda sem `--strict`, pois resultado incompleto é esperado durante a observação
e deve ficar registrado no journal sem simular um incidente. O modo `--strict` é reservado
para a decisão humana de aumentar orçamento.

## Sinais de observabilidade

Os logs usam chaves estáveis e não incluem e-mail, token, texto de anamnese ou payload:

- `curva_funnel_client_event_rejected` e `curva_funnel_event_duplicate`;
- `curva_work_item_created` e `curva_work_item_transition`;
- `curva_publication_without_work_item`;
- `curva_outbox_lease_recovered`, `curva_outbox_delivery_failed` e
  `curva_outbox_drain_summary`;
- `curva_checkout_without_attribution`, `curva_invoice_without_attribution` e os erros
  de Price ID registrados pelo webhook;
- `curva_metrics_snapshot` e `curva_metrics_snapshot_slow`, incluindo gate, bloqueios
  e duração da captura;
- `curva_refund_requested`, `curva_refund_failed` e `curva_refund_completed`.

Alertar imediatamente para outbox `dead`, reembolso com falha e snapshot `red`. Consolidar
os demais por contagem/estado, evitando alerta por cada visita ou cálculo de capacidade.
O comando diário de métricas só imprime o payload completo quando existe ação ou mudança;
em gate verde estável responde `NO_ACTION`.

## Incidentes

### Programa ou plano publicado, mas e-mail não chegou

1. Confirmar que existe mensagem na outbox.
2. Ver `last_error` e a configuração de `PUBLIC_WORKOUT_PUBLIC_BASE_URL`.
3. Corrigir o gateway/configuração.
4. Reabrir a mensagem `dead` no Admin; não republicar conteúdo para forçar envio.

### Checkout foi barrado sem intenção

1. Trocar `PUBLIC_WORKOUT_CAPACITY_MODE` para `warn` ou `observe`.
2. Conferir minutos semanais dos profissionais e work items abertos.
3. Nunca apagar entradas da waitlist; cancelar ou convidar preserva a trilha.

### Reembolso falhou

1. Conferir `last_error` no pedido e o invoice na Stripe.
2. Verificar se a invoice possui `payment_intent` e se a assinatura ainda existe.
3. Reexecutar a ação somente no mesmo pedido: a chave idempotente evita estorno duplo.
4. Confirmar o status `refunded` do pagamento e `canceled` da assinatura.

### Assinatura ativa sem work item aberto

1. Rodar `python manage.py reconcile_public_workout_operations --dry-run` para ver
   quantas assinaturas seriam avaliadas.
2. Se a suspeita for uma conta específica, checar se ela já preencheu a anamnese
   (`training_profile`). `ensure_required_work_items` só abre trabalho depois que a
   anamnese existe — conta paga sem anamnese ainda e sem work item é esperado, não é
   incidente.
3. Rodar `python manage.py reconcile_public_workout_operations` (sem `--dry-run`) —
   é idempotente, só cria o que realmente falta. Já roda a cada hora por cadência
   normal; disparar manualmente só antecipa o ciclo.
4. Se o gap persistir depois de reconciliar com anamnese confirmada, o defeito está
   na chamada síncrona em `billing.py` (`ensure_required_work_items` no momento em
   que a assinatura vira `ACTIVE`), não em dado ausente — tratar como bug de código,
   não repetir a reconciliação esperando resultado diferente.

### `customer.subscription.updated` com Price ID desconhecido

1. Ler o log `customer.subscription.updated com Price ID desconhecido` — traz
   `event`, `subscription` e o `price` recebido da Stripe.
2. No Dashboard da Stripe, confirmar a qual produto/tier aquele Price ID pertence.
3. Comparar com `PUBLIC_WORKOUT_STRIPE_PRICE_ID_ESSENCIAL/COMPLETO/PREMIUM` do
   ambiente — o evento é descartado sem atualizar nada quando nenhuma das três
   variáveis bate com o price recebido (troca de plano feita pelo cliente no
   Customer Portal fica sem efeito no produto).
4. Corrigir a variável de ambiente e redeployar. A mudança não é reprocessada
   automaticamente: reenviar o evento pela Stripe (Dashboard → Webhooks → Resend)
   ou, como paliativo imediato, ajustar o tier manualmente no Admin.

### Evento de funil não chegou

1. Separar rejeitado de perdido antes de investigar. Rejeitado aparece no log como
   `curva_funnel_client_event_rejected reason=...` (JSON inválido, formato fora do
   esperado, tipo não-allowlisted ou `client_event_id` malformado) — é validação
   funcionando, não perda silenciosa.
2. `curva_funnel_event_duplicate` também não é perda: o mesmo `client_event_id` já
   foi salvo: leitura correta é idempotência.
3. Perda de verdade é do lado do cliente (bloqueador de anúncio, falha de rede antes
   do POST) e não deixa rastro no servidor — só aparece como queda inesperada de
   contagem no funil (ex.: `pricing_viewed` muito abaixo do esperado para o volume de
   visitas na landing).
4. Antes de investigar mais, confirmar que `PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED`
   está ligado — com a flag desligada, `record_funnel_event` retorna `None` em
   silêncio por design, e isso não é bug.

## Rollback

- Tracking: desligar `PUBLIC_WORKOUT_FUNNEL_TRACKING_ENABLED`.
- Operação: desligar `PUBLIC_WORKOUT_OPERATIONS_ENABLED`; dados existentes ficam preservados.
- Capacidade: voltar imediatamente para `observe`; a lista de espera permanece auditável.
- Entrega: interromper o scheduler da outbox sem desfazer publicações; retomar após correção.
