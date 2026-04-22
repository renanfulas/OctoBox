<!--
ARQUIVO: workflow de otimizacao sistemica para problemas complexos do OctoBOX.

POR QUE ELE EXISTE:
- transforma intuicao de performance em metodo tecnico e mensuravel.
- ajuda a escolher a alavanca certa entre banco, cache, fila, snapshot e processamento assincrono.

O QUE ESTE ARQUIVO FAZ:
1. define um workflow para diagnosticar gargalos com rigor.
2. evita usar Celery, cache ou banco como palavras magicas.
3. entrega um prompt pronto para investigar e propor ganhos reais.

PONTOS CRITICOS:
- Celery nao acelera consulta ao banco por magia.
- performance boa nasce de modelo, medicao e escolha certa da alavanca.
-->

# Workflow G.E.N.I.O.

`G.E.N.I.O.` significa:

- `G` Geometrizar o sistema
- `E` Evidenciar o gargalo
- `N` Nomear a alavanca dominante
- `I` Intervir no menor ponto de maior impacto
- `O` Operar, observar e otimizar

Esse workflow existe para quando voce estiver olhando um problema e pensando:

- "isso esta pesado"
- "acho que Celery ajudaria"
- "talvez cache resolva"
- "o banco esta procurando dado um a um"

A resposta profissional nao e escolher uma palavra bonita.
A resposta profissional e modelar o problema como custo, fluxo, latencia, concorrencia e repeticao.

## Regra de ouro

Celery nao faz o banco "achar mais rapido".

Celery faz outra coisa:

- tira trabalho pesado da requisicao HTTP
- executa em background
- permite fila, retry, prioridade e desacoplamento

Se o banco esta lento, as alavancas mais comuns sao:

- indice
- query melhor
- `select_related` ou `prefetch_related`
- batch
- cache
- snapshot materializado
- menos round trips
- menos recalculo

## Quando usar

Use este workflow para:

- lentidao de dashboard
- fila pesada
- leitura repetitiva de dados
- jobs caros
- gargalo em exportacao
- integracao pesada
- necessidade de decidir entre cache, Celery, banco ou snapshot

## Workflow na pratica

### G. Geometrizar o sistema

Primeiro voce desenha a forma do problema.

Pergunte:

- qual fluxo esta lento?
- quem chama isso?
- quantas vezes por minuto ou por hora?
- quantos registros entram na jogada?
- quanto tempo isso leva hoje?
- quanto deveria levar?
- o custo esta em CPU, IO, banco, rede ou serializacao?

Sem isso, voce esta tentando consertar um carro no escuro.

### E. Evidenciar o gargalo

Agora voce troca intuicao por prova.

Procure:

- contagem de queries
- tempo por query
- `EXPLAIN`
- picos de CPU
- hit rate de cache
- tempo de fila
- tempo de execucao do job
- fan-out de chamadas
- trechos com loop e consulta um a um

Se nao houver evidencia, a resposta certa e: ainda estamos no campo da hipotese.

### N. Nomear a alavanca dominante

Escolha a alavanca principal.

Use esta tabela mental:

| Sinal dominante | Alavanca mais provavel |
| --- | --- |
| muitos acessos repetindo a mesma leitura | cache |
| request HTTP carregando trabalho pesado que pode esperar | Celery |
| loop gerando consulta por item | batch ou prefetch |
| consulta unica lenta por filtro ou join | indice ou rewrite de query |
| dashboard recalculando agregados caros toda hora | snapshot ou materializacao |
| fila acumulando porque job e grande demais | dividir job, chunking ou prioridade |
| banco sofrendo com volume historico | arquivamento, particionamento ou snapshot |

Nomear a alavanca errada e como tentar cortar madeira com martelo.

### I. Intervir no menor ponto de maior impacto

Agora sim voce escolhe a menor mudanca com maior retorno.

Pergunte:

- qual corte da o maior ganho sem reescrever tudo?
- consigo atacar 80 por cento do custo com 20 por cento de mudanca?
- essa mudanca e reversivel?
- ela aumenta ou reduz debito tecnico?
- o ganho e real para o usuario ou so interno?

Priorize:

- indice antes de arquitetura espacial
- cache antes de reescrever modulo inteiro
- batch antes de paralelizar tudo
- snapshot antes de recalcular a mesma montanha toda hora

### O. Operar, observar e otimizar

Depois da intervencao, compare antes e depois.

Meca:

- latencia
- contagem de queries
- custo do job
- tamanho da fila
- hit rate de cache
- p95 e p99
- uso de CPU e RAM

Se nao melhorou no numero, voce nao otimizou. Voce so mexeu.

## Prompt pronto para colar

```md
Voce vai atuar como engenheiro de otimizacao sistemica do OctoBOX.

Seu papel e combinar pensamento matematico, engenharia de sistemas e rigor de evidencia para identificar a alavanca correta de eficiencia.

Nao trate Celery, cache, banco ou arquitetura como palavras magicas.
Modele o problema, prove o gargalo e escolha a menor intervencao de maior impacto.

Use o workflow G.E.N.I.O:
- Geometrizar o sistema
- Evidenciar o gargalo
- Nomear a alavanca dominante
- Intervir no menor ponto de maior impacto
- Operar, observar e otimizar

Regras:
- responda em Portugues do Brasil
- pense no contexto real do OctoBOX
- separe sintoma, causa raiz, estrategia e implementacao
- nao invente evidencia
- cite arquivos e linhas quando houver
- diga claramente se o problema parece de banco, cache, serializacao, fila, CPU, IO ou desenho de fluxo

Entregue a resposta exatamente nesta ordem:

1. `Leitura do problema`
2. `Modelo matematico simples do custo atual`
3. `Gargalo dominante`
4. `Alavanca recomendada`
5. `Por que as outras alavancas nao sao a primeira melhor resposta`
6. `Menor intervencao de maior impacto`
7. `Arquivos e areas provaveis`
8. `Riscos e tradeoffs`
9. `Plano de validacao`
10. `Metricas antes e depois`

Minha descricao:
[cole aqui]

Arquivos suspeitos:
[cole aqui]

Fluxo afetado:
[cole aqui]

Restricoes:
[cole aqui]
```

## Exemplo mental: Celery, cache e banco

Se voce disser:

- "quero mexer no Celery para o banco achar mais rapido"

o workflow deve te corrigir com elegancia:

- talvez o problema nao seja Celery
- talvez o problema seja query um a um
- talvez o problema seja falta de snapshot
- talvez o problema seja leitura repetida sem cache
- talvez o problema seja trabalho caro dentro do request

Ou seja:

- Celery entra se o trabalho pode sair do caminho do usuario
- cache entra se a resposta se repete muito
- banco entra se a busca esta mal desenhada
- snapshot entra se o sistema recalcula demais

## Como encaixar no seu sistema de prompts

Use assim:

1. ideia nebulosa -> `prompts/corda-diagnostico.md`
2. estruturacao rapida -> `prompts/corda-fast.md`
3. prompt completo -> `prompts/corda.md`
4. decisao de eficiencia -> este workflow
5. execucao especializada -> `architecture`, `debug`, `refactor` ou `research`

## Regra final

Genialidade util em engenharia nao e inventar magia.
E ver o gargalo certo, aplicar a alavanca certa e provar o ganho com numero.
