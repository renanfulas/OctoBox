<!--
ARQUIVO: arquitetura oficial da experiencia mobile online-first do OctoBox.

TIPO DE DOCUMENTO:
- direcao arquitetural

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [architecture-growth-plan.md](architecture-growth-plan.md)

QUANDO USAR:
- quando a duvida for como o OctoBox mobile deve autenticar, publicar a grade, escalar leitura e limitar custo operacional

POR QUE ELE EXISTE:
- transforma a visao do app mobile em regras tecnicas claras e executaveis.
- impede que o mobile vire uma copia comprimida do web ou um PWA com custo imprevisivel.

O QUE ESTE ARQUIVO FAZ:
1. define a arquitetura online-first do PWA do OctoBox.
2. define a politica de autenticacao persistente para uso frequente no celular.
3. define a arquitetura da Grade de Aulas mobile baseada em snapshots publicados.
4. define a disciplina de publicacao por ticket, draft e emergency handoff.
5. registra a estrategia de escala para manter leitura com custo baixo em 1k, 10k e 100k usuarios.

PONTOS CRITICOS:
- o mobile nao deve armazenar credencial crua no client side.
- a grade mobile nao deve recalcular estado pesado por refresh individual.
- urgencia operacional nao deve virar automacao ruidosa sem controle humano.
-->

# Arquitetura oficial do OctoBox Mobile

## Tese

O OctoBox Mobile deve ser um PWA online-first, instalavel, com autenticacao quase invisivel e leitura instantanea da Grade de Aulas.

Ele nao deve ser um app offline.

Ele nao deve ser uma SPA gigante.

Ele nao deve ser uma copia encolhida do sistema web.

Ele deve abrir como app, manter a sessao viva de forma segura e entregar a ultima verdade publicada com latencia percebida minima.

## Formula curta

O usuario abre o app, ve a ultima grade publicada em milissegundos e so paga o custo da nova verdade quando o sistema realmente precisa publica-la.

## Objetivos de produto

1. remover a dependencia pratica do computador para operacao rotineira.
2. permitir abertura por icone na tela inicial com sensacao de app nativo.
3. reduzir drasticamente a necessidade de login repetido no celular.
4. fazer a Grade de Aulas parecer instantanea sem transferir carga inutil para o servidor.
5. manter o sistema online-only, sem complexidade de operacao offline.

## O que esta arquitetura aceita

1. PWA instalavel.
2. tudo online.
3. sessao persistente por dispositivo confiavel.
4. login social com Google e Apple.
5. snapshot publicado da grade como leitura principal.
6. draft imediato para quem edita.
7. publicacao consolidada em lote fixo de 5 minutos.
8. urgencia tratada por comunicacao humana via WhatsApp.

## O que esta arquitetura nao aceita

1. salvar email e senha em localStorage ou armazenamento cru no browser.
2. recalcular a grade inteira por refresh individual.
3. usar print da tela como estrategia de estado.
4. publicar microalteracoes da grade em tempo real para todos os usuarios.
5. transformar qualquer mudanca em alerta automatico de WhatsApp.
6. deixar a camada mobile inventar sua propria verdade transacional.

## Camada 1: PWA online-first

### Papel

O PWA existe para reduzir friccao de acesso, nao para dar autonomia offline ao produto.

### Entregas obrigatorias

1. `manifest.webmanifest`
2. icones `192x192`, `512x512` e maskable
3. `theme-color`
4. `apple-touch-icon`
5. modo `standalone`
6. fluxo de instalacao guiado

### Regra

O PWA pode registrar service worker minimo para shell e experiencia de instalacao, mas nao deve assumir responsabilidade por operar dados de negocio offline.

## Camada 2: autenticacao mobile persistente

### Tese

O problema do login repetido no celular nao sera resolvido por cache de credencial no client. Ele sera resolvido por sessao persistente segura.

### Estado atual relevante

Hoje o projeto usa sessao curta e expira ao fechar o navegador:

1. `SESSION_COOKIE_AGE = 1800`
2. `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`
3. `SESSION_ENGINE = django.contrib.sessions.backends.cache`

Essa configuracao e adequada para navegador descartavel, mas nao para PWA mobile de uso recorrente.

### Direcao oficial

1. manter sessao em cache quente.
2. abandonar expiracao ao fechar navegador para dispositivos confiaveis.
3. ampliar a duracao da sessao mobile.
4. usar cookie `Secure`, `HttpOnly` e `SameSite=Lax` ou mais restritivo quando possivel.
5. adicionar login social com Google.
6. adicionar login social com Apple para iPhone.

### Regra de seguranca

O mobile nao armazena senha.

O mobile nao controla sua propria autenticacao fora do Django.

