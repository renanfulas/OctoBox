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

1. quase pronto

Ja esta forte em:

1. casca global coesa
2. topbar, compass e sidebar integrados
3. hooks estruturais principais no shell
4. ownership e JS centralizados

Ainda precisa fechar:

1. varredura final de responsividade e leitura em notebook estreito e mobile
2. sweep de hooks em includes transversais mais usados
3. checklist curto de acessibilidade do shell completo

### 2. Login e busca global

Status:

1. quase pronta

Ja esta forte em:

1. login visualmente maduro
2. busca global centralizada no shell
3. autocomplete com fluxo basico e hooks estaveis no shell

Ainda precisa fechar:

1. observacao assistida da busca em uso real no shell estreito
2. reduzir dependencia de estilo inline do login quando isso couber sem reabrir frente grande
3. observar a busca em uso assistido para confirmar o novo compasso de teclado e fallback

### 3. Dashboard principal

Status:

1. quase pronto

Ja esta forte em:

1. leitura curta de prioridade
2. payload namespaced
3. superficie principal estavel e validada em rota autenticada

Ainda precisa fechar:

1. revisar microambiguidades entre leitura executiva e atalhos de acao
2. garantir consistencia total entre modo default e modo recepcao
3. rodada assistida curta para confirmar se a priorizacao continua clara sob uso corrido

### 4. Alunos

Status:

1. quase pronto

Ja esta forte em:

1. listagem principal madura
2. prioridades, intake e filtros bem orientados
3. payload namespaced consolidado

Ainda precisa fechar:

1. revisar leitura de estados e vazios sob uso mais corrido
2. smoke de exportacao e foco operacional da mesa de atendimento
3. passada assistida curta para confirmar ritmo de triagem e diretório

### 5. Ficha leve do aluno

Status:

1. quase pronto

Ja esta forte em:

1. fluxo progressivo fora do admin
2. payload namespaced consolidado
3. automacao de plano conectado e parcelamento

Ainda precisa fechar:

1. tornar os estados do fluxo ainda mais explicitos por etapa
2. revisar leitura em mobile e em uso longo de recepcao/manager
3. passada assistida curta de cadastro, conversao e resumo financeiro

### 6. Financeiro

Status:

1. quase pronto

Ja esta forte em:

1. leitura operacional e comercial clara
2. filtros, fila, portfolio e regua na mesma superficie
3. payload namespaced consolidado

Ainda precisa fechar:

1. revisar estados de recorte ativo, vazio e feedback nas acoes mais sensiveis
2. fechar leitura de beta para uso corrido de cobranca e retencao
3. passada assistida curta para filtro, fila e motor de planos

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
2. revisar leitura em viewport mais estreita sob rotina longa
3. lapidacao final de piloto porque esta tela continua simbolica e central

### 10. Ficha leve do aluno

Status:

1. pronta para beta assistido

Ja esta forte em:

1. save leve validado em uso real
2. datas principais renderizadas em formato compativel com input date
3. leitura comercial, financeira e de matricula segue concentrada na mesma tela

Ainda merece vigilancia em:

1. erros compostos quando plano, cobranca e matricula mudam juntos
2. comportamento do formulario em viewport estreita
3. uso longo com alteracoes sucessivas no mesmo aluno

## Ambiguidades restantes que mais pesam hoje

Estas sao as ambiguidades que mais atrapalham declarar o front pronto para beta:

1. algumas telas ja estao fechadas estruturalmente e em save real, mas ainda pedem observacao em uso longo e viewport estreita
2. login e busca global ainda precisam ser tratados como superficies de beta, e nao apenas como periferia tecnica
3. os proximos riscos sao menos de persistencia central e mais de leitura, ritmo e fallback sob pressao operacional

## Declaracao atual de readiness

Estado atual:

1. o front esta pronto para beta assistido com vigilancia operacional
2. as superficies centrais do beta ja tem payload namespaced, hooks estruturais principais, smoke autenticado por rota e passada visual assistida nas telas simbolicas
3. a rodada assistida de saves leves ja validou recepcao, grade, ficha leve do aluno e edicao de plano em uso real com confirmacao de persistencia
4. o que permanece aberto agora e observacao assistida de uso real sob ritmo corrido, viewport estreita e sessoes mais longas

Traducao pratica:

1. a arquitetura do front ja saiu da fase de exploracao e entrou em consolidacao real
2. novas mudancas devem priorizar leitura, estados, acessibilidade curta e confianca operacional
3. o que falta agora nao e reinvencao estrutural, e observacao assistida do que ja esta montado
4. os saves centrais de baixo risco deixaram de ser hipotese e passaram a ser validacao observada

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
3. passada visual assistida concluida nas superficies simbolicas
4. declaracao de pronto para beta assistido emitida com vigilancia operacional

## Regra de uso deste quadro

Sempre que uma mudanca relevante de front entrar, responder:

1. ela empurra alguma superficie deste quadro um passo para frente?
2. ela remove ambiguidade real ou so adiciona novidade?
3. ela ajuda a declarar uma onda concluida?

Se a resposta for nao, a mudanca provavelmente nao pertence ao momento atual do front.