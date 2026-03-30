<!--
ARQUIVO: reporte da rodada browser-assisted externa de validacao mobile do front.

TIPO DE DOCUMENTO:
- snapshot operacional de validacao

AUTORIDADE:
- media para o fechamento complementar do beta

DOCUMENTO PAI:
- [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md)

QUANDO USAR:
- quando a duvida for o que aconteceu na rodada externa assistida em browser real nas larguras 320px, 390px e 430px

POR QUE ELE EXISTE:
- registra a evidencia objetiva da rodada feita fora do browser integrado.
- reduz memoria oral sobre o que realmente passou, tolerou ou ainda bloqueia no mobile.
- separa claramente browser-assisted de validacao fisica em aparelho real.

PONTOS CRITICOS:
- esta rodada usou engine real de browser, mas nao substitui toque humano em aparelho fisico.
- os resultados abaixo refletem o dataset local usado na sessao de validacao.
-->

# Reporte de validacao mobile - Onda 3.2 assistida

## Resumo executivo

Data:

1. 2026-03-28

Metodo:

1. validacao browser-assisted em Microsoft Edge com engine real
2. viewports testadas: 320px, 390px e 430px
3. servidor local autenticado com rota real por superficie
4. captura de metricas de overflow, scrollers locais e screenshots

Limite desta rodada:

1. nao houve toque em aparelho fisico
2. autocomplete da busca global ficou inconclusivo porque o dataset local devolveu lista vazia

## Janela de resultados

| Superficie | 320px | 390px | 430px | Leitura honesta |
| --- | --- | --- | --- | --- |
| Login | OK | OK | OK | Sem overflow de pagina e leitura estavel |
| Shell e dashboard | Toleravel | Toleravel | Toleravel | Pan lateral residual de ~24px ligado a geometria do sidebar oculto |
| Recepcao | OK | OK | OK | Sem overflow de pagina; scroll horizontal ficou contido dentro da tabela local |
| Diretorio de alunos | Bloqueador | Toleravel | Toleravel | Em 320px a faixa de acoes e filtros ainda empurra a pagina ~43px para a direita |
| Busca global | Toleravel | Toleravel | Toleravel | Campo e encaixe visual estaveis; autocomplete sem resultados reais nesta rodada |

## Evidencia tecnica por superficie

### 1. Login

Rotas:

1. `/login/`

Resultado:

1. `pageOverflow=0` em 320px, 390px e 430px
2. sem quebra visual relevante
3. superficie tratada como `ok`

Leitura pratica:

1. a porta de entrada ficou do tamanho certo para o celular passar sem raspar nas laterais

### 2. Shell global e dashboard

Rotas:

1. `/dashboard/`

Resultado:

1. `pageOverflow=24` em 320px, 390px e 430px
2. o pan lateral aparece mesmo com a tela visualmente estavel
3. os ofensores visiveis capturados pertencem ao `aside.sidebar` fora da area principal
4. superficie tratada como `toleravel`

Hipotese tecnica:

1. o sidebar off-canvas ainda participa da largura total da pagina, como um armario escondido atras da porta mas ainda ocupando espaco no corredor

Risco:

1. o usuario pode perceber um arrasto lateral curto se puxar a pagina no eixo X
2. nao houve colapso visual grave nas larguras testadas

### 3. Recepcao

Rotas:

1. `/operacao/recepcao/`

Resultado:

1. `pageOverflow=0` em 320px, 390px e 430px
2. a grade principal empilha corretamente
3. a tabela interna continua podendo rolar lateralmente, mas o scroll fica contido em `operation-table-wrap`
4. superficie tratada como `ok`

Leitura pratica:

1. a cozinha operacional deixou de travar a passagem do celular; agora o corredor principal ficou livre

### 4. Diretorio de alunos

Rotas:

1. `/alunos/`

Resultado:

1. em `320px`, `pageOverflow=43`
2. houve pan horizontal real da pagina em 320px
3. em `390px` e `430px`, `pageOverflow=0`
4. superficie tratada como `bloqueador em 320px` e `toleravel` nas demais larguras testadas

Ofensores reais em 320px:

1. faixa de acoes do cabecalho com `Importar CSV`, `Exportar CSV` e `+ Novo aluno`
2. faixa de filtros com o botao `Filtrar`

Leitura pratica:

1. os KPIs respiram melhor do que antes, mas a mesa de comando do diretorio ainda fica larga demais para um celular muito pequeno

### 5. Busca global

Rotas:

1. `/dashboard/` com busca global ativa

Resultado:

1. o campo de busca encaixou na viewport sem overflow
2. o dropdown nao chegou a abrir com resultados porque a rota `/api/v1/students/autocomplete/?query=Renan` devolveu `{"results": []}` no dataset local
3. superficie tratada como `toleravel` por falta de evidencia completa do autocomplete

Leitura pratica:

1. a moldura da busca esta no lugar certo, mas ainda faltou gente entrando na fila para provar o comportamento completo do dropdown

## Decisao operacional

Estado desta rodada:

1. login e recepcao passaram
2. shell e dashboard ficaram toleraveis com debito pequeno e conhecido
3. diretorio de alunos ainda pede ajuste final se o beta precisar abracar 320px como largura suportada
4. a validacao fisica com toque humano continua pendente

Recomendacao:

1. registrar beta assistido como pronto em desktop e nas larguras mobile mais comuns de 390px a 430px
2. tratar `alunos em 320px` como ultimo bloqueador mobile explicito
3. decidir se o pan lateral residual do shell entra como patch rapido agora ou como vigilancia aceita para o piloto
