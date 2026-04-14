<!--
ARQUIVO: mapa de padroes recorrentes de erro e correcao no front-end.

POR QUE ELE EXISTE:
- transforma os achados das cirurgias recentes em uma cartilha operacional reutilizavel.
- ajuda a distinguir bug local de problema de ownership, cascata ou contrato visual.
- reduz o custo de reabrir a mesma investigacao toda vez que a UI "fica estranha".

O QUE ESTE ARQUIVO FAZ:
1. lista padroes recorrentes de erro encontrados na base.
2. descreve sinais, causa raiz e correcao segura para cada padrao.
3. registra a heuristica que mais funcionou nas limpezas recentes.

PONTOS CRITICOS:
- este documento nao substitui runtime, leitura de template e smoke visual.
- os exemplos aqui vieram de achados reais na base atual.
- o objetivo nao e aplicar a solucao de forma cega, e sim reconhecer o cheiro do problema mais cedo.
-->

# Mapa de padroes de erro e correcao no front-end

Este documento responde a pergunta:

1. "quando esse tipo de bug aparece, qual costuma ser a causa raiz e qual e o corte mais seguro?"

Em linguagem simples:

1. e como um livro de pistas de detetive
2. quando o mesmo tipo de pegada aparece no chao, a gente ja sabe que tipo de sapato procurar

## Regra de ouro

Antes de perguntar:

1. "qual propriedade eu mudo?"

Pergunte:

1. "quem deveria mandar aqui?"

Quase todos os bugs recorrentes desta trilha nasceram de autoridade visual espalhada, nao de falta de CSS.

## Padrao 1: owner duplicado

Sinais:

1. o mesmo seletor aparece em mais de um arquivo relevante
2. pequenas mudancas mexem em telas diferentes
3. o scanner acusa `duplicate-rule`

Causa raiz provavel:

1. duas camadas diferentes acham que sao donas da mesma peca
2. uma camada canonica define a base e uma camada local repete a mesma responsabilidade

Exemplos reais:

1. `meta-text`
2. `field-label`
3. `operation-card-head`
4. `operation-card-title`
5. `metric-card`

Correcao que mais funcionou:

1. descobrir o dono canonico
2. mover a anatomia para o dono canonico
3. deixar a camada local cuidar apenas do contexto

Analogia:

1. e como descobrir quem e o professor titular da turma
2. monitor pode ajudar, mas nao deve assinar boletim

## Padrao 2: classe semantica virando classe de contexto

Sinais:

1. a mesma classe parece significar "tipo de texto" e "tom visual da tela"
2. a classe aparece em tokens e tambem em shareds locais
3. o componente muda de humor dependendo da sala onde entra

Causa raiz provavel:

1. uma classe global esta sendo usada para tipografia base e tambem para coloracao ou espacamento local

Exemplo real:

1. `meta-text` e `meta-text-sm`

Correcao que mais funcionou:

1. manter anatomia no design system
2. trocar redefinicao direta por seletor contextual
3. estilizar o uso local sem reemitir a identidade da classe

Heuristica:

1. se a classe nomeia o "que e", ela nao deveria nomear tambem "como aquela tela sente"

## Padrao 3: token conhecendo componente

Sinais:

1. arquivo de token menciona nome de componente especifico
2. o scanner acusa duplicacao entre fundacao e modulo de componente
3. fica dificil dizer onde termina tipografia base e onde comeca o componente

Causa raiz provavel:

1. a camada de fundacao desceu demais para dentro da implementacao de um modulo

Exemplo real:

1. `operation-card-title` em `tokens.css`

Correcao que mais funcionou:

1. deixar token cuidar de primitivo
2. deixar componente cuidar do nome do componente
3. mover fonte, escala ou anatomia para o arquivo do proprio modulo quando a identidade ja for do componente

Analogia:

1. e como a prefeitura decidir a cor da porta de um apartamento especifico
2. ela define o codigo da rua, nao a decoracao do quarto

## Padrao 4: responsividade com dois donos

Sinais:

1. o mesmo seletor aparece em dois arquivos de responsividade
2. o comportamento em breakpoint parece funcionar, mas fica fragil
3. um ajuste mobile em uma area pode afetar outra

