<!--
ARQUIVO: indice da categoria GTM (go-to-market) — material comercial executavel da Fase 1.

TIPO DE DOCUMENTO:
- indice operacional

DOCUMENTO PAI:
- [../reference/documentation-authority-map.md](../reference/documentation-authority-map.md)

QUANDO USAR:
- quando a duvida for "onde esta o script de venda", "onde registro o funil" ou
  "o que eu mando para o dono do box"

POR QUE ELE EXISTE:
- separa material comercial de documentacao tecnica sem espalhar os dois pelo repositorio.
- garante que o aprendizado de venda da Fase 1 vire arquivo versionado, e nao memoria do fundador.

O QUE ESTE ARQUIVO FAZ:
1. lista as tres pecas de campo da Fase 1 e para que serve cada uma.
2. registra a regra de precedencia entre o material comercial e o gate tecnico.

PONTOS CRITICOS:
- nenhuma peca daqui pode prometer o que o gate tecnico ainda nao sustenta. O arbitro e
  [../rollout/phase1-commercial-gate-audit-2026-08-06.md](../rollout/phase1-commercial-gate-audit-2026-08-06.md).
-->

# GTM — material de campo da Fase 1

Três peças, uma para cada momento da venda dos boxes 1 a 20.

| Peça | Para que serve | Quando usar |
|---|---|---|
| [script-abordagem-fase1.md](script-abordagem-fase1.md) | Mensagens de abertura, roteiro da demo de 20 minutos, respostas de objeção e cadência de follow-up | Todo dia, nas 10 abordagens, e antes de cada demo |
| [lista-dos-200-fase1.xlsx](lista-dos-200-fase1.xlsx) | Onde os 200 boxes-alvo vivem: score automático, prioridade A/B/C, funil e log de objeções | Preencher uma vez, atualizar depois de cada conversa |
| [one-pager-programa-fundador.html](one-pager-programa-fundador.html) | A página que o dono relê sozinho e mostra ao sócio | Enviar depois da demo, ou quando ele pedir "manda por escrito" |

## Como as três se encaixam

1. A **planilha** diz com quem falar hoje (prioridade A primeiro).
2. O **script** diz o que dizer.
3. O **one-pager** é o que fica com ele depois que a conversa acaba.
4. A objeção que ele levantar volta para a planilha — e, quando se repetir, vira seção no script.

O passo 4 é o que transforma a Fase 1 em ativo: o objetivo não é só vender 20 boxes, é **descobrir o método** que outra pessoa vai executar na Fase 2.

## Regra de precedência

O material comercial nunca pode prometer mais do que a operação sustenta.

Antes de acrescentar qualquer promessa nova a estas peças — garantia, SLA, prazo de recuperação, feature — confira o gate em [../rollout/phase1-commercial-gate-audit-2026-08-06.md](../rollout/phase1-commercial-gate-audit-2026-08-06.md).

Duas promessas hoje **proibidas** nestes materiais, porque a operação ainda não as sustenta:

1. **PIX recorrente nativo** — a recorrência automática hoje é cartão via Stripe; PIX é cobrança assistida pela fila financeira.
2. **Tempo de recuperação individual de um box** — enquanto a Parte C do [drill de restore](../rollout/restore-and-rollback-drill.md) não rodar, não existe número medido para prometer.

