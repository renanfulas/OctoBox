<!--
ARQUIVO: snapshot browser-assisted da passada mobile no perfil de iPhone 13.

TIPO DE DOCUMENTO:
- snapshot operacional de validacao

AUTORIDADE:
- media para o fechamento complementar do beta

DOCUMENTO PAI:
- [../plans/front-beta-closure-board.md](../plans/front-beta-closure-board.md)

QUANDO USAR:
- quando a duvida for como as superficies centrais se comportaram no perfil de iPhone 13

POR QUE ELE EXISTE:
- registra uma rodada por perfil de aparelho, nao so por faixa generica de viewport.
- ajuda a separar o que ja ficou comprovado em iPhone 13 do que ainda depende de toque fisico real.

PONTOS CRITICOS:
- esta rodada foi browser-assisted com perfil de iPhone 13, nao execucao em aparelho fisico.
- o engine usado foi Chromium via Edge, com viewport e comportamento mobile equivalentes ao perfil do iPhone 13.
-->

# Reporte de validacao mobile - iPhone 13 browser-assisted

## Resumo executivo

Data:

1. 2026-03-29

Perfil:

1. `iPhone 13`
2. viewport observada: `390 x 664`
3. browser-assisted com touch/mobile profile habilitado

## Resultado por superficie

| Superficie | Status | Evidencia curta |
| --- | --- | --- |
| Login | OK | campos e submit visiveis, overflow 0 |
| Dashboard e shell | OK | toggle visivel, menu abre e fecha, overflow 0 |
| Busca global | Toleravel | campo visivel, mas autocomplete local retornou 0 resultados |
| Recepcao | OK | overflow 0 e acoes principais visiveis |
| Alunos | OK | overflow 0, filtros visiveis e abertura da ficha funcionando |
| Ficha leve | OK | abas visiveis, inputs renderizados e overflow 0 |

## Evidencia tecnica

1. `login`: `pageOverflow=0`, campos visiveis, submit visivel
2. `dashboard`: `pageOverflow=0`, `sidebarToggleVisible=true`, `sidebarOpenAfterTap=true`, `sidebarClosedAfterEscape=true`
3. `busca global`: campo visivel, mas `searchFetch.count=0` para `Renan` no dataset local
4. `recepcao`: `pageOverflow=0`, acoes principais renderizadas
5. `alunos`: `pageOverflow=0`, 4 pills de filtro visiveis, abertura da ficha em `/alunos/1/editar/#student-financial-overview`
6. `ficha leve`: `pageOverflow=0`, abas essencial e financeira visiveis, primeiro input visivel

## Leitura pratica

1. no perfil de iPhone 13, a casa esta caminhavel
2. o dedo consegue abrir a porta do menu e entrar na ficha do aluno sem a tela escapar para o lado
3. o ponto menos provado continua sendo a busca com resultados reais, nao a estrutura visual

## Pendencia que continua de pe

1. confirmar toque fisico em aparelho real
2. validar autocomplete com dataset local que realmente devolva resultados
