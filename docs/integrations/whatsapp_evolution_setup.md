# Integração de enquetes Evolution → OctoBOX

## Estado

A conexão direta com `api-v1-whatsapp-poll-webhook` não está pronta. O script antigo desta página
foi removido porque configurava a URL do receiver sem autenticação compatível e enviava nomes de
eventos/campos que não correspondem ao contrato atual. Não configure a Evolution para apontar
diretamente para esse endpoint.

O receiver OctoBOX está implementado em `api/v1/integrations_views.py` e
`integrations/whatsapp/webhook_auth.py`. Ele autentica HMAC-SHA256 sobre os bytes originais e exige
os headers `X-OctoBox-Instance`, `X-OctoBox-Timestamp`, `X-OctoBox-Event-Id`, `X-OctoBox-Key-Id` e
`X-OctoBox-Signature`. O corpo tem de ser JSON normalizado com `event_id`, `voter_phone`,
`poll_name` e `option_text`; o `event_id` deve ser id estável e coincidir com o header assinado.
O mapa de instância para Box é server-side, e a configuração `WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON`
permanece vazia por padrão.

Primitivas locais de autenticação JWT→HMAC estão em `integrations/whatsapp/evolution_bridge.py`.
Elas verificam JWT HS256 de propósito `evolution/webhook`, validade máxima de 10 minutos, rota
opaca configurada, segredo JWT diferente da chave HMAC e assinatura do DTO normalizado no protocolo
do receiver. O formato opcional esperado na configuração por instância é:

```json
{
  "instance-opaque-id": {
    "schema": "box_example",
    "evolution_jwt_secret": "<segredo exclusivo da Evolution com ao menos 32 bytes>",
    "active_hmac_key_id": "evo-hmac-v1",
    "keys": {"evo-hmac-v1": "<chave HMAC OctoBOX distinta, com ao menos 32 bytes>"}
  }
}
```

Essas primitivas ainda não são uma bridge implantável: não há endpoint HTTP, transporte para o
receiver, configuração de produção nem adapter de payload. A configuração Evolution teria de
enviar `X-OctoBox-Instance` e `Authorization: Bearer ...`; isso deve ser confirmado na release real.
Reentregas precisam ser deduplicadas pelo ID estável do voto no inbox tenant-local; o JWT de curta
duração não é proteção contra replay do evento.

## Auditoria da fonte upstream — candidata 2.4.0-rc2 (23/10/2026)

Na fonte oficial do commit `5624bda` (canal `develop`, release candidata `2.4.0-rc2`), o fluxo
Baileys de `messageHandle` localiza a mensagem original da enquete a partir de
`pollCreationMessageKey`, obtém o segredo e o contexto das opções no armazenamento da própria
Evolution, descriptografa o payload e resolve os hashes para nomes de opção antes de emitir
`MESSAGES_UPSERT`. O objeto contém `messageRaw.key.id` e `pollUpdates`; o título vem da mensagem
original correlacionada, não do evento de voto. O identificador e os campos do votante ainda
precisam ser confirmados por fixture da imagem instalada, incluindo JID alternativo e normalização
do telefone.

