<!--
ARQUIVO: retrospectiva tecnica e de produto da V1.

POR QUE ELE EXISTE:

registra o que foi aprendido no primeiro ciclo funcional do projeto enquanto o contexto ainda esta fresco.

preserva as decisoes e trade-offs para futuras iteracoes sem depender de memoria.

O QUE ESTE ARQUIVO FAZ:

resume o problema enfrentado e a proposta da V1.

documenta decisoes arquiteturais e de produto tomadas no ciclo inicial.

registra aprendizados, riscos encontrados e proximos passos sugeridos.

PONTOS CRITICOS:

este documento precisa acompanhar a realidade do projeto e nao virar narrativa inflada.

se novas fases mudarem as decisoes centrais, esta retrospectiva deve continuar deixando claro que se refere ao primeiro marco funcional.
-->

# Retrospectiva da V1
O brilhante é transformar coisas complexas em simples.

Dev, aproveite cada conteúdo escrito aqui.. vale ouro!

Posso ter um jeito meio incisivo, mas escrevo com toda humildade e empatia do mundo, meu companheiro de profissão.

Introdução do Conhecimento
Possivelmente este vai ser o maior texto que escrevi com minhas próprias mãos neste programa, pois aqui vou abrir a "caixa preta" de como fazer um excelente trabalho em Django.

Primeiro de tudo, é necessário entender o que você quer resolver. Sem clareza, não haverá como arquitetar o sistema, nem os processos de forma integrada e inteligente. Nem que seja necessário você adiar um dia apenas pensando e planejando o que vai fazer: faça.

Não estou dizendo para você só colocar no papel ou no VS Code quando estiver com a ideia madura; não é isso. Aqui é pensamento organizado. Você precisa entender as estruturas que quer construir para que, quando for levantar o alicerce, ele seja fixo e suba do jeito EXATO que você planejou.

Imagine que você é um engenheiro e tem em mente levantar um prédio de 30 andares, mas fica ansioso e quer agir rapidamente. Não esperou o aval da prefeitura, não verificou o terreno, não fez a lição de casa e, de repente, descobre que naquele solo só poderia levantar 20 andares.

Poxa vida, você se comprometeu. Já implementou o alicerce em um terreno limitado. Agora é se contentar com isso, ver se consegue demolir imóveis ao lado para suprir a demanda e viver fazendo gambiarras para compensar o erro inicial.

Agora, se você aguarda mais um tempo, pensa na estrutura e vê que o projeto é grande para aquele terreno, você procuraria outro, faria uma base sólida, um alicerce firme e um fundamento perfeito. Aquele prédio de 30 andares seria feito já imaginando a expansão, o bom solo, o terraço, o terreno vizinho e a localização estratégica. Você deixou maneiras preventivas de expandi-lo.

Tudo isso aconteceu apenas porque você teve cuidado com o alicerce. Um dia a mais pensando, calculando e prevendo o que poderia acontecer.

Nessa hora você deve estar pensando: "Nossa, que chato, já vou ter um trabalhão e ainda vou adiar o código?".

Vai por mim: é melhor um bom trabalho feito com critério do que um trabalho mal feito, refeito e remendado rapidamente.

Primeiros passos
Bem, você já gastou tempo imaginando o futuro e as expansões. Tá na hora de quê? Botar a mão na massa?

Claro que não! Vamos organizar as ideias primeiro.

"Ah, mas assim vai demorar demais, tenho que entregar isso em 5 dias". Pare de pensar como um executor de tarefas e comece a pensar como um engenheiro/arquiteto. Veja, eu entreguei um sistema limpo, organizado, funcional e livre de bugs críticos em 1 dia. A maioria dos devs faria isso em uma ou duas semanas. (Claro, teve um hiperfoco intenso da minha parte).

Então, siga minhas instruções, elas fazem sentido. Não seja negligente com o método. Estruture um mapa mental do sistema para, aí sim, definir os parâmetros e começar a codar.

Antes de tudo, seja disciplinado. Um print("Hello world") para não dar azar.

Logo após, tenha em mente que em todo código você vai relatar:

O porquê do código?

O que ele faz?

Quais os pontos críticos que podem causar panes?

Escreva comentários nas linhas complexas ou obscuras. Não comentários prolixos, mas assertivos. Pense que não é só você ali; pense que você pode voltar daqui a 5 anos e terá esquecido os detalhes.

AGORA O PRINCIPAL:

NÃO DESPERDICE SUA INTELIGÊNCIA. Entenda que você gasta muita energia decifrando código. Fico abismado com códigos que pego de outros devs; eles não percebem que prejudicam a si mesmos.