O mobile usa sessao persistente segura e renovacao por atividade.

## Camada 3: Grade de Aulas mobile

### Papel

A Grade de Aulas e a primeira superficie premium do OctoBox Mobile. Ela precisa abrir rapido, ler rapido e escalar barato.

### Regra central

A grade mobile nao e montada do zero para cada refresh do usuario.

Ela consome snapshots publicados.

### Estruturas oficiais

1. `published snapshot`
2. `draft ticket`
3. `draft view`
4. `ghost resume`

## Published Snapshot

### Definicao

O snapshot publicado e a ultima versao oficial da grade pronta para leitura em massa.

### Responsabilidades

1. ser leve.
2. ser compartilhado entre muitos clientes.
3. ter `version`, `generated_at`, `hash` e recorte claro.
4. ser servido rapidamente por cache quente.

### Regra

Refresh manual nunca deve forcar recomputacao pesada por conta propria.

O refresh consulta o snapshot publicado e compara versao.

## Ghost Resume

### Definicao

Ao abrir o app, o client mostra imediatamente o ultimo snapshot conhecido salvo localmente e sinaliza o horario da ultima atualizacao.

### Regra

O Ghost Resume mostra leitura pronta.

Ele nao inventa estado.

Ele nao substitui a verdade do servidor.

Ele reduz a latencia percebida entre abrir o app e voltar a operar.

### Experiencia minima

1. abrir e renderizar ultimo snapshot local.
2. mostrar `Atualizado as HH:mm`.
3. permitir sincronizacao manual.
4. trocar para nova versao quando o servidor publicar.

## Draft Ticket de 5 minutos

### Tese

O custo da grade deve escalar por publicacao consolidada, nao por microedicao.

### Definicao

Toda alteracao de grade abre ou continua um ticket de mudancas com janela fixa de 5 minutos.

Durante essa janela, o editor pode:

1. criar aulas
2. mover horarios
3. trocar coach
4. cancelar
5. excluir
6. corrigir o que acabou de fazer

### Regra oficial

A grade publicada nao muda a cada microalteracao.

Ela publica o estado final consolidado do ticket.

### Motivo

Se cada micromudanca publicar imediatamente, o custo explode e o humano transforma o sistema em alarme continuo.

### Resultado esperado

1. 20 microalteracoes podem virar 1 publicacao.
2. o servidor deixa de escalar por impulsividade de refresh e de edicao.
3. o sistema passa a escalar por numero de versoes publicadas.

## Draft View

### Definicao

Quem esta editando ve as alteracoes imediatamente no proprio editor, antes da publicacao oficial.

### Regra

O editor ve draft.

Os demais usuarios veem somente published.

### Elementos obrigatorios da UX

1. preview imediato da grade em draft.
2. resumo consolidado das mudancas em andamento.
3. indicacao de que a publicacao ocorrera em ate 5 minutos.

### Resumo minimo de mudancas

Exemplos:

1. `Voce criou 7 aulas`
2. `Voce alterou 3 horarios`
3. `Voce cancelou 1 aula`
4. `Voce trocou 2 coaches`

## Publicacao consolidada

### Regra

Ao fim da janela do ticket, o sistema:

1. le o estado final do ticket.
2. calcula o delta material.
3. regenera apenas os recortes afetados.
4. publica nova versao.

### Regenerar apenas o que foi afetado

Exemplos:

1. alteracao em aula de hoje afeta `today`, `week` e talvez `meta`.
2. alteracao em aula da semana seguinte afeta `week` e talvez `month`, mas nao `today`.
3. mudanca de horario de 08:00 para 08:01 afeta somente os blocos que usam esse horario.

### Regra de hash

O sistema deve comparar o estado anterior e o estado final material da mudanca.

Nao importa o numero de passos intermediarios.

Importa apenas o delta final publicado.

## Refresh manual

### Regra

O refresh do usuario nao recompoe a grade.

Ele:

1. consulta o snapshot publicado.
2. compara `version` e `hash`.
3. recebe `sem mudancas` ou o novo snapshot.

### Protecao de custo

O refresh manual deve respeitar cooldown de 10 minutos para evitar avalanche de consultas desnecessarias em massa.

### Regra superior

Evento importante passa por cima do cooldown de leitura.

Cooldown existe para proteger o servidor contra ansiedade de refresh, nao para congelar verdade de negocio.

## Eventos importantes

### Regra

Eventos importantes invalidam snapshots imediatamente e entram na fila de publicacao do recorte afetado.

### Exemplos de eventos importantes

1. aula criada
2. aula cancelada
3. horario alterado
4. coach alterado
5. status da aula alterado
6. mudanca operacional relevante de capacidade ou ocupacao, se o produto definir isso como leitura sensivel