Causa raiz provavel:

1. contrato responsivo compartilhado e refinamento de area estao segurando o mesmo volante

Exemplo real:

1. `operation-card-head` em `responsiveness.css` e `operations/refinements/responsive.css`

Correcao que mais funcionou:

1. consolidar o comportamento base em um unico contrato responsivo
2. deixar o arquivo local cuidar so do que e especifico da area

Heuristica:

1. breakpoint compartilhado deve morar numa rua so

## Padrao 5: ordem errada de cascata resolvida com grito

Sinais:

1. aparece `!important`
2. a regra parece correta, mas so funciona na marra
3. a camada dark ou de estado vem antes da camada base

Causa raiz provavel:

1. a ordem do arquivo ou da cascata esta invertida
2. o CSS virou briga de volume, nao de hierarquia

Exemplo real:

1. `pills.css`

Correcao que mais funcionou:

1. reposicionar a regra para a cascata certa
2. remover `!important`
3. manter a intencao visual sem usar megafone

Analogia:

1. nao era problema de falar mais alto
2. era problema de deixar a pessoa certa falar por ultimo

## Padrao 6: estrutura de componente repetida fora do design system

Sinais:

1. um shared local redefine estrutura que a classe base ja garante
2. o HTML mostra a combinacao `card + componente`
3. o scanner acusa duplicacao entre design system e shared local

Causa raiz provavel:

1. o arquivo local repetiu estrutura por inercia ou por fase antiga da base

Exemplo real:

1. `metric-card` e `finance-metric-card` com `position: relative` e `overflow: hidden` repetidos em `utilities.css`

Correcao que mais funcionou:

1. confirmar no template se a estrutura base ja vem junto
2. remover o eco estrutural local
3. manter no modulo local apenas tamanho, variacao e assinatura da superficie

## Padrao 7: falso positivo de duplicacao

Sinais:

1. o scanner acusa duplicado, mas olhando de perto um lado e base e o outro e estado ou contexto
2. a classe reaparece dentro de `:is(...)`, dark mode ou container local
3. o seletor parece repetido, mas a intencao nao e a mesma

Causa raiz provavel:

1. o scanner enxerga nome igual, mas o problema real e menor
2. o ruido esta em como o seletor foi escrito

Exemplo real:

1. `field-label` no dark mode do `student_form_stepper.css`

Correcao que mais funcionou:

1. reescrever o seletor contextual
2. reduzir a colisao nominal sem mudar o visual
3. nao confundir ruido de leitura com duplicacao estrutural

## Padrao 15: casca generica do container achatando host especifico

Sinais:

1. o componente parece ter dark mode proprio, mas no contexto embedado ele fica "lavado"
2. existe uma regra generica do wrapper pai aplicando `background` e `border-color` em `> *`
3. a peca melhora fora do drawer, modal ou quick panel, mas piora dentro dele

Causa raiz provavel:

1. o container contextual esta vestindo todos os filhos com a mesma roupa
2. o host especifico perde sua assinatura visual porque o pai passa um verniz por cima

Exemplo real:

1. `student-quick-panel__fragment-slot > *` achatando `student-financial-drawer student-payment-management-card student-page-payments-checkout-card`

Correcao que mais funcionou:

1. manter a regra generica para os filhos comuns
2. criar excecao contextual para o host especializado
3. devolver superficie, borda e sombra ao dono canonico daquele card

Analogia:

1. e como colocar o mesmo uniforme em todas as pessoas da festa
2. a noiva deixa de parecer noiva porque o cerimonial vestiu todo mundo igual

## Padrao 8: legado protegido confundido com lixo

Sinais:

1. o nome parece velho
2. a vontade inicial e apagar
3. os docs ou o runtime ainda mostram uso real

Causa raiz provavel:

1. alias canonizado ou ponte legada ainda viva

Exemplos reais:

1. `note-panel*`
2. `legacy-copy*`

Correcao que mais funcionou:

1. classificar antes de excluir
2. tratar como protegido ate prova em contrario
3. so aposentar com trilha de migracao explicita

## Padrao 9: componente compartilhado com hotspots de especificidade

