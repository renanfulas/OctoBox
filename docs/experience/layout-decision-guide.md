<!--
ARQUIVO: guia permanente para pensar, montar e revisar layouts do Octobox.

TIPO DE DOCUMENTO:
- guia oficial de front-end e UI/UX do produto

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [front-display-wall.md](front-display-wall.md)

QUANDO USAR:
- SEMPRE. este documento e o cabecalho permanente de qualquer decisao de tela, layout, componente ou interacao do Octobox.
- antes de desenhar uma tela nova

## Linguagem e escrita

1. toda interface deve usar ortografia correta em portugues, com acentuacao, concordancia, pontuacao e coerencia de leitura
2. texto de interface nao pode parecer rascunho tecnico; labels, mensagens, placeholders e ajudas precisam soar claros e humanos
3. o mesmo fluxo nao pode alternar tom, tempo verbal ou nome de objeto sem motivo real
4. erro de portugues em interface e defeito de produto, nao detalhe editorial
- antes de reorganizar uma tela existente
- antes de revisar uma entrega de front
- antes de decidir se algo visual faz sentido ou nao
- quando houver duvida sobre como resolver qualquer questao de interface

POR QUE ELE EXISTE:
- transforma intuicao de layout em rotina repetivel.
- evita telas bonitas mas burras, e telas funcionais mas cansativas.
- preserva a identidade do produto como sistema orientado a prioridade, pendencia e proxima acao.
- consolida melhores praticas consagradas de front-end e UI/UX como parte do padrao do projeto.

8. todo input com formato previsivel deve limitar a digitacao ao contrato real do campo; o usuario nao pode conseguir inserir lixo maior do que o formato permite
9. quando a digitacao vier quebrada, o sistema deve corrigir automaticamente para o valor valido mais proximo possivel antes de falhar
10. datas, horas, CPF, telefone, inteiros e valores monetarios devem ter normalizacao ativa durante a digitacao e no blur
11. campos monetarios devem aceitar no maximo quatro digitos inteiros e duas casas decimais, salvo regra explicitamente documentada em contrario
12. mascara visual sem saneamento real nao basta; a borda do sistema precisa receber dado limpo e previsivel
O QUE ESTE ARQUIVO FAZ:
1. define o padrao oficial permanente que toda decisao de tela deve seguir.
2. registra as melhores praticas de front-end que o projeto respeita.
3. registra as melhores praticas de UI/UX que o projeto respeita.
4. estabelece a ordem correta de pensamento antes de desenhar uma tela.
5. oferece um passo a passo para montar paginas coerentes com o Octobox.
17. digitacao fora do formato e corrigida ou limitada antes de virar bug?
6. oferece um checklist final para validar se a tela realmente ficou pronta para uso real.

PONTOS CRITICOS:
18. a pagina e navegavel por teclado?
19. contraste de texto contra fundo atende WCAG AA?
20. elementos interativos tem estado de foco visivel?
21. alvos de toque tem pelo menos 44x44px?
22. cor nao e o unico indicador de estado?

# Guia permanente de decisao de layout

23. o ritmo de espacamento entre blocos segue o padrao da base?
24. hierarquia visual reforça hierarquia logica?
25. a tela parece produto pronto e nao estrutura exposta?
26. existe identidade visual suficiente sem comprometer clareza?
Toda decisao de tela, layout, componente, formulario, estado, navegacao ou interacao deve se guiar por este guia.

Ele nao e sugestao. Ele e padrao.
27. a responsividade preserva legibilidade e prioridade?
28. foi testada em celular, tablet e desktop?
29. grids empilham antes de comprimir?
30. botoes ficam clicaveis e legiveis em largura menor?

Uma tela boa do Octobox nao nasce da pergunta "como deixar bonito?".

31. toda acao do usuario tem feedback visivel?
32. estados vazios orientam proxima acao?
33. loading aparece quando a espera e perceptivel?
34. mensagem de erro explica o que aconteceu e como resolver?
3. qual acao precisa ficar obvia sem esforco
4. como organizar tudo isso de modo limpo, vivo e consistente

Se a tela falha em qualquer uma dessas camadas, ela ainda nao esta pronta.

## Regra mestra do produto

Toda tela deve ajudar a pessoa a resolver o que importa mais rapido do que resolveria em um sistema comum.

Por isso, a regra mestra do Octobox e esta:

1. a tela precisa mostrar prioridade
2. a tela precisa mostrar pendencia
3. a tela precisa mostrar proxima acao

Essa regra nao vale so para o topo com os tres botoes.

Ela vale para a composicao inteira da pagina.

---

# Parte I — Melhores praticas de front-end

Estas sao as regras tecnicas de front-end que o projeto respeita independente da tela.

## HTML semantico e acessivel

1. use tags com significado real: `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<header>`, `<footer>`, `<details>`, `<summary>`
2. cada pagina deve ter exatamente um `<main>` com o conteudo principal
3. titulos devem seguir hierarquia logica: `<h1>` uma vez por pagina, depois `<h2>`, `<h3>` em sequencia, sem pular niveis
4. todo elemento interativo deve ser acessivel por teclado
5. imagens significativas devem ter `alt` descritivo; imagens decorativas devem ter `alt=""`
6. formularios devem usar `<label>` vinculado ao campo por `for` ou envolvendo o input
7. grupos logicos de campos devem usar `<fieldset>` com `<legend>` quando isso ajudar a leitura
8. links devem parecer links e botoes devem parecer botoes; nao troque o papel de um pelo outro
9. `aria-label`, `aria-describedby` e `role` devem ser usados quando o HTML semantico sozinho nao explicar o proposito do elemento

## Acessibilidade como padrao

1. contraste minimo de texto contra fundo deve respeitar WCAG AA: 4.5:1 para texto normal, 3:1 para texto grande
2. elementos interativos devem ter estado de foco visivel e claro, nunca remover `outline` sem substituir por equivalente
3. areas clicaveis devem ter tamanho minimo de toque de 44x44px em qualquer dispositivo
4. a pagina deve funcionar e ser navegavel usando apenas teclado
5. alertas, erros e confirmacoes devem usar `role="alert"` ou `aria-live` quando o conteudo muda sem recarga de pagina
6. cor nunca deve ser o unico indicador de estado; combine cor com icone, texto ou forma

## Performance e carregamento

1. CSS e JS devem ser minimos e necessarios; nao carregar arquivo pesado para usar uma funcao
2. imagens devem estar em formato otimizado e com dimensoes adequadas
3. evitar layout shift: elementos devem ter dimensoes reservadas antes de carregar
4. folhas de estilo criticas devem estar no `<head>`; scripts nao-criticos devem ter `defer`
5. fontes customizadas devem usar `font-display: swap` para evitar texto invisivel
6. evitar CSS que force recalculo de layout em cascata: prefira `transform` e `opacity` para animacao

## CSS disciplinado

1. cada classe importante deve ter contrato explicito no arquivo CSS correto da area
2. nomes de classe descrevem papel e dominio, nao aparencia: `finance-board-rail` em vez de `right-column`
3. `!important` so entra quando nao existe alternativa estrutural; uso frequente indica problema de arquitetura
4. variaveis CSS (`--token`) devem ser usadas para cores, espacamentos e tipografia recorrentes
5. heranca e cascata devem ser usadas com intencao, nunca por acidente
6. seletores especificos demais (tres ou mais niveis de aninhamento) devem ser simplificados
7. CSS morto deve ser removido; classe no template sem seletor correspondente e defeito
8. media queries devem ser mobile-first quando possivel: defina o base e adicione complexidade conforme a tela cresce

Para regras detalhadas de CSS, nomenclatura, localizacao e debug, use [css-guide.md](css-guide.md).

## Formularios tecnicamente corretos

1. campos devem ter `type` correto: `email`, `tel`, `number`, `date`, `url`, `search` conforme o dado esperado
2. `inputmode` deve ser usado para controlar o teclado exibido em mobile: `numeric`, `decimal`, `tel`, `email`
3. `autocomplete` deve estar presente em campos de nome, email, telefone, endereco e pagamento
4. validacao HTML nativa (`required`, `min`, `max`, `minlength`, `maxlength`, `pattern`) deve existir como primeira camada
5. feedback de erro deve aparecer proximo do campo, nao apenas no topo do formulario
6. placeholder nunca substitui label; ele apenas sugere formato
7. desabilitar botao de submit enquanto o formulario estiver invalido so quando o feedback for claro o suficiente para a pessoa entender o que corrigir

## Exibicao de valores monetarios

