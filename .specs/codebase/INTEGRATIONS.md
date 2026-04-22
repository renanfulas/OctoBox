# External Integrations - OctoBOX

O OctoBOX se conecta a diversos serviços externos para viabilizar pagamentos, comunicações e monitoramento. Este documento mapeia essas conexões e como elas são tratadas no código.

## 1. Stripe (Pagamentos)

O Stripe é o nosso motor financeiro principal.

*   **Implementação:** Localizada em `integrations/stripe/` e `finance/payment_services.py`.
*   **Fluxos:**
    *   **Checkout Session:** Criado dinamicamente para matrículas.
    *   **Webhooks:** Recebidos em `/integrations/stripe/webhook/`. Tratados com idempotência via `WebhookIdempotencyMiddleware`.
    *   **Versão da API:** 15.0.0 (Python SDK).

## 2. WhatsApp Cloud API (Comunicação)

Utilizado para notificações automáticas e suporte.

*   **Implementação:** Lógica de negócio em `communications/` e camada de transporte em `integrations/whatsapp/`.
*   **Identidade:** O `WhatsAppContact` é vinculado ao `Student` através do `phone_lookup_index`.

## 3. Redis (Cache & Shadow State)

Utilizado para desacoplar a leitura pesada do banco de dados principal.

*   **Implementação:** `shared_support/redis_snapshots.py`.
*   **Armazenamento:** Salva dicionários JSON que representam o "Estado Financeiro" do aluno, permitindo que o Dashboard carregue instantaneamente sem JOINS complexos.

## 4. Monitoramento e Observabilidade

*   **Sentry:** Captura exceções não tratadas e performance profiling.
*   **Prometheus:** Middleware em `monitoring/prometheus_middleware.py` que expõe métricas de tempo de resposta e status de requisições para o Grafana.

## 5. Segurança de Integração

*   **Signature Verification:** Todas as integrações de Webhook (Stripe e WhatsApp) validam a assinatura da carga útil para evitar ataques de personificação.
*   **Idempotency Keys:** Usamos chaves de idempotência para garantir que falhas de rede não causem cobranças duplicadas.
