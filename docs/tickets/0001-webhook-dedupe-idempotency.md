**Título:** Webhooks WhatsApp: duplicação de mensagens / falta de idempotência

**Resumo:**
Durante a simulação operacional foram observadas duplicações de mensagens e eventos quando o Evolution API retorna erros temporários (ex: 502) e reenvia payloads. O handler atual não garante idempotência, resultando em message_logs duplicados e contatos criados em duplicidade.

**Impacto:**
- Métricas do Owner ficam inconsistentes.
- Manager enfrenta trabalho manual para remover duplicatas.
- Maria lida com registros de conversa duplicados no atendimento.

**Arquivos/locais relevantes:**
- `integrations/whatsapp/services.py`
- `communications.facade` (flow de registro inbound)
- Handlers de webhook em `api/v1/integrations/whatsapp` (se presentes)
- Modelos relacionados a message logs / contacts (ex.: `communications`, `students`)

**Passos para reproduzir:**
1. Configurar Evolution/API para apontar webhook para ambiente de staging do OctoBOX.
2. Enviar um payload de mensagem válido (payload A) — observar criação de `message_log`/entrada.
3. Simular falha temporária do OctoBOX (forçar 502 ou cortar rede) no momento do primeiro envio e permitir que o Evolution reenvie o mesmo payload A.
4. Verificar que o sistema criou um segundo registro idêntico (duplicata).

**Comportamento esperado:**
- Reenvios idênticos não devem criar novas entradas; o webhook deve reconhecer e ignorar duplicatas.

**Causa provável:**
- Ausência de campo `external_id`/fingerprint persistido para mensagens webhook recebidas.
- Handlers aplicando criação direta sem verificação dedupe antes de gravar.
- Falta de transação/lock ou uso de fila idempotente para processamento concorrente.

**Proposta de solução (passos técnicos):**
1. Adicionar persistência identificadora nas entidades de entrada de mensagens
   - Novo campo opcional `external_id` (string/UUID) em `communications.MessageLog` ou model equivalente.
   - Index único parcial (`external_id` não nulo) para prevenir duplicatas ao inserir.
2. Calcular e persistir um `webhook_fingerprint` no momento do recebimento
   - fingerprint = HMAC(payload_serializado, secret) ou hash determinístico dos campos relevantes.
3. Atualizar handler de webhook (`integrations/whatsapp/services.py` ou camada de facade) para:
   - Extrair `external_id` do payload quando presente (por exemplo, id da mensagem no Evolution).
   - Calcular `webhook_fingerprint` sempre.
   - Tentar inserir record com `external_id` ou `fingerprint` dentro de transação; em caso de conflito de chave única, abortar processamento e retornar 200 OK ao webhook.
4. Tornar processamento idempotente:
   - Se o evento já existe, logar e retornar sucesso sem recriar entidades dependentes (contacts, registros de presença, etc.).
5. Opcional/forte recomendação: mover processamento para fila (Rabbit/Celery/Kafka) com consumer idempotente e retries configurados.
6. Adicionar testes unitários e integração que:
   - Verifiquem que reenvios idênticos não criam duplicatas.
   - Simulem concurrency e retries.
7. Instrumentação/observabilidade:
   - Métricas Prometheus: contador `webhook_duplicates_detected` e `webhook_processing_latency`.
   - Logs estruturados com `webhook_fingerprint` para triagem.

**Patch/diff sugerido (esboço):**
- Model: adicionar campo `external_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)` e `webhook_fingerprint = models.CharField(max_length=64, db_index=True)` + `UniqueConstraint(fields=['external_id'], condition=Q(external_id__isnull=False))`.
- Handler: defensiva `get_or_create` por `external_id` ou `webhook_fingerprint`.

**Critérios de aceitação:**
- Reenvios idênticos do mesmo payload não criam novos registros.
- Métricas mostram redução de duplicatas após deploy.
- Testes automatizados cobrindo reenvios passam na CI.

**Estimativa de esforço:**
- Implementação e migração do DB: 1–2 dias
- Testes + QA: 1 dia
- Observability + deploy: 0.5–1 dia

**Prioridade:** Alta (impacto em métricas e operação diária).

**Notas:**
- Garantir migração segura: criar campo nullable e deploy do código que só usa campo se presente; depois popular e adicionar constraint única em migração subsequente.
- Rever integração com Evolution para confirmar onde buscar `external_id` (nome do campo no payload).

---
_Ticket gerado automaticamente pelo assistente — se quiser, eu posso abrir um PR com migração/model/tarefas de handler esboçadas._