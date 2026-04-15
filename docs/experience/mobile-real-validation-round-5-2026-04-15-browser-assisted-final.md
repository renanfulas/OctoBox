<!--
ARQUIVO: rodada final browser-assisted apos as ondas de responsividade mobile.

TIPO DE DOCUMENTO:
- snapshot operacional de validacao

AUTORIDADE:
- media para fechamento complementar do beta assistido

DOCUMENTO PAI:
- [mobile-real-validation-checklist.md](mobile-real-validation-checklist.md)

QUANDO USAR:
- quando a duvida for o estado consolidado das principais rotas mobile apos shell, alunos, financeiro, ficha, grade e recepcao

POR QUE ELE EXISTE:
- fecha a trilha de validacao browser-assisted das ondas 1 a 5
- registra o que esta ok, o que continua toleravel e o que ainda depende de dedo humano em aparelho real

PONTOS CRITICOS:
- este snapshot nao substitui o teste fisico real em iPhone ou Android
- aqui o foco e estabilidade estrutural em viewport estreita, nao sensacao subjetiva de uso
-->

# Reporte final de validacao mobile - Onda 5

## Resumo executivo

Data:

1. 2026-04-15

Escopo:

1. validacao consolidada browser-assisted em `320px`, `390px` e `430px`
2. rotas auditadas: `login`, `dashboard`, `alunos`, `ficha do aluno`, `financeiro`, `grade de aulas` e `recepcao`
3. fechamento das ondas de responsividade e hardening final

## Resultado objetivo

| Superficie | 320px | 390px | 430px | Status |
| --- | --- | --- | --- | --- |
| Login | overflow 0 | overflow 0 | overflow 0 | OK |
| Dashboard | overflow 0 | overflow 0 | overflow 0 | OK |
| Diretorio de alunos | overflow 0 | overflow 0 | overflow 0 | Toleravel |
| Ficha do aluno | overflow 0 | overflow 0 | overflow 0 | OK |
| Financeiro | overflow 0 | overflow 0 | overflow 0 | OK |
| Grade de aulas | overflow 0 | overflow 0 | overflow 0 | OK |
| Recepcao | overflow 0 | overflow 0 | overflow 0 | OK |

## Evidencias curtas por superficie

Shell global autenticado:

1. status: ok
2. largura ou aparelho: `390px` browser-assisted
3. evidencia: `scrollWidth = 390`; topbar consolidada em `266.39px`; quick links e alert chips contidos em `336px`
4. observacao: nao houve nova sobreposicao estrutural entre topbar e conteudo

Login e busca global:

1. status: ok
2. largura ou aparelho: `320px`, `390px`, `430px`
3. evidencia: login sem overflow em todas as larguras; CTA de submit manteve largura util e sem compressao critica
4. observacao: autocomplete da busca global continua dependendo de dataset local com retorno real para prova funcional completa

Recepcao:

1. status: ok
2. largura ou aparelho: `390px` browser-assisted
3. evidencia: `scrollWidth = 390`; fila de intake virou cards mobile; labels `Contato`, `Origem`, `Status` e `Proximo passo` renderizaram corretamente
4. observacao: o balcao ficou legivel sem depender de scroll lateral bruto

Diretorio de alunos:

1. status: toleravel
2. largura ou aparelho: `320px`, `390px`, `430px`
3. evidencia: `scrollWidth` igual a viewport nas tres larguras; listagem abre sem vazamento lateral
4. observacao: os cards da tabela mobile continuam altos e densos; nao bloqueia uso, mas ainda pede polimento futuro de condensacao de conteudo

Ficha leve do aluno:

1. status: ok
2. largura ou aparelho: `390px` browser-assisted
3. evidencia: tabs empilhados em coluna unica; workspace financeiro presente e sem overflow horizontal
4. observacao: hierarquia geral ficou previsivel para toque, com densidade mais curta nos paineis financeiros

Financeiro:

1. status: ok
2. largura ou aparelho: `320px`, `390px`, `430px`
3. evidencia: KPIs empilhados em coluna unica no mobile estreito; `scrollWidth` igual a viewport nas tres larguras
4. observacao: a leitura ficou muito mais segura; o que sobrou e ajuste fino de conforto, nao quebra estrutural

Grade de aulas:

1. status: ok
2. largura ou aparelho: `390px` browser-assisted
3. evidencia: `scrollWidth = 390`; CTA do planejador ocupando largura util; badges e blocos do workspace sem vazar
4. observacao: a superficie continua densa por natureza, mas o fluxo principal ficou acionavel

## Leitura tecnica

1. o front mobile terminou esta rodada sem bloqueador estrutural novo de overflow horizontal nas rotas centrais
2. shell, financeiro, ficha, grade e recepcao fecharam em estado `ok` no recorte browser-assisted
3. o unico atrito residual com cara de backlog, nao de bloqueio, e a altura excessiva dos cards do diretorio de alunos em largura muito estreita

## Leitura pratica

1. as portas, corredores e escadas agora cabem na largura do celular sem a casa escorregar para o lado
2. o que ainda sobra e mais “peso da mochila” do que “porta emperrada”

## Fechamento da rodada

Resumo final curto:

1. superficies ok: `login`, `dashboard`, `recepcao`, `ficha do aluno`, `financeiro`, `grade de aulas`
2. superficies toleraveis: `alunos`
3. bloqueadores: nenhum bloqueador estrutural novo nesta rodada
4. prints ou videos coletados: nao
5. decisao: manter beta assistido e seguir para validacao fisica com toque humano

## Pendencias que continuam fora deste snapshot

1. teste fisico real em iPhone e Android continua sendo a confirmacao final
2. autocomplete da busca global ainda precisa de dataset local com resultados reais para validar toque ponta a ponta
3. condensacao visual dos cards do diretorio de alunos continua como oportunidade de refinamento, nao como bloqueador
