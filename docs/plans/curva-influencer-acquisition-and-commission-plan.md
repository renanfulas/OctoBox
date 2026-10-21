# Curva — aquisição por influencers e comissão

**Status:** página e atribuição isolada da Jully implementadas; comissão automática e política de estorno aguardam implementação/validação.
**Data:** 2026-10-04
**Escopo:** aquisição e pagamentos do produto Curva em `/treinos/`.

## Objetivo

Medir separadamente campanhas próprias da Curva e divulgações de influencers,
atribuir novos pagamentos a um parceiro com regra clara e, se aprovado,
calcular e transferir comissão sem duplicidade.

Este plano não reutiliza o fluxo `signup.PendingSignup` do Early Adopters do
OctoBox. O corredor Curva tem landing, assinatura, tabelas financeiras, checkout
Stripe e webhooks próprios.

## Diagnóstico do runtime

Já estão implementados:

- landing `/treinos/` com captura de `utm_source`, `utm_medium` e `utm_campaign`;
- sessão de aquisição própria e cookie assinado `curva_acquisition`, `HttpOnly`,
  `SameSite=Lax` e validade de 90 dias;
- primeiro e último toque, eventos do funil e atribuição vinculada à assinatura;
- checkout Stripe e confirmação de pagamento pelo webhook/registro financeiro;
- relatório de coortes por origem, mídia e campanha em `/treinos/analytics/`;
- métricas de CAC para custos registrados por campanha.

O caminho atual não tem cadastro de influencers, link com identificador estável
de parceiro, relatório dedicado de parceiros nem geração de comissão. A rotina
financeira atual define `application_fee_amount=0` e não faz repasses.

Referências canônicas: `public_workouts/acquisition.py`,
`public_workouts/funnel_analytics.py`,
`student_identity/public_workout_views.py`,
`public_workouts/stripe_checkout.py`, `public_workouts/stripe_handlers.py`,
`public_workouts/billing.py` e `docs/runbooks/curva-funnel-analytics.md`.

## Separação obrigatória de métricas

Aquisição própria e aquisição de parceiros precisam ser categorias explícitas
e mutuamente identificáveis. Uma campanha da própria Curva nunca pode aparecer
como comissão de influencer; uma visita de influencer não pode inflar CAC de
mídia própria.

Proposta de segmentação:

1. manter o relatório geral atual como visão consolidada;
2. apresentar um bloco de **campanhas próprias**, com origem, campanha, custo,
   novos pagantes e CAC;
3. apresentar um bloco de **influencers**, com parceiro, cliques, visitantes,
   cadastros, checkouts, primeiros pagamentos, receita, estornos e comissão;
4. fazer o resumo consolidado reconciliar os dois blocos sem somar comissão como
   gasto de mídia ou duplicar receita. Se um cliente teve toque próprio e de
   influencer, a visão consolidada conta um pagante; as duas visões de canal
   podem mostrar assistência e precisam indicar essa sobreposição;
5. conservar first touch e last touch gerais para diagnóstico, além de um
   parceiro atribuído separado. O primeiro link válido de influencer dentro da
   janela definida fica associado à assinatura; links próprios e retornos
   diretos não apagam essa associação.

Os parâmetros UTM continuam úteis para ferramentas e relatórios, mas o
identificador de parceiro deve ser uma chave interna validada, e não texto
arbitrário informado pelo navegador.

## Evolução proposta

### Fase 1 — parceiro e link rastreável

- Página da Jully em `/treinos/jully/`, com identidade visual da Curva,
  conteúdo de indicação e os mesmos planos/checkout oficiais.
- Associar `partner_code=jully` à sessão analítica em campos próprios, sem gravar
  influencer em `source`, `medium` ou `campaign` das campanhas próprias.
- Contar a abertura da página, preservar first-touch de parceiro e levar o código
  até eventos, cadastro, assinatura e pagamento.
- Para adicionar parceiros além da Jully, criar cadastro de parceiro e rota
  controlada pelo slug antes de emitir novos links.
- Preservar as campanhas próprias existentes sem obrigá-las a usar o modelo de
  parceiros.
- No relatório, separar cliques brutos de visitantes únicos: cookie removido,
  bloqueadores e troca de dispositivo podem alterar a contagem de visitantes.

### Fase 2 — livro de comissão

Regra comercial definida pelo produto: **60% da primeira fatura efetivamente
paga atribuída ao influencer; 0% nas renovações**. Exemplo: numa primeira
cobrança de R$ 100, registrar R$ 60 para o parceiro e R$ 40 como participação
bruta da Curva. Os custos de processamento da Stripe são descontados da parte da
Curva, salvo nova decisão comercial.

Quando essa primeira fatura for confirmada como paga, registrar uma linha
idempotente de comissão ligada ao parceiro, à assinatura e ao pagamento. A linha
deve guardar valor-base (valor pago após descontos, antes da tarifa de
processamento Stripe), percentual, valor calculado, moeda e versão da regra
aplicada. Duplicatas de webhook não podem gerar uma segunda comissão. Pagamentos
posteriores da mesma assinatura não geram comissão.