1. todo valor monetario exibido na interface deve ter exatamente duas casas decimais; nunca mostrar float cru sem formatacao
2. em templates Django, usar `{{ valor|floatformat:2 }}` ao lado do prefixo `R$`
3. em Python, usar `f'R$ {valor:.2f}'` ou `'R$ %.2f' % valor` ao formatar strings de exibicao
4. valores vindos de `Sum()` ou `aggregate()` podem ser `None` ou `Decimal` com muitas casas; a formatacao deve ser aplicada antes de chegar ao template ou dentro do proprio template
5. a funcao `_format_currency_br` em `catalog/finance_snapshot/metrics.py` e o padrao canonico para formatacao server-side com virgula brasileira
6. nunca confiar que o banco devolve duas casas; sempre aplicar formatacao explicita no ponto de renderizacao

## Navegacao e estado de URL

1. toda pagina importante deve ter URL propria e legivel
2. acoes que mudam contexto devem refletir na URL quando fizer sentido
3. anchors devem ser usados para navegar a secoes internas da pagina
4. `scroll-margin-top` deve existir em alvos de ancora quando o topo tiver sticky header
5. apos acao (salvar, confirmar, editar), o redirect deve devolver a pessoa para a secao correta, nao para o topo morto
6. breadcrumbs devem existir quando o usuario pode estar a mais de dois niveis de profundidade

## Responsividade real

1. breakpoints devem acompanhar conteudo, nao dispositivos especificos
2. mobile-first: a estrutura base funciona em tela pequena; complexidade visual e adicionada para telas maiores
3. imagens e midias devem ser fluidas: `max-width: 100%` e `height: auto`
4. texto nunca deve precisar de scroll horizontal
5. grids complexos devem empilhar antes de comprimir e esmagar conteudo
6. botoes e alvos tocaveis devem ser maiores e mais espaçados em tela pequena
7. testar em pelo menos tres larguras reais: celular (~375px), tablet (~768px), desktop (~1280px)

---

# Parte II — Melhores praticas de UI/UX

Estas sao as regras de experiencia e design que o projeto respeita independente da tela.

## Principios fundamentais de UX

## Contrato enxuto entre backend e frontend

1. a tela deve receber do backend o dado semantico uma vez e replicar no frontend o que for apenas apresentacao
2. backend deve priorizar acesso, permissao, navegacao, estado real, acao possivel e leitura operacional
3. frontend deve assumir repeticao visual, espelhamento de numero, badge auxiliar e composicao de apoio quando isso nao altera regra do sistema
4. duplicacao de payload para sustentar o mesmo valor em dois pontos da interface e anti-padrao, salvo quando houver motivo tecnico real e documentado

Exemplo correto:

1. backend entrega um `count`
2. frontend usa esse `count` no bloco principal e em um apoio visual secundario

Exemplo errado:

1. backend entrega `count`, `short_count_label`, `hint_count_copy` e outra variacao equivalente sem diferenca funcional

### Lei de Jakob

Usuarios preferem interfaces que funcionam como as que ja conhecem.

Regra pratica:

1. siga convencoes consagradas de web sempre que possivel
2. nao invente interacao nova quando o padrao comum funciona bem
3. menu no lugar esperado, botao onde o olho procura, confirmacao onde a mao ja esta

### Lei de Hick

Quanto mais opcoes, mais tempo para decidir.

Regra pratica:

1. reduza choices visiveis por tela ao minimo necessario
2. use progressive disclosure: mostre o essencial primeiro, revele complexidade sob demanda
3. agrupe opcoes relacionadas em vez de listar tudo no mesmo nivel

### Lei de Fitts

Alvos grandes e proximos sao mais faceis de acertar.

Regra pratica:

1. CTA principal deve ser grande, visivel e posicionado onde o olho e o cursor ja estao
2. acoes destrutivas devem ser menores e mais distantes das acoes primarias
3. em mobile, botoes devem ter area de toque generosa

### Principios de Gestalt

O olho humano agrupa elementos automaticamente por proximidade, similaridade, continuidade e regiao comum.

Regra pratica:

1. itens relacionados devem ficar proximos; itens nao-relacionados devem ter espaco claro entre eles
2. elementos com a mesma funcao devem ter a mesma aparencia
3. blocos devem ter borda, fundo ou espacamento que defina regiao visual clara
4. alinhamento consistente transmite ordem e profissionalismo

### Carga cognitiva

Toda tela impoe esforco mental. O objetivo e reduzir esse esforco ao minimo.

Regra pratica:

1. mostre apenas o que a pessoa precisa para a tarefa atual
2. esconda complexidade extra atras de disclosure, tabs ou passos
3. use reconhecimento em vez de memorizacao: mostre opcoes em vez de exigir que a pessoa lembre
4. labels, titulos e copys devem ser curtos, diretos e sem ambiguidade

## Hierarquia visual

1. tamanho, peso, cor e posicao definem importancia; o olho le do maior para o menor, do mais contrastante para o mais neutro
2. cada tela deve ter exatamente uma area de destaque principal; se tudo grita, nada se destaca
3. informacao secundaria deve ter peso visual menor que a primaria
4. whitespace nao e espaco perdido; e ferramenta de hierarquia, respiro e foco
5. agrupamento visual deve refletir agrupamento logico do conteudo

## Tipografia legivel

1. corpo de texto deve ter tamanho minimo de 16px em telas normais
2. altura de linha deve ser entre 1.4 e 1.6 para textos de leitura
3. comprimento maximo de linha de corpo deve ficar entre 45 e 75 caracteres para leitura confortavel
4. nao use mais do que duas familias tipograficas no mesmo produto
5. hierarquia tipografica deve ser clara: titulo, subtitulo, corpo, apoio, cada um com tamanho e peso distintos
6. nunca use texto todo maiusculo em blocos longos; reserve maiusculas para rotulos curtos e botoes

## Cor com intencao

1. cor comunica significado: verde para sucesso, vermelho para risco ou urgencia, amarelo para atencao, azul para informacao ou acao neutra
2. nao use mais cores do que o necessario; paleta restrita transmite maturidade
3. cor nunca deve ser o unico canal de informacao; combine com icone, texto ou forma
4. fundos e textos devem manter contraste suficiente em qualquer estado (normal, hover, focus, disabled)
5. cor de destaque deve ser usada com parcimonia; se tudo for colorido, nada se destaca

## Feedback e visibilidade de estado

1. toda acao do usuario deve ter feedback visivel: clicou, processando, concluiu, falhou
2. o sistema deve mostrar seu estado atual de forma clara: carregando, vazio, erro, sucesso, parcial
3. estados vazios devem orientar a proxima acao em vez de mostrar tela em branco
4. mensagens de erro devem dizer o que aconteceu e como resolver, nao apenas "erro"
5. confirmacoes devem aparecer proximo de onde a acao foi disparada
6. loading indicators devem existir quando a espera for perceptivel (acima de 300ms)

## Prevencao de erro sobre correcao de erro

1. e melhor impedir o erro do que avisar depois
2. desabilite opcoes que nao fazem sentido no estado atual em vez de permitir e depois reclamar
3. acoes irreversiveis devem pedir confirmacao explicita com contexto claro
4. inputs devem guiar o formato correto com mascara, placeholder util e tipo de campo adequado
5. quando a intencao do usuario for obvia e segura, o sistema deve corrigir automaticamente
6. undo deve ser possivel quando razoavel; toda acao destrutiva deve ter escape

## Consistencia como regra inegociavel

1. o mesmo tipo de elemento deve ter a mesma aparencia e comportamento em todas as telas
2. botoes primarios devem ser sempre da mesma cor, tamanho e posicao relativa
3. padroes de card, lista, formulario e alerta devem ser reutilizados, nao reinventados
4. vocabulario de interface deve ser uniforme: se e "aluno" em uma tela, nao pode virar "cliente" em outra sem motivo
5. espacamento, borda-raio, sombra e tom de fundo devem seguir tokens definidos no design system
6. se uma interacao funciona de um jeito em um lugar, deve funcionar igual em qualquer outro

## Navegacao clara e previsivel

1. a pessoa deve saber onde esta, de onde veio e para onde pode ir, em qualquer momento
2. sidebar e topbar devem indicar a pagina ativa de forma inequivoca
3. voltar deve voltar; nao redirecionar para lugar inesperado
4. links devem descrever destino, nao apenas "clique aqui"
5. fluxos com multiplos passos devem mostrar progresso e permitir voltar
6. atalhos devem existir para fluxos frequentes sem quebrar a estrutura geral

## Microinteracoes que ajudam

1. hover deve sinalizar que o elemento e interativo antes do clique
2. focus deve ser visivel e claro para orientar navegacao por teclado
3. transicoes suaves entre estados transmitem qualidade e previsibilidade
4. animacao so deve existir quando melhora leitura, orientacao ou confianca; nunca por enfeite
5. feedback tactil e visual ao clicar (pressed state) confirma que a acao foi recebida

