<!--
ARQUIVO: plano de divulgacao e aquisicao dos boxes 2 a 20 do beta fechado do OctoBox.

TIPO DE DOCUMENTO:
- plano de execucao comercial

AUTORIDADE:
- alta para "como e quando divulgar o OctoBox para donos de box"
- nao substitui docs/rollout/phase1-commercial-gate-audit-2026-08-06.md, que continua
  sendo a fonte do gate tecnico que este plano depende

DOCUMENTO PAI:
- [phase1-closed-beta-20-boxes-corda.md](phase1-closed-beta-20-boxes-corda.md)

DOCUMENTOS IRMAOS:
- [../rollout/phase1-commercial-gate-audit-2026-08-06.md](../rollout/phase1-commercial-gate-audit-2026-08-06.md)
- [../rollout/restore-and-rollback-drill.md](../rollout/restore-and-rollback-drill.md)
- [../rollout/environment-activation-registry.md](../rollout/environment-activation-registry.md)
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)
- [growth-engine-activation-plan.md](growth-engine-activation-plan.md)

QUANDO USAR:
- quando a duvida for como comecar a divulgar o OctoBox e trazer os proximos boxes pagantes
- quando precisarmos decidir a ordem entre "provar que a garantia comercial e real" e "sair divulgando"
- quando quisermos organizar canal, cadencia e limite de vagas do beta fechado

POR QUE ELE EXISTE:
- o funil comercial (landing, Stripe, magic link, oferta de fundador com garantia de 60 dias)
  ja existe no codigo, mas nao existia nenhum plano de como e quando acionar divulgacao publica
  em cima dele.
- a auditoria de 2026-08-06 provou que a garantia de recuperacao individual do box so pode ser
  prometida com seguranca depois do drill de restore por tenant (Parte C). Divulgar em massa
  antes disso significa vender uma promessa que ainda nao foi ensaiada.

O QUE ESTE ARQUIVO FAZ:
1. define os canais de divulgacao (LinkedIn, landing page, Instagram, Facebook) e o papel de cada um.
2. separa "pipeline" (pode comecar ja) de "fechamento com garantia" (depende do gate tecnico).
3. define cadencia e teto de vagas para nao furar o limite de 20 boxes em 1 servidor.
4. da um checklist de saida antes de qualquer post publico ou campanha paga.

PONTOS CRITICOS:
- nao abrir campanha paga (Instagram/Facebook ads) ou anuncio publico amplo antes do gate de
  docs/rollout/phase1-commercial-gate-audit-2026-08-06.md fechar (Parte C do drill provada).
- este plano NAO autoriza abrir cadastro self-service. Toda entrada continua sendo aplicacao
  para o beta, com vaga liberada manualmente.
- preco e oferta ja estao definidos no codigo (Stripe: R$97/mes ou R$997/ano, "Early Adopter",
  1 mes gratis de teste) — este plano nao redefine preco, so organiza a aquisicao.
-->

# Plano de divulgacao — beta fechado, boxes 2 a 20

## Tese central

O OctoBox ja tem produto, ja tem funil de cobranca (Stripe + magic link + landing) e ja tem o
primeiro box pagante em producao desde 2026-05-23.

O que falta nao e criar demanda generica. E fazer duas coisas em paralelo sem deixar uma
atropelar a outra:

1. **construir pipeline** de donos de box interessados (isso pode comecar hoje)
2. **fechar o gate tecnico** que permite prometer com seguranca a garantia de 60 dias a partir
   do segundo cliente pagante (isso e pre-requisito para *fechar venda* e para *qualquer canal
   publico amplo*)

Regra de ouro: **divulgar != vender**. Dá para abrir conversa, gerar fila de espera e qualificar
lead antes do gate fechar. Não dá para *fechar* boxes 2-20 com a promessa de garantia individual
intacta enquanto a Parte C do drill continuar `pendente`.

## Estado atual (verificado no repo em 2026-08-29)