Quando você tenta ler algo complexo, emaranhado em várias outras lógicas, você consome a energia do seu cérebro. Uma energia que você poderia estar usando para resolver problemas novos ou criar funcionalidades.

Você gasta seu tempo voltando ao passado para entender o que um arquivo faz só por causa de uma preguiça momentânea de documentar. Se você muda uma letra ou um diretório em um código crítico e não documentado, você acaba de criar um problema enorme para si mesmo.

Enfim, adote essas boas práticas. É bom para o colega, mas é muito melhor para você.

Mão na massa
Agora sim! Começamos o projeto, às vezes horas depois do planejado, e está tudo bem. A ideia é correr na direção certa, não correr o mais rápido possível para qualquer lado. É afiar o machado antes de bater no tronco.

E vamos afiar fazendo o backup, certo?

COMO É O PROJETO?
Quais frameworks são necessários? O que eu vou precisar? Consigo extrair o máximo usando o mínimo possível?

Essa é uma pegada que adotei aqui e achei excelente. Muitas funções eu poderia resolver com frameworks extras por costume, mas preferi o stack nativo do Django (ORM, autenticação, forms, admin).

Se você coloca frameworks demais sem necessidade, ganha complexidade: front separado, dois sistemas para rotear, duas camadas para validar, brechas de segurança... um custo alto para manter a coerência.

Sistema enxuto é mais leve. Sistema leve é mais rápido. Sistema rápido é menos propenso a bugs. Menos bugs significam menos manutenção e usuários mais satisfeitos. E usuário satisfeito é dinheiro no bolso de todo mundo!

Organização
Pense em estruturar sempre da maneira mais organizada possível. "Lápis com lápis, caneta com caneta". Isso é fundamental para que seus colegas entendam o projeto em minutos, não em meses.

Você pode até saber onde está cada coisa agora, mas em algum momento você vai se perder procurando um arquivo por 5 minutos. Em um projeto grande, você faz isso centenas de vezes. No final, gastou horas apenas procurando coisas.

Pastas que conversam entre si, nomes claros, lógica de organização. E, pelo amor de Deus, não jogue tudo no views.py. Tire tudo o que for possível de lá. Organize por domínios.

Está ganhando forma
Sempre use o relógio a seu favor. Mantenha a disciplina de documentar em todo arquivo:

Para que serve?

O que faz?

Qual o ponto crítico?

Após algo complexo, faça um debug e um backup desse ponto. Precaução nunca é demais e custa pouco espaço em disco.

Aqui eu deixo você brilhar com sua arte
Aqui você brilha. Existem diversos caminhos para o mesmo resultado. O importante é: resolve o problema de forma eficiente? Se sim, fique em paz.

Poderia ser melhor? Sim! Sempre poderá. Mas o foco é a eficiência agora. Com essa mentalidade, cada vez você resolverá os problemas de forma mais elegante.

Espero que tenha gostado, DEV.

Agora vai o conteúdo técnico

## O que a V1 entregou

Eu cheguei ao primeiro marco funcional entregando uma base operacional integrada com:

1. base de alunos com WhatsApp como identificador operacional principal
2. intake para leads e entradas provisiorias antes do cadastro definitivo
3. fluxo leve de cadastro e edicao de aluno fora do admin bruto
4. conexao entre aluno, plano, matricula e cobranca inicial
5. centro visual de financeiro com filtros e leituras gerenciais
6. grade de aulas com agenda do dia, visao semanal, visao mensal e planejador recorrente
7. regras por papel para owner, dev, manager e coach
8. trilha de auditoria para eventos sensiveis

## Decisoes que eu tomei

### 1. Separar por dominio antes de crescer

Uma decisao forte da V1 foi evitar concentrar tudo em arquivos genericos demais. Em vez de deixar a logica espalhada em views grandes, eu organizei a base por dominio e por responsabilidade:

1. views HTTP para orquestracao
2. queries e snapshots para leitura
3. services, actions e workflows para regra de negocio

Essa decisao me ajudou especialmente no catalogo, no financeiro e na grade de aulas.

### 2. Priorizar operacao real antes de polimento excessivo

Na V1 eu nao tentei resolver tudo. O foco foi construir fluxo operacional utilizavel. A prioridade nao foi um painel perfeito, mas uma base que ajudasse de verdade em recepcao, gerencia, cobranca e agenda.

### 3. Tirar trabalho do admin onde a operacao mais usa

O admin do Django continua valioso como backoffice, mas eu tratei como importante mover as rotinas mais frequentes para telas mais leves, diretas e legiveis. Isso apareceu principalmente em:

1. diretorio de alunos
2. ficha leve do aluno
3. centro financeiro visual
4. grade visual de aulas

### 4. Assumir que papeis importam desde cedo

