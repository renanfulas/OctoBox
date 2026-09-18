<!--
ARQUIVO: plano de divulgacao e aquisicao dos boxes 2 a 20 do beta fechado do OctoBox,
desenhado para operar em ciclo 80% agente / 20% humano.

TIPO DE DOCUMENTO:
- plano de execucao comercial e operacional

AUTORIDADE:
- alta para "como e quando divulgar o OctoBox para donos de box"
- nao substitui docs/rollout/phase1-commercial-gate-audit-2026-08-06.md para a decisao tecnica
  de restore por tenant, mas esta rodada NAO trata esse gate como bloqueador de divulgacao
  (decisao explicita do dono do produto em 2026-08-29 — ver secao "O que fica de fora por ora")

DOCUMENTO PAI:
- [phase1-closed-beta-20-boxes-corda.md](phase1-closed-beta-20-boxes-corda.md)

DOCUMENTOS IRMAOS:
- [../rollout/phase1-commercial-gate-audit-2026-08-06.md](../rollout/phase1-commercial-gate-audit-2026-08-06.md)
- [../rollout/environment-activation-registry.md](../rollout/environment-activation-registry.md)
- [scale-transition-20-100-open-multitenancy-plan.md](scale-transition-20-100-open-multitenancy-plan.md)
- [growth-engine-activation-plan.md](growth-engine-activation-plan.md)

QUANDO USAR:
- quando a duvida for como comecar a divulgar o OctoBox e trazer os proximos boxes pagantes
- quando quisermos saber o que e trabalho do agente (pesquisa, redacao, conteudo, rastreio) e o
  que exige a mao do dono do produto (enviar, postar, conversar com o lead)

POR QUE ELE EXISTE:
- a primeira versao deste plano (2026-08-29, manha) sequenciava divulgacao atras do gate tecnico
  de restore por tenant. O dono do produto decidiu explicitamente destravar a divulgacao agora e
  tratar o gate tecnico como frente paralela, nao como bloqueador.
- o pedido concreto desta rodada foi um plano com alta probabilidade real de conversao e uma
  divisao de esforco de aproximadamente 80% agente / 20% humano, para ganhar escala sem o dono
  do produto virar gargalo operacional.

O QUE ESTE ARQUIVO FAZ:
1. ordena os canais por probabilidade de conversao x automatizabilidade real (nao por moda).
2. separa, tarefa por tarefa, o que o agente faz sozinho do que exige a mao do humano.
3. desenha um ciclo operacional semanal que roda sem o humano precisar pedir de novo.
4. define o que cada canal PODE e NAO PODE fazer dado o teto tecnico de 20 boxes / 1 servidor.

PONTOS CRITICOS:
- nao existe conector de LinkedIn, Instagram ou Facebook nesta sessao — o agente nao consegue
  postar nem mandar DM diretamente nessas redes. Automatizavel de fato: pesquisa, redacao,
  geracao de imagem/video (Higgs), e-mail (Gmail), landing/SEO (repo), rastreio de pipeline.
  Nao automatizavel sem o humano: clicar enviar/postar nas 3 redes, e a conversa de venda em si.
- primeiras semanas de e-mail saem como RASCUNHO no Gmail, nao envio direto — ver guardrail de
  reputacao. Autonomia de envio direto e uma etapa deliberada, so depois de validar a mensagem.
- este plano NAO autoriza abrir cadastro self-service. Toda entrada continua sendo aplicacao
  para o beta, com vaga liberada manualmente pelo dono do produto.
- preco e oferta ja estao definidos no codigo (Stripe, conta `Octoboxfit`, livemode: R$97/mes ou
  R$997/ano, oferta "Early Adopter" + 1 mes gratis) — este plano nao redefine preco.
-->

# Plano de divulgacao — ciclo 80/20 agente/humano

## Tese central

O OctoBox ja tem produto e ja tem o primeiro box em producao (Endorfina Cross, desde 2026-05-23).
O funil de cobranca "Early Adopter" (Stripe + magic link + landing) ja esta configurado, mas uma
leitura direta do Stripe em 2026-08-29 mostrou que **nunca foi usado de verdade** — zero
assinaturas, zero clientes, zero faturas na conta livemode. Confirmado com o dono do produto em
2026-08-29: **o Fernando esta em acordo manual, fora do Stripe** — nunca passou pelo checkout.
Consequencia direta: o checkout de assinatura em si **nunca foi provado ponta a ponta com
pagamento real**. Ver "Achado critico do Stripe" em
[divulgacao-pipeline-tracker.md](divulgacao-pipeline-tracker.md).

