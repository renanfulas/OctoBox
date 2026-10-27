# Contrato-fonte de webhook de enquete — Evolution API 2.3.7

**Estado:** evidência extraída do código-fonte publicado; não é captura HTTP da instalação do OCTOBOX e não autoriza ativação.

**Revisão:** 2026-10-24. O release upstream marcado como mais recente é `v2.3.7`; o commit correspondente é `cd800f2` e seu `package.json` informa `2.3.7`. A release `2.4.0-rc2` é pré-release.

## Autenticação por instância

No commit `cd800f2`, `WebhookController.emit()` copia `instance.headers`; quando encontra `jwt_key`, assina JWT HS256, envia `Authorization: Bearer <token>` e remove `jwt_key` do conjunto de headers enviados. O token tem `iat`, `exp` (600 segundos), `app=evolution` e `action=webhook`.

Isto confirma a interoperabilidade das primitivas locais `authenticate_evolution_callback()` para esse contrato de autenticação. Ainda é preciso confirmar que a instalação alvo está nessa versão e que conserva a configuração por instância após reinício.

## `MESSAGES_UPSERT`: candidato individual por voto

No handler `messages.upsert`, quando a mensagem recebida é `pollUpdateMessage`, a Evolution:

1. Lê `message.pollUpdateMessage.pollCreationMessageKey` e procura a mensagem original no armazenamento local.
2. Usa o segredo da mensagem original e `decryptPollVote()` para resolver o voto, quando os dados necessários estão disponíveis.
3. Compara as opções selecionadas com os hashes das opções originais e grava os nomes resolvidos em `message.pollUpdateMessage.vote.selectedOptions`.
4. Preenche `data.pollUpdates` com opções `{name, voters}` e envia `MESSAGES_UPSERT` com `messageRaw`.

O esqueleto abaixo descreve os campos que o código fonte constrói; **não é um payload capturado nem um fixture de release instalado**:

```json
{
  "event": "messages.upsert",
  "instance": "<instancia-opaca>",
  "data": {
    "key": {
      "id": "<id-candidato-do-voto>",
      "remoteJid": "<grupo-redigido>@g.us",
      "participant": "<jid-do-votante-redigido>",
      "fromMe": false
    },
    "messageType": "pollUpdateMessage",
    "message": {
      "pollUpdateMessage": {
        "pollCreationMessageKey": {
          "id": "<id-da-enquete>",
          "remoteJid": "<grupo-redigido>@g.us"
        },
        "vote": {"selectedOptions": ["<opcao-em-texto>"]}
      }
    },
    "pollUpdates": [
      {"name": "<opcao-em-texto>", "voters": ["<jid-do-votante-redigido>"]}
    ]
  }
}
```

### Resultado candidato e condições de rejeição

| Entrada | Resultado esperado da futura adapter | Evidência ainda exigida |
|---|---|---|
| `pollUpdateMessage` com `pollCreationMessageKey`, mensagem original disponível, opção resolvida e JID do votante | Candidate para normalização de uma intenção de voto; `data.key.id` é candidato a identificador de evento | Confirmar no fixture real o formato, estabilidade em retry e associação do JID a telefone pertencente ao Box |
| Mensagem original ausente da store da Evolution | Não inferir título nem opção; não registrar presença | Confirmar se a Evolution reenvia ou se o evento fica sem opção resolvida |
| `selectedOptions` vazio ou sem opção conhecida | Rejeitar sem escrita | Fixture redigida de falha de decrypt/option mismatch |
| JID `@lid`, `participant` ausente ou telefones alternativos em conflito | Não adivinhar telefone pelo `remoteJid` do grupo nem pelo nome da opção | Confirmar `participant`, `participantAlt`, `remoteJidAlt` e estratégia de lookup de identidade |
| Mesmo `data.key.id` e mesmo conteúdo em retry | Retornar a mesma intenção persistida, sem repetir presença | Confirmar ID em duas entregas do mesmo voto |
| Mesmo `data.key.id` com opção diferente | Conflito; não aceitar uma segunda interpretação | Verificar se a instalação altera o ID em edição de voto |

`data.key.id` é apenas candidato até a captura confirmar que identifica a mensagem individual do voto e persiste em reentregas. `pollCreationMessageKey` identifica a enquete de origem; não substitui o ID do voto.

## `MESSAGES_UPDATE`: estado agregado

O handler `messages.update` monta `data` com `keyId`, `remoteJid`, `fromMe`, `participant`, `status`, `pollUpdates` e `instanceId`; `messageId` pode ser acrescentado se a mensagem original foi encontrada. `pollUpdates` é produzido por `getAggregateVotesInPollMessage()` a partir da mensagem de enquete armazenada.

Esse formato não fornece, no código inspecionado, um identificador individual de voto equivalente a `data.key.id` do caminho `MESSAGES_UPSERT`. Não usar `keyId` da enquete como `event_id` individual. A atualização atual também deduplica por instância, `key.id` e status, com cache de 30 minutos; isto não prova semântica de replay para votos agregados.

## Decisão de integração

- Se a instalação comprovar `2.3.7` e o fixture real corresponder ao caminho de voto resolvido, avaliar `MESSAGES_UPSERT` como evento de entrada da adapter.
- Não aceitar `MESSAGES_UPDATE` como evento individual sem uma decisão explícita sobre snapshot, diff, voto alterado, reordenação e persistência da última seleção.
- Exigir HTTPS, configuração por instância, JWT Evolution separado da chave HMAC OctoBOX e resolução de Box exclusivamente por mapa server-side.
- Não habilitar parser, endpoint bridge ou tráfego até receber a versão/tag/imagem instalada e fixture de enquete criada + voto, redigida e capturada em ambiente descartável.

## Fontes primárias

- [Release oficial v2.3.7, commit `cd800f2`](https://github.com/evolution-foundation/evolution-api/releases/tag/2.3.7)
- [WebhookController no commit `cd800f2`](https://github.com/evolution-foundation/evolution-api/blob/cd800f2/src/api/integrations/event/webhook/webhook.controller.ts)
- [Baileys service no commit `cd800f2`](https://github.com/evolution-foundation/evolution-api/blob/cd800f2/src/api/integrations/channel/whatsapp/whatsapp.baileys.service.ts)