Estados propostos: calculada, disponível, transferida, revertida e em revisão.
Estornos e chargebacks atualizam/revertem o saldo de comissão com trilha de
auditoria; não apagam o fato financeiro original.

### Fase 3 — repasse Stripe Connect

Para uma divisão automática dos fundos, cada influencer precisa ter uma conta
conectada elegível e concluir o onboarding/KYC exigido pela Stripe. O código
deve acompanhar mudanças de habilitação da conta e bloquear repasses enquanto
ela não puder recebê-los.

Para esta comissão de afiliado, a proposta é manter a assinatura e a cobrança na
conta da plataforma e criar uma transferência separada após a primeira fatura
paga e a comissão registrada. Essa abordagem permite não pagar por checkout
abandonado, fatura não paga ou renovação fora da regra. Como a Curva já oferece
garantia de reembolso de 7 dias, a recomendação é manter os R$ 60 como saldo
pendente durante essa janela e transferir depois dela; um reembolso integral
cancela o saldo antes de virar pagável. A comissão é adquirida na primeira
fatura, mas o repasse fica aguardando a janela. Se o produto preferir repassar
imediatamente, será necessário decidir como reverter a transferência em caso de
reembolso ou chargeback.

A integração precisa usar chave de idempotência, processamento recuperável e
conciliação via webhooks; o webhook de pagamento não deve fazer um repasse não
idempotente diretamente.

Stripe Connect oferece assinaturas com transferências separadas e cita taxa de
afiliado como caso de uso. Essa opção é diferente de `application_fee_percent`
com `transfer_data.destination`, que transfere uma parte por fatura e pode
refletir uma comissão recorrente. A escolha final depende de a comissão ser
única ou recorrente. [Stripe: subscriptions with Connect](https://docs.stripe.com/connect/subscriptions)

## Decisões comerciais pendentes

Antes de gerar saldo pagável, definir:

1. **Definido:** 60% sobre a primeira fatura paga; 0% sobre recorrências. Para
   transformar “60% da venda” em valor de cálculo, a proposta usa o valor
   efetivamente pago após descontos e antes das tarifas Stripe; a parte de 40%
   da Curva absorve as tarifas.
2. Confirmar a janela de atribuição ao parceiro e como tratar múltiplos links
   de influencers ou códigos compartilhados. Proposta: primeiro link válido de
   influencer recebido nos 90 dias antes do primeiro checkout.
3. **Recomendação:** disponibilizar a transferência após a garantia de
   reembolso de 7 dias já usada pela Curva; um reembolso integral nesse prazo
   cancela a comissão pendente.
4. Política para chargeback, estorno parcial e saldo já transferido.
5. Periodicidade dos repasses e tratamento de impostos/documentação dos
   parceiros.

## Revisão de arquitetura

O plano existente de produção Curva registrou que Connect Express e repasses
ficariam para a fase multi-profissional. O pedido de comissionar influencers
reabre essa decisão: influenciadores são recebedores de comissão, mesmo sem
serem profissionais que prestam o serviço. A evolução deve ficar restrita ao
corredor Curva e não alterar `signup`, `finance.Payment` do OctoBox ou outros
relatórios próprios.

Os campos atuais `PublicWorkoutSubscription.stripe_connected_account_id` e
`PublicWorkoutPayment.application_fee_amount` pertencem ao plano de repasse do
profissional. Não os reutilizar para influencers: são relações e modelos de
repasse diferentes. O parceiro deve ter identidade, onboarding e saldo de
comissão próprios.

## Critérios de aceite

- Links de influencer e UTMs de campanha própria aparecem em áreas separadas.
- Cliques, visitantes e pagantes têm nomes/unidades distintas no painel.
- A origem atribuída sobrevive ao checkout Stripe e ao webhook.
- Um único pagamento não pode gerar comissão duplicada.
- Pagamentos recusados/pendentes não geram comissão disponível.
- Estornos e chargebacks ficam reconciliados com o livro de comissão.
- Transferência automática só ocorre para parceiro habilitado e saldo elegível.
- Uma repetição de webhook/job não transfere dinheiro duas vezes.
- Os indicadores próprios e de influencer reconciliam com a visão consolidada.

## Rollout

1. Confirmar janela de atribuição, base da venda e política de estorno.
2. Adicionar novos parceiros/links mantendo o rastreamento atual compatível.
3. Validar a página da Jully, a separação do painel e a cobertura da atribuição
   em modo sem repasse.
4. Implementar o livro de comissão e reconciliar pagamentos de teste.
5. Habilitar onboarding Connect e repasses primeiro em modo de teste.
6. Liberar transferências reais somente após validar onboarding, duplicidade,
   reembolso, chargeback, falha e conciliação com Stripe.

Rollback de marketing: desativar um link/parceiro sem apagar históricos nem
alterar campanhas próprias. Rollback de payout: interromper novos repasses;
preservar o livro e reconciliar transferências já criadas antes de reabrir.
