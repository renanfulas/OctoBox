<!--
ARQUIVO: plano de UI/UX da primeira etapa do produto.

POR QUE ELE EXISTE:
- Organiza a finalizacao da primeira fase visual do sistema antes de novas automacoes.

O QUE ESTE ARQUIVO FAZ:
1. Define principios de interface para o produto.
2. Prioriza as telas de maior impacto operacional.
3. Registra um passo a passo de execucao focado em clareza, fluidez e preparacao para automacao futura.

PONTOS CRITICOS:
- Este plano precisa acompanhar a realidade do front-end e nao virar wish list solta.
- Qualquer melhoria visual aqui deve respeitar a estrutura real de permissoes por papel e os fluxos do negocio.
-->

# Plano UI/UX Fase 1

## Objetivo da fase

Deixar o produto visualmente maduro para uso real no dia a dia, com navegacao clara, leitura rapida, acoes obvias, formularios menos cansativos e base pronta para automacoes futuras sem inflar a interface com firula.

## Fontes obrigatorias desta estrategia

Esta fase deve ser conduzida sobre tres bases complementares:

1. [front-display-wall.md](front-display-wall.md) como criterio de linguagem visual e de fachada do produto
2. [ui-ux-phase1-plan.md](ui-ux-phase1-plan.md) como ordem de ataque e checklist de execucao
3. [v1-retrospective.md](v1-retrospective.md) como relatorio de risco para nao repetir erro de priorizacao

Traducao pratica:

1. o Front Display Wall impede que o front pareca canteiro de obra
2. este plano define a ordem disciplinada de lapidacao
3. a retrospectiva lembra que a interface precisa mostrar proxima acao, e nao apenas estado

## Regra inegociavel da fase

Nunca vamos aceitar que um usuario fique confuso ao ler uma tela.

Se a pessoa precisa parar para interpretar demais:

1. a hierarquia falhou
2. a copy falhou
3. a organizacao da tela falhou

Regra central:

1. tudo deve ser intuitivo, facil e simples
2. a genialidade desta fase esta na simplicidade
3. clareza vence volume de informacao
4. orientacao vence decoracao
5. proxima acao vence exibicao passiva de estado

## Principios que vao guiar as mudancas

1. uma tela deve responder rapido ao olho antes de responder ao clique
2. a interface deve expor prioridade, nao apenas quantidade de informacao
3. acoes principais precisam aparecer cedo e sempre no mesmo lugar mental
4. formularios devem revelar complexidade aos poucos
5. todo estado vazio, alerta ou erro precisa orientar a proxima acao
6. interatividade so entra quando melhora decisao, velocidade ou confianca
7. tudo que for desenhado agora deve deixar espaco para automacoes futuras
8. se um elemento confunde mais do que ajuda, ele deve sair
9. se a mesma tela parece exigir treinamento para ser lida, ela ainda nao esta pronta

## Filtro de decisao visual

Toda decisao de interface nesta fase precisa passar por estas perguntas:

1. em ate tres segundos, o usuario entende o que esta vendo?
2. em ate tres segundos, o usuario entende o que esta mais importante agora?
3. em ate tres segundos, o usuario encontra a acao principal?
4. a tela parece produto pronto ou mecanismo interno exposto?
5. existe algum bloco ali porque o sistema quis mostrar estrutura, e nao porque o usuario precisava entender algo?

Se a resposta ruim aparecer em qualquer uma dessas perguntas, a tela ainda nao esta boa o suficiente.

## O que nao entra nesta fase

1. animacao decorativa sem ganho de leitura
2. dashboards cheios de graficos por vaidade
3. filtros excessivos que compliquem atendimento rapido
4. modos paralelos de uso que dupliquem fluxo
5. automacao fake sem regra de negocio por tras
6. jargao visual ou tecnico que obrigue o usuario a interpretar demais
7. blocos bonitos que nao ajudem decisao, leitura ou acao

## Leitura atual do front-end

O produto ja tem uma base visual coerente em layout global, dashboard, alunos, financeiro e operacao. O problema hoje nao e ausencia de estrutura. O problema e hierarquia de uso.

Os principais pontos percebidos na base atual sao:

1. o layout global ja sustenta bem sidebar, topbar e cards, mas ainda pode ganhar navegacao mais inteligente e mais contexto de pagina
2. dashboard mostra bastante coisa, mas ainda mistura leitura estrategica com atalhos administrativos e perde foco operacional
3. alunos esta forte em conteudo, porem ainda pode ficar mais escaneavel para atendimento rapido
4. formulario de aluno esta bem montado, mas ainda exige leitura longa e pode ficar mais progressivo e confiante
5. a linguagem visual esta boa, so que ainda falta consistencia de prioridades, estados e feedback entre telas