| Peca | Status |
|---|---|
| Landing page dedicada + checkout Stripe + magic link | existe (`docs/history/mudaram-o-nivel-do-projeto.md` #78-80) |
| Preco definido | R$97/mes ou R$997/ano, oferta "Early Adopter" + 1 mes gratis |
| Garantia comercial oferecida | 60 dias, discurso "seus dados sao seus" |
| Primeiro box pagante | em producao desde 2026-05-23 |
| Restore/rollback do cluster inteiro | provado (Parte A/B do drill) |
| **Restore por tenant isolado (Parte C)** | **pendente** — bloqueador da garantia a partir do box 2 |
| Teto tecnico da Fase 1 | 20 boxes, 1 servidor, isolamento forte |

## Fase 0 — Pipeline controlado (pode comecar imediatamente)

Objetivo: gerar fila qualificada de donos de box interessados, sem prometer data de entrada nem
fechar cobranca em volume, e sem canal publico amplo ainda.

### Canal 1 — LinkedIn (abordagem direta)

Este e o canal de maior controle e maior sinal — decisor identificavel, sem risco de gerar
avalanche de demanda.

1. Cadencia: 5-10 conversas novas por semana, nao mais que isso.
2. Perfil-alvo: dono/gerente de box com operacao ja rodando (nao box em fase de abertura).
3. Abordagem: mensagem curta, pergunta sobre dor operacional real (planilha, WhatsApp, controle
   financeiro manual) antes de citar o produto.
4. Oferta na conversa: "beta fechado, vagas limitadas, aplicacao — nao cadastro aberto".
5. Toda conversa fechada em interesse vai para uma lista de espera (nao para o checkout ainda,
   se o gate do drill nao tiver fechado — ver Fase 1).

### Canal 2 — Landing page existente

1. Reaproveitar a landing/funil ja construidos. Nao criar nova.
2. Ajustar copy para deixar explicito: "beta fechado", "vagas limitadas", sem linguagem de
   auto-servico irrestrito.
3. Enquanto o gate do drill nao fechar: a landing pode captar lead (fila de espera), mas o
   time decide manualmente quando liberar o checkout para cada lead — nao e self-service puro
   pros boxes 2-20.

### Canal 3 e 4 — Instagram e Facebook (organico, devagar)

Canal de construcao de prova social e autoridade, nao de conversao imediata. Nao usar como
gatilho de fechamento nesta fase.

1. Conteudo: bastidores de operacao, antes/depois de boxes que ja usam (com autorizacao),
   estrutura do produto — nunca metricas ou promessas que a Fase 1 nao sustenta (ex: nao prometer
   escala, nao prometer recursos que ainda nao existem, como owner hub completo ou
   multitenancy aberto).
2. Frequencia leve e sustentavel (ex: 1-2 posts/semana) — melhor manter ritmo real do que
   prometer cadencia que nao vai se sustentar sozinho.
3. Sem impulsionamento pago (ads) nesta fase — ver guardrail abaixo.

## Fase 1 — Gate de fechamento (pre-requisito para vender boxes 2-20 de verdade)

Antes de fechar qualquer novo box pagante (checkout liberado, cobranca ativa), o gate de
[phase1-commercial-gate-audit-2026-08-06.md](../rollout/phase1-commercial-gate-audit-2026-08-06.md)
precisa fechar:

1. [ ] Drill Parte C executado (dump de um tenant, restore isolado, `smoke_test_tenant` verde)
2. [ ] Sequencia de promocao ensaiada em homologacao
3. [ ] Tempo de recuperacao medido (vira o SLA que se pode prometer em venda)
4. [ ] Registro do drill preenchido com evidencia real
5. [ ] Uma linha no material comercial (landing, discurso de venda) dizendo o que a garantia
   cobre de fato, com o tempo medido no item 3

Enquanto isso nao fechar: leads capturados na Fase 0 ficam em fila de espera, sem cobranca ativa.
Isso e a diferenca entre "gerar pipeline" (permitido agora) e "vender a promessa de recuperacao
individual" (nao permitido agora).

## Fase 2 — Abertura controlada dos boxes 2 a 20

So comeca depois da Fase 1 fechada.

1. Liberar checkout para a fila de espera em ondas pequenas (ex: 2-3 boxes por vez, nao todos de
   uma vez), respeitando a capacidade de onboarding assistido de cada um.
2. Cada box liberado segue o mesmo checklist de go-live ja usado no primeiro
   ([first-box-production-execution-checklist.md](../rollout/first-box-production-execution-checklist.md)).
3. So a partir daqui vale considerar impulsionar Instagram/Facebook com budget pago — e mesmo
   assim, com teto de leads compativel com a capacidade de onboarding, nao com o teto de 20
   boxes do servidor (nunca vender alem da Fase 1).
4. Ao se aproximar de 15-18 boxes: comecar a preparar a transicao de Fase 1 para Fase 2 da
   escala tecnica ([scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)),
   nao esperar bater 20 para comecar a pensar nisso.

## Guardrails (o que nao fazer nesta rodada)

1. nao abrir cadastro self-service publico — toda entrada e aplicacao/fila, liberada manualmente
2. nao rodar campanha paga (Instagram/Facebook ads) antes do gate da Fase 1 fechar
3. nao prometer na divulgacao nada que dependa do Growth Engine (esse e feature futura, bloqueada
   ate 80-100 clientes — ver [growth-engine-activation-plan.md](growth-engine-activation-plan.md))
4. nao vender ou fechar cobranca do box 2 em diante com o discurso de garantia de 60 dias
   intacto enquanto a Parte C do drill continuar `pendente`
5. nao ultrapassar o teto tecnico de 20 boxes / 1 servidor da Fase 1 mesmo se a demanda permitir

## Metricas para acompanhar (Fase 0)

1. conversas iniciadas no LinkedIn por semana
2. taxa de resposta e taxa de interesse real (nao so "curtiu")
3. leads capturados na landing (fila de espera)
4. tamanho da fila de espera acumulada esperando o gate da Fase 1 fechar

## Regra final

Divulgar sem o gate fechado nao e proibido — e util para construir pipeline. O que nao pode
acontecer e fechar o box 2 em diante com a mesma promessa de garantia que ainda nao foi
ensaiada. A ordem certa e: pipeline agora, prova tecnica em paralelo, venda em volume depois
que as duas se encontrarem.
