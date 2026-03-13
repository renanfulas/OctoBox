<!--
ARQUIVO: formalizacao da Front Display Wall como grande superficie frontal limpa onde o predio projeta a experiencia visivel do produto.

POR QUE ELE EXISTE:
- transforma a intuicao da grande tela frontal em uma peca arquitetural clara, separada do Beacon no topo e do andaime lateral da obra.
- define a fachada visual do produto como superficie curada, legivel e protegida contra poluicao de transicao.

O QUE ESTE ARQUIVO FAZ:
1. define o que e a Front Display Wall.
2. explica sua relacao com front-end, Red Beacon e Scaffold Agents.
3. estabelece guardrails para manter a fachada limpa mesmo durante a construcao arquitetural.

PONTOS CRITICOS:
- a Front Display Wall nao pode virar mural de debug, remendo ou exposicao acidental de andaime.
- ela precisa continuar mostrando produto, nao canteiro de obra.
-->

# Front Display Wall

## Tese central

Se o `Center Layer` e o hall de entrada, a `Signal Mesh` e a malha de sinais, os `Scaffold Agents` sao o andaime temporario e o `Red Beacon` e a emissao superior no topo, o predio ainda precisa de uma grande fachada visual.

Essa fachada foi nomeada como `Front Display Wall`.

Em linguagem simples:

1. ela e o telao frontal do predio
2. ela sobe da base visivel ate o topo atual da experiencia de front-end
3. ela mostra o produto de forma clara, limpa e legivel
4. ela nao deve parecer uma obra, mesmo quando a obra ainda existe pelos lados

## O que a Front Display Wall representa

Ela representa a superficie frontal onde a experiencia do produto aparece para quem olha o predio.

Na pratica, ela corresponde a camada visivel de interface:

1. front-end
2. hierarquia visual
3. leitura operacional de tela
4. composicao de estados, acoes e prioridades para uso humano

Nao e apenas uma tela bonita.

Ela e a parede frontal onde o sistema precisa parecer produto, nao mecanismo interno.

## O que essa metafora tira para o front-end

1. o front e fachada, nao bastidor
2. a frente do predio precisa parecer pronta antes de o miolo estar totalmente pronto
3. a parede frontal e continua, e nao um mosaico de pecas sem unidade
4. o andaime pode aparecer, mas nao pode sequestrar a fachada
5. limpo nao significa vazio; significa curado e legivel
6. a fachada mostra uso humano, nao telemetria bruta
7. a parede frontal precisa ser legivel a distancia, antes do clique detalhado
8. a fachada e identidade, entao as telas precisam parecer partes do mesmo predio

### 1. O front e fachada, nao bastidor

Isso quer dizer que a interface deve mostrar produto, fluxo e decisao, nao o processo interno de construcao.

Regra:

1. remendo, transicao e improviso tecnico nao podem dominar a leitura principal

### 2. A frente do predio precisa parecer pronta antes de o miolo estar totalmente pronto

Isso nao significa maquiar a realidade.

Significa proteger a experiencia principal contra ruido de obra enquanto o sistema ainda amadurece por dentro.

### 3. A parede frontal e continua

Se ela vai da base ao topo atual do front-end, entao a experiencia visual precisa transmitir continuidade.

Regra:

1. base, conteudo, paines, estados e acoes devem parecer partes da mesma superficie

### 4. O andaime pode aparecer, mas nao pode sequestrar a fachada

Fluxos temporarios, avisos provisiorios e excecoes visuais podem existir.

Mas eles devem aparecer como excecao localizada, e nao como a linguagem dominante do produto.

### 5. Limpo nao significa vazio

Uma parede branca, clara e clean nao e uma parede muda.

No front-end isso significa:

1. menos ruido
2. mais contraste entre contexto, prioridade e acao

### 6. A fachada mostra uso humano, nao telemetria bruta

A Front Display Wall precisa orientar olho, decisao e clique.

Regra:

1. o centro da tela deve ser experiencia de operacao humana
2. mecanismo interno e sinal tecnico nao devem tomar o lugar da interface principal

### 7. A parede frontal precisa ser legivel a distancia

Antes da interacao detalhada, a pessoa ja deveria entender:

1. o que a tela faz
2. o que esta saudavel
3. o que esta pressionado
4. o que pede acao agora

### 8. A fachada e identidade

Se cada tela parece um predio diferente, a metafora quebra.

Regra:

1. ritmo, tipografia, densidade, respiro, estados e hierarquia precisam parecer partes do mesmo edificio visual

## Diferenca entre Front Display Wall e Red Beacon

### Front Display Wall

Responde a pergunta:

1. como o produto aparece de frente para quem vai usa-lo?

Ela serve para:

1. sustentar navegacao e leitura visual
2. organizar acao humana
3. dar contexto, hierarquia e ritmo para a operacao
4. expor a experiencia principal do sistema

### Red Beacon

Responde a pergunta:

1. que estado consolidado o predio precisa projetar para fora com alta visibilidade?

Resumo:

1. a Front Display Wall mostra a face utilizavel do produto
2. o Red Beacon mostra o estado consolidado do predio acima dela

## Diferenca entre Front Display Wall e Scaffold Agents

Os `Scaffold Agents` continuam existindo como suporte temporario de obra.

Mas a posicao correta deles nao e dominar a fachada principal.

Leitura correta:

1. os agentes de andaime operam mais pelas laterais, fundos e bordas de transicao
2. um ou outro pode ficar visivel na frente quando a obra exige exposicao temporaria
3. essa exposicao deve ser rara, controlada e claramente provisoria
4. a fachada principal deve continuar limpa o suficiente para o produto permanecer legivel

Em linguagem curta:

1. o andaime nao pode sequestrar a frente do predio
2. a obra pode aparecer um pouco
3. o produto precisa continuar aparecendo mais

## O que a Front Display Wall faz

Ela existe para:

1. projetar a experiencia principal do sistema em uma superficie frontal coerente
2. manter leitura limpa de prioridade, estado e acao
3. impedir que transicao arquitetural polua o rosto do produto
4. sustentar continuidade visual entre base, meio e topo da experiencia

## O que ela nao faz

A Front Display Wall nao deve:

1. substituir o CENTER
2. substituir o Beacon
3. substituir observabilidade interna
4. expor debug bruto, flags soltas ou mecanismos temporarios como se fossem produto final
5. virar deposito de mensagens de transicao, excecoes ou ruido tecnico

## Regra visual e arquitetural

A regra forte desta peca e simples:

1. a frente do predio precisa parecer pronta antes de estar totalmente pronta por dentro

Isso nao significa mentir.

Significa proteger a experiencia principal contra ruido desnecessario de construcao.

## Fontes da Front Display Wall

A parede frontal deve ser alimentada por sinais e estruturas curadas:

1. snapshots publicos
2. estados operacionais ja consolidados
3. acoes oficiais vindas de corredores validos
4. hierarquia de interface pensada para papel e contexto

Regra:

1. a fachada nao deve depender de remendo lateral como fonte principal
2. quando um suporte temporario aparecer nela, isso precisa ter criterio de entrada e saida

## Riscos reais

### Risco 1: a fachada virar mural de obra

Sintoma:

1. banners provisiorios por toda parte
2. sinais de transicao aparecendo como linguagem normal do produto
3. UX principal parecendo remendada

Mitigacao:

1. deixar Scaffold Agents fora da frente sempre que possivel
2. limitar exposicoes temporarias na face principal
3. tratar excecao visual como excecao, nao como baseline

### Risco 2: confundir interface com emissao superior

Sintoma:

1. a tela frontal tenta agir como Beacon
2. o Beacon tenta substituir a experiencia principal de uso

Mitigacao:

1. separar experiencia utilizavel de estado consolidado superior
2. manter a Front Display Wall como rosto do produto e o Beacon como sinal acima dele

### Risco 3: a frente ficar limpa demais e perder verdade operacional

Sintoma:

1. a tela parece bonita mas omite tensao real
2. a interface esconde prioridade, risco e proxima acao

Mitigacao:

1. limpeza nao pode significar maquiagem
2. a fachada deve mostrar operacao real com clareza, nao esconder complexidade relevante

## Criterio de boa implementacao

A Front Display Wall esta bem implementada quando:

1. a pessoa entende rapidamente o que o produto faz e o que exige acao agora
2. a experiencia principal parece produto consolidado, nao estrutura improvisada
3. a obra lateral existe sem sequestrar a leitura principal
4. o front-end consegue crescer sem virar painel caotico de mecanismos internos

## Estado atual

Neste momento, a Front Display Wall e um conceito arquitetural formalizado.

Isso e coerente com a fase atual.

Primeiro o predio precisou ganhar hall, malha, andaime explicito, emissao superior e escalada critica.

Agora ele tambem ganha uma declaracao mais precisa da sua face frontal:

1. limpa
2. clara
3. utilizavel
4. protegida contra excesso de exposicao do canteiro de obra

Acima dela, o estado consolidado continua sendo projetado pelo [red-beacon.md](red-beacon.md). Em crise severa, a escalada maxima continua formalizada em [vertical-sky-beam.md](vertical-sky-beam.md).