Em vez de deixar permissao para depois, eu fiz a base nascer com papeis e navegacao filtrada por owner, dev, manager e coach. Isso evita que a interface fique falsa, expondo areas que o usuario nao deveria operar.

### 5. Tratar auditoria como parte do produto e nao como detalhe futuro

Outra decisao importante foi incluir rastreabilidade desde cedo em login, logout, mudancas no admin e acoes sensiveis. Para mim, isso fortalece manutencao, seguranca operacional e confianca no sistema.

## Coisas que funcionaram bem

1. a separacao entre leitura e mutacao deixou a base mais legivel do que uma V1 costuma ser
2. a organizacao por dominio tornou a manutencao mais simples do que seria numa pasta unica de views enormes
3. a grade de aulas evoluiu rapido porque a estrutura aguentou refatoracao sem desmontar a tela inteira
4. o uso de testes focados em fluxo real ajudou a segurar a evolucao sem voltar bug toda hora
5. a padronizacao de cabecalhos deixou a base mais navegavel para leitura humana

## Principais aprendizados

### 1. Velocidade boa nao e fazer correndo, e cortar escopo certo

O projeto andou rapido nao porque eu fiz tudo de qualquer jeito, mas porque houve foco no que precisava existir primeiro. O que deu velocidade foi priorizacao, nao improviso.

### 2. Interface operacional precisa mostrar proxima acao, nao apenas estado

Isso ficou muito evidente para mim nas telas de alunos, financeiro e grade. Uma tela so com lista e numero ajuda menos do que uma tela que indica o que precisa ser feito agora.

### 3. Quando a tela cresce, a arquitetura por responsabilidade vira obrigatoria

Na grade de aulas isso ficou muito claro. Sem separar dispatcher, commands, policy, messages e workflow, a view iria virar um bloco dificil de manter muito rapido.

### 4. Erro de produto tambem nasce em detalhe tecnico pequeno

Um exemplo concreto foi o bug dos limites da grade: a regra parecia correta, mas a contagem em lote estava somando o que ja estava salvo com contadores pendentes ao mesmo tempo. Esse tipo de detalhe me mostrou como uma tela pode parecer pronta e ainda assim quebrar comportamento real.

### 5. Comentario bom reduz custo de retorno ao codigo

Os cabecalhos e a organizacao por arquivo se provaram uteis porque o projeto foi evoluindo muito rapido. Sem isso, meu retorno posterior ao codigo ficaria mais caro e mais lento.

## Bugs e riscos importantes encontrados na V1

1. o planejador recorrente da grade bloqueava limites antes da hora por dupla contagem no lote
2. parte das telas tinha texto e copy inconsistentes entre template, view, query e teste
3. alguns templates usavam inline style com expressao do Django e geravam ruido desnecessario no editor
4. o README ficou para tras em alguns pontos da arquitetura e precisou ser realinhado depois da consolidacao da grade

## Trade-offs aceitos na V1

1. priorizar base funcional e coerente antes de cobertura exaustiva de todos os cenarios
2. manter parte do sistema ainda apoiada no admin enquanto as rotinas mais usadas ganhavam tela propria
3. aceitar uma primeira versao forte em operacao, mas ainda em lapidacao visual e documental fina

## O que eu faria diferente numa V2

1. consolidaria mais cedo um changelog ou diario de decisao de arquitetura
2. criaria mais testes de fronteira logo no momento em que cada fluxo fosse introduzido
3. reduziria ainda mais strings espalhadas cedo, principalmente em mensagens e copy operacional
4. adicionaria uma camada mais explicita de estados e eventos para a interface operar em cima de estruturas mais previsiveis

## O que vale preservar daqui para frente

1. organizacao por dominio e por responsabilidade
2. views finas com regra de negocio fora da camada HTTP
3. documentacao curta no topo dos arquivos relevantes
4. foco em fluxo operacional real em vez de painel genérico
5. testes cobrindo comportamento que ja causou bug ou risco real

## Proximos passos naturais

1. ampliar cobertura de testes em limites, bordas e acoes operacionais
2. continuar o refinamento visual das telas mantendo coerencia com o fluxo real
3. aprofundar relatorios e leituras gerenciais sem inflar a interface
4. expandir automacoes e comunicacoes sem perder rastreabilidade
5. preparar uma V2 com mais robustez de produto sem abandonar a simplicidade da operacao

## Conclusao

A V1 do OctoBox me provou que era possivel sair rapidamente de uma base inicial para um produto operacional serio, desde que o foco estivesse no problema certo: organizar a rotina real do box, e nao apenas exibir dados. O resultado nao foi um sistema terminado para sempre, mas uma fundacao funcional, legivel e pronta para evolucao com criterio.