# Publicação pelo MCP do Metricool

Leia esta referência quando o treinador pedir envio, agendamento ou publicação em Instagram Reels/TikTok pelo Metricool. Em 12/10/2026, o fluxo recebeu sem redução dois masters 4K verticais 2160 × 3840 HEVC Main 10/BT.2020 HLG, de 155.483.124 e 69.363.407 bytes. As URLs hospedadas responderam 200 com MIME `video/mp4` e os mesmos tamanhos dos arquivos locais; ambos os posts chegaram a `PUBLISHED` e retornaram URLs públicas nas duas redes. Isso valida estes arquivos e este fluxo, sem garantir todos os codecs nem a resolução reproduzida após transcodificação. **Aceite do agendamento ainda não confirma publicação**; acompanhe cada rede até o estado final.

## 1. Preparar e conferir

1. Confirme a autorização do treinador para **este** post, as redes e se deve sair imediatamente ou numa data indicada. Não deduza autorização para postar outros cortes.
2. Confirme o master aprovado em 4K 2160 × 3840, 9:16, áudio inteligível, sequência e duração. A referência técnica do Metricool consultada para Instagram lista até 1920 px de largura e H.264 4:2:0; apesar disso, um MP4 H.264 SDR de 2160 px de largura foi publicado com sucesso no Instagram e no TikTok em 12/10/2026. Isso é evidência para aquele arquivo, não uma mudança no limite documentado nem garantia para 4K HEVC/HDR, que não foi testado. Para TikTok, o Metricool lista MP4/MOV, até 500 MB, 3 s–10 min para autopublicação. Verifique os requisitos atuais e teste o arquivo 4K num rascunho. Se houver incompatibilidade, não reduza a resolução; informe o bloqueio ao treinador.
3. Confirme a capa JPEG aprovada em proporção vertical, com texto legível no recorte do feed. O Metricool recomenda 1080 × 1920 para Instagram, mas aceitou 1440 × 2560 no rascunho testado; isso não comprova suporte a uma capa 4K nem garante a aparência após a publicação. Preserve o master de vídeo em 4K; trate qualquer exigência de capa separadamente e confirme antes de publicar.
4. Use `metricool_getbrandsettings` para obter `blogId`, fuso e redes conectadas. Não fixe um ID ou nome de conta nesta skill. Consulte `metricool_getscheduledposts` no intervalo pertinente para evitar duplicar um post já agendado.

## 2. Enviar a capa como rascunho técnico

O conector aceita **caminho absoluto local** em `mediaFiles` e copia o arquivo para a hospedagem permanente do Metricool. Isso foi confirmado por respostas anteriores do MCP e pelo teste de 12/10/2026; não é preciso anexar o arquivo à conversa nem contratar o Upload-Post para esse envio.

Use `metricool_createscheduledpost` com `blogId`, `date` futura e `info` como JSON serializado contendo `publicationDate` no fuso da marca, `text` identificando o rascunho, `providers:[{network:"instagram"}]`, `instagramData:{type:"POST",autoPublish:false}`, `draft:true` e `autoPublish:false`; passe **somente o caminho da capa** em `mediaFiles`. Confirme na resposta `draft:true` e capture `id`, `uuid` e a URL HTTPS em `media[0]`. Essa URL passa a ser a capa do vídeo. Se o conector não criar rascunho, não crie um post de capa agendado/publicável como substituto.

## 3. Transformar o mesmo rascunho no vídeo

Leia de volta o rascunho com `metricool_getscheduledposts`, recuperando o `id` atual e `uuid`. Use `metricool_updatescheduledpost` com `blogId`, `id`, `uuid`, `mediaFiles:[CAMINHO_ABSOLUTO_DO_MASTER]` e o conteúdo completo relevante de `info`:

```json
{
  "publicationDate": {"dateTime": "AAAA-MM-DDTHH:MM:SS", "timezone": "America/Sao_Paulo"},
  "text": "Legenda factual aprovada para o vídeo",
  "providers": [{"network": "instagram"}, {"network": "tiktok"}],
  "instagramData": {"type": "REEL", "showReelOnFeed": true, "autoPublish": false},
  "tiktokData": {"title": "Título factual", "privacyOption": "PUBLIC_TO_EVERYONE"},
  "videoCoverMilliseconds": 500,
  "videoThumbnailUrl": "URL_HTTPS_DA_CAPA_EM_STATIC_METRICOOL",
  "draft": true,
  "autoPublish": false
}
```

O `date` do `create` é ISO 8601 com offset (ex.: `...-03:00`); `publicationDate.dateTime` dentro de `info` é hora local sem offset e `timezone` traz o fuso. O TikTok exige `tiktokData.title`. `instagramData.type` precisa ser `REEL`. Após um `update`, o **`id` muda** e o `uuid` permanece; use o novo `id` da resposta ou consulte o post outra vez. Não reenvie com o ID antigo.

Se apenas uma rede puder receber o post, ajuste `providers` a essa rede. Não presuma que o mesmo campo de capa será aplicado a todas: segundo o Metricool, imagem personalizada é aceita no Instagram Reel e no TikTok **Business**; no TikTok pessoal, a opção documentada é escolher um quadro do vídeo. Descubra o tipo de conta e confirme a capa por rede antes de agendar/publicar. Se isso não for possível pelo MCP, mantenha o rascunho e informe a limitação; não publique no feed sem a capa combinada.