O gargalo não é falta de canal — é que todo canal óbvio (LinkedIn, Instagram, Facebook) exige
mãos humanas para postar e conversar, e o dono do produto é um time de uma pessoa só. Então a
pergunta certa não é "qual rede social", é: **qual estrutura faz o agente absorver o máximo de
trabalho (pesquisa, redação, conteúdo, rastreio, follow-up) e deixa para o humano só os cliques
que fisicamente só um humano pode dar?**

Regra de ouro deste plano: **se uma tarefa pode ser pesquisa, texto, imagem/vídeo ou
rastreamento — o agente faz. Se a tarefa é "clicar enviar numa rede sem API" ou "ter uma
conversa de venda" — cai para o humano, já pronta para execução em segundos, não em minutos.**

## Por que os canais estão nesta ordem (probabilidade x automatizabilidade)

> **Revisão de 2026-08-29 (tarde):** esta ordem foi ajustada depois da primeira leva real de
> pesquisa. A fonte de dados de boxes (TomTom Maps) entrega **telefone, não e-mail** — e a
> maioria dos telefones é celular, ou seja, WhatsApp. O canal *disponível* para este público não
> é e-mail; é telefone/WhatsApp. Ver "Achado que muda o plano" em
> [divulgacao-pipeline-tracker.md](divulgacao-pipeline-tracker.md).

| Ordem | Canal | Por que aqui | Automatizável pelo agente |
|---|---|---|---|
| 1 | **Indicação do cliente atual** | Box de CrossFit é comunidade pequena e interconectada (competições, afiliação). Indicação calorosa converte muito mais que abordagem fria, e custa uma mensagem. Reforçado pela pesquisa: 7 dos 119 leads levantados são de Guarulhos, mesma cidade da Endorfina — o Fernando provavelmente conhece vários. | Pesquisa de contexto + redação da mensagem de pedido de indicação e do follow-up — 90% |
| 2 | **WhatsApp (contato morno)** | É onde o público vive, e é o contato que a pesquisa efetivamente entrega. Restrito a contato morno: indicação do Fernando e quem já respondeu por outro canal. **Nunca disparo frio em massa** — queima o número. | Redação da mensagem — 90%; envio depende do conector de WhatsApp estar ativo |
| 3 | **Cold e-mail** | Continua sendo o canal de melhor controle ponta a ponta (Gmail conectado), mas cai de posição porque o e-mail do box precisa ser garimpado site a site — não vem pronto na pesquisa. | Garimpo do e-mail + redação + rascunho pronto — 85%; envio inicial fica com humano por reputação (ver guardrail) |
| 4 | **LinkedIn (abordagem direta)** | Decisor identificável, mas sem API — precisa de humano em cada envio. Cobertura de dono de box pequeno no LinkedIn tende a ser fraca no Brasil. | Pesquisa de perfil + redação da mensagem — 80%; enviar é sempre humano |
| 5 | **Landing page + SEO** | Já existe, zero atrito, captura organicamente sem ação recorrente do humano. | Cópia, formulário, conteúdo de blog/SEO — 100%, é código no repo |
| 6 | **Instagram / Facebook orgânico** | Onde donos de box efetivamente vivem, mas **não existe conector de publicação** no registry (só analytics e ads) — cada post exige upload humano. | Roteiro, legenda e a imagem/vídeo em si via Higgs — 85%; postar é sempre humano |

Ordem 1-3 são as de maior retorno por esforço humano — priorizar aí primeiro. 4-6 entram no ciclo
semanal em paralelo, não depois.

### Sinal de qualificação descoberto na pesquisa

Box com URL `crossfit.com/gym/...` é **afiliado oficial da CrossFit HQ** — paga taxa de
afiliação, logo é negócio estabelecido, com operação real e carga administrativa de verdade.
É o alvo mais qualificado e deve ser contatado primeiro dentro de cada região.

## Estado atual (verificado no repo + Stripe em 2026-08-29)

