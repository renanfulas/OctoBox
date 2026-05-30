<!--
ARQUIVO: rodada consolidada de validacao browser-assisted apos os patches de alunos e shell.

TIPO DE DOCUMENTO:
- snapshot operacional de validacao

AUTORIDADE:
- media para o fechamento complementar do beta

DOCUMENTO PAI:
- [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md)

QUANDO USAR:
- quando a duvida for o estado consolidado de overflow horizontal nas superficies mobile centrais apos os patches finais

POR QUE ELE EXISTE:
- junta em um unico snapshot a fotografia atual de login, dashboard, recepcao e alunos.
- evita depender de varias rodadas antigas para responder se o front ainda escorrega lateralmente no mobile.

PONTOS CRITICOS:
- esta rodada continua sendo browser-assisted, nao toque fisico em aparelho real.
- autocomplete da busca global continua fora do escopo porque o dataset local nao devolveu resultados.
-->

# Reporte de validacao mobile - Onda 3.4 consolidada

## Resumo executivo

Data:

1. 2026-03-29

Escopo:

1. revalidacao consolidada de `login`, `dashboard`, `recepcao` e `alunos`
2. browser-assisted em Microsoft Edge com engine real
3. larguras testadas: `320px`, `390px` e `430px`

## Resultado objetivo

| Superficie | 320px | 390px | 430px | Status |
| --- | --- | --- | --- | --- |
| Login | overflow 0 | overflow 0 | overflow 0 | OK |
| Dashboard | overflow 0 | overflow 0 | overflow 0 | OK |
| Recepcao | overflow 0 | overflow 0 | overflow 0 | OK |
| Alunos | overflow 0 | overflow 0 | overflow 0 | OK |

## Leitura tecnica

1. o patch responsivo de alunos removeu o vazamento lateral do cabecalho e da barra de filtros
2. o patch de contenção na raiz do shell removeu o pan lateral residual do dashboard
3. nas quatro superficies auditadas, `pageScrollWidth` ficou igual a largura da viewport e `scrollXAfter` permaneceu `0`

## Leitura pratica

1. agora as portas principais da casa estao na largura certa
2. a pessoa consegue andar no corredor sem a parede deslizar para o lado

## Pendencias que continuam fora deste snapshot

1. validacao fisica com toque humano continua pendente
2. autocomplete da busca global continua precisando de dataset local com resultados reais
3. observacao de densidade, leitura e uso corrido continua mais importante que overflow horizontal neste momento