## 4. Checklist no Metricool antes da autopublicação

Antes de liberar o rascunho, confira no Metricool, item por item:

- master aprovado em 2160 × 3840, 9:16, reproduzível e sem redução;
- consentimento para publicação de participantes identificáveis confirmado; terceiros incidentais identificáveis autorizados ou ocultados;
- legenda, título do TikTok, redes e privacidade corretos;
- `draft:true` e `autoPublish:false` no rascunho de revisão;
- Instagram configurado como `REEL` com `showReelOnFeed:true`;
- `media` com **um MP4** e `videoThumbnailUrl` com a capa JPEG aprovada;
- para TikTok sem capa JPEG personalizada disponível, `videoCoverMilliseconds` no nível superior do post apontando para um quadro intencional. `photoCoverIndex` é para capas de foto/carrossel e não substitui o quadro de vídeo;
- data, hora e fuso conferidos;
- URLs HTTPS de vídeo e capa respondem com MIME e tamanhos esperados, comparados aos arquivos locais.

Se algum item obrigatório falhar, mantenha o post como rascunho e corrija a causa antes de liberar. Não inclua blocos `*Data` de redes que não estejam em `providers`: o MCP rejeita, por exemplo, `twitterData` sem `twitter` na lista. Uma resposta com `PENDING` ou uma URL de planejamento comprova apenas o rascunho/agendamento, não a publicação nem a aparência final da capa.

## 5. Agendar e acompanhar

Depois das verificações e quando o pedido incluir postagem, atualize **o mesmo rascunho** pelo MCP, preservando `media` (URL permanente do MP4), `videoThumbnailUrl`, `videoCoverMilliseconds`, texto e opções de rede; mude a data para um horário futuro solicitado ou próximo quando o treinador pediu publicação imediata, e defina `draft:false` e `autoPublish:true` (inclusive em `instagramData`). Nessa atualização, passe o array `media` no JSON de `info` e omita `mediaFiles`: o conector conservou os arquivos já hospedados sem reupload. Nos cortes 01 e 03 de 12/10/2026, `videoCoverMilliseconds:500` permaneceu no post para selecionar um quadro do TikTok, enquanto `videoThumbnailUrl` preservou a capa JPEG associada ao Reel. A documentação do Metricool permite capa JPEG personalizada no TikTok Business e seleção de quadro de vídeo; use o quadro em milissegundos quando essa for a opção da conta. Confira a resposta e releia o agendamento. Não crie outro post do zero nesta etapa. Se o conector não conservar a configuração da capa, mantenha como rascunho.

No horário, acompanhe o estado de Instagram e TikTok separadamente com `metricool_getscheduledposts` no intervalo da data de publicação. Nos dois posts de 12/10, o Instagram passou por `PUBLISHING` e o TikTok por `AWAITING_CONFIRMATION`; depois ambos chegaram a `PUBLISHED` com `publicUrl`. Registre IDs/URLs públicos apenas quando cada rede confirmar `PUBLISHED`. Se não houver leitura final disponível, descreva o estado como agendado/pendente; não diga “publicado” com base apenas no aceite do agendamento. Evite repetição cega após erro para não duplicar posts.

Depois de definir a autopublicação, crie ou atualize um registro num **calendário independente de verificação**, separado do calendário de conteúdo do Metricool. Esse calendário serve apenas para checar publicação, URLs, capa e, nas janelas da rotina de métricas, resultados por rede; nunca para criar, duplicar ou agendar posts. Registre horário, corte, ID/UUID, redes, link do Planner e checklist. Se não houver calendário de verificação conectado, mantenha `outputs/<projeto>/calendario-verificacao.md`; não use o calendário Família nem o calendário pessoal sem pedido explícito.

## Limites e fontes

- Em 12/10/2026, dois masters 4K HEVC Main 10/BT.2020 HLG de 2160 × 3840 foram enviados sem redução pelo MCP: corte 03 (155.483.124 bytes) e corte 01 (69.363.407 bytes). As URLs hospedadas responderam 200, `video/mp4` e o tamanho local exato; Instagram e TikTok confirmaram ambos como `PUBLISHED`. A capa JPEG foi hospedada e associada no Metricool; a aparência final no perfil não foi verificada visualmente. O teste comprova esses dois uploads 4K HLG HEVC, sem garantir todos os codecs nem que as redes conservem 4K na reprodução.
- A API HTTP direta do Metricool exige plano Advanced/Custom e fica fora do canal MCP escolhido. Links de mídia privados ou temporários podem ser ignorados; não os use para contornar o envio local que já funciona.
- [Requisitos técnicos de mídia do Metricool](https://help.metricool.com/publishing-requirements-for-images-and-videos-from-metricool-vfc8n)
- [Publicação no TikTok](https://help.metricool.com/schedule-and-post-on-tiktok-bkepi)
- [Capas por rede e tipo de conta](https://help.metricool.com/how-to-add-a-cover-thumbnail-to-your-posts-jabtw)
- [Campo `videoThumbnailUrl` no esquema oficial](https://app.metricool.com/api/swagger.json)
- [MCP do Metricool e revisão do post](https://help.metricool.com/schedule-and-edit-posts-through-an-llm-with-metricools-mcp-p8y4b)