| Peça | Status |
|---|---|
| Landing page dedicada + checkout Stripe + magic link | existe (`docs/history/mudaram-o-nivel-do-projeto.md` #78-80), **nunca testada ponta a ponta com pagamento real** |
| Preço definido | R$97/mês ou R$997/ano, oferta "Early Adopter" + 1 mês grátis — preços configurados no Stripe, mas sem nenhuma venda registrada |
| Conta Stripe conectada nesta sessão | `Octoboxfit`, **livemode** — confirmado: 0 assinaturas, 0 clientes, 0 faturas |
| Primeiro box (Endorfina Cross) | em produção desde 2026-05-23; **acordo manual com o Fernando, fora do Stripe** (confirmado com o dono do produto em 2026-08-29) |
| Teto técnico da Fase 1 | 20 boxes, 1 servidor, isolamento forte |
| Gate de restore por tenant | pendente, tratado como frente paralela nesta rodada (não bloqueia divulgação) |

## Divisão de trabalho por atividade

| Atividade | Quem faz | Detalhe |
|---|---|---|
| Pesquisar boxes-alvo (nome, cidade, endereço, telefone, site) | **Agente** | via TomTom Maps — enumeração sistemática por raio geográfico, ~40 resultados por consulta, sem precisar de lista pronta do humano |
| Redigir mensagem de pedido de indicação ao cliente atual | **Agente** | pronta para copiar/colar ou enviar por e-mail direto |
| Redigir e-mail frio personalizado por lead | **Agente** | usa o que achou na pesquisa (dor real, não genérico) |
| Enviar as primeiras levas de e-mail | **Humano** (1a fase) → **Agente** depois de validar | ver guardrail de reputação abaixo |
| Redigir mensagem de LinkedIn por lead | **Agente** | pronta para colar |
| Enviar conexão/DM no LinkedIn | **Humano** | sem API, sem alternativa |
| Roteiro + legenda de post/reel | **Agente** | |
| Gerar a imagem/vídeo do post | **Agente** (Higgs) | |
| Publicar no Instagram/Facebook | **Humano** | sem API, sem alternativa |
| Escrever/ajustar copy da landing e conteúdo de SEO | **Agente** | edita o repo direto, vira PR |
| Ter a conversa quando o lead responde | **Humano** | é venda de verdade, não delega |
| Registrar estágio do lead no rastreador | **Agente** | atualiza o arquivo semanalmente a partir do que o humano reportar |
| Ler conversão real no Stripe | **Agente** | usa o conector já conectado |

Contagem honesta: das ~13 linhas acima, 9 são 100% ou majoritariamente agente. As 4 que exigem
humano (indicação pessoal ao cliente, enviar LinkedIn, postar Instagram/Facebook, ter a
conversa) são justamente as que **não têm substituto técnico** — não é escolha de escopo, é
limite real de API nesta sessão.

## Ciclo operacional semanal (o agente roda isso sem precisar ser chamado de novo)

Cada semana, o agente:

1. Varre uma região nova com o TomTom Maps (raio geográfico), deduplica por marca, filtra
   não-boxes e adiciona ao rastreador já qualificado por afiliação oficial. Guarulhos, ZN/ZL,
   zona sul, ABC e zona oeste/Osasco já cobertos (119 leads no tracker) — a partir daqui o
   gargalo é contato, não pesquisa; nova varredura só quando os tiers atuais se esgotarem sem
   converter. Próxima fronteira, se necessário: litoral e interior próximo, ou outras capitais.
2. Redige e deixa como **rascunho no Gmail** os e-mails frios da semana (um por lead novo).
3. Redige as mensagens de LinkedIn da semana (5-10, no ritmo que um humano consegue mandar sem
   parecer bot) e entrega como lista pronta para copiar/colar.
4. Gera 1-2 peças de conteúdo (imagem ou vídeo curto) para Instagram/Facebook com legenda pronta.
5. Lê o Stripe e reporta: quantos checkouts iniciados, quantos completados, MRR atual.
6. Atualiza o rastreador de pipeline com tudo isso e resume em uma mensagem curta ao humano:
   **o que está pronto para ele clicar enviar/postar, e nada além disso.**

O humano, por semana, precisa fazer no máximo:
1. Enviar a mensagem de indicação ao cliente atual (uma vez, não repete toda semana).
2. Revisar e enviar os rascunhos de e-mail no Gmail (poucos minutos).
3. Copiar/colar as mensagens de LinkedIn prontas (poucos minutos).
4. Fazer upload dos posts gerados no Instagram/Facebook (poucos minutos).
5. Responder quem respondeu.

## Rastreador de pipeline

Fonte única de verdade do funil, mantida pelo agente em
[`docs/plans/divulgacao-pipeline-tracker.md`](divulgacao-pipeline-tracker.md) — versionada no
repo, sem depender de planilha externa. Colunas: nome do box, canal, cidade, estágio (pesquisado
→ contatado → respondeu → aplicou no beta → fechado), última ação, próxima ação.

## Canal 1 — Indicação do cliente atual (prioridade máxima, começa nesta semana)

1. Agente redige uma mensagem curta pedindo 2-3 indicações de outros donos de box que o cliente
   atual conhece (competição, afiliação, grupo de WhatsApp do nicho).
2. Humano envia (pessoalmente ou por WhatsApp/e-mail — fora do escopo de automação desta sessão).
3. Cada indicação vira lead de prioridade alta no rastreador, contatado por e-mail ou LinkedIn
   pelo agente com menção explícita a quem indicou.

## Canal 2 — Cold e-mail (maior volume automatizável)

1. Agente pesquisa e-mail público do box (site institucional, Instagram bio, Google Meu Negócio).
2. Agente redige e-mail curto e específico — nunca template genérico — citando um sinal real de
   dor operacional encontrado na pesquisa.
3. **Guardrail de reputação**: as primeiras 2-3 semanas, os e-mails ficam como rascunho no Gmail
   para o humano revisar e enviar. Depois de validar taxa de resposta (nenhuma reclamação de
   spam, resposta positiva > 0), o agente pode passar a enviar direto, com o humano avisado antes
   dessa mudança de modo.
4. Follow-up automático: se não houver resposta em 5 dias úteis, agente redige um segundo
   toque (rascunho), nunca mais que dois toques sem resposta.

## Canal 3 — LinkedIn (abordagem direta)

1. Cadência: 5-10 conversas novas por semana — ritmo humano, não rajada de bot.
2. Perfil-alvo: dono/gerente de box com operação já rodando.
3. Agente prepara a mensagem (pergunta sobre dor real antes de citar produto); humano cola e
   envia.
4. Oferta na conversa: "beta fechado, vagas limitadas, aplicação" — nunca cadastro aberto.

## Canal 4 — Landing page e SEO

1. Ajustar copy para deixar claro "beta fechado, vagas limitadas" sem soar auto-serviço
   irrestrito.
2. Agente pode propor e implementar (via PR) conteúdo de SEO/blog sobre dores reais de gestão de
   box (planilha, WhatsApp, cobrança manual) para captação orgânica de médio prazo — trabalho de
   repositório, zero recorrência de esforço humano depois de publicado.

## Canal 5 — Instagram e Facebook (orgânico)

1. Conteúdo: bastidores de operação, prova social do box atual (com autorização), estrutura do
   produto.
2. Nunca prometer recursos que não existem (owner hub completo, multitenancy aberto, Growth
   Engine — essa é feature futura bloqueada até 80-100 clientes, ver
   [growth-engine-activation-plan.md](growth-engine-activation-plan.md)).
3. Frequência sustentável: 1-2 posts/semana, gerados pelo agente, publicados pelo humano.
4. Sem impulsionamento pago nesta rodada — reavaliar quando o volume de pipeline pedir.

## Guardrails

1. Não abrir cadastro self-service público — toda entrada é aplicação/fila, vaga liberada
   manualmente.
2. Não ultrapassar o teto técnico de 20 boxes / 1 servidor da Fase 1, mesmo se a demanda permitir.
3. Não prometer na divulgação nada que dependa do Growth Engine.
4. E-mail frio nunca sai em modo "envio automático" sem o humano ter validado pelo menos uma
   rodada de rascunhos primeiro.
5. Nenhuma mensagem (e-mail, LinkedIn, legenda) promete SLA de recuperação de dados além do que
   já está publicamente assumido hoje — isso continua sendo decisão do gate técnico, tratado à
   parte.
6. Não fechar (cobrança ativa) nenhum box do Tier 1/2/3 antes de rodar um checkout de teste
   ponta a ponta (pagamento → webhook → e-mail de ativação → onboarding) pelo menos uma vez —
   o funil nunca foi provado com pagamento real (ver "Achado crítico do Stripe" no
   [tracker](divulgacao-pipeline-tracker.md)). Gerar pipeline e ter a conversa pode continuar
   normalmente; só a cobrança fica pendente desse teste.

## O que fica de fora por ora

O gate de restore por tenant (`phase1-commercial-gate-audit-2026-08-06.md`) segue como frente
paralela e não bloqueia nada neste plano — decisão explícita do dono do produto em 2026-08-29.
Continua registrado porque é uma promessa comercial real (garantia de 60 dias) e alguém vai
precisar fechar essa frente antes do volume de boxes pagantes crescer o suficiente para o risco
virar concreto — mas isso não trava a divulgação agora.

## Métricas do ciclo semanal

1. leads pesquisados e adicionados ao rastreador
2. e-mails/LinkedIn enviados (não só rascunhados) e taxa de resposta
3. peças de conteúdo publicadas
4. checkouts iniciados vs. completados no Stripe, MRR atual
5. tamanho da fila de aplicação para o beta

## Regra final

O agente absorve pesquisa, redação, conteúdo e rastreio — a parte que consome tempo mas não
exige ser humano. O humano absorve o clique que só ele pode dar e a conversa que só ele pode
ter. Essa divisão é o que faz o plano escalar sem o dono do produto virar gargalo — e é
mensurável: se depois de 2-3 semanas o humano estiver gastando mais que ~20% do tempo do ciclo
nisso, o plano está desequilibrado e precisa ser revisto.