---

# Parte III — Ordem de pensamento e passo a passo

## Ordem correta de pensamento

Antes de abrir o template, o CSS ou o componente, responda em texto curto:

1. qual promessa esta pagina faz para o usuario
2. o que precisa saltar ao olho em ate tres segundos
3. qual decisao a pessoa mais precisa tomar aqui
4. qual erro humano mais provavel precisa ser evitado
5. para onde a tela deve levar a pessoa logo depois da acao principal

Se isso nao estiver claro, ainda e cedo para desenhar layout.

## Passo a passo para montar uma tela

## 1. Defina a promessa da pagina

Toda tela precisa ter uma funcao central clara.

Exemplos de promessa:

1. mostrar quem precisa de atencao financeira hoje
2. permitir cadastrar aluno sem perder contexto operacional
3. orientar a recepcao para a proxima acao mais quente

Regra:

1. se uma pagina tenta cumprir promessas demais ao mesmo tempo, ela vai parecer inchada e insegura

## 2. Defina a leitura operacional antes do layout

Antes de pensar em grid, defina tres alvos:

1. prioridade: o que mais exige acao imediata
2. pendente: o que esta acumulado ou aguardando resolucao
3. proxima acao: qual movimento objetivo destrava o fluxo

Esses tres alvos devem existir mesmo quando nao virarem botoes no topo.

Pergunta obrigatoria:

1. se eu escondesse todo o resto, esta pagina ainda deixaria claro qual e o foco operacional?

## 3. Monte a hierarquia da primeira leitura

A pessoa precisa bater o olho e entender a cena.

A hierarquia inicial deve responder, nessa ordem:

1. onde estou
2. o que esta bem ou sob controle
3. o que esta pressionado
4. o que faco agora

Regra:

1. contexto vem antes de detalhe
2. pressao vem antes de inventario completo
3. acao vem antes de ornamento

## 4. Separe blocos por papel real, nao por capricho visual

Cada bloco da tela precisa existir porque ajuda uma decisao.

Blocos comuns da base:

1. contexto da pagina
2. quadro de prioridade ou pressao
3. fila pendente
4. area de execucao direta
5. historico ou detalhes secundarios

Regra:

1. se dois cards dizem a mesma coisa com nomes diferentes, existe redundancia
2. se um bloco so existe para preencher espaco, ele deve sair

## 5. Decida o pouso e o retorno da navegacao

Uma tela boa nao termina no clique.

Ela precisa saber:

1. onde o usuario pousa ao entrar por link direto
2. onde ele retorna depois de salvar, confirmar ou editar
3. qual ancora ou secao deve receber foco apos a acao

No Octobox, isso e especialmente importante em:

1. cadastro de aluno
2. matricula
3. cobranca
4. recepcao
5. financeiro

Regra:

1. depois de uma acao, a pessoa deve cair no trecho certo da pagina, nao no topo generico sem contexto

## 6. Garanta consistencia de estado entre telas

Nenhuma tela pode contar uma historia diferente da outra sobre o mesmo objeto.

Checklist mental obrigatorio:

1. se um pagamento ficou vencido aqui, ele parece vencido nas outras leituras relevantes?
2. se uma confirmacao mudou o estado, os quadros dependentes tambem refletem isso?
3. existe alguma query simplificada demais que mascara a verdade operacional?

Regra:

1. primeiro alinhe a regra de negocio exibida, depois refine o visual

## 7. Desenhe formularios para impedir erro, nao apenas receber dados

Formulario bom nao e o que aceita qualquer entrada.

Formulario bom e o que protege o usuario de digitar errado, salva no formato certo e reduz retrabalho.

Toda tela com formulario precisa responder:

1. este campo deixa claro o que aceita?
2. existe mascara, limite ou formatacao quando fizer sentido?
3. o usuario consegue concluir sem ficar traduzindo formato manualmente?
4. o erro aparece cedo, claro e no lugar certo?

Regra:

1. entrada guiada faz parte da experiencia de produto, nao e detalhe tecnico

## 8. Aplique ritmo visual e respiro consistente

Depois que a estrutura estiver certa, refine a fachada.

O objetivo nao e deixar a tela neutra.

## 9. Busca global com autocomplete

