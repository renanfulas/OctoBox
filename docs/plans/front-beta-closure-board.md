<!--
ARQUIVO: quadro operacional de fechamento do front para beta.

TIPO DE DOCUMENTO:
- plano curto de consolidacao de beta

AUTORIDADE:
- alta para a fase atual do front-end

DOCUMENTO PAI:
- [front-end-restructuring-guide.md](front-end-restructuring-guide.md)

QUANDO USAR:
- quando a duvida for o que ja esta pronto para beta, o que ainda esta ambiguo e qual ordem curta de fechamento seguir no front

POR QUE ELE EXISTE:
- transforma a maturidade percebida do produto em quadro operacional objetivo.
- evita reabrir exploracao visual quando o momento pede consolidacao.
- organiza o fechamento do front por ondas curtas e superficies reais do beta.

O QUE ESTE ARQUIVO FAZ:
1. lista as superficies centrais do beta.
2. marca o estado atual de prontidao de cada uma.
3. registra ambiguidade restante com linguagem objetiva.
4. define ondas curtas de fechamento do front.

PONTOS CRITICOS:
- este quadro precisa continuar honesto; nao existe para inflar sensacao de pronto.
- qualquer superficie marcada como pronta ainda pode receber refinamento, mas nao deve voltar a oscilar estruturalmente sem motivo forte.
-->

# Quadro de fechamento do front para beta

## Legenda de status

1. pronta para beta assistido: a superficie ja sustenta uso real assistido sem reabrir arquitetura
2. quase pronta: a base esta madura, mas ainda existe ambiguidade ou fechamento operacional pendente
3. precisa fechar: a superficie ja tem valor, mas ainda nao deve ser tratada como consolidada para beta

## Matriz honesta de prontidao

### 1. Shell global autenticado

Status:

1. pronta para beta assistido

Ja esta forte em:

1. casca global coesa
2. topbar, compass e sidebar integrados
3. hooks estruturais principais no shell
4. ownership e JS centralizados
5. interacao fisica sem quebras documentada

Vigilancia pos-gate:

1. sweep de hooks em includes transversais mais usados
2. checklist curto de acessibilidade do shell completo a longo prazo

### 2. Login e busca global

Status:

1. pronta para beta assistido

Ja esta forte em:

1. login visualmente maduro
2. busca global centralizada no shell
3. autocomplete com fluxo basico e hooks estaveis no shell
4. toque validado e operando corretamente

Vigilancia pos-gate:

1. observar a busca em uso assistido real para ritmo de usuario e debounce
2. limar paddings exagerados identificados nos espacos de interacao

### 3. Dashboard principal

Status:

1. pronta para beta assistido

Ja esta forte em:

1. leitura curta de prioridade
2. payload namespaced
3. superficie principal estavel e validada em rota autenticada sem quebras

Vigilancia pos-gate:

1. revisar microambiguidades entre leitura executiva e atalhos de acao longo prazo
2. garantir consistencia estetica total entre modo default e modo recepcao

### 4. Alunos

Status:

1. pronta para beta assistido

Ja esta forte em:

1. listagem principal madura
2. prioridades, intake e filtros bem orientados
3. payload namespaced consolidado
4. tabela responsiva via scroll sem empurrar a grid (aprovada no fisico)

Vigilancia pos-gate:

1. revisar leitura de estados e vazios sob uso massivo
2. smoke continuo de exportacao e foco operacional

### 5. Ficha leve do aluno

Status:

1. pronta para beta assistido

Ja esta forte em:

1. fluxo progressivo fora do admin
2. payload namespaced consolidado
3. automacao de plano conectado e parcelamento
4. save leve validado em uso real com leitura financeira concentrada

Ainda merece vigilancia em:

1. tornar os estados do fluxo ainda mais explicitos por etapa
2. confirmar leitura em mobile fisico e em uso longo de recepcao/manager
3. erros compostos quando plano, cobranca e matricula mudam juntos
4. comportamento do formulario em viewport estreita
5. uso longo com alteracoes sucessivas no mesmo aluno

### 6. Financeiro

Status:

1. pronta para beta assistido

Ja esta forte em:

1. leitura operacional e comercial clara
2. filtros, fila, portfolio e regua na mesma superficie
3. barreira de acesso forte (bloqueia perfeitamente nivel Coach)

Vigilancia pos-gate:

1. refino isolado de tipologias superdimensionadas ao longo do beta
2. calibracao do uso corrido das operacoes de cobranca

### 7. Edicao de plano

Status:

1. pronta para beta assistido

Ja esta forte em:

1. superficie curta e bem delimitada
2. payload namespaced consolidado
3. objetivo da tela claro

Ainda merece vigilancia em:

1. leitura de erro em formulario incompleto
2. mobile e ancoras da tela

### 8. Grade de aulas

Status:

1. pronta para beta assistido

Ja esta forte em:

1. visoes do dia, semana e mes
2. planejador e edicao rapida integrados
3. JS de pagina isolado e ownership claro
4. quick edit validado em save real sem reabrir sessao concluida

Ainda merece vigilancia em:

1. smoke de reorder e modal mensal em uso real mais corrido
2. confirmar leitura clara da tela para quem nao participou da construcao
3. observar o comportamento da agenda em uso assistido prolongado

### 9. Recepcao

Status:

1. pronta para beta assistido

Ja esta forte em:

1. papel proprio claro
2. boa leitura de balcao
3. foco operacional curto e humano
4. cobranca curta validada em save real com payload localizado

Ainda merece vigilancia em:

1. intake e leitura de balcao em uso corrido prolongado
2. confirmar toque real em viewport estreita sob navegador externo manual ou dispositivo fisico
3. lapidacao final de piloto porque esta tela continua simbolica e central

## Vigilancia ativa de longo prazo

As ambiguidades estruturais graves foram sanadas. O que resta para o beta assistido em observacao:

1. pequenos padroes de espacamento (paddings do login) e tipologia (labels grandalhonas)
2. acompanhamento do desgaste cognitivo de leitura sob uso continuo longo na recepcao
3. possiveis refinos de usabilidade em botoes flutuantes baseados no ritmo real da equipe

## Fechamento complementar mais recente

Ultima rodada concluida:

1. a rodada assistida inicial de `2026-03-28` foi registrada em [../experience/mobile-real-validation-round-2-2026-03-28-assisted.md](../experience/mobile-real-validation-round-2-2026-03-28-assisted.md)
2. a revalidacao focada do diretorio de alunos ficou registrada em [../experience/mobile-real-validation-round-3-2026-03-28-students-postfix.md](../experience/mobile-real-validation-round-3-2026-03-28-students-postfix.md)
3. a rodada consolidada mais recente ficou registrada em [../experience/mobile-real-validation-round-4-2026-03-29-browser-assisted-postfix.md](../experience/mobile-real-validation-round-4-2026-03-29-browser-assisted-postfix.md)
4. login, dashboard, recepcao e alunos ficaram sem overflow horizontal em `320px`, `390px` e `430px`
5. o pan lateral residual do shell foi removido antes do piloto
6. a busca global ficou visualmente estavel, mas o autocomplete permaneceu inconclusivo porque o dataset local nao devolveu resultados

7. O QA Fisico Operacional foi APROVADO sem bloqueadores na Rodada 6, liberando o front-end para ambiente real assistido.

Gate Beta: APROVADO PARA BETA ASSISTIDO RESTRITO
SEM BLOQUEADORES FUNCIONAIS CONHECIDOS NO GATE ATUAL
COM RESSALVAS ESTETICAS E VIGILANCIA OPERACIONAL

1. a confirmacao fisica com toque humano via script de 10 min foi 100% cumprida.
2. o roadmap oficial esta despausado para prosseguir com evolucoes modulares e correcoes puramente esteticas.

## Declaracao atual de readiness

Estado atual:

1. o front esta pronto para beta assistido em desktop e nas larguras mobile de `320px` a `430px`, com vigilancia operacional
2. as superficies centrais do beta ja tem payload namespaced, hooks estruturais principais, smoke autenticado por rota e passada visual assistida nas telas simbolicas
3. a rodada assistida de saves leves ja validou recepcao, grade, ficha leve do aluno e edicao de plano em uso real com confirmacao de persistencia
4. a rodada consolidada de `2026-03-29` manteve login, dashboard, recepcao e alunos sem overflow horizontal em `320px`, `390px` e `430px`
5. o que permanece aberto agora e observacao assistida de uso real sob ritmo corrido, viewport estreita fisica, autocomplete real da busca e sessoes mais longas

Traducao pratica:

1. a arquitetura do front ja saiu da fase de exploracao e entrou em consolidacao real
2. novas mudancas devem priorizar leitura, estados, acessibilidade curta e confianca operacional
3. o que falta agora nao e reinvencao estrutural, e validar toque real do que ja esta montado e observar o comportamento humano do fluxo
4. os saves centrais de baixo risco deixaram de ser hipotese e passaram a ser validacao observada
5. a confirmacao mobile fisica esta inteiramente concluida e oficializada fora dos simuladores (sem bugs bloqueantes).

## Trilha estrutural obrigatoria a partir de agora

Mesmo com readiness de beta assistido, estas frentes continuam obrigatorias porque reduzem custo estrutural sem reabrir a fachada do produto.

### 1. Retirar montagem visual residual das views

Status:

1. pendente prioritario

Escopo imediato:

1. edicao de plano em [../../catalog/views/finance_views.py](../../catalog/views/finance_views.py)
2. dashboard em [../../dashboard/dashboard_views.py](../../dashboard/dashboard_views.py)
3. guia em [../../guide/views.py](../../guide/views.py)

Saida esperada:

1. view HTTP curta
2. presenter ou builder explicito
3. payload claro anexado em um ponto unico

### 2. Podar payload cosmetico e contexto informal

Status:

1. pendente prioritario

Escopo imediato:

1. revisar as telas acima antes de aceitar nova copy estrutural
2. mover para frontend toda repeticao de leitura que nao altere regra, permissao, estado ou acao
3. manter aliases legados so no helper compartilhado

Saida esperada:

1. payload menor e mais semantico
2. menos risco de duplicacao de apresentacao
3. fronteira backend versus frontend mais defensavel

### 3. Fechar ownership por tela sem inflar camadas

Status:

1. em andamento

Escopo imediato:

1. template principal fino
2. includes por papel claro
3. CSS e JS localizaveis
4. hooks estruturais usados por comportamento e teste

Saida esperada:

1. manutencao curta
2. engenharia reversa simples
3. zero caca cega entre view, template e script

### 4. Regra de entrada para o restante do projeto

Status:

1. ativo como norma

Regra:

1. tela nova nao nasce com montagem visual pesada na view
2. backend entrega verdade semantica, nao cosmetica redundante
3. frontend assume composicao, repeticao visual e distribuicao da leitura
4. se a mudanca nao melhora estrutura ou operacao real, ela nao vence prioridade

## Ondas curtas de fechamento

### Onda 1. Entrada e balcao

Objetivo:

1. fechar o que o beta mais sente logo na porta de entrada e no balcao

Escopo:

1. login
2. busca global
3. shell global autenticado
4. recepcao

Saida esperada:

1. entrada confiavel
2. busca previsivel
3. shell validado em responsividade e acessibilidade curta
4. recepcao pronta para piloto assistido

### Onda 2. Operacao central do box

Objetivo:

1. consolidar as superficies que sustentam leitura, atendimento e dinheiro no dia a dia

Escopo:

1. dashboard
2. alunos
3. ficha leve do aluno
4. financeiro
5. edicao de plano

Saida esperada:

1. clareza de proxima acao estabilizada
2. hooks estruturais fechados nas areas mais densas
3. estados e feedback mais consistentes sob uso real

### Onda 3. Agenda e declaracao de pronto

Objetivo:

1. fechar a grade e declarar readiness do front para beta assistido

Escopo:

1. grade de aulas
2. varredura final de hooks estruturais em includes centrais
3. smoke final por superficie do beta
4. fechamento documental de pronto

Saida esperada:

1. grade pronta para uso assistido
2. superficies centrais do beta com status honesto atualizado
3. declaracao formal de front pronto para beta assistido

Estado desta onda agora:

1. fechamento estrutural concluido
2. validacao tecnica concluida
3. passada browser-assisted concluida nas superficies simbolicas
4. fechamento mobile fisico concluido e validado de ponta a ponta sem estourador de rota.

## Regra de uso deste quadro

Sempre que uma mudanca relevante de front entrar, responder:

1. ela empurra alguma superficie deste quadro um passo para frente?
2. ela remove ambiguidade real ou so adiciona novidade?
3. ela ajuda a declarar uma onda concluida?

Se a resposta for nao, a mudanca provavelmente nao pertence ao momento atual do front.