Isso torna necessária uma correlação prévia da criação da enquete por `(instance_id,
poll_message_id)` para recuperar o título no adapter. A bridge não deve descriptografar
`encPayload` nem inferir título, telefone ou identidade do voto. A fonte consultada pertence a uma
release candidata de `develop`; ela não prova que a imagem usada pelo OctoBOX publique o mesmo
payload ou sequer suporte os headers JWT descritos acima. Referências: [release Evolution
2.4.0-rc2](https://github.com/EvolutionAPI/evolution-api/releases/tag/2.4.0-rc2) e [código
Baileys no commit 5624bda](https://github.com/evolution-foundation/evolution-api/blob/5624bda/src/api/integrations/channel/whatsapp/whatsapp.baileys.service.ts).

## Incompatibilidade a resolver

Uma PR no repositório de documentação da Evolution descreve headers customizados por instância e
a opção `jwt_key`, com geração de JWT HS256 e claims `iat`, `exp`, `app=evolution` e
`action=webhook`. A PR consultada continua aberta e informa que o branch não foi implantado; ela
não comprova que a versão/imagem usada pelo OctoBOX implemente ou exponha esses campos. Mesmo se
disponível, o JWT descrito autentica a origem, mas não assina os bytes do corpo no formato exigido
pelo receiver HMAC. A URL global por variável de ambiente também não deve ser presumida compatível
com headers customizados. Confirme o contrato na release exata, na API e no `GET
/webhook/find/{instance}` do ambiente de teste antes de configurar qualquer instância. Referência:
[PR de documentação Evolution #22](https://github.com/evolution-foundation/docs-evolution/pull/22).

Os eventos de voto também exigem validação da versão concreta do provedor. Há relatos oficiais de
`MESSAGES_UPDATE` sem resultado legível em Evolution API 2.3.0 e de `pollUpdateMessage` com
`encPayload`/`encIV` cifrados em Evolution Go 0.7.1. Esses relatos não determinam o comportamento da
instalação usada pelo OctoBOX, mas mostram que não se pode presumir que `option_text` esteja no
payload. Consulte [Evolution API issue 1644](https://github.com/evolution-foundation/evolution-api/issues/1644)
e [Evolution Go issue 60](https://github.com/evolution-foundation/evolution-go/issues/60).

## Arquitetura exigida para ativação

Antes de enviar tráfego de produção, implementar e validar uma bridge confiável entre Evolution e
o receiver. A bridge deve:

1. Receber apenas webhooks de instâncias configuradas; exigir HTTPS e autenticar a configuração
   por instância, preferencialmente validando o JWT HS256 da Evolution com um segredo exclusivo.
2. Resolver o ID opaco da instância para Box/schema por configuração server-side. Nunca derivar o
   schema de campos do payload.
3. Correlacionar a criação da enquete por `(instance_id, poll_message_id)` para recuperar o título;
   normalizar o voto apenas quando a versão provada fornecer telefone do votante, opção em texto e
   identificador estável. Rejeitar correlação ausente, opção inválida ou telefone não normalizável.
   Não decifrar `encPayload` com algoritmo presumido nem usar título/horário como identidade.
4. Criar `event_id` determinístico a partir do identificador estável de origem e do contexto da
   instância. Reentregas do mesmo voto precisam gerar o mesmo ID; votos distintos precisam gerar IDs
   distintos.
5. Assinar o corpo normalizado com o protocolo HMAC do receiver e encaminhá-lo. Segredo da Evolution
   e chave HMAC OctoBOX são distintos, ficam no secret store e nunca entram em logs, payloads ou Git.
6. Preservar a semântica de retry: respostas 5xx/503 são repetíveis; resposta de voto já processado
   é sucesso idempotente; evento inválido ou não suportado falha sem gravar presença.

Se a Evolution já disponibilizar todos os campos em claro para a versão adotada, ainda será
necessário provar o shape com fixtures redigidas e integrar a autenticação/normalização. Se não
disponibilizar a opção em texto, a bridge depende de um decoder mantido e validado para essa versão
ou de uma capacidade oficial que exponha o voto resolvido. Até lá, mantenha o receiver fechado e
não marque a integração como concluída.

## Evidência requerida antes de habilitar

Registrar sem credenciais e sem telefone real:

- versão/tag/imagem exata da Evolution e canal WhatsApp usado;
- exemplo redigido de webhook para enquete criada e voto recebido, com indicação dos campos
  sensíveis removidos;
- ciclo de vida da correlação de enquete: persistência mínima, reinício, voto entregue fora de ordem,
  reentrega e expiração;
- confirmação de como extrair telefone normalizado, título, opção clara e ID estável;
- prova de duas instâncias/boxes com segredos distintos, incluindo tentativa de roteamento cruzado;
- prova de assinatura inválida, token vencido, replay, reentrega do mesmo voto, votos distintos,
  box congelado e recuperação após 503;
- configuração retornada por `GET /webhook/find/{instance}` após reinício da Evolution, para
  detectar perda de URL, evento ou header na versão instalada.

Use somente um ambiente descartável com dois Boxes de teste. A configuração por instância deve
habilitar apenas o evento necessário (normalmente `MESSAGES_UPSERT`, sujeito à fixture real),
desabilitar payload de mídia em base64 e apontar para a bridge — nunca diretamente ao receiver
HMAC. O teste físico em WhatsApp/Evolution e a reconciliação da fila legada `WebhookEvent` em
`public` continuam sendo gates separados.

Para preparar a reconciliação sem expor conteúdo, o workspace fornece
`manage.py report_legacy_whatsapp_queue --schema public`. O comando agrega status, provedor
allowlisted, faixas de idade/tentativas, retries e contagem de IDs ausentes numa transação
PostgreSQL read-only; não lê `payload`, mensagens de erro, IDs individuais ou telefones. Foi
validado **4/4** em PostgreSQL descartável com migrations reais; uma linha com telefone marcador,
payload e erro sintéticos permaneceu intacta e nenhum marcador foi emitido. Ainda não foi executado
sobre a fila de nenhum ambiente real.

## Revalidação upstream — Evolution bridge (24/10/2026)

A fonte oficial foi conferida após a auditoria anterior. A mudança de webhook JWT (#1318) foi integrada ao branch `develop` em 10/05/2025; o diff oficial usa `headers.jwt_key`, emite `Authorization: Bearer`, HS256 e claims `iat`, `exp`, `app=evolution`, `action=webhook`, com validade de 600 s. Isso confirma que as primitivas `authenticate_evolution_callback()` implementam o contrato dessa mudança upstream, mas não comprova qual tag/imagem está instalada no ambiente OctoBOX. A documentação correspondente (#22) continua como PR aberta, e `2.4.0-rc2` continua identificada pelo upstream como pré-release, baseada em `develop` e não integrada a `main`. Fontes: [PR API #1318](https://github.com/evolution-foundation/evolution-api/pull/1318), [PR docs #22](https://github.com/evolution-foundation/docs-evolution/pull/22), [release upstream](https://github.com/evolution-foundation/evolution-api/releases).

A conferência não resolve a semântica do evento de enquete na imagem instalada: seguem ausentes tag/imagem real, fixture redigida, voto em texto, telefone/JID estável e correlação/reinício. Portanto não foi criado parser/endpoint nem habilitado tráfego. Como hardening independente do payload, receiver e bridge agora rejeitam JSON com chaves duplicadas em mapa de rotas, claims/headers e DTO assinado, evitando que parsers diferentes escolham Box ou `event_id` divergentes. `python -m unittest tests.test_whatsapp_poll_webhook_auth tests.test_whatsapp_evolution_bridge -v` passou **17/17**, incluindo duplicatas em rotas, JWT e DTO; nenhuma conexão externa ou chave real foi usada. Uma chamada via pytest padrão não alcançou os testes: o autouse fixture conectou ao banco dev driftado (`control_box.write_frozen_at` ausente), por isso a validação pura foi rodada diretamente com unittest.

### Separação de segredos das rotas (24/10/2026)

A configuração por instância também exige material criptográfico exclusivo: nenhuma chave HMAC pode ser reutilizada entre Boxes, entre key IDs de rotação ou como `evolution_jwt_secret`; no modo bridge, nenhum segredo JWT ou HMAC válido pode reaparecer em outra rota. Duplicidade invalida a configuração com HTTP 503 antes de aceitar o callback. `python -m unittest tests.test_whatsapp_poll_webhook_auth tests.test_whatsapp_evolution_bridge -v` passou **19/19**, incluindo chave repetida entre Boxes, entre key IDs e entre instâncias Evolution. Isto valida configuração sintética; não é um censo/rotação das credenciais instaladas, que seguem sem verificação até se obter o secret store da instalação.

### Contrato-fonte da release publicada 2.3.7 (24/10/2026)

A inspeção read-only do commit oficial `cd800f2` confirmou que a release publicada `v2.3.7` já contém suporte a `jwt_key`, assinatura HS256 e conversão para `Authorization: Bearer` com claims de 600 segundos. No handler Baileys dessa mesma revisão, `MESSAGES_UPSERT` resolve `pollUpdateMessage` usando a mensagem de enquete armazenada e produz `selectedOptions` em texto e `pollUpdates` com nomes/JIDs quando consegue descriptografar o voto. `MESSAGES_UPDATE` emite `pollUpdates` agregados com `keyId` da enquete, sem ID individual de voto nesse caminho.

O contrato extraído do source e os casos que ainda exigem fixture estão em [evolution-poll-contract-2.3.7.md](../testing/evolution-poll-contract-2.3.7.md). Isso melhora a referência upstream anterior, mas não prova qual imagem está instalada no OCTOBOX. ID de voto em retry, `@lid`/telefone, store da mensagem original e shape HTTP real continuam pendentes. Até receber essa fixture, não criar parser/endpoint nem habilitar tráfego.

**Censo local da fila antiga (24/10/2026):** `manage.py report_legacy_whatsapp_queue --schema public` foi executado no PostgreSQL local `octobox_control` (`127.0.0.1:5433`). O resultado agregado foi `rows=0`, sem faixas de idade, tentativas ou retries; o comando é transacional `READ ONLY` e não altera registros. Isso descreve somente esta base local, não a fila da instalação alvo nem o tráfego fora do checkout.