Sinais:

1. seletor profundo demais
2. cadeia longa de descendentes
3. ajustes locais ficam caros porque a especificidade ja nasce alta

Causa raiz provavel:

1. o componente foi sendo refinado por encaixe em vez de por contrato

Exemplos reais:

1. blocos de `student-financial.css`
2. boards operacionais antes da migracao de `id` para `data-panel`

Correcao que mais funcionou:

1. reduzir autoridade estrutural falsa
2. preferir contrato semantico como `data-panel`
3. manter layout macro separado da identidade local

## Padrao 10: dark mode colocado por cima de host light-first

Sinais:

1. o componente fica aceitavel no light e dependente de varios remendos no dark
2. aparecem muitos blocos `body[data-theme="dark"]` dentro do modulo local
3. surface, border, shadow e copy sao todos reescritos na camada da pagina

Causa raiz provavel:

1. o host compartilhado nao fecha sozinho o contrato dark
2. a tela local vira um pequeno motor de tema para compensar

Exemplos reais:

1. `metric-card` do dashboard entre [../../static/css/design-system/components/cards.css](../../static/css/design-system/components/cards.css) e [../../static/css/design-system/components/dashboard/metrics.css](../../static/css/design-system/components/dashboard/metrics.css)
2. `#dashboard-sessions-board` entre [../../static/css/design-system/components/dashboard/sessions_board.css](../../static/css/design-system/components/dashboard/sessions_board.css) e [../../static/css/design-system/components/dashboard/side.css](../../static/css/design-system/components/dashboard/side.css)
3. topbar antes do ajuste de busca em dark

Correcao que mais funcionou:

1. endurecer primeiro o host compartilhado
2. depois remover o repaint local que sobrou
3. impedir que a tela local continue definindo surface base, copy base e sombra base

Analogia:

1. o casaco local estava tapando o furo do uniforme
2. primeiro costura o uniforme
3. depois decide se o casaco ainda precisa existir

## Padrao 11: familia semantica sem branch dark completo

Sinais:

1. a classe base tem dark mode
2. as subclasses reais de status ou ocupacao ficam com contraste torto
3. o time comeca a corrigir pill por pill em arquivos locais

Causa raiz provavel:

1. o dicionario semantico do shared nao terminou de ensinar o dark mode para todas as familias

Exemplos reais:

1. `class-status-scheduled`
2. `class-occupancy-critical`
3. sinais locais de KPI como `card-signal.is-warning`

## Padrao 12: controle nativo sem contrato dark completo

Sinais:

1. o campo fechado parece correto no dark
2. ao abrir `select`, `date`, autocomplete nativo ou menu do navegador, os itens ficam ilegiveis
3. o CSS local define `color`, mas esquece `background-color` ou `color-scheme`

Causa raiz provavel:

1. o componente estilizou a casca do controle, mas nao ensinou o tema ao popup nativo
2. o navegador ou o sistema operacional escolhe um fundo padrao que entra em choque com a tinta do texto

Exemplos reais:

1. `select` do `student_form_stepper.css` em dark mode

Correcao que mais funcionou:

1. definir `background-color` explicito para `select` e `option` no contexto dark
2. aplicar `color-scheme: dark` quando o controle realmente pertence ao tema escuro da tela
3. tratar isso como contrato do controle, nao como bug do label em volta

Analogia:

1. a vitrine da loja estava escura e bonita
2. mas quando a gaveta abria, por dentro ainda parecia loja de dia

Correcao que mais funcionou:

1. fechar a semantica no host compartilhado
2. deixar o local consumir a familia pronta
3. nao resolver status de dominio dentro do board local

Heuristica:

1. se a tela esta tentando consertar estado semantico no CSS local, quase sempre o shared ficou incompleto

## Padrao 13: assinatura tardia repintando primitivo canonico

Sinais:

1. o componente parece certo no modulo canonico, mas fica estranho no runtime
2. a mudanca feita em `_cards.css` ou `_boards.css` aparentemente nao pega
3. o ultimo arquivo da cascade, como `_signature.css`, ainda reaplica `background`, `border` ou `color` no mesmo primitivo

Causa raiz provavel:

1. a camada de assinatura, que deveria cuidar de atmosfera e casca macro, desceu para dentro do componente compartilhado
2. o primitivo canonico passa a ter dois donos: o modulo do componente e a assinatura final

Exemplos reais:

1. `finance-action-message` no handoff de cobranca
2. `finance-summary-chip` e `finance-alert-stat` no financeiro

Correcao que mais funcionou:

1. devolver o primitivo para o owner canonico, como `_cards.css`
2. remover esse primitivo da `signature` e do `bulk dark`
3. manter a `signature` restrita a shell, host e atmosfera

Analogia:

1. o estilista da vitrine escolhe a iluminacao da loja
2. ele nao deveria costurar a camisa de cada vendedor depois que o uniforme ja foi definido

## Padrao 14: shell duplicado em grid aninhado

Sinais:

1. o dark mode para de "vazar", mas nasce uma moldura feia dentro de outra moldura
2. aparecem dois contornos arredondados no mesmo bloco de KPI ou dashboard
3. o grid fica com cara de caixa dentro de caixa e o vazio entre cards vira protagonista

Causa raiz provavel:

1. container pai e filho estao pintando surface, border e shadow ao mesmo tempo
2. a hierarquia estrutural foi promovida duas vezes para hierarquia visual

Exemplos reais:

1. `dashboard-metrics-cluster` e `dashboard-metrics-lead` no dark mode do dashboard

Correcao que mais funcionou:

1. escolher um unico dono da casca visual
2. deixar o container interno voltar a ser apenas trilho de layout
3. validar por screenshot, porque esse erro parece "contraste" quando na verdade e "moldura duplicada"

Analogia:

1. nao era falta de tinta
2. era quadro com duas molduras brigando pelo olho

## Padrao 13: largura magica cortando trilha de progresso

Sinais:

1. a barra de progresso parece curta demais dentro do card
2. o preenchimento parece certo, mas o trilho inteiro nao acompanha a largura do conteudo
3. o problema melhora no mobile e piora no desktop

Causa raiz provavel:

1. o componente recebeu `width` fixa ou `min()` com teto em pixels herdado de uma fase antiga
2. o card cresceu, mas a barra continuou usando uma regua velha

Exemplos reais:

1. `dashboard-session-progress` com `233px` em `side.css`
2. `#dashboard-sessions-board .dashboard-session-progress` com `214px` em `sessions_board.css`

Correcao que mais funcionou:

1. devolver a largura para `100%`
2. remover `max-width` artificial
3. conferir se a diferenca restante e apenas o padding interno do card

## Padrao 14: baseline historico ainda pintando host canonico

Sinais:

1. o host moderno parece ter owner claro
2. um arquivo legado ou de scaffolding ainda aplica `background`, `surface` ou `shadow` na mesma familia
3. no light isso parece aceitavel, mas no dark a assinatura nova briga com o verniz velho

Causa raiz provavel:

1. a base historica nunca foi totalmente rebaixada depois da chegada da assinatura nova
2. o host canonico passa a ter um dono atual e um ex-dono que ainda mexe na tinta

Exemplos reais:

1. `finance-board-trend` e `finance-board-trend-side` entre [../../static/css/catalog/finance/_shell.css](../../static/css/catalog/finance/_shell.css) e [../../static/css/catalog/finance/_signature.css](../../static/css/catalog/finance/_signature.css)

Correcao que mais funcionou:

1. reduzir o arquivo historico a scaffolding e compatibilidade
2. consolidar casca e personalidade no arquivo de assinatura
3. deixar o dark complementar atuar em contraste e estados, nao na superficie principal

Analogia:

1. e como reformar uma casa bonita, mas esquecer uma camada antiga de verniz por baixo
2. de longe parece tudo novo
3. quando bate a luz certa, o acabamento velho reaparece

## Padrao 15: contraste perceptual ruim com cascata tecnicamente correta

Sinais:

1. a regra local esta entrando no runtime
2. o inspetor mostra `color` aplicada
3. mesmo assim o texto continua parecendo apagado, lavado ou fraco no dark mode

Causa raiz provavel:

1. a tinta escolhida ficou correta em teoria, mas fraca demais para aquela surface, sombra e blur
2. o bug nao e de ownership nem de ordem; e de percepcao visual dentro da atmosfera local

Exemplos reais:

1. `operation-card-title` e `field-label` em `/acessos`
2. `operation-card-copy` e `capability-list` dos cards de papel

Correcao que mais funcionou:

1. trocar `color-mix(...)` timido por tinta mais solida
2. reduzir glow difuso quando ele piora nitidez
3. validar a leitura como humano, nao so como cascata

Analogia:

1. a luz do quarto estava ligada
2. mas a lampada era fraca demais para ler o livro

## Padrao 16: anatomia textual errada disfarcada de bug de dark mode

Sinais:

1. o time fica tentando salvar um bloco com mais contraste
2. o texto continua estranho mesmo quando a tinta melhora
3. titulos longos, resumos e copys parecem estar usando o recipiente errado

Causa raiz provavel:

1. o HTML promoveu texto de resumo para classe de titulo
2. a tela tenta resolver em CSS um erro que nasceu na semantica do template

Exemplos reais:

1. card de papel em `/acessos`, onde `role.summary` estava como `operation-card-title`

Correcao que mais funcionou:

1. devolver nome curto para `operation-card-title`
2. mover resumo para `operation-card-copy`
3. so depois recalibrar contraste no dark

Analogia:

1. e como usar uma placa de porta para escrever um paragrafo inteiro
2. nao adianta trocar a tinta se o quadro continua errado

## Padrao 17: controle nativo no limite do navegador

Sinais:

1. o campo fechado fica correto
2. o popup aberto de `select` ainda fica parcialmente ilegiveis em alguns navegadores
3. pequenas mudancas de CSS melhoram uma parte e pioram outra

Causa raiz provavel:

1. parte do popup pertence ao navegador ou ao sistema operacional, nao ao componente
2. o projeto controla a casca do campo, mas nao 100% da janela aberta

Exemplos reais:

1. `select` de `Papel` em `/acessos`

Correcao que mais funcionou:

1. primeiro levar o nativo ate o maximo seguro com `color`, `background`, `option`, `option:checked`, `option:hover` e `color-scheme`
2. registrar explicitamente quando o limite restante e do navegador
3. so construir `custom select` se houver necessidade real e fit visual comprovado

Analogia:

1. a gaveta da frente da loja e sua
2. o mecanismo la dentro ainda pode ser da fabrica do predio

## Sequencia de correcao que mais funcionou

Quando o bug tem cheiro recorrente, a ordem com menor arrependimento foi:

1. confirmar runtime ativo e descartar arvore espelho
2. localizar owner real
3. diferenciar anatomia, contexto e responsividade
4. remover eco estrutural
5. ajustar ordem de cascata
6. fechar branch dark nas familias semanticas compartilhadas
7. so depois pensar em apagar legado ou mexer em token

## Erro comum de iniciante que gera debito tecnico

O erro mais caro nao foi:

1. "esqueci uma propriedade"

O erro mais caro foi:

1. "corrigi visualmente no lugar errado"

Isso cria debito tecnico porque:

1. a tela parece resolvida hoje
2. mas o ownership continua torto
3. e o proximo ajuste vai custar mais do que o anterior

## Heuristica final

Se um problema parece simples demais para precisar de mapa, vale desconfiar de tres coisas:

1. voce esta mexendo na camada errada
2. a ordem da cascata esta torta
3. ha mais de um dono segurando a mesma peca

Em resumo:

1. bugs recorrentes de UI nesta base costumam ser problemas de autoridade
2. a correcao mais segura quase sempre passa por ownership
3. antes de "mudar CSS", vale descobrir "quem deveria mandar"

## Padrao 18: card de status descrevendo o problema sem traduzir a proxima acao

Sinais:

1. o card parece informativo, mas nao ajuda a decidir
2. aparecem palavras como `monitorar`, `ver`, `acompanhar` ou sequencias como `comece`, `depois`, `feche`
3. o usuario entende o tema do problema, mas nao entende o melhor proximo clique

Causa raiz provavel:

1. o card foi escrito como mini-relatorio de situacao, nao como copiloto operacional
2. o payload descreve dominio e volume, mas nao transforma isso em urgencia, impacto e acao

Exemplos reais:

1. lane do manager em `manager_operational_focus`

Correcao que mais funcionou:

1. estruturar cada card como `sinal -> impacto -> proxima acao`
2. trocar headline de navegacao por headline de decisao
3. usar CTA com verbo imperativo especifico, como `priorizar`, `corrigir` ou `atacar`
4. ordenar os cards por pressao operacional real, nao por ordem fixa de cadastro

Analogia:

1. um relatorio diz "ha transito na estrada"
2. um copiloto diz "pega a proxima saida agora"

## Padrao 19: lane evoluida com board principal ainda preso em header hardcoded

Sinais:

1. a lane parece mais inteligente, mas o usuario olha a pagina e sente que nada mudou
2. o board principal ainda mostra textos genericos como nome de secao
3. lane e board do mesmo dominio contam historias diferentes

Causa raiz provavel:

1. o cerebro semantico foi promovido na lane ou no hero
2. os includes principais continuam com `eyebrow`, `title` e `copy` fixos no template

Exemplos reais:

1. manager, onde a `command lane` evoluiu antes dos boards principais

Correcao que mais funcionou:

1. criar contrato de `board content` no snapshot
2. fazer os boards consumirem esse contrato
3. preservar ids, anchors e estrutura de tabela
4. deixar o template renderizar e o backend decidir a semantica

Analogia:

1. a torre de controle fala um plano novo no radio
2. mas as placas dentro do aeroporto continuam impressas com o mapa antigo

## Padrao 20: dark mode local correto sendo achatado por refinamento global tardio

Sinais:

1. o board tem dark mode proprio no arquivo local
2. mesmo assim o runtime mostra uma versao mais generica, mais lavada ou com sotaque errado
3. o inspetor revela que um refinamento importado mais tarde reaplicou `background`, `border-color` ou `box-shadow`

Causa raiz provavel:

1. a camada global de refinamento esta descendo para dentro de um host que ja tinha owner local legitimo
2. o card passa a ter dois donos no dark mode: o modulo da superficie e o "verniz final" da display wall

Exemplos reais:

1. `reception-priority-card`, `reception-secondary-card` e `reception-support-card` em `/operacao/recepcao/`
2. `display-wall.css` repintando boards que ja tinham contrato local em `reception/scene.css`, `reception/payment.css` e `reception/class-grid.css`

Correcao que mais funcionou:

1. manter o refinamento global como trilho, nao como repintura obrigatoria
2. devolver a autoridade visual ao modulo local por variaveis ou hooks explicitos
3. deixar o global cair para fallback, em vez de vencer no grito sobre o dark mode local

Analogia:

1. o arquiteto da fachada escolhe a iluminacao do predio
2. ele nao deveria entrar depois no quarto e trocar a lampada que ja estava certa

## Padrao 21: superficie operacional usando classe emprestada sem carregar o dono original

Sinais:

1. um card de uma area reaproveita classes de outra, como financeiro dentro da recepcao
2. no HTML parece tudo reaproveitado de forma elegante, mas a pagina nao carrega o CSS dono daquela familia
3. o light ou dark mode fica dependente de heranca casual, coincidencia de nome ou cobertura parcial do design system

Causa raiz provavel:

1. o template reutilizou um host sem trazer junto o contrato visual completo
2. a superficie local ficou apoiada em "roupa emprestada" sem fechar seu proprio sotaque

Exemplos reais:

1. `reception-class-session-card` usando `finance-alert-stat`
2. `reception-payment-card` usando `finance-action-card`, `history-entry` e `payment-primary-summary` enquanto a recepcao carrega apenas `operations.css`

Correcao que mais funcionou:

1. decidir se a familia deve subir para owner compartilhado de verdade
2. se nao subir, fechar explicitamente o contrato local da superficie hospedeira
3. registrar no CSS local como texto, stat, subcard e controle nativo devem se comportar em light e dark

Analogia:

1. pegar emprestado o uniforme do financeiro pode servir para um ensaio
2. para trabalhar de verdade, a recepcao precisa da propria roupa ajustada ao corpo
