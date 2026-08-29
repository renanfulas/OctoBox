<!--
ARQUIVO: rastreador vivo do pipeline de divulgacao/aquisicao dos boxes 2 a 20.

TIPO DE DOCUMENTO:
- rastreador operacional (dados, nao decisao)

AUTORIDADE:
- alta para "qual e o estado atual do pipeline" — atualizado pelo agente no ciclo semanal
- nao substitui docs/plans/divulgacao-launch-plan.md, que e o plano; este arquivo e so o estado

DOCUMENTO PAI:
- [divulgacao-launch-plan.md](divulgacao-launch-plan.md)

QUANDO USAR:
- quando a duvida for "quantos leads temos, em que estagio, o que fazer a seguir"
- como insumo do ciclo semanal descrito no plano pai

POR QUE ELE EXISTE:
- fonte unica de verdade do funil comercial, versionada no repo em vez de planilha externa,
  para o agente conseguir ler e atualizar sem depender de ferramenta fora do ambiente.

O QUE ESTE ARQUIVO FAZ:
1. lista os leads por estagio do funil.
2. registra ultima acao e proxima acao por lead.
3. acumula metricas semanais simples.

PONTOS CRITICOS:
- estagios: pesquisado -> contatado -> respondeu -> aplicou no beta -> fechado (ou descartado).
- este arquivo comeca vazio nesta rodada — o primeiro ciclo semanal do plano pai preenche a
  primeira leva de leads pesquisados.
-->

# Rastreador de pipeline — divulgação OctoBox

## Como ler este arquivo

Cada linha é um lead (dono de box). Estágio segue sempre esta ordem:
`pesquisado` → `contatado` → `respondeu` → `aplicou no beta` → `fechado` (ou `descartado`, com motivo).

## Leads

| Box | Cidade | Canal | Estágio | Última ação | Próxima ação | Indicado por |
|---|---|---|---|---|---|---|
| _(vazio — primeira rodada de pesquisa ainda não rodou)_ | | | | | | |

## Indicações pendentes (Canal 1)

| Pedido enviado a | Data | Resposta | Indicações recebidas |
|---|---|---|---|
| _(vazio — mensagem de pedido de indicação ainda não foi enviada ao cliente atual)_ | | | |

## Métricas semanais

| Semana | Leads pesquisados | E-mails enviados | LinkedIn enviados | Respostas | Posts publicados | Checkouts iniciados (Stripe) | Checkouts completados (Stripe) | MRR |
|---|---|---|---|---|---|---|---|---|
| _(primeira semana ainda não fechada)_ | | | | | | | | |

## Notas do ciclo

_(o agente adiciona aqui observações curtas a cada atualização semanal — ex: sinais de dor
recorrentes encontrados na pesquisa, mensagens que estão gerando mais resposta, ajustes de
abordagem)_
