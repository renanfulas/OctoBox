<!--
ARQUIVO: reporte da validacao posterior ao patch de responsividade do diretorio de alunos.

TIPO DE DOCUMENTO:
- snapshot operacional de validacao

AUTORIDADE:
- media para o fechamento complementar do beta

DOCUMENTO PAI:
- [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md)

QUANDO USAR:
- quando a duvida for se o patch aplicado ao diretorio de alunos removeu o overflow lateral em 320px

POR QUE ELE EXISTE:
- preserva a trilha entre o problema detectado e a comprovacao do conserto.
- evita que o board continue preso a um bloqueador que ja nao existe.

PONTOS CRITICOS:
- esta rodada valida apenas o diretorio de alunos apos o patch.
- ainda nao substitui a passada fisica com toque humano.
-->

# Reporte de validacao mobile - Onda 3.3 alunos apos patch

## Resumo executivo

Data:

1. 2026-03-28

Escopo:

1. revalidacao do diretorio de alunos apos o patch responsivo do cabecalho e da barra de filtros
2. browser-assisted em Microsoft Edge com engine real
3. larguras testadas: 320px, 390px e 430px

## Resultado objetivo

| Largura | pageScrollWidth | pageOverflow | scrollX apos arrasto | Status |
| --- | --- | --- | --- | --- |
| 320px | 320 | 0 | 0 | OK |
| 390px | 390 | 0 | 0 | OK |
| 430px | 430 | 0 | 0 | OK |

## Leitura tecnica

1. o cabecalho de acoes deixou de empurrar a pagina lateralmente
2. a barra de filtros e os pills passaram a quebrar sem estourar a viewport
3. o bloqueador de overflow lateral do diretorio de alunos foi removido

## Leitura pratica

1. antes, a estante era mais larga que a porta do quarto
2. agora, cada modulo dobra e entra pela porta sem raspar na parede

## Pendencias que continuam fora deste snapshot

1. validacao fisica com toque real continua pendente
2. autocomplete da busca global continua dependendo de dataset local com resultados
3. o pan lateral residual do shell continua sendo uma vigilancia separada do diretorio de alunos