A busca global no topbar deve funcionar como autocomplete em tempo real.

Regra:

1. ao digitar no campo de busca global, uma requisicao e disparada ao endpoint `/api/v1/students/autocomplete/?q=` com debounce de 200ms
2. resultados aparecem em dropdown absoluto abaixo do campo, com nome, telefone e status de cada aluno
3. minimo de 1 caractere para disparar a busca
4. maximo de 10 resultados por consulta
5. clicar em um resultado leva diretamente para a pagina do aluno (`/alunos/{id}/editar/`)
6. navegacao por teclado: seta cima/baixo seleciona, Enter navega, Escape fecha
7. ao perder foco, o dropdown fecha
8. a busca filtra por `full_name`, `phone` e `cpf`
9. o endpoint exige autenticacao (LoginRequiredMixin)

## 10. Clique em card navega ao topo da pagina

Cards (`.card`, `.table-card`) funcionam como blocos clicaveis que levam ao topo da pagina para facilitar a navegacao.

Regra:

1. clicar em qualquer area de um card (exceto botoes, links, inputs, selects, textareas e elements com `role="button"`) executa `scrollTo({ top: 0, behavior: 'smooth' })`
2. isso permite ao usuario ler um card e subir rapidamente sem precisar rolar manualmente
3. botoes e links internos ao card continuam funcionando normalmente sem interferencia
4. o listener e delegado no `document` para funcionar com cards inseridos dinamicamente

O objetivo e deixar a tela clara, viva e reconhecivel como Octobox.

Verifique:

1. espacos entre cards e blocos seguem o mesmo ritmo da base
2. destaque visual aparece nos lugares de maior importancia, nao em todo lugar
3. a pagina parece parte do mesmo predio visual das outras telas
4. ha energia visual suficiente para evitar cara de sistema burocratico

Regra:

1. beleza entra para reforcar clareza, valor percebido e identidade

## 9. Feche com responsividade de leitura, nao so de quebra de grid

Responsividade nao e apenas caber na largura menor.

Pergunte:

1. o foco operacional continua obvio em mobile e tablet?
2. os blocos mais quentes continuam aparecendo cedo?
3. os botoes seguem clicaveis e legiveis?
4. o topo ancora bem quando a tela usa sticky header ou hash?

## 10. Valide a pagina pelo teste dos tres segundos

Abra a tela e se force a responder em ate tres segundos:

1. o que esta acontecendo aqui?
2. o que esta mais importante agora?
3. qual e a proxima acao?

Se qualquer resposta depender de leitura lenta demais, a tela ainda precisa de trabalho.

## Regra oficial dos tres botoes do shell

Quando a pagina usar o padrao global de topo do Octobox, os botoes devem obedecer a esta semantica:

1. Prioridade: leva para o ponto de maior urgencia operacional da pagina
2. Pendente: leva para a fila ou acumulado que pede acompanhamento
3. Proxima acao: leva para o bloco mais acionavel para destravar o fluxo

Esses destinos nao devem ser arbitrarios.

Eles precisam refletir a realidade da pagina naquele contexto.

Se a pagina nao consegue definir esses tres alvos com conviccao, a propria pagina ainda esta mal resolvida.

---

# Parte IV — Anti-padroes

## Anti-padroes que este guia proibe

### Anti-padroes de layout e hierarquia

1. topo bonito que nao ajuda a decidir nada
2. bloco chamativo ocupando espaco de algo mais urgente
3. acao principal escondida abaixo de informacao secundaria
4. cards apertados, sem respiro ou com alturas desconexas sem motivo
5. excesso de elementos com o mesmo peso visual; se tudo grita, nada se destaca
6. pagina que parece ferramenta interna improvisada em vez de produto
7. whitespace tratado como desperdicio em vez de ferramenta de foco

### Anti-padroes de navegacao e estado

1. redirect que devolve a pessoa para um ponto morto da tela
2. tela A dizendo pago enquanto tela B insinua vencido
3. link que diz "clique aqui" em vez de descrever o destino
4. voltar que nao volta; redireciona para lugar inesperado
5. pagina sem indicacao clara da localizacao atual na navegacao

### Anti-padroes de formulario e entrada

1. formulario que joga todo o peso de formatacao no usuario
2. campo sem type correto: input generico onde deveria ter number, email, tel ou date
3. placeholder usado como substituto de label
4. erro generico no topo do formulario sem apontar qual campo tem problema
5. submit habilitado com dados invalidos sem feedback claro sobre o que corrigir
6. acao irreversivel sem confirmacao explicita com contexto

