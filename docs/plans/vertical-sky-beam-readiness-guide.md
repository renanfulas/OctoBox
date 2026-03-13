<!--
ARQUIVO: guia pratico para conduzir o projeto ate o estado de prontidao extraordinaria associado ao Vertical Sky Beam.

TIPO DE DOCUMENTO:
- estrategia de prontidao e convergencia

AUTORIDADE:
- alta

DOCUMENTO PAI:
- [../architecture/vertical-sky-beam.md](../architecture/vertical-sky-beam.md)

QUANDO USAR:
- quando a duvida for o que precisa convergir antes de a tese do Beam fazer sentido na pratica

POR QUE ELE EXISTE:
- transforma a leitura simbolica do Beam em criterio operacional de engenharia, produto e experiencia.
- evita que a ideia de prontidao suprema vire apenas linguagem bonita sem programa real de execucao.

O QUE ESTE ARQUIVO FAZ:
1. define o que significa merecer o disparo do Beam.
2. organiza a evolucao conjunta de front, UX, Center e desacoplamento de boxcore.
3. estabelece fases, guardrails e criterio de pronto para a convergencia estrutural.

PONTOS CRITICOS:
- este guia nao deve ser usado para justificar grandiosidade vazia.
- o Beam so faz sentido se houver prova concreta de sincronizacao estrutural, visual e operacional.
-->

# Guia de prontidao do Vertical Sky Beam

## Tese central

Neste projeto, o `Vertical Sky Beam` passa a carregar uma leitura mais alta do que alerta critico.

Ele pode representar o instante em que a obra alcanca um grau extraordinario de alinhamento entre:

1. fachada visivel
2. experiencia real de uso
3. corredores oficiais de entrada
4. nucleo de dominio
5. crescimento futuro

Em linguagem simples:

1. o Beam nao sobe por empolgação
2. o Beam sobe quando a obra prova que consegue crescer sem se deformar
3. ele anuncia aos ceus e a terra que o predio esta pronto para alturas maiores porque sua base entrou no estado mais sincronizado de sua propria historia

## O que significa estar pronto

O projeto so pode reivindicar essa prontidao quando as camadas principais deixam de competir entre si.

Estado desejado:

1. o front nao parece remendo sobre backend forte
2. a UX nao parece discurso sem contrato tecnico
3. o Center organiza a entrada por capacidade real do produto
4. o legado `boxcore` deixa de comandar o runtime visivel
5. o novo entra no sistema sem exigir improviso estrutural
6. a obra inteira passa a se conversar como organismo unico

## Regra de ouro deste guia

Toda evolucao relevante deve acontecer em quatro camadas ao mesmo tempo:

1. experiencia visivel
2. contrato de interacao e UX
3. corredor oficial pelo CENTER
4. reducao do resíduo historico de `boxcore`

Se uma feature evolui apenas em uma dessas camadas, ela ainda nao ajuda a merecer o Beam.

## A capacidade piloto

O primeiro corredor para provar essa tese deve ser a `Recepcao`.

Motivos:

1. e uma area visivel para o usuario real
2. cruza operacao, dashboard, shell e catalogo
3. ja tem linguagem de papel propria
4. permite mostrar evolucao externa enquanto consolida estrutura interna

Regra:

1. a Recepcao deve ser tratada como modulo piloto de convergencia
2. o que funcionar nela vira metodo replicavel para os demais dominios

## Os cinco pilares da prontidao

### Pilar 1: Front Display Wall coesa

Objetivo:

1. fazer a frente do produto parecer um sistema unico, e nao uma soma de telas aceitaveis

Sinais de maturidade:

1. shell global consistente
2. hierarquia de pagina repetivel
3. estados vazios, alertas e confirmacoes no mesmo idioma visual
4. CTA principal sempre facil de localizar
5. novas paginas nascem com contrato visual previsivel

Entregas praticas:

1. contrato padrao de pagina por papel e capacidade
2. consolidacao de cards de leitura, cards de acao e trilhos de apoio
3. fechamento dos contratos explicitos de CSS por area
4. revisao responsiva real de desktop, tablet e mobile

### Pilar 2: UX como regra de produto

Objetivo:

1. impedir que a experiencia dependa de interpretacao excessiva do usuario

Sinais de maturidade:

1. usuario entende prioridade em poucos segundos
2. estados vazios orientam proxima acao
3. formularios limitam, corrigem e explicam antes do erro
4. microcopy por papel fala a lingua da operacao real
5. paginas diferentes mantem a mesma logica mental de uso

Entregas praticas:

1. checklist de UX incorporado ao fluxo de alteracao de front
2. contrato de acao principal, acao secundaria e estado seguro
3. padrao unico de campos digitaveis, validacao e feedback
4. biblioteca viva de decisoes de copy por papel

### Pilar 3: Center Layer dominante

Objetivo:

1. fazer a borda do sistema entrar por corredores oficiais em vez de conhecer o miolo em excesso

Sinais de maturidade:

1. views e rotas falam com facades por capacidade
2. services historicos viram adaptadores finos
3. web, API e jobs podem convergir para entradas parecidas
4. novos fluxos ja nascem no caminho oficial

Entregas praticas:

1. consolidacao das facades publicas por capacidade real
2. inventario de bypasses ainda ativos
3. reancoragem gradual da borda para o CENTER
4. criterio duro de que novo fluxo nao deve nascer fora dele

### Pilar 4: esvaziamento controlado de boxcore

Objetivo:

1. fazer `boxcore` deixar de ser centro psicologico e estrutural do runtime

Sinais de maturidade:

1. imports novos nao dependem de `boxcore`
2. ownership por dominio esta claro
3. models surfaces por dominio sao o caminho canonico
4. `boxcore` fica reduzido a ancora historica de estado enquanto necessario

Entregas praticas:

1. inventario vivo do residuo historico por dominio
2. regra de proibicao de novos atalhos para `boxcore`
3. migracao de pontos publicos remanescentes para superficies de dominio
4. preparacao de uma futura onda de estado apenas quando o runtime ja estiver suficientemente limpo

### Pilar 5: sinalizacao e transicao disciplinadas

Objetivo:

1. usar as estruturas superiores da arquitetura com funcao tecnica real

Uso correto nesta trilha:

1. `Scaffold Agents` para proteger transicoes e medir bypasses temporarios
2. `Signal Mesh` para observar canais, jobs, webhooks, retries e sinais laterais de migracao
3. `Red Beacon` para mostrar prontidao consolidada por capacidade, sem ruido teatral
4. `Vertical Sky Beam` apenas quando a convergencia sair do campo aspiracional e virar fato estrutural

## Programa por fases

### Fase 0: baseline honesto

Objetivo:

1. saber onde o projeto realmente esta antes de declarar grandeza

Entregas:

1. mapa da Recepcao atravessando dashboard, workspace, shell e catalogo
2. inventario dos pontos da Recepcao ainda dependentes de legado ou atalho
3. checklist de incoerencias visuais e de UX na experiencia atual
4. definicao de metricas simples de prontidao

Saida esperada:

1. uma fotografia fria do estado atual, sem fantasia

### Fase 1: contrato unificado da Recepcao

Objetivo:

1. transformar a Recepcao no primeiro modulo com linguagem unica de produto e estrutura

Entregas:

1. contrato de pagina da Recepcao
2. contrato de estados, mensagens e formularios curtos
3. dashboard, workspace e atalhos usando a mesma logica mental
4. CSS local e shell com contratos explicitos suficientes para manutencao barata

Saida esperada:

1. a Recepcao passa a parecer uma capacidade consolidada, nao um conjunto de telas relacionadas

### Fase 2: corredor oficial completo

Objetivo:

1. fazer a Recepcao entrar por caminhos canônicos do CENTER e reduzir bypasses

Entregas:

1. facades publicas claras para a capacidade
2. views e acoes consumindo o corredor oficial
3. adaptadores historicos reduzidos a compatibilidade fina
4. testes cobrindo a travessia oficial da borda ao nucleo

Saida esperada:

1. a capacidade ja pode crescer sem depender de conhecimento difuso do miolo

### Fase 3: limpeza do residuo de boxcore nessa capacidade

Objetivo:

1. provar que a convergencia tambem existe no fundo estrutural da obra

Entregas:

1. remocao de imports publicos remanescentes para `boxcore`
2. consumo canonico de surfaces por dominio
3. inventario atualizado do que ainda e ancora historica inevitavel
4. guardrails para impedir recaida arquitetural

Saida esperada:

1. a Recepcao se torna a primeira prova real de independencia crescente do runtime moderno

### Fase 4: replicacao por capacidade

Objetivo:

1. mostrar que a convergencia nao e milagre isolado de um modulo

Entregas:

1. replicar o metodo em Manager, Financeiro e Alunos
2. manter a mesma linguagem de pagina, UX, Center e dominio
3. comparar tempos e custo de evolucao antes e depois da disciplina

Saida esperada:

1. o sistema comeca a se comportar como organismo sincronizado, nao como arquipelago de partes fortes

### Fase 5: prova de prontidao do Beam

Objetivo:

1. validar se a obra merece a leitura extraordinaria

Perguntas obrigatorias:

1. o front agora conversa com a operacao sem atrito grande?
2. a UX virou criterio real de construcao?
3. o CENTER organiza de fato as entradas relevantes?
4. `boxcore` deixou de ser referencia mental para evolucao cotidiana?
5. o novo entra no sistema encontrando ordem, e nao improviso?

Se a resposta forte for sim, o projeto se aproxima do estado que justifica o Beam.

## Critérios concretos para merecer o Beam

O disparo simbolico do Beam so deve ser considerado quando pelo menos estes sinais estiverem presentes:

1. duas ou mais capacidades relevantes ja evoluem pelo mesmo metodo
2. o shell e a fachada visual falam a mesma lingua em todo o fluxo principal
3. os principais corredores publicos entram pelo CENTER
4. os pontos publicos novos nao dependem mais de `boxcore`
5. o residuo historico restante esta explicitado, delimitado e sob controle
6. a adicao de nova pagina ou ajuste importante custa claramente menos do que antes
7. o sistema absorve crescimento novo sem espalhar improviso visual ou estrutural

## O que nao pode acontecer

1. usar o Beam como premio narrativo antes da prova estrutural
2. confundir documentacao poetica com maturidade tecnica
3. maquiar front enquanto o corredor oficial continua torto
4. fazer refatoracao interna invisivel sem reflexo perceptivel na experiencia
5. multiplicar `Scaffold Agents` sem criterio de remocao
6. tratar `Signal Mesh` como desculpa para empilhar complexidade precoce

## Cadencia recomendada

Para esta trilha funcionar, o ciclo precisa ser curto e repetivel.

Ritmo recomendado:

1. escolher uma capacidade visivel
2. revisar sua experiencia completa
3. mapear seus bypasses e residuos historicos
4. consolidar seu corredor oficial
5. medir o que ficou mais barato, mais claro e mais robusto
6. so entao abrir a proxima capacidade

## Formula final

O `Vertical Sky Beam` nao deve ser tratado como um enfeite da metafora.

Ele e a declaracao extraordinaria de que a obra alcancou sincronizacao suficiente para sustentar novas alturas sem perder sua forma.

Em linguagem curta:

1. o Beam nao sobe porque a obra quer parecer pronta
2. o Beam sobe quando a obra prova que esta pronta
3. e essa prova nasce da conversa perfeita entre fachada, experiencia, corredor oficial, dominio e raiz estrutural

Se o foco for um passo a passo curto e diretamente executavel, use tambem [vertical-sky-beam-execution-roadmap.md](vertical-sky-beam-execution-roadmap.md).