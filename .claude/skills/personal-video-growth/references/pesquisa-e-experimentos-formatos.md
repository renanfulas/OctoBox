# Pesquisa de referências e experimentos de formatos

Leia esta referência quando o pedido envolver inspiração em vídeos que viralizam, diversas versões ou busca de um formato vencedor. A preferência atual do treinador é testar principalmente a formulação e a quantidade de texto contextual, mantendo o áudio real tratado e as vozes inteligíveis em todas as versões novas. Registre pesquisa e testes em Markdown; não gere combinações sem propósito.

[Exemplos públicos consultados](referencias-publicas-formatos.md) documenta uma rodada de pesquisa, sua data e limites. Consulte quando útil como ponto de partida e atualize fatos temporais pela web antes de apresentar contagens como atuais.

## Pesquisa que possa ser verificada

- Prefira vídeos publicados pelo próprio criador. Registre título, autor, link, data da consulta, duração quando acessível e visualizações/curtidas com a procedência. Diferencie número exibido na página, metadado indexado e relato de terceiro; contagens podem mudar ou estar defasadas.
- Descreva somente a parte inspecionada: título/descrição, abertura, trecho, transcrição automática ou vídeo completo. Não diga que ouviu, assistiu integralmente ou mediu retenção se isso não ocorreu.
- Extraia uma hipótese de apresentação — demonstração cedo, pergunta específica, execução direta, contexto de acompanhamento, reação humana — e adapte ao material do treinador. Não reutilize a mídia, a trilha ou uma fala de outro criador como se fosse própria.
- Não importar alegações técnicas, recomendações clínicas, promessas ou “erros” só porque aparecem em um vídeo popular. A autoridade deve aparecer em algo sustentado pelo arquivo atual ou confirmado pelo treinador.
- Mantenha exemplos menores como referências de formato, sem chamá-los de virais. Sucesso público e fracasso público não isolam o efeito de edição.

## Matriz de variações

Escolha famílias editoriais que o arquivo permita, como orientação com fala, detalhe durante a série, execução curta, reação respeitosa, bastidores, sequência com começo/meio/fim ou duas cenas lado a lado. “Sem contexto” pode significar sem texto, sem explicação verbal ou apenas execução: nomeie a diferença com precisão. Fala original ainda pode oferecer contexto mesmo sem texto sobreposto.

Para testar texto, use o mesmo trecho, duração, montagem e **áudio de contexto tratado** em cada versão:

| Versão | Mudança de texto a avaliar |
|---|---|
| A | Contexto completo e factual para um espectador novo |
| B | O mesmo contexto, escrito de forma mais concisa |
| C | Menos texto ou execução direta, somente se a situação continuar compreensível |

Compare A×B para clareza e concisão; use A×C quando a fala e a imagem já fornecerem contexto suficiente. Não crie versões com trilha sonora ou sem áudio. Mais contexto não deve ocupar pés, joelhos, apoio, rosto ou gesto que demonstra o ponto. Um texto alternativo precisa mudar a compreensão de forma identificável, não apenas trocar sinônimos.

As proporções 9:16, 4:5, 1:1 e 16:9 servem a usos diferentes. Use composição própria, padding ou duas cenas lado a lado quando um recorte destruir o movimento. Informe quando o plano vertical fica menor dentro de outro quadro; um canvas 4K não significa que cada painel mantém a resolução original. Mudar proporção, duração, texto e estrutura ao mesmo tempo é exploração, não um teste isolado da proporção.

## Áudio e contexto

Trate a gravação real para priorizar as vozes: reduza ruído e música ambiente concorrente somente quando a separação for viável sem destruir a fala; equilibre níveis, controle picos e preserve a sincronia e um ambiente natural. Ouça as falas essenciais em celular ou alto-falante pequeno, além de conferir medição de níveis. Se o diálogo continuar ininteligível, escolha outro trecho ou construa uma narrativa visual factual; não o substitua por trilha ou silêncio. Áudio tratado não significa voz perfeitamente isolada, e música residual da academia não é trilha adicionada pela edição.

Não usar uma transcrição automática pouco confiável como legenda literal. Texto editorial deve ser distinguível de fala. Quando houver legenda literal, revisar palavras e sincronização em relação ao áudio. Não simular voz de aluno/treinador nem atribuir falas inexistentes. Em cada cartão contextual, confirmar quem faz o quê, em qual etapa e qual consequência é realmente visível; evitar explicações técnicas, relações de causa e marcadores temporais sem evidência. Se a fala já esclarece a cena, o texto pode situar a etapa ou direcionar o olhar, sem transcrevê-la de novo.

## Galeria e revisão das versões

O treinador aprovou editorialmente uma rodada apresentada em galeria local. Em pedidos semelhantes, organize uma entrada por família com seletor de variação de texto/contexto e proporção, quando existir, comparação de duas versões e links para cópia de publicação e master. Não inclua filtro de trilha ou mudo nas novas rodadas. Preserve o acesso às rodadas anteriores como histórico. Favoritos locais representam escolhas de revisão, não métricas de publicação.

Nomeie diferenças entre as duas versões: somente texto contextual, mesma versão ou comparação exploratória quando duração/gancho/montagem mudarem. Confira no navegador que filtros, seletores e links levam aos arquivos corretos e que os vídeos carregam. O relatório deve apontar o que foi realmente verificado; a interface não substitui a auditoria audiovisual.

## Auditoria dos exports

Inspecione os arquivos finais quanto a duração, resolução, orientação, taxa de quadros, proporção de pixel e sinalização de cor. Composições e redimensionamentos podem herdar SAR diferente de 1 ou perder etiquetas de cor. Para uma entrega SDR BT.709, confira a conversão dos pixels e as etiquetas no arquivo; trocar etiquetas não converte HDR em SDR. Um canvas quadrado ou horizontal não deve deformar o plano vertical.

Confira a presença da faixa de áudio tratada em todos os novos arquivos, a inteligibilidade das vozes, a consistência de volume, a ausência de clipping/artefatos e as posições de texto ao longo da ação. Para lotes de variantes, decodificar integralmente detecta arquivos truncados ou erros de reprodução; isso não certifica o sentido de cada palavra da fala. Registre os limites da inspeção do áudio.

Ao trocar somente texto, mantenha o mesmo trecho e o mesmo áudio tratado; quando reutilizar o fluxo de áudio, confira sua identidade por hash. Se uma correção alterar um arquivo, atualize sua verificação e os hashes dos pares afetados. Uma correção apenas de metadados pode usar cópia do fluxo quando os pixels já estiverem corretos.

## Registro e decisão

No projeto ativo, mantenha Markdown com: referências e limites da pesquisa; inventário de arquivos/trechos/proporções; pares comparáveis; hipótese e métrica primária; resultados ainda vazios quando não publicados; auditoria concreta. Guarde arquivos intermediários em `work/` e entregáveis em `outputs/`.

Escolha a métrica pela finalidade: tempo médio, retenção inicial ou conclusão para consumo; salvamentos por utilidade; compartilhamentos por valor social; comentários pertinentes por conversa. Compare na mesma plataforma e em condições próximas. Registre janela de observação, distribuição e tamanho da exposição. Ausência de dado é “não disponível”, nunca zero.

Para comparar duração, considere também tempo médio dividido pela duração, sem confundir esse valor com conclusão: repetição do vídeo pode elevá-lo acima de 100%. Taxas por mil precisam indicar denominador; não misturar plays, alcance e visualizações engajadas como se fossem equivalentes.

Antes da publicação, pode haver um favorito editorial. Depois, registre candidato vencedor por objetivo/plataforma e confirme se o padrão se repete em outra rodada comparável. Não inventar resultados, limiares universais ou certeza causal a partir de um post. Reaplique somente aprendizados que os dados sustentem na memória editorial.