### Anti-padroes de front-end tecnico

1. classe no template sem seletor correspondente no CSS
2. `!important` como solucao rapida em vez de correcao estrutural
3. seletor com tres ou mais niveis de aninhamento sem necessidade
4. CSS morto acumulado sem uso
5. imagem sem dimensoes definidas causando layout shift
6. outline de foco removido sem alternativa visual
7. cor como unico indicador de estado, sem icone, texto ou forma complementar

### Anti-padroes de responsividade

1. responsividade que so encolhe, mas nao reorganiza leitura
2. botoes esmigalhados em tela pequena sem area de toque adequada
3. texto com scroll horizontal em mobile
4. breakpoints baseados em dispositivos especificos em vez de conteudo

### Anti-padroes de UX

1. tela cheia de opcoes sem agrupamento ou progressive disclosure
2. estado vazio que nao orienta proxima acao
3. mensagem de erro que diz "erro" sem explicar o que aconteceu e como resolver
4. inconsistencia de vocabulario: aluno em uma tela, cliente em outra
5. interacao inventada quando a convencao comum funciona perfeitamente
6. animacao decorativa que atrasa a tarefa em vez de ajudar
7. informacao irrelevante competindo com o que a pessoa precisa agora

---

# Parte V — Checklist final

## Checklist completo antes de considerar a tela pronta

Use esta lista sempre antes de fechar uma implementacao relevante de front:

### Promessa e foco

1. a promessa da pagina esta clara em uma frase curta?
2. prioridade, pendencia e proxima acao estao objetivamente identificadas?
3. a leitura dos tres primeiros segundos funciona?
4. o bloco principal da tela esta realmente acima dos secundarios?
5. a acao principal esta visivel cedo e em lugar mental previsivel?

### Navegacao e retorno

6. anchors, redirects e foco levam a pessoa para a secao certa depois das acoes?
7. a pessoa sabe onde esta, de onde veio e para onde pode ir?
8. voltar funciona como esperado?
9. breadcrumbs existem quando a profundidade exige?

### Consistencia

10. a historia exibida pela pagina bate com o resto do sistema?
11. vocabulario, cores, botoes e cards seguem o padrao das outras telas?
12. tokens do design system estao sendo respeitados?

### Formulario e entrada

13. os formularios previnem erro de entrada em vez de so reclamar depois?
14. campos tem type, inputmode e autocomplete corretos?
15. label esta visivel e vinculado ao campo?
16. feedback de erro aparece perto do campo e diz como corrigir?

### Acessibilidade

17. a pagina e navegavel por teclado?
18. contraste de texto contra fundo atende WCAG AA?
19. elementos interativos tem estado de foco visivel?
20. alvos de toque tem pelo menos 44x44px?
21. cor nao e o unico indicador de estado?

### Ritmo visual e identidade

22. o ritmo de espacamento entre blocos segue o padrao da base?
23. hierarquia visual reforça hierarquia logica?
24. a tela parece produto pronto e nao estrutura exposta?
25. existe identidade visual suficiente sem comprometer clareza?

### Responsividade

26. a responsividade preserva legibilidade e prioridade?
27. foi testada em celular, tablet e desktop?
28. grids empilham antes de comprimir?
29. botoes ficam clicaveis e legiveis em largura menor?

### Feedback e estado

30. toda acao do usuario tem feedback visivel?
31. estados vazios orientam proxima acao?
32. loading aparece quando a espera e perceptivel?
33. mensagem de erro explica o que aconteceu e como resolver?

## Formula curta para uso recorrente

Sempre que for montar uma tela no Octobox, siga esta ordem:

1. promessa
2. prioridade
3. pendencia
4. proxima acao
5. hierarquia
6. pouso e retorno
7. consistencia de estado
8. prevencao de erro
9. acessibilidade
10. ritmo visual
11. responsividade
12. feedback e estados
13. teste dos tres segundos

Se essa sequencia for respeitada, a chance de a tela nascer limpa, util e coerente sobe muito.

Para revisar a entrega de forma curta antes de subir uma alteracao, use [front-pr-checklist.md](front-pr-checklist.md).

Para regras detalhadas de CSS, nomenclatura e debug, use [css-guide.md](css-guide.md).