## Leitura estrategica consolidada

O ataque do front nesta fase deve seguir esta leitura:

1. o produto ja tem estrutura suficiente para parecer maduro
2. o problema principal agora nao e falta de tela, e excesso de ambiguidade na leitura
3. a prioridade nao e deixar o sistema mais bonito antes de deixa-lo mais claro
4. a frente do produto precisa parecer limpa, simples e utilizavel
5. a interface deve reduzir esforco cognitivo, nao redistribui-lo

Resumo operacional:

1. menos ruido
2. mais hierarquia
3. menos texto que explica demais
4. mais sinais que orientam o que fazer
5. menos interface que parece sistema
6. mais interface que parece ferramenta de uso real

## Ordem de execucao recomendada

### Etapa 1: casca global do produto

Arquivos centrais:

1. templates/layouts/base.html
2. static/css/design-system.css

Objetivo:

Melhorar a experiencia estrutural que afeta todas as telas antes de lapidar telas isoladas.

Melhorias alvo:

1. destacar melhor a pagina atual na navegacao
2. criar area de contexto da pagina no topo com titulo, resumo e acao primaria consistente
3. reduzir ruido visual da topbar e tornar alertas mais legiveis
4. melhorar responsividade da shell para uso rapido em notebook e celular
5. reforcar estados de foco, hover e click para dar sensacao de interface mais viva e confiavel

### Etapa 2: dashboard com foco operacional

Arquivos centrais:

1. templates/dashboard/index.html
2. boxcore/dashboard/dashboard_views.py
3. boxcore/dashboard/dashboard_snapshot_queries.py

Objetivo:

Transformar o dashboard em uma tela de orientacao e decisao, nao em uma pagina de apresentacao do sistema.

Melhorias alvo:

1. separar claramente o que e urgente hoje, o que e tendencia e o que e atalho rapido
2. trocar acoes muito administrativas por acoes operacionais reais
3. destacar filas que pedem decisao imediata
4. reduzir texto introdutorio e aumentar sinal visual das prioridades
5. preparar cards clicaveis quando fizer sentido

### Etapa 3: base de alunos como mesa de operacao real

Arquivos centrais:

1. templates/catalog/students.html
2. boxcore/catalog/views/student_views.py
3. boxcore/catalog/student_queries.py
4. static/css/catalog-system.css

Objetivo:

Fazer a tela de alunos funcionar como uma mesa de atendimento e acompanhamento comercial, com leitura instantanea de quem exige acao.

Melhorias alvo:

1. condensar melhor filtros e resultados ativos
2. tornar a fila prioritaria mais clara e mais acionavel
3. melhorar o contraste entre lead, sem plano, em atraso e aluno ativo
4. reforcar resumo por linha sem obrigar leitura horizontal cansativa
5. preparar padrao de busca, filtro salvo e atalhos futuros sem redesenhar a pagina inteira depois

### Etapa 4: formulario de aluno mais fluido

Arquivos centrais:

1. templates/catalog/student-form.html
2. boxcore/catalog/forms.py
3. boxcore/catalog/views/student_views.py
4. static/css/catalog-system.css

Objetivo:

Diminuir cansaco cognitivo no cadastro e edicao sem sacrificar a consistencia do fluxo comercial e financeiro.

Melhorias alvo:

1. tornar os passos mais visuais e menos parecidos com um bloco longo de formulario
2. destacar melhor o essencial versus o opcional
3. exibir feedback imediato sobre plano, cobranca e impacto da escolha atual
4. tornar a area de historico e gestao financeira mais clara quando o aluno ja existe
5. preparar validacao e mensagens mais inteligentes para automacao futura

### Etapa 5: financeiro e grade

Arquivos centrais:

1. templates/catalog/finance.html
2. templates/catalog/finance-plan-form.html
3. templates/catalog/class-grid.html
4. boxcore/catalog/views/finance_views.py
5. boxcore/catalog/views/class_grid_views.py

Objetivo:

Fechar a fase 1 nas telas que sustentam leitura gerencial e rotina do box.

Melhorias alvo:

1. tornar cobranca, fila financeira e plano mais legiveis sem excesso de tabela
2. destacar proximas acoes em vez de apenas estado atual
3. melhorar a compreensao da grade de aulas em desktop e mobile
4. padronizar cartoes, legendas e filtros com o resto do sistema

### Etapa 6: workspaces operacionais por papel

Arquivos centrais:

1. templates/operations/
2. boxcore/operations/workspace_views.py
3. boxcore/operations/workspace_snapshot_queries.py

Objetivo:

Concluir a fase com telas operacionais mais enxutas, cada uma mostrando o minimo necessario para o papel certo.

Melhorias alvo:

1. reduzir elementos que nao ajudam o papel atual
2. destacar acao principal de cada workspace
3. melhorar feedback pos-acao para check-in, ocorrencia e rotina operacional
4. deixar a linguagem visual coerente entre manager, coach, owner e dev

## Componentes e comportamentos que valem investir agora

1. barra de acao fixa ou semi-fixa em telas longas
2. secoes recolhiveis com bom estado inicial
3. indicadores de prioridade com semantica consistente
4. estados vazios orientados por acao
5. confirmacoes e mensagens de sucesso mais objetivas
6. melhor sinalizacao da pagina atual e do papel atual
7. filtros com leitura do recorte ativo
8. cards clicaveis apenas onde reduz navegacao desnecessaria

## Checklist obrigatorio por tela

Antes de considerar qualquer tela suficientemente boa, validar:

1. o titulo da tela diz claramente para que ela serve
2. a acao principal aparece sem precisar procurar
3. a diferenca entre normal, atencao e urgencia esta visivel sem leitura longa
4. o usuario entende o recorte ativo de filtros e contexto atual
5. estados vazios, erros e alertas orientam o que fazer em seguida
6. tabelas, cards e blocos podem ser escaneados sem fadiga horizontal desnecessaria
7. a tela nao expoe mecanismo interno, improviso ou transicao como linguagem dominante
8. um usuario novo conseguiria operar o fluxo principal sem ficar travado por interpretacao

Se qualquer item acima falhar, a tela ainda esta confusa demais.

## Preparacao para automacao futura

Estas decisoes devem ser tomadas agora para evitar retrabalho:

1. manter nomes consistentes para estados operacionais e financeiros
2. separar claramente informacao, alerta e acao sugerida no front-end
3. preservar espacos de interface para sugestoes automatizadas futuras
4. evitar depender de texto solto quando o sistema puder expor estado estruturado
5. padronizar feedback visual de eventos bem-sucedidos, pendentes e falhos

## Definicao de pronto da fase 1

Esta fase pode ser considerada redonda quando:

1. a navegacao principal estiver clara em desktop e mobile
2. dashboard, alunos e formulario de aluno estiverem mais rapidos de escanear e operar
3. as principais telas tiverem hierarquia visual consistente
4. os estados de vazio, erro, alerta e sucesso estiverem padronizados
5. a interface parecer produto real, e nao painel tecnico em evolucao
6. a operacao principal puder ser entendida sem explicacao longa
7. a simplicidade percebida for alta mesmo nas telas mais densas

## Riscos de priorizacao que nao podem voltar

Com base em [v1-retrospective.md](v1-retrospective.md), esta fase nao pode repetir estes erros:

1. confundir quantidade de informacao com qualidade de orientacao
2. deixar a tela mostrar estado sem deixar clara a proxima acao
3. aceitar copy inconsistente entre template, view, query e teste
4. lapidar visual localizado antes de acertar casca, hierarquia e leitura global
5. introduzir refinamento visual que aumenta carga mental em vez de reduzi-la

Regra de defesa:

1. primeiro clareza estrutural
2. depois foco operacional
3. so depois refinamento fino

## Sequencia pratica sugerida para comecar

1. lapidar layout global e design tokens compartilhados
2. redesenhar o dashboard para foco de decisao
3. melhorar a tela de alunos como mesa de operacao
4. refinar o formulario de aluno com interacao progressiva
5. fechar financeiro, grade e operacao por papel

## Primeiro corte recomendado

Se formos fazer isso com criterio, a melhor abertura de trabalho e esta:

1. mexer primeiro em templates/layouts/base.html e static/css/design-system.css
2. em seguida atacar templates/dashboard/index.html
3. depois entrar em templates/catalog/students.html

Essa ordem evita maquiagem localizada. Primeiro acertamos a casca e a hierarquia global. Depois acertamos a tela principal. So entao refinamos a mesa operacional mais critica.

## Formula curta desta estrategia

Para esta fase, a formula correta e:

1. usar o Front Display Wall para proteger a face do produto contra ruido
2. usar este plano para definir ordem, escopo e criterio de pronto
3. usar a retrospectiva para impedir recaida em priorizacao errada

Em frase unica:

1. o front do OctoBox precisa ser simples o suficiente para nao confundir, claro o suficiente para orientar e forte o suficiente para parecer produto real em uso diario