### Regra adicional

Mesmo com invalidacao imediata, a arquitetura deve manter consolidacao curta para evitar tempestade de recomputacao em sequencia.

## Emergencia operacional

### Tese

Urgencia nao deve virar atalho de publicacao automatica.

Urgencia deve sair do pipeline tecnico e ir para a mao humana.

### Regra oficial

Se uma situacao nao pode esperar a publicacao normal da grade, o sistema oferece um atalho humano para comunicacao via WhatsApp.

### Fluxo

1. usuario detecta emergencia.
2. clica em `Comunicar urgencia`.
3. sistema abre a API do WhatsApp.
4. usuario escreve e envia a mensagem manualmente.

### Exemplo

`ATENCAO!! AULA DAS 7 CANCELADA EM CIMA DA HORA.`

### Regra

O sistema nao deve sugerir mensagem automatica para cada ticket comum.

Isso geraria ruido, banalizaria a urgencia e misturaria fluxo normal com excecao.

## Camada de cache e distribuicao

### Regra

Leitura massiva da grade deve viver em cache quente, preferencialmente Redis, e nao depender de recomputacao por cliente.

### Estrategia

1. snapshots publicados por recorte.
2. chaves de cache por box, recorte e versao.
3. invalidacao por evento.
4. leitura compartilhada em massa.

### Forma conceitual das chaves

1. `class-grid:mobile:{box_id}:today`
2. `class-grid:mobile:{box_id}:week`
3. `class-grid:mobile:{box_id}:meta`
4. `class-grid:ticket:{box_id}`

## Politica de aquecimento

### Horarios oficiais

1. 04:30
2. 15:30

### Papel

Esses horarios pre-aquecem snapshots quentes do dia e do segundo pico operacional.

### Regra

O servidor aquece o estado de leitura compartilhado, nao cada dispositivo individualmente.

## Escala e custo

### Tese

O custo precisa permanecer baixo em 1k, 10k e 100k usuarios porque leitura nao deve escalar por recomputacao individual.

### Modelo rejeitado

Cada refresh recalcula grade:

1. custo cresce quase linearmente com usuarios.
2. banco e CPU sofrem.
3. latencia piora em cascata.

### Modelo oficial

1. leitura em massa consome snapshot pronto.
2. edicao vira ticket.
3. publicacao vira lote.
4. urgencia vira comunicacao humana.

### Resultado esperado

1. 1k usuarios: baixo
2. 10k usuarios: baixo
3. 100k usuarios: baixo

### Condicoes para isso continuar verdadeiro

1. payload mobile pequeno.
2. recortes de snapshot bem definidos.
3. invalidacao cirurgica.
4. nenhuma credencial crua no client.
5. nenhuma recomputacao pesada por refresh manual.
6. publicacao consolidada por ticket.

## Metricas de sucesso

### Produto

1. usuario abre por icone e nao sente falta do computador.
2. login vira excecao rara, nao ritual diario.
3. grade abre com leitura util imediata.

### Performance

1. tempo de leitura percebida da grade cai para abertura quase instantanea.
2. refresh manual deixa de provocar recomputacao pesada em massa.
3. snapshots quentes atendem o grosso da leitura mobile.

### Operacao

1. editores entendem claramente o que esta em draft.
2. usuarios comuns veem somente versao oficial.
3. urgencia usa canal humano, nao automacao caotica.

## Ordem de implementacao recomendada

### Fase 1: acesso mobile

1. manifest
2. icones
3. meta tags
4. instalacao do PWA

### Fase 2: autenticacao persistente

1. sessao mobile longa
2. dispositivo confiavel
3. login Google
4. login Apple

### Fase 3: Grade de Aulas published

1. snapshot published
2. ghost resume
3. endpoint de sync por versao/hash

### Fase 4: Grade de Aulas draft

1. ticket de 5 minutos
2. draft view
3. resumo das mudancas
4. publicacao consolidada

### Fase 5: emergency handoff

1. atalho humano para WhatsApp
2. politica de uso de urgencia

## Decisao final

O OctoBox Mobile sera um PWA online-first com autenticacao persistente segura e Grade de Aulas baseada em snapshots publicados.

O editor trabalha em draft.

O publico consome published.

Urgencia nao fura o pipeline tecnico; urgencia vai para a mao humana.

Essa e a arquitetura oficial para manter velocidade percebida alta, custo baixo e disciplina operacional conforme o produto escala.

Para transformar esta arquitetura em ordem de implementacao executavel, use [../plans/octobox-mobile-execution-plan.md](../plans/octobox-mobile-execution-plan.